import type { AiProviderCatalogPublic, CoverImageModelOption } from "../client/types.gen";

/** Provider is ready to use on the home page (key saved or no key required). */
export function isProviderConfigured(
  provider: AiProviderCatalogPublic,
  savedApiKeys: Record<string, boolean> | undefined,
): boolean {
  if (provider.is_custom) {
    return true;
  }
  if (provider.requires_api_key === false) {
    return true;
  }
  return savedApiKeys?.[provider.slug] === true;
}

export function listConfiguredProviders(
  providers: AiProviderCatalogPublic[],
  savedApiKeys: Record<string, boolean> | undefined,
): AiProviderCatalogPublic[] {
  return providers.filter((provider) => isProviderConfigured(provider, savedApiKeys));
}

/** Whether provider model names should be shown on the Settings page. */
export function shouldShowProviderModels(
  provider: AiProviderCatalogPublic,
  savedApiKeys: Record<string, boolean> | undefined,
): boolean {
  if (provider.slug === "ollama") {
    return true;
  }
  return isProviderConfigured(provider, savedApiKeys);
}

export function listVisibleProviderModels(
  provider: AiProviderCatalogPublic,
  savedApiKeys: Record<string, boolean> | undefined,
) {
  return shouldShowProviderModels(provider, savedApiKeys) ? provider.models : [];
}

/** Providers shown on the main Settings list (configured or Ollama). */
export function isActiveSettingsProvider(
  provider: AiProviderCatalogPublic,
  savedApiKeys: Record<string, boolean> | undefined,
): boolean {
  return isProviderConfigured(provider, savedApiKeys);
}

export function listActiveSettingsProviders(
  providers: AiProviderCatalogPublic[],
  savedApiKeys: Record<string, boolean> | undefined,
): AiProviderCatalogPublic[] {
  return providers.filter((provider) =>
    isActiveSettingsProvider(provider, savedApiKeys),
  );
}

/** Built-in providers without a saved key — offered inside Add provider. */
export function listAddableBuiltinProviders(
  providers: AiProviderCatalogPublic[],
  savedApiKeys: Record<string, boolean> | undefined,
): AiProviderCatalogPublic[] {
  return providers.filter(
    (provider) =>
      !provider.is_custom &&
      provider.slug !== "ollama" &&
      provider.requires_api_key !== false &&
      !isProviderConfigured(provider, savedApiKeys),
  );
}

const SUPPORTED_COVER_KEY_PROVIDERS = new Set(["openai", "gemini"]);

/** Cover image model is selectable when its provider has a saved API key. */
export function isCoverImageModelAvailable(
  model: CoverImageModelOption,
  savedApiKeys: Record<string, boolean> | undefined,
): boolean {
  if (!SUPPORTED_COVER_KEY_PROVIDERS.has(model.key_provider)) {
    return false;
  }
  return savedApiKeys?.[model.key_provider] === true;
}

export function listAvailableCoverImageModels(
  models: CoverImageModelOption[],
  savedApiKeys: Record<string, boolean> | undefined,
): CoverImageModelOption[] {
  return models.filter((model) => isCoverImageModelAvailable(model, savedApiKeys));
}

const REFRESHABLE_KEYED_SLUGS = new Set([
  "openai",
  "groq",
  "openrouter",
  "gemini",
  "anthropic",
]);

/** Whether the Settings page can refresh models live from this provider. */
export function canRefreshProviderModels(
  provider: AiProviderCatalogPublic,
  savedApiKeys: Record<string, boolean> | undefined,
): boolean {
  if (provider.can_refresh_models === true) {
    return true;
  }
  if (provider.can_refresh_models === false) {
    return false;
  }

  // Fallback for older API responses that omit can_refresh_models.
  if (provider.slug === "ollama") {
    return true;
  }
  if (provider.is_custom) {
    return true;
  }
  if (provider.models_source === "ollama" || provider.models_source === "live") {
    return true;
  }
  if (REFRESHABLE_KEYED_SLUGS.has(provider.slug)) {
    return isProviderConfigured(provider, savedApiKeys);
  }
  return false;
}
