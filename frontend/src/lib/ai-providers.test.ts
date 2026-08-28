import { describe, it, expect } from "vitest";
import {
  canRefreshProviderModels,
  isCoverImageModelAvailable,
  isProviderConfigured,
  listActiveSettingsProviders,
  listAddableBuiltinProviders,
  listAvailableCoverImageModels,
  listConfiguredProviders,
  listVisibleProviderModels,
  shouldShowProviderModels,
} from "./ai-providers";
import type { AiProviderCatalogPublic, CoverImageModelOption } from "../client/types.gen";

const baseProvider = (
  overrides: Partial<AiProviderCatalogPublic>,
): AiProviderCatalogPublic => ({
  slug: "openai",
  label: "OpenAI",
  default_model: "gpt-4o",
  models: [],
  requires_api_key: true,
  ...overrides,
});

describe("ai-providers", () => {
  it("treats providers without keys as configured when no key is required", () => {
    expect(
      isProviderConfigured(
        baseProvider({ slug: "ollama", requires_api_key: false }),
        {},
      ),
    ).toBe(true);
  });

  it("requires saved API key for hosted providers", () => {
    expect(isProviderConfigured(baseProvider({ slug: "openai" }), {})).toBe(false);
    expect(
      isProviderConfigured(baseProvider({ slug: "openai" }), { openai: true }),
    ).toBe(true);
  });

  it("lists only configured providers", () => {
    const providers = [
      baseProvider({ slug: "openai" }),
      baseProvider({ slug: "gemini", label: "Gemini" }),
      baseProvider({ slug: "ollama", label: "Ollama", requires_api_key: false }),
    ];
    const configured = listConfiguredProviders(providers, { openai: true });
    expect(configured.map((p) => p.slug)).toEqual(["openai", "ollama"]);
  });

  it("hides provider models without a saved key except ollama", () => {
    const openai = baseProvider({
      slug: "openai",
      models: [{ id: "gpt-4o", label: "GPT-4o" }],
    });
    const ollama = baseProvider({
      slug: "ollama",
      label: "Ollama",
      requires_api_key: false,
      models: [{ id: "qwen3:8b", label: "qwen3:8b" }],
    });

    expect(shouldShowProviderModels(openai, {})).toBe(false);
    expect(listVisibleProviderModels(openai, {})).toEqual([]);
    expect(shouldShowProviderModels(openai, { openai: true })).toBe(true);
    expect(listVisibleProviderModels(openai, { openai: true })).toHaveLength(1);

    expect(shouldShowProviderModels(ollama, {})).toBe(true);
    expect(listVisibleProviderModels(ollama, {})).toHaveLength(1);
  });

  it("splits active and addable providers for the settings page", () => {
    const providers = [
      baseProvider({
        slug: "openai",
        models: [{ id: "gpt-4o", label: "GPT-4o" }],
      }),
      baseProvider({ slug: "gemini", label: "Gemini" }),
      baseProvider({
        slug: "ollama",
        label: "Ollama",
        requires_api_key: false,
        models: [{ id: "qwen3:8b", label: "qwen3:8b" }],
      }),
    ];

    expect(listActiveSettingsProviders(providers, {}).map((p) => p.slug)).toEqual([
      "ollama",
    ]);
    expect(listAddableBuiltinProviders(providers, {}).map((p) => p.slug)).toEqual([
      "openai",
      "gemini",
    ]);
    expect(listActiveSettingsProviders(providers, { openai: true }).map((p) => p.slug)).toEqual(
      ["openai", "ollama"],
    );
    expect(listAddableBuiltinProviders(providers, { openai: true }).map((p) => p.slug)).toEqual([
      "gemini",
    ]);
  });

  it("allows refresh for ollama even when can_refresh_models is omitted", () => {
    expect(
      canRefreshProviderModels(
        baseProvider({ slug: "ollama", requires_api_key: false }),
        {},
      ),
    ).toBe(true);
  });

  it("allows refresh for openai only when configured", () => {
    expect(canRefreshProviderModels(baseProvider({ slug: "openai" }), {})).toBe(false);
    expect(
      canRefreshProviderModels(baseProvider({ slug: "openai" }), { openai: true }),
    ).toBe(true);
  });

  it("allows refresh for gemini and anthropic when configured", () => {
    expect(canRefreshProviderModels(baseProvider({ slug: "gemini" }), {})).toBe(false);
    expect(
      canRefreshProviderModels(baseProvider({ slug: "gemini" }), { gemini: true }),
    ).toBe(true);
    expect(canRefreshProviderModels(baseProvider({ slug: "anthropic" }), {})).toBe(false);
    expect(
      canRefreshProviderModels(baseProvider({ slug: "anthropic" }), { anthropic: true }),
    ).toBe(true);
  });

  it("respects explicit can_refresh_models=false from API", () => {
    expect(
      canRefreshProviderModels(
        baseProvider({ slug: "ollama", can_refresh_models: false }),
        {},
      ),
    ).toBe(false);
  });

  it("filters cover image models by saved provider API keys", () => {
    const models: CoverImageModelOption[] = [
      { id: "gemini-3-pro-image", label: "Gemini 3 Pro Image", key_provider: "gemini" },
      { id: "dall-e-3", label: "DALL-E 3", key_provider: "openai" },
    ];

    expect(isCoverImageModelAvailable(models[0], {})).toBe(false);
    expect(isCoverImageModelAvailable(models[0], { gemini: true })).toBe(true);
    expect(
      isCoverImageModelAvailable(
        { id: "other", label: "Other", key_provider: "groq" },
        { groq: true },
      ),
    ).toBe(false);
    expect(listAvailableCoverImageModels(models, { gemini: true }).map((m) => m.id)).toEqual([
      "gemini-3-pro-image",
    ]);
    expect(listAvailableCoverImageModels(models, { openai: true, gemini: true }).map((m) => m.id)).toEqual([
      "gemini-3-pro-image",
      "dall-e-3",
    ]);
  });
});
