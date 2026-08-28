-- =============================================================================
-- DraftAI — Dynamic AI Provider & Model Catalog
-- =============================================================================
--
-- DESIGN REVIEW (current → proposed)
-- ---------------------------------
-- Today:
--   • Provider enum (Postgres ALTER TYPE per new vendor) — not scalable
--   • Hardcoded PROVIDER_MODEL_OPTIONS in Python — requires deploy to add models
--   • ai_agent_config has N encrypted key columns (openai_*, gemini_*, …) — schema
--     migration for every new provider
--   • Fernet blob (no explicit IV column) — works but opaque for AES-256-GCM audit
--
-- Proposed (this file):
--   1. ai_provider  — vendor registry + per-user credential rows (BYOK)
--   2. ai_model     — model catalog linked to *system* provider rows
--
-- Provider rows come in two scopes (same table, no enum explosion):
--   • System catalog: user_id IS NULL, parent_provider_id IS NULL, secrets NULL
--   • User binding:   user_id NOT NULL, parent_provider_id → system row, optional
--                     api_key_* columns + optional base_url override (e.g. Ollama)
--
-- Models always reference system provider rows (enforced by FK + CHECK).
-- Adding OpenAI / Anthropic / Ollama = INSERT rows, not ALTER TYPE.
--
-- Encryption note:
--   Use AES-256-GCM. Store ciphertext, 12-byte IV/nonce, and 16-byte auth tag
--   separately. Application master key stays in CREDENTIALS_ENCRYPTION_KEY / KMS.
--   (Distinct from legacy Fernet columns on ai_agent_config during migration.)
--
-- Future (not in this file): slim ai_agent_config to FKs —
--   text_model_id → ai_model.id, cover_model_id → ai_model.id
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- 1. ai_provider
-- ---------------------------------------------------------------------------
CREATE TABLE ai_provider (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Scope: NULL = system catalog template; set = user-specific binding
    user_id             UUID REFERENCES "user" (id) ON DELETE CASCADE,
    parent_provider_id  UUID REFERENCES ai_provider (id) ON DELETE CASCADE,

    -- Identity (slug is stable API identifier: openai, anthropic, ollama, …)
    slug                VARCHAR(64)  NOT NULL,
    display_name        VARCHAR(128) NOT NULL,
    description         TEXT,

    -- Connectivity
    base_url            VARCHAR(2048) NOT NULL,
    api_adapter         VARCHAR(64)  NOT NULL,
    -- openai_compatible | anthropic_messages | gemini | ollama | custom

    auth_style          VARCHAR(32)  NOT NULL DEFAULT 'bearer',
    -- bearer | api_key_header | query_param | none

    auth_header_name    VARCHAR(64),
    -- e.g. Authorization, x-api-key, x-goog-api-key

    extra_headers       JSONB        NOT NULL DEFAULT '{}'::JSONB,

    -- AES-256-GCM secret material (populated on user binding rows only)
    api_key_ciphertext  BYTEA,
    api_key_iv          BYTEA,        -- 12-byte GCM nonce
    api_key_tag         BYTEA,        -- 16-byte GCM authentication tag

    is_active           BOOLEAN      NOT NULL DEFAULT TRUE,
    sort_order          SMALLINT     NOT NULL DEFAULT 0,

    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    -- System templates: unique slug globally
    CONSTRAINT ai_provider_system_slug_ck CHECK (
        (user_id IS NULL AND parent_provider_id IS NULL)
        OR (user_id IS NOT NULL AND parent_provider_id IS NOT NULL)
    ),

    -- User rows must not carry slug duplicates per parent
    CONSTRAINT ai_provider_user_parent_uniq UNIQUE (user_id, parent_provider_id),

    -- Secrets only on user rows; system rows must not store ciphertext
    CONSTRAINT ai_provider_secrets_scope_ck CHECK (
        (user_id IS NULL AND api_key_ciphertext IS NULL AND api_key_iv IS NULL AND api_key_tag IS NULL)
        OR (user_id IS NOT NULL)
    ),

    -- If ciphertext present, IV and tag are required
    CONSTRAINT ai_provider_secrets_complete_ck CHECK (
        (api_key_ciphertext IS NULL AND api_key_iv IS NULL AND api_key_tag IS NULL)
        OR (api_key_ciphertext IS NOT NULL AND api_key_iv IS NOT NULL AND api_key_tag IS NOT NULL)
    )
);

-- One slug per system provider
CREATE UNIQUE INDEX ai_provider_system_slug_uidx
    ON ai_provider (slug)
    WHERE user_id IS NULL;

CREATE INDEX ai_provider_user_id_idx
    ON ai_provider (user_id)
    WHERE user_id IS NOT NULL;

CREATE INDEX ai_provider_parent_id_idx
    ON ai_provider (parent_provider_id)
    WHERE parent_provider_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- 2. ai_model
-- ---------------------------------------------------------------------------
CREATE TYPE ai_model_modality AS ENUM (
    'text',
    'image',
    'embedding',
    'multimodal'
);

