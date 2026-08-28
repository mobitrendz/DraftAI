import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  readPlatformConfigApiV1SettingsPlatformGet,
  updatePlatformConfigApiV1SettingsPlatformPatch,
  readAiConfigApiV1SettingsAiGet,
  readAiModelsCatalogApiV1SettingsAiModelsGet,
  updateAiConfigApiV1SettingsAiPatch,
  createCustomAiProviderApiV1SettingsAiProvidersPost,
  deleteCustomAiProviderApiV1SettingsAiProvidersProviderIdDelete,
  refreshProviderModelsApiV1SettingsAiProvidersProviderSlugRefreshModelsPost,
} from "../client/sdk.gen";
import type { AiProviderCatalogPublic, CustomAiProviderCreate } from "../client/types.gen";
import { isProviderConfigured, canRefreshProviderModels, listActiveSettingsProviders, listAddableBuiltinProviders, listAvailableCoverImageModels, listVisibleProviderModels, shouldShowProviderModels } from "../lib/ai-providers";
import { extractApiError } from "../lib/error-handler";
import DeleteProviderConfirmModal from "./DeleteProviderConfirmModal";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Loader2, Settings, Cpu, Share2, Plus, Trash2, RefreshCw } from "lucide-react";

type Tab = "providers" | "platform";

const API_KEY_PLACEHOLDERS: Record<string, string> = {
  openai: "sk-...",
  anthropic: "sk-ant-...",
  gemini: "AIza...",
  groq: "gsk_...",
  openrouter: "sk-or-...",
};

const API_KEY_HELP_LINKS: Record<string, { href: string; label: string }> = {
  gemini: {
    href: "https://aistudio.google.com/apikey",
    label: "Google AI Studio",
  },
  groq: {
    href: "https://console.groq.com/keys",
    label: "console.groq.com",
  },
  openrouter: {
    href: "https://openrouter.ai/keys",
    label: "openrouter.ai",
  },
};

type AddProviderMode = "builtin" | "custom";

