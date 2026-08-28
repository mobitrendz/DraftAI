"""add ai provider and model catalog tables

Revision ID: e6a7b8c9d010
Revises: d4e5f6a7b809
Create Date: 2026-06-15 25:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.crud.ai_catalog import MODEL_SEEDS, PROVIDER_SEEDS

revision: str = "e6a7b8c9d010"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b809"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

modality_enum = postgresql.ENUM(
    "text",
    "image",
    "embedding",
    "multimodal",
    name="aimodelmodality",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        "CREATE TYPE aimodelmodality AS ENUM "
        "('text', 'image', 'embedding', 'multimodal')"
    )

    op.create_table(
        "ai_provider",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("parent_provider_id", sa.Uuid(), nullable=True),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("base_url", sa.String(length=2048), nullable=False),
        sa.Column("api_adapter", sa.String(length=64), nullable=False),
        sa.Column("auth_style", sa.String(length=32), nullable=False, server_default="bearer"),
        sa.Column("auth_header_name", sa.String(length=64), nullable=True),
        sa.Column(
            "extra_headers",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column("api_key_ciphertext", sa.LargeBinary(), nullable=True),
        sa.Column("api_key_iv", sa.LargeBinary(), nullable=True),
        sa.Column("api_key_tag", sa.LargeBinary(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["parent_provider_id"], ["ai_provider.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "parent_provider_id", name="ai_provider_user_parent_uniq"),
    )
    op.create_index(
        "ai_provider_system_slug_uidx",
        "ai_provider",
        ["slug"],
        unique=True,
        postgresql_where=sa.text("user_id IS NULL"),
    )
    op.create_index(
        "ai_provider_user_id_idx",
        "ai_provider",
        ["user_id"],
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )

    op.create_table(
        "ai_model",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("model_key", sa.String(length=256), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "modality",
            modality_enum,
            nullable=False,
            server_default="text",
        ),
        sa.Column("context_window_tokens", sa.Integer(), nullable=True),
        sa.Column("max_output_tokens", sa.Integer(), nullable=True),
        sa.Column("input_cost_per_million", sa.Numeric(12, 6), nullable=True),
        sa.Column("output_cost_per_million", sa.Numeric(12, 6), nullable=True),
        sa.Column(
            "capabilities",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["provider_id"], ["ai_provider.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", "model_key", name="ai_model_provider_model_key_uniq"),
    )
    op.create_index(
        "ai_model_provider_modality_idx",
        "ai_model",
        ["provider_id", "modality"],
        postgresql_where=sa.text("is_active = true"),
    )

    op.add_column("ai_agent_config", sa.Column("text_model_id", sa.Uuid(), nullable=True))
    op.add_column("ai_agent_config", sa.Column("cover_model_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "ai_agent_config_text_model_id_fkey",
        "ai_agent_config",
        "ai_model",
        ["text_model_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "ai_agent_config_cover_model_id_fkey",
        "ai_agent_config",
        "ai_model",
        ["cover_model_id"],
        ["id"],
        ondelete="SET NULL",
    )

    _seed_catalog()
    _migrate_legacy_api_keys()
    _backfill_model_fks()


def _seed_catalog() -> None:
    import json
    import uuid as uuid_mod

    conn = op.get_bind()
    slug_to_id: dict[str, str] = {}
    for seed in PROVIDER_SEEDS:
        provider_id = str(uuid_mod.uuid4())
        conn.execute(
            sa.text(
                """
                INSERT INTO ai_provider (
                    id, slug, display_name, description, base_url, api_adapter,
                    auth_style, auth_header_name, extra_headers, sort_order
                )
                VALUES (
                    :id, :slug, :display_name, :description, :base_url, :api_adapter,
                    :auth_style, :auth_header_name, CAST(:extra_headers AS jsonb), :sort_order
                )
                """
            ),
            {
                "id": provider_id,
                "slug": seed["slug"],
                "display_name": seed["display_name"],
                "description": seed.get("description"),
                "base_url": seed["base_url"],
                "api_adapter": seed["api_adapter"],
                "auth_style": seed.get("auth_style", "bearer"),
                "auth_header_name": seed.get("auth_header_name"),
                "extra_headers": json.dumps(seed.get("extra_headers", {})),
                "sort_order": seed.get("sort_order", 0),
            },
        )
        slug_to_id[seed["slug"]] = provider_id

    for seed in MODEL_SEEDS:
        conn.execute(
            sa.text(
                """
                INSERT INTO ai_model (
                    id, provider_id, model_key, display_name, description, modality,
                    context_window_tokens, max_output_tokens,
                    input_cost_per_million, output_cost_per_million,
                    capabilities, is_default, sort_order
                )
                VALUES (
                    gen_random_uuid(), :provider_id, :model_key, :display_name,
                    :description, CAST(:modality AS aimodelmodality),
                    :context_window_tokens, :max_output_tokens,
                    :input_cost_per_million, :output_cost_per_million,
                    CAST(:capabilities AS jsonb), :is_default, :sort_order
                )
                """
            ),
            {
                "provider_id": slug_to_id[seed["provider_slug"]],
                "model_key": seed["model_key"],
                "display_name": seed["display_name"],
                "description": seed.get("description"),
                "modality": seed["modality"],
                "context_window_tokens": seed.get("context_window_tokens"),
                "max_output_tokens": seed.get("max_output_tokens"),
                "input_cost_per_million": seed.get("input_cost_per_million"),
                "output_cost_per_million": seed.get("output_cost_per_million"),
                "capabilities": json.dumps(seed.get("capabilities", {})),
                "is_default": seed.get("is_default", False),
                "sort_order": seed.get("sort_order", 0),
            },
        )


def _migrate_legacy_api_keys() -> None:
    from app.core.encryption import decrypt_secret, encrypt_secret_aes
    from app.crud.ai_catalog import LEGACY_PROVIDER_KEY_COLUMNS

    conn = op.get_bind()
    configs = conn.execute(
        sa.text(
            """
            SELECT id, user_id, openai_api_key_encrypted, anthropic_api_key_encrypted,
                   gemini_api_key_encrypted, groq_api_key_encrypted,
                   openrouter_api_key_encrypted
            FROM ai_agent_config
            """
        )
    ).mappings().all()

    system_providers = {
        row["slug"]: row["id"]
        for row in conn.execute(
            sa.text(
                "SELECT id, slug FROM ai_provider WHERE user_id IS NULL"
            )
        ).mappings().all()
    }

    for config in configs:
        for slug, column in LEGACY_PROVIDER_KEY_COLUMNS.items():
            encrypted = config[column]
            if not encrypted:
                continue
            try:
                plaintext = decrypt_secret(encrypted)
            except ValueError:
                continue
            system_id = system_providers.get(slug)
            if not system_id:
                continue
            ciphertext, iv, tag = encrypt_secret_aes(plaintext)
            conn.execute(
                sa.text(
                    """
                    INSERT INTO ai_provider (
                        id, user_id, parent_provider_id, slug, display_name,
                        base_url, api_adapter, auth_style, auth_header_name,
                        extra_headers, api_key_ciphertext, api_key_iv, api_key_tag
                    )
                    SELECT
                        gen_random_uuid(), :user_id, sp.id, sp.slug, sp.display_name,
                        sp.base_url, sp.api_adapter, sp.auth_style, sp.auth_header_name,
                        sp.extra_headers, :ciphertext, :iv, :tag
                    FROM ai_provider sp
                    WHERE sp.id = :system_id
                    ON CONFLICT (user_id, parent_provider_id) DO UPDATE SET
                        api_key_ciphertext = EXCLUDED.api_key_ciphertext,
                        api_key_iv = EXCLUDED.api_key_iv,
                        api_key_tag = EXCLUDED.api_key_tag,
                        updated_at = now()
                    """
                ),
                {
                    "user_id": config["user_id"],
                    "system_id": system_id,
                    "ciphertext": ciphertext,
                    "iv": iv,
                    "tag": tag,
                },
            )


def _backfill_model_fks() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE ai_agent_config c
            SET text_model_id = m.id
            FROM ai_model m
            JOIN ai_provider p ON p.id = m.provider_id
            WHERE p.user_id IS NULL
              AND p.slug = c.provider::text
              AND m.model_key = c.model
              AND m.modality = 'text'
              AND c.text_model_id IS NULL
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE ai_agent_config c
            SET cover_model_id = m.id
            FROM ai_model m
            JOIN ai_provider p ON p.id = m.provider_id
            WHERE p.user_id IS NULL
              AND m.model_key = c.cover_image_model
              AND m.modality = 'image'
              AND c.cover_model_id IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint("ai_agent_config_cover_model_id_fkey", "ai_agent_config", type_="foreignkey")
    op.drop_constraint("ai_agent_config_text_model_id_fkey", "ai_agent_config", type_="foreignkey")
    op.drop_column("ai_agent_config", "cover_model_id")
    op.drop_column("ai_agent_config", "text_model_id")
    op.drop_index("ai_model_provider_modality_idx", table_name="ai_model")
    op.drop_table("ai_model")
    op.drop_index("ai_provider_user_id_idx", table_name="ai_provider")
    op.drop_index("ai_provider_system_slug_uidx", table_name="ai_provider")
    op.drop_table("ai_provider")
    op.execute("DROP TYPE aimodelmodality")
