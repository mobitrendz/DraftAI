import type {
  AiAgentConfigPublic,
  AiModelsCatalogPublic,
  ContentDraftDetailPublic,
  ContentDraftPublic,
  ContentDraftsPublic,
  PlatformConfigPublic,
} from "../client/types.gen";

export const createMockPlatformConfig = (
  overrides: Partial<PlatformConfigPublic> = {},
): PlatformConfigPublic => ({
  id: "platform-config-1",
  devto_enabled: true,
  linkedin_enabled: true,
  devto_profile_url: null,
  linkedin_profile_url: null,
  has_devto_api_key: false,
  ...overrides,
});

export const createMockAiConfig = (
  overrides: Partial<AiAgentConfigPublic> = {},
): AiAgentConfigPublic => ({
  id: "ai-config-1",
  provider: "openai",
  model: "gpt-4o",
  cover_image_model: "gemini-3-pro-image",
  temperature: 0.7,
  system_prompt: null,
  saved_api_keys: {},
  ...overrides,
});

export const createMockAiModelsCatalog = (): AiModelsCatalogPublic => ({
  providers: [
    {
      slug: "openai",
      label: "OpenAI",
      description: "GPT and DALL-E APIs",
      default_model: "gpt-4o",
      requires_api_key: true,
      models: [
        { id: "gpt-4o", label: "GPT-4o", description: "Best overall quality" },
        { id: "gpt-4o-mini", label: "GPT-4o mini", description: "Fast and cost-effective" },
      ],
      can_refresh_models: false,
    },
    {
      slug: "gemini",
      label: "Google Gemini",
      default_model: "gemini-2.0-flash",
      requires_api_key: true,
      models: [
        { id: "gemini-2.0-flash", label: "Gemini 2.0 Flash", description: "Default" },
        { id: "gemini-2.5-pro", label: "Gemini 2.5 Pro", description: "Best for complex writing" },
      ],
    },
    {
      slug: "groq",
      label: "Groq",
      default_model: "llama-3.3-70b-versatile",
      requires_api_key: true,
      models: [
        { id: "llama-3.3-70b-versatile", label: "Llama 3.3 70B", description: "Default" },
      ],
    },
    {
      slug: "openrouter",
      label: "OpenRouter",
      default_model: "meta-llama/llama-3.3-70b-instruct:free",
      requires_api_key: true,
      models: [
        {
          id: "meta-llama/llama-3.3-70b-instruct:free",
          label: "Llama 3.3 70B (free)",
          description: "Default free tier",
        },
      ],
    },
    {
      slug: "ollama",
      label: "Ollama (local)",
      description: "Local Ollama OpenAI-compatible server",
      default_model: "qwen3:8b",
      requires_api_key: false,
      models_source: "ollama",
      can_refresh_models: true,
      models: [
        { id: "qwen3:8b", label: "qwen3:8b", description: "5.2 GB local" },
      ],
    },
    {
      slug: "anthropic",
      label: "Anthropic",
      default_model: "claude-3-5-sonnet-20241022",
      requires_api_key: true,
      models: [
        {
          id: "claude-3-5-sonnet-20241022",
          label: "Claude 3.5 Sonnet",
          description: "Balanced quality and speed",
        },
      ],
    },
  ],
  cover_image_models: [
    {
      id: "gemini-3-pro-image",
      label: "Gemini 3 Pro Image",
      description: "Best quality",
      key_provider: "gemini",
    },
    {
      id: "dall-e-3",
      label: "DALL-E 3",
      description: "OpenAI widescreen",
      key_provider: "openai",
    },
  ],
  default_cover_image_model: "gemini-3-pro-image",
  ollama: {
    base_url: "http://localhost:11434/v1",
    reachable: true,
    model_count: 2,
  },
  credential_providers: [
    { slug: "openai", label: "OpenAI", requires_api_key: true, auth_style: "bearer" },
    { slug: "anthropic", label: "Anthropic", requires_api_key: true, auth_style: "api_key_header" },
    { slug: "gemini", label: "Google Gemini", requires_api_key: true, auth_style: "query_param" },
    { slug: "groq", label: "Groq", requires_api_key: true, auth_style: "bearer" },
    { slug: "openrouter", label: "OpenRouter", requires_api_key: true, auth_style: "bearer" },
    { slug: "ollama", label: "Ollama (local)", requires_api_key: false, auth_style: "none" },
  ],
});

export const createMockContentDraft = (
  overrides: Partial<ContentDraftPublic> = {},
): ContentDraftPublic => ({
  id: "draft-1",
  user_id: "user-1",
  topic: "Async APIs with FastAPI",
  user_prompt: null,
  status: "draft",
  created_at: "2026-06-15T10:00:00Z",
  updated_at: "2026-06-15T10:00:00Z",
  ...overrides,
});

export const createMockContentDraftDetail = (
  overrides: Partial<ContentDraftDetailPublic> = {},
): ContentDraftDetailPublic => ({
  ...createMockContentDraft(),
  devto_article: {
    id: "devto-1",
    title: "Test Article Title",
    body_markdown: "# Hello\n\nThis is test content.",
    tags: "python,fastapi",
    cover_image_id: null,
  },
  linkedin_post: {
    id: "linkedin-1",
    teaser_text: "Check out this new article on FastAPI!",
    article_url: null,
    cover_image_id: null,
  },
  cover_images: [],
  ...overrides,
});

export const createMockContentDraftsList = (
  drafts: ContentDraftPublic[] = [],
): ContentDraftsPublic => ({
  data: drafts,
  count: drafts.length,
});