CREATE TABLE ai_model (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- FK to *system* provider row only (see CHECK below)
    provider_id             UUID NOT NULL REFERENCES ai_provider (id) ON DELETE RESTRICT,

    -- Provider-native model identifier (gpt-4o, claude-3-5-sonnet-20241022, …)
    model_key               VARCHAR(256) NOT NULL,

    display_name            VARCHAR(128) NOT NULL,
    description             TEXT,

    modality                ai_model_modality NOT NULL DEFAULT 'text',

    context_window_tokens   INTEGER,
    max_output_tokens       INTEGER,

    -- USD per 1M tokens (NULL = unknown / local / free)
    input_cost_per_million  NUMERIC(12, 6),
    output_cost_per_million NUMERIC(12, 6),

    -- Flexible capability flags without schema changes
    -- e.g. {"json_mode": true, "vision": true, "tools": true, "reasoning": false}
    capabilities            JSONB NOT NULL DEFAULT '{}'::JSONB,

    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    is_default              BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order              SMALLINT NOT NULL DEFAULT 0,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ai_model_provider_model_key_uniq UNIQUE (provider_id, model_key),

    CONSTRAINT ai_model_costs_non_negative_ck CHECK (
        (input_cost_per_million IS NULL OR input_cost_per_million >= 0)
        AND (output_cost_per_million IS NULL OR output_cost_per_million >= 0)
    ),

    CONSTRAINT ai_model_context_positive_ck CHECK (
        (context_window_tokens IS NULL OR context_window_tokens > 0)
        AND (max_output_tokens IS NULL OR max_output_tokens > 0)
    )
);

-- Only one default text model per provider (partial unique index)
CREATE UNIQUE INDEX ai_model_one_default_per_provider_uidx
    ON ai_model (provider_id)
    WHERE is_default = TRUE AND modality = 'text';

CREATE INDEX ai_model_provider_modality_idx
    ON ai_model (provider_id, modality)
    WHERE is_active = TRUE;

CREATE INDEX ai_model_capabilities_gin_idx
    ON ai_model USING GIN (capabilities);

-- Enforce: models link to system catalog providers only
CREATE OR REPLACE FUNCTION ai_model_provider_must_be_system()
RETURNS TRIGGER AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM ai_provider p
        WHERE p.id = NEW.provider_id
          AND p.user_id IS NULL
          AND p.parent_provider_id IS NULL
    ) THEN
        RAISE EXCEPTION 'ai_model.provider_id must reference a system catalog provider row';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ai_model_provider_system_trg
    BEFORE INSERT OR UPDATE OF provider_id ON ai_model
    FOR EACH ROW
    EXECUTE FUNCTION ai_model_provider_must_be_system();

-- ---------------------------------------------------------------------------
-- updated_at triggers (optional convenience)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ai_provider_updated_at_trg
    BEFORE UPDATE ON ai_provider
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER ai_model_updated_at_trg
    BEFORE UPDATE ON ai_model
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- Seed: system providers (idempotent via slug)
-- ---------------------------------------------------------------------------
INSERT INTO ai_provider (slug, display_name, description, base_url, api_adapter, auth_style, auth_header_name, sort_order)
SELECT v.slug, v.display_name, v.description, v.base_url, v.api_adapter, v.auth_style, v.auth_header_name, v.sort_order
FROM (VALUES
    ('openai', 'OpenAI', 'GPT and DALL-E APIs', 'https://api.openai.com/v1', 'openai_compatible', 'bearer', 'Authorization', 10),
    ('anthropic', 'Anthropic', 'Claude Messages API', 'https://api.anthropic.com/v1', 'anthropic_messages', 'api_key_header', 'x-api-key', 20),
    ('gemini', 'Google Gemini', 'Gemini generative language API', 'https://generativelanguage.googleapis.com/v1beta', 'gemini', 'query_param', NULL, 30),
    ('groq', 'Groq', 'Groq OpenAI-compatible inference', 'https://api.groq.com/openai/v1', 'openai_compatible', 'bearer', 'Authorization', 40),
    ('openrouter', 'OpenRouter', 'Multi-model OpenAI-compatible router', 'https://openrouter.ai/api/v1', 'openai_compatible', 'bearer', 'Authorization', 50),
    ('ollama', 'Ollama (local)', 'Local Ollama OpenAI-compatible server', 'http://localhost:11434/v1', 'openai_compatible', 'bearer', 'Authorization', 60)
) AS v(slug, display_name, description, base_url, api_adapter, auth_style, auth_header_name, sort_order)
WHERE NOT EXISTS (
    SELECT 1 FROM ai_provider p WHERE p.slug = v.slug AND p.user_id IS NULL
);