const SettingsPage = () => {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>("providers");
  const [devtoKey, setDevtoKey] = useState("");
  const [apiKeyDrafts, setApiKeyDrafts] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);
  const [ollamaBaseUrlDraft, setOllamaBaseUrlDraft] = useState("");
  const [ollamaBaseUrlDebounced, setOllamaBaseUrlDebounced] = useState("");
  const [showAddProvider, setShowAddProvider] = useState(false);
  const [addProviderMode, setAddProviderMode] = useState<AddProviderMode>("builtin");
  const [selectedBuiltinSlug, setSelectedBuiltinSlug] = useState("");
  const [builtinApiKeyDraft, setBuiltinApiKeyDraft] = useState("");
  const [refreshingSlug, setRefreshingSlug] = useState<string | null>(null);
  const [refreshMessages, setRefreshMessages] = useState<Record<string, string>>({});
  const [providerToDelete, setProviderToDelete] = useState<{
    id?: string;
    slug: string;
    label: string;
    mode: "custom" | "credentials";
  } | null>(null);
  const [newProvider, setNewProvider] = useState<CustomAiProviderCreate>({
    display_name: "",
    base_url: "",
    api_adapter: "openai_compatible",
    auth_style: "bearer",
    api_key: "",
  });

  const platformQuery = useQuery({
    queryKey: ["settings", "platform"],
    queryFn: async () => {
      const { data, error } = await readPlatformConfigApiV1SettingsPlatformGet();
      if (error) throw error;
      return data;
    },
  });

  const aiQuery = useQuery({
    queryKey: ["settings", "ai"],
    queryFn: async () => {
      const { data, error } = await readAiConfigApiV1SettingsAiGet();
      if (error) throw error;
      return data;
    },
  });

  const modelsCatalogQuery = useQuery({
    queryKey: ["settings", "ai-models", ollamaBaseUrlDebounced || aiQuery.data?.ollama_base_url],
    queryFn: async () => {
      const previewUrl = ollamaBaseUrlDebounced || aiQuery.data?.ollama_base_url;
      const { data, error } = await readAiModelsCatalogApiV1SettingsAiModelsGet({
        query: previewUrl ? { ollama_base_url: previewUrl } : undefined,
      });
      if (error) throw error;
      return data;
    },
    enabled: aiQuery.isSuccess,
  });

  useEffect(() => {
    if (aiQuery.data?.ollama_base_url != null) {
      setOllamaBaseUrlDraft(aiQuery.data.ollama_base_url);
      setOllamaBaseUrlDebounced(aiQuery.data.ollama_base_url);
    }
  }, [aiQuery.data?.ollama_base_url]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setOllamaBaseUrlDebounced(ollamaBaseUrlDraft);
    }, 400);
    return () => clearTimeout(timer);
  }, [ollamaBaseUrlDraft]);

  useEffect(() => {
    if (!aiQuery.data || !modelsCatalogQuery.data) return;
    const availableCoverModels = listAvailableCoverImageModels(
      modelsCatalogQuery.data.cover_image_models ?? [],
      aiQuery.data.saved_api_keys ?? {},
    );
    if (availableCoverModels.length === 0) return;
    const current = aiQuery.data.cover_image_model;
    if (!availableCoverModels.some((model) => model.id === current)) {
      updateAiField("cover_image_model", availableCoverModels[0].id);
    }
  }, [
    aiQuery.data?.cover_image_model,
    aiQuery.data?.saved_api_keys,
    modelsCatalogQuery.data,
  ]);

  const catalog = modelsCatalogQuery.data;
  const textProviders = catalog?.providers ?? [];
  const coverImageModels = catalog?.cover_image_models ?? [];
  const ollamaStatus = catalog?.ollama;
  const savedApiKeys = aiQuery.data?.saved_api_keys ?? {};
  const availableCoverImageModels = listAvailableCoverImageModels(
    coverImageModels,
    savedApiKeys,
  );
  const activeProviders = listActiveSettingsProviders(textProviders, savedApiKeys);
  const addableBuiltinProviders = listAddableBuiltinProviders(
    textProviders,
    savedApiKeys,
  );
  const selectedBuiltinProvider = addableBuiltinProviders.find(
    (provider) => provider.slug === selectedBuiltinSlug,
  );

  const platformMutation = useMutation({
    mutationFn: async () => {
      const platform = platformQuery.data;
      const { data, error } = await updatePlatformConfigApiV1SettingsPlatformPatch({
        body: {
          devto_enabled: platform?.devto_enabled,
          linkedin_enabled: platform?.linkedin_enabled,
          devto_profile_url: platform?.devto_profile_url ?? undefined,
          linkedin_profile_url: platform?.linkedin_profile_url ?? undefined,
          ...(devtoKey ? { devto_api_key: devtoKey } : {}),
        },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      setDevtoKey("");
      setSaved(true);
      queryClient.invalidateQueries({ queryKey: ["settings", "platform"] });
      setTimeout(() => setSaved(false), 2000);
    },
  });

  const aiMutation = useMutation({
    mutationFn: async () => {
      const ai = aiQuery.data;
      const provider_api_keys = Object.fromEntries(
        Object.entries(apiKeyDrafts).filter(([, value]) => value.length > 0),
      );
      const { data, error } = await updateAiConfigApiV1SettingsAiPatch({
        body: {
          cover_image_model: ai?.cover_image_model,
          ollama_base_url: ollamaBaseUrlDraft || ai?.ollama_base_url || undefined,
          ...(Object.keys(provider_api_keys).length > 0
            ? { provider_api_keys }
            : {}),
        },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      setApiKeyDrafts({});
      setSaved(true);
      queryClient.invalidateQueries({ queryKey: ["settings", "ai"] });
      queryClient.invalidateQueries({ queryKey: ["settings", "ai-models"] });
      setTimeout(() => setSaved(false), 2000);
    },
  });

  const addBuiltinProviderMutation = useMutation({
    mutationFn: async ({ slug, apiKey }: { slug: string; apiKey: string }) => {
      const { error } = await updateAiConfigApiV1SettingsAiPatch({
        body: {
          provider_api_keys: { [slug]: apiKey },
        },
      });
      if (error) throw error;
    },
    onSuccess: () => {
      setShowAddProvider(false);
      setSelectedBuiltinSlug("");
      setBuiltinApiKeyDraft("");
      setSaved(true);
      queryClient.invalidateQueries({ queryKey: ["settings", "ai"] });
      queryClient.invalidateQueries({ queryKey: ["settings", "ai-models"] });
      setTimeout(() => setSaved(false), 2000);
    },
  });

  const addProviderMutation = useMutation({
    mutationFn: async () => {
      const body: CustomAiProviderCreate = {
        display_name: newProvider.display_name.trim(),
        base_url: newProvider.base_url.trim(),
        api_adapter: newProvider.api_adapter ?? "openai_compatible",
        auth_style: newProvider.auth_style ?? "bearer",
        description: newProvider.description,
        ...(newProvider.api_key ? { api_key: newProvider.api_key } : {}),
      };
      const { data, error } = await createCustomAiProviderApiV1SettingsAiProvidersPost({
        body,
      });
      if (error) throw error;
      return data;
    },
    onSuccess: async () => {
      setShowAddProvider(false);
      setAddProviderMode("builtin");
      setNewProvider({
        display_name: "",
        base_url: "",
        api_adapter: "openai_compatible",
        auth_style: "bearer",
        api_key: "",
      });
      await queryClient.invalidateQueries({ queryKey: ["settings", "ai-models"] });
      await queryClient.invalidateQueries({ queryKey: ["settings", "ai"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  const deleteProviderMutation = useMutation({
    mutationFn: async (target: NonNullable<typeof providerToDelete>) => {
      if (target.mode === "custom") {
        const { error } =
          await deleteCustomAiProviderApiV1SettingsAiProvidersProviderIdDelete({
            path: { provider_id: target.id! },
          });
        if (error) throw error;
        return;
      }

      const { error } = await updateAiConfigApiV1SettingsAiPatch({
        body: {
          provider_api_keys: { [target.slug]: "" },
        },
      });
      if (error) throw error;
    },
    onSuccess: () => {
      setProviderToDelete(null);
      setApiKeyDrafts((prev) => {
        const next = { ...prev };
        if (providerToDelete?.slug) {
          delete next[providerToDelete.slug];
        }
        return next;
      });
      queryClient.invalidateQueries({ queryKey: ["settings", "ai-models"] });
      queryClient.invalidateQueries({ queryKey: ["settings", "ai"] });
    },
  });

  const refreshModelsMutation = useMutation({
    mutationFn: async (provider: AiProviderCatalogPublic) => {
      const { data, error } =
        await refreshProviderModelsApiV1SettingsAiProvidersProviderSlugRefreshModelsPost({
          path: { provider_slug: provider.slug },
          query:
            provider.slug === "ollama" && ollamaBaseUrlDraft
              ? { ollama_base_url: ollamaBaseUrlDraft }
              : undefined,
        });
      if (error) throw error;
      return data;
    },
    onMutate: (provider) => {
      setRefreshingSlug(provider.slug);
    },
    onSuccess: (data) => {
      if (data?.message) {
        setRefreshMessages((prev) => ({ ...prev, [data.slug]: data.message! }));
      }
      queryClient.invalidateQueries({ queryKey: ["settings", "ai-models"] });
    },
    onSettled: () => {
      setRefreshingSlug(null);
    },
  });

  const updatePlatformField = (field: string, value: string | boolean) => {
    queryClient.setQueryData(["settings", "platform"], (old: any) => ({
      ...old,
      [field]: value,
    }));
  };

  const updateAiField = (field: string, value: string) => {
    queryClient.setQueryData(["settings", "ai"], (old: any) => ({
      ...old,
      [field]: value,
    }));
  };

  const handleCoverModelSelect = (value: string) => {
    updateAiField("cover_image_model", value);
  };

  const updateApiKeyDraft = (slug: string, value: string) => {
    setApiKeyDrafts((prev) => ({ ...prev, [slug]: value }));
  };

  const canRemoveProvider = (
    provider: AiProviderCatalogPublic,
    hasSavedKey: boolean,
  ) => {
    if (provider.is_custom && provider.provider_id) {
      return true;
    }
    return hasSavedKey && provider.requires_api_key !== false;
  };

  const renderProviderCard = (provider: AiProviderCatalogPublic) => {
    const configured = isProviderConfigured(provider, savedApiKeys);
    const canRefresh = canRefreshProviderModels(provider, savedApiKeys);
    const helpLink = API_KEY_HELP_LINKS[provider.slug];
    const hasSavedKey = savedApiKeys[provider.slug] === true;
    const showModels = shouldShowProviderModels(provider, savedApiKeys);
    const visibleModels = listVisibleProviderModels(provider, savedApiKeys);

    return (
      <div
        key={provider.slug}
        className="rounded-xl border border-border bg-card p-4 space-y-3"
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="font-semibold text-foreground">
              {provider.label}
              {provider.is_custom && (
                <span className="ml-2 text-xs font-normal text-muted-foreground">
                  custom
                </span>
              )}
            </h3>
            {provider.description && (
              <p className="text-xs text-muted-foreground mt-1">{provider.description}</p>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {canRefresh && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-8 px-2 text-xs"
                disabled={
                  refreshingSlug === provider.slug ||
                  (provider.requires_api_key !== false &&
                    !provider.is_custom &&
                    provider.slug !== "ollama" &&
                    !hasSavedKey)
                }
                title={
                  provider.requires_api_key !== false &&
                  !provider.is_custom &&
                  provider.slug !== "ollama" &&
                  !hasSavedKey
                    ? "Save an API key first, then refresh models"
                    : "Search for newly available models from this provider"
                }
                onClick={() => refreshModelsMutation.mutate(provider)}
              >
                {refreshingSlug === provider.slug ? (
                  <Loader2 className="w-3 h-3 animate-spin mr-1" />
                ) : (
                  <RefreshCw className="w-3 h-3 mr-1" />
                )}
                Refresh models
              </Button>
            )}
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                configured
                  ? "bg-green-500/10 text-green-600"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {configured ? "Ready" : "Needs key"}
            </span>
            {canRemoveProvider(provider, hasSavedKey) && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-8 px-2 text-xs text-destructive hover:text-destructive"
                disabled={deleteProviderMutation.isPending}
                onClick={() =>
                  setProviderToDelete({
                    id: provider.provider_id ?? undefined,
                    slug: provider.slug,
                    label: provider.label,
                    mode: provider.is_custom ? "custom" : "credentials",
                  })
                }
              >
                <Trash2 className="w-3 h-3 mr-1" />
                Remove
              </Button>
            )}
          </div>
        </div>

        {provider.slug === "ollama" && (
          <div className="space-y-2">
            <Label htmlFor="ollama_base_url">Ollama base URL</Label>
            <Input
              id="ollama_base_url"
              value={ollamaBaseUrlDraft}
              placeholder="http://localhost:11434/v1"
              onChange={(e) => setOllamaBaseUrlDraft(e.target.value)}
            />
            {modelsCatalogQuery.isFetching && (
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <Loader2 className="w-3 h-3 animate-spin" />
                Refreshing models…
              </p>
            )}
            {ollamaStatus?.message && (
              <p
                className={`text-xs ${
                  ollamaStatus.reachable ? "text-muted-foreground" : "text-amber-600"
                }`}
              >
                {ollamaStatus.message}
              </p>
            )}
          </div>
        )}

        {provider.requires_api_key !== false && !provider.is_custom && (
          <div className="space-y-2">
            <Label htmlFor={`api_key_${provider.slug}`}>
              {provider.label} API key{" "}
              {hasSavedKey && <span className="text-green-600 text-xs">(saved)</span>}
            </Label>
            <Input
              id={`api_key_${provider.slug}`}
              type="password"
              placeholder={API_KEY_PLACEHOLDERS[provider.slug] ?? "API key"}
              value={apiKeyDrafts[provider.slug] ?? ""}
              onChange={(e) => updateApiKeyDraft(provider.slug, e.target.value)}
            />
            {provider.slug === "openrouter" && (
              <p className="text-xs text-muted-foreground">
                Free models use the <code className="text-xs">:free</code> suffix.
              </p>
            )}
            {helpLink && (
              <p className="text-xs text-muted-foreground">
                Get a key from{" "}
                <a
                  href={helpLink.href}
                  target="_blank"
                  rel="noreferrer"
                  className="text-primary hover:underline"
                >
                  {helpLink.label}
                </a>
                .
              </p>
            )}
          </div>
        )}

        {provider.is_custom && (
          <p className="text-xs text-muted-foreground">
            API key was saved when this provider was added.
          </p>
        )}

        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground">
            Available models ({visibleModels.length})
          </p>
          {refreshMessages[provider.slug] && (
            <p className="text-xs text-green-600">{refreshMessages[provider.slug]}</p>
          )}
          {!showModels ? (
            <p className="text-xs text-muted-foreground">
              Save an API key above to view available models.
            </p>
          ) : visibleModels.length > 0 ? (
            <ul className="max-h-32 overflow-y-auto rounded-lg bg-muted/40 px-3 py-2 text-xs space-y-1">
              {visibleModels.map((model) => (
                <li key={model.id} className="font-mono">
                  {model.label}
                  {model.description ? (
                    <span className="text-muted-foreground ml-1">— {model.description}</span>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-amber-600">
              No models discovered. Check connection settings above.
            </p>
          )}
        </div>
      </div>
    );
  };

  const isLoading =
    platformQuery.isLoading || aiQuery.isLoading || modelsCatalogQuery.isLoading;
  const error =
    platformMutation.error ||
    aiMutation.error ||
    addBuiltinProviderMutation.error ||
    addProviderMutation.error ||
    deleteProviderMutation.error ||
    refreshModelsMutation.error;

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h2 className="text-2xl font-bold text-foreground flex items-center gap-2">
          <Settings className="w-7 h-7 text-primary" />
          Configuration
        </h2>
        <p className="text-muted-foreground mt-1">
          Manage AI providers, API keys, and available models. Select a provider and model
          on the home page when generating content.
        </p>
      </div>

      <div className="flex gap-4 border-b border-border">
        <button
          onClick={() => setTab("providers")}
          className={`flex items-center gap-2 pb-2 text-sm font-bold border-b-2 transition-colors ${
            tab === "providers"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground"
          }`}
        >
          <Cpu className="w-4 h-4" /> AI Providers
        </button>
        <button
          onClick={() => setTab("platform")}
          className={`flex items-center gap-2 pb-2 text-sm font-bold border-b-2 transition-colors ${
            tab === "platform"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground"
          }`}
        >
          <Share2 className="w-4 h-4" /> Platforms
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 text-red-500 text-sm font-medium">
          {extractApiError(error)}
        </div>
      )}

      {saved && (
        <div className="p-4 rounded-xl bg-green-500/10 text-green-600 text-sm font-medium">
          Settings saved successfully.
        </div>
      )}

      {tab === "providers" && aiQuery.data && (
        <div className="space-y-6 max-w-2xl">
          <div className="rounded-xl border border-border p-4 space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold">Add provider</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Connect a built-in provider with an API key, or add a custom
                  OpenAI-compatible or Ollama endpoint.
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                aria-expanded={showAddProvider}
                aria-label="Show add provider"
                onClick={() => {
                  setShowAddProvider((open) => {
                    const next = !open;
                    if (next) {
                      setAddProviderMode(
                        addableBuiltinProviders.length > 0 ? "builtin" : "custom",
                      );
                    }
                    return next;
                  });
                }}
              >
                <Plus className="w-4 h-4 mr-1" />
                Add provider
              </Button>
            </div>
            {showAddProvider && (
              <div className="space-y-4 border-t border-border pt-4">
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant={addProviderMode === "builtin" ? "default" : "outline"}
                    disabled={addableBuiltinProviders.length === 0}
                    onClick={() => setAddProviderMode("builtin")}
                  >
                    Built-in provider
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant={addProviderMode === "custom" ? "default" : "outline"}
                    onClick={() => setAddProviderMode("custom")}
                  >
                    Custom provider
                  </Button>
                </div>

                {addProviderMode === "builtin" ? (
                  <div className="space-y-3">
                    {addableBuiltinProviders.length === 0 ? (
                      <p className="text-xs text-muted-foreground">
                        All built-in providers are already connected.
                      </p>
                    ) : (
                      <>
                        <div className="space-y-2">
                          <Label htmlFor="builtin_provider_select">Provider</Label>
                          <select
                            id="builtin_provider_select"
                            value={selectedBuiltinSlug}
                            onChange={(e) => {
                              setSelectedBuiltinSlug(e.target.value);
                              setBuiltinApiKeyDraft("");
                            }}
                            className="w-full rounded-xl border border-border bg-background px-4 py-3 text-sm"
                          >
                            <option value="">Choose a provider…</option>
                            {addableBuiltinProviders.map((provider) => (
                              <option key={provider.slug} value={provider.slug}>
                                {provider.label}
                              </option>
                            ))}
                          </select>
                        </div>
                        {selectedBuiltinProvider && (
                          <>
                            {selectedBuiltinProvider.description && (
                              <p className="text-xs text-muted-foreground">
                                {selectedBuiltinProvider.description}
                              </p>
                            )}
                            <div className="space-y-2">
                              <Label htmlFor="builtin_provider_key">
                                {selectedBuiltinProvider.label} API key
                              </Label>
                              <Input
                                id="builtin_provider_key"
                                type="password"
                                placeholder={
                                  API_KEY_PLACEHOLDERS[selectedBuiltinProvider.slug] ??
                                  "API key"
                                }
                                value={builtinApiKeyDraft}
                                onChange={(e) => setBuiltinApiKeyDraft(e.target.value)}
                              />
                              {selectedBuiltinProvider.slug === "openrouter" && (
                                <p className="text-xs text-muted-foreground">
                                  Free models use the{" "}
                                  <code className="text-xs">:free</code> suffix.
                                </p>
                              )}
                              {API_KEY_HELP_LINKS[selectedBuiltinProvider.slug] && (
                                <p className="text-xs text-muted-foreground">
                                  Get a key from{" "}
                                  <a
                                    href={
                                      API_KEY_HELP_LINKS[selectedBuiltinProvider.slug].href
                                    }
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-primary hover:underline"
                                  >
                                    {
                                      API_KEY_HELP_LINKS[selectedBuiltinProvider.slug]
                                        .label
                                    }
                                  </a>
                                  .
                                </p>
                              )}
                            </div>
                          </>
                        )}
                        <Button
                          type="button"
                          onClick={() =>
                            addBuiltinProviderMutation.mutate({
                              slug: selectedBuiltinSlug,
                              apiKey: builtinApiKeyDraft.trim(),
                            })
                          }
                          disabled={
                            addBuiltinProviderMutation.isPending ||
                            !selectedBuiltinSlug ||
                            !builtinApiKeyDraft.trim()
                          }
                        >
                          {addBuiltinProviderMutation.isPending ? (
                            <Loader2 className="w-4 h-4 animate-spin mr-2" />
                          ) : null}
                          Connect provider
                        </Button>
                      </>
                    )}
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="space-y-2">
                      <Label htmlFor="custom_provider_name">Display name</Label>
                      <Input
                        id="custom_provider_name"
                        placeholder="My LM Studio"
                        value={newProvider.display_name}
                        onChange={(e) =>
                          setNewProvider((prev) => ({
                            ...prev,
                            display_name: e.target.value,
                          }))
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="custom_provider_url">Base URL</Label>
                      <Input
                        id="custom_provider_url"
                        placeholder="http://localhost:1234/v1"
                        value={newProvider.base_url}
                        onChange={(e) =>
                          setNewProvider((prev) => ({ ...prev, base_url: e.target.value }))
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="custom_provider_adapter">API type</Label>
                      <select
                        id="custom_provider_adapter"
                        value={newProvider.api_adapter ?? "openai_compatible"}
                        onChange={(e) => {
                          const api_adapter = e.target.value;
                          setNewProvider((prev) => ({
                            ...prev,
                            api_adapter,
                            auth_style: api_adapter === "ollama" ? "none" : "bearer",
                            api_key: api_adapter === "ollama" ? "" : prev.api_key,
                          }));
                        }}
                        className="w-full rounded-xl border border-border bg-background px-4 py-3 text-sm"
                      >
                        <option value="openai_compatible">OpenAI-compatible</option>
                        <option value="ollama">Ollama</option>
                      </select>
                    </div>
                    {newProvider.api_adapter !== "ollama" && (
                      <div className="space-y-2">
                        <Label htmlFor="custom_provider_key">API key</Label>
                        <Input
                          id="custom_provider_key"
                          type="password"
                          placeholder="Required for most hosted APIs"
                          value={newProvider.api_key ?? ""}
                          onChange={(e) =>
                            setNewProvider((prev) => ({ ...prev, api_key: e.target.value }))
                          }
                        />
                      </div>
                    )}
                    <Button
                      type="button"
                      onClick={() => addProviderMutation.mutate()}
                      disabled={
                        addProviderMutation.isPending ||
                        !newProvider.display_name.trim() ||
                        !newProvider.base_url.trim() ||
                        (newProvider.api_adapter !== "ollama" && !newProvider.api_key?.trim())
                      }
                    >
                      {addProviderMutation.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      ) : null}
                      Save provider
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-semibold">Providers</h3>
            {activeProviders.length > 0 ? (
              activeProviders.map(renderProviderCard)
            ) : (
              <p className="text-sm text-muted-foreground">
                No providers connected yet. Use Add provider above to get started.
              </p>
            )}
          </div>

          <div className="space-y-2 border-t border-border pt-6">
            {availableCoverImageModels.length > 0 ? (
              <>
                <Label htmlFor="cover_image_model">Cover image model</Label>
                <select
                  id="cover_image_model"
                  value={aiQuery.data.cover_image_model ?? ""}
                  onChange={(e) => handleCoverModelSelect(e.target.value)}
                  className="w-full rounded-xl border border-border bg-background px-4 py-3 text-sm"
                >
                  {availableCoverImageModels.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.label}
                      {model.description ? ` — ${model.description}` : ""}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-muted-foreground">
                  Cover images use Gemini or OpenAI. Only models with a connected
                  provider API key are shown.
                </p>
              </>
            ) : (
              <>
                <p className="text-sm font-medium">Cover image model</p>
                <p className="text-xs text-amber-600">
                  Connect Gemini or OpenAI in Add provider to choose a cover image model.
                </p>
              </>
            )}
          </div>

          <Button onClick={() => aiMutation.mutate()} disabled={aiMutation.isPending}>
            {aiMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : null}
            Save provider settings
          </Button>
        </div>
      )}

      {tab === "platform" && platformQuery.data && (
        <div className="space-y-6 max-w-xl">
          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={platformQuery.data.devto_enabled}
              onChange={(e) => updatePlatformField("devto_enabled", e.target.checked)}
            />
            <span className="font-medium">Enable DEV.to</span>
          </label>
          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={platformQuery.data.linkedin_enabled}
              onChange={(e) => updatePlatformField("linkedin_enabled", e.target.checked)}
            />
            <span className="font-medium">Enable LinkedIn</span>
          </label>
          <div className="space-y-2">
            <Label htmlFor="devto_profile">DEV.to profile URL</Label>
            <Input
              id="devto_profile"
              value={platformQuery.data.devto_profile_url ?? ""}
              onChange={(e) => updatePlatformField("devto_profile_url", e.target.value)}
              placeholder="https://dev.to/yourhandle"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="linkedin_profile">LinkedIn profile URL</Label>
            <Input
              id="linkedin_profile"
              value={platformQuery.data.linkedin_profile_url ?? ""}
              onChange={(e) => updatePlatformField("linkedin_profile_url", e.target.value)}
              placeholder="https://linkedin.com/in/you"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="devto_key">
              DEV.to API key{" "}
              {platformQuery.data.has_devto_api_key && (
                <span className="text-green-600 text-xs">(saved)</span>
              )}
            </Label>
            <Input
              id="devto_key"
              type="password"
              value={devtoKey}
              onChange={(e) => setDevtoKey(e.target.value)}
            />
          </div>
          <Button
            onClick={() => platformMutation.mutate()}
            disabled={platformMutation.isPending}
          >
            {platformMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : null}
            Save platform settings
          </Button>
        </div>
      )}

      {providerToDelete && (
        <DeleteProviderConfirmModal
          providerLabel={providerToDelete.label}
          mode={providerToDelete.mode}
          isDeleting={deleteProviderMutation.isPending}
          onClose={() => setProviderToDelete(null)}
          onConfirm={() => deleteProviderMutation.mutate(providerToDelete)}
        />
      )}
    </div>
  );
};

export default SettingsPage;