-- ---------------------------------------------------------------------------
-- Seed: models (sample — extend via INSERT without DDL changes)
-- ---------------------------------------------------------------------------
INSERT INTO ai_model (provider_id, model_key, display_name, description, modality, context_window_tokens, input_cost_per_million, output_cost_per_million, capabilities, is_default, sort_order)
SELECT p.id, m.model_key, m.display_name, m.description, m.modality::ai_model_modality, m.context_window, m.input_cost, m.output_cost, m.capabilities::JSONB, m.is_default, m.sort_order
FROM ai_provider p
JOIN (VALUES
    -- OpenAI text
    ('openai', 'gpt-4o', 'GPT-4o', 'Best overall quality', 'text', 128000, 2.50, 10.00, '{"json_mode": true, "vision": true, "tools": true}', TRUE, 10),
    ('openai', 'gpt-4o-mini', 'GPT-4o mini', 'Fast and cost-effective', 'text', 128000, 0.15, 0.60, '{"json_mode": true, "vision": true, "tools": true}', FALSE, 20),
    ('openai', 'gpt-4.1', 'GPT-4.1', 'Latest flagship', 'text', 128000, NULL, NULL, '{"json_mode": true, "tools": true}', FALSE, 30),
    -- OpenAI image
    ('openai', 'dall-e-3', 'DALL-E 3', 'Widescreen cover images', 'image', NULL, NULL, NULL, '{"aspect_ratios": ["1792x1024"]}', FALSE, 10),
    -- Anthropic
    ('anthropic', 'claude-3-5-sonnet-20241022', 'Claude 3.5 Sonnet', 'Balanced quality and speed', 'text', 200000, 3.00, 15.00, '{"json_mode": true, "vision": true, "tools": true}', TRUE, 10),
    ('anthropic', 'claude-3-5-haiku-20241022', 'Claude 3.5 Haiku', 'Fast and economical', 'text', 200000, 0.80, 4.00, '{"json_mode": true, "vision": true}', FALSE, 20),
    -- Gemini text
    ('gemini', 'gemini-2.0-flash', 'Gemini 2.0 Flash', 'Default fast multimodal', 'text', 1000000, NULL, NULL, '{"json_mode": true, "vision": true}', TRUE, 10),
    ('gemini', 'gemini-2.5-pro', 'Gemini 2.5 Pro', 'Complex writing', 'text', 1000000, NULL, NULL, '{"json_mode": true, "vision": true, "tools": true}', FALSE, 20),
    -- Gemini image
    ('gemini', 'gemini-3-pro-image', 'Gemini 3 Pro Image', 'Nano Banana Pro covers', 'image', NULL, NULL, NULL, '{"aspect_ratios": ["16:9"]}', TRUE, 10),
    ('gemini', 'gemini-3.1-flash-image', 'Gemini 3.1 Flash Image', 'Fast image generation', 'image', NULL, NULL, NULL, '{"aspect_ratios": ["16:9"]}', FALSE, 20),
    ('gemini', 'gemini-2.5-flash-image', 'Gemini 2.5 Flash Image', 'Efficient images', 'image', NULL, NULL, NULL, '{"aspect_ratios": ["16:9"]}', FALSE, 30),
    -- Groq
    ('groq', 'llama-3.3-70b-versatile', 'Llama 3.3 70B', 'Versatile open model', 'text', 128000, NULL, NULL, '{"json_mode": true}', TRUE, 10),
    -- OpenRouter (free tier examples)
    ('openrouter', 'meta-llama/llama-3.3-70b-instruct:free', 'Llama 3.3 70B (free)', 'Default free tier', 'text', 128000, 0, 0, '{"json_mode": true}', TRUE, 10),
    -- Ollama (local — costs NULL)
    ('ollama', 'llama3.2', 'Llama 3.2', 'Local default', 'text', 128000, NULL, NULL, '{}', TRUE, 10)
) AS m(provider_slug, model_key, display_name, description, modality, context_window, input_cost, output_cost, capabilities, is_default, sort_order)
    ON p.slug = m.provider_slug AND p.user_id IS NULL
WHERE NOT EXISTS (
    SELECT 1 FROM ai_model existing
    WHERE existing.provider_id = p.id AND existing.model_key = m.model_key
);

COMMIT;

-- ---------------------------------------------------------------------------
-- Example: user BYOK row (application layer encrypts with AES-256-GCM)
-- ---------------------------------------------------------------------------
-- INSERT INTO ai_provider (
--     user_id, parent_provider_id, slug, display_name, base_url, api_adapter,
--     auth_style, auth_header_name,
--     api_key_ciphertext, api_key_iv, api_key_tag
-- )
-- SELECT
--     :user_id,
--     p.id,
--     p.slug,
--     p.display_name,
--     p.base_url,           -- or override: 'http://host.docker.internal:11434/v1' for Ollama
--     p.api_adapter,
--     p.auth_style,
--     p.auth_header_name,
--     :ciphertext, :iv, :tag
-- FROM ai_provider p
-- WHERE p.slug = 'gemini' AND p.user_id IS NULL;

-- ---------------------------------------------------------------------------
-- Example: resolve user model for generation
-- ---------------------------------------------------------------------------
-- SELECT m.*, COALESCE(up.base_url, sp.base_url) AS base_url, up.api_key_ciphertext, …
-- FROM ai_model m
-- JOIN ai_provider sp ON sp.id = m.provider_id
-- LEFT JOIN ai_provider up ON up.parent_provider_id = sp.id AND up.user_id = :user_id
-- WHERE m.model_key = :model_key AND m.is_active;
