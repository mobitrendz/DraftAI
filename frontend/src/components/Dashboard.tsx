import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import DashboardLayout from "./layout/DashboardLayout";
import {
  deleteContentDraftApiV1ContentDraftsDraftIdDelete,
  generateContentDraftApiV1ContentDraftsGeneratePost,
  getEnvSettingsApiV1GetEnvironmentGet,
  listContentDraftsApiV1ContentDraftsGet,
  readAiConfigApiV1SettingsAiGet,
  readAiModelsCatalogApiV1SettingsAiModelsGet,
  readPlatformConfigApiV1SettingsPlatformGet,
  updateAiConfigApiV1SettingsAiPatch,
} from "../client/sdk.gen";
import type { ContentDraftDetailPublic } from "../client/types.gen";
import { listConfiguredProviders } from "../lib/ai-providers";
import { extractApiError } from "../lib/error-handler";
import DeleteDraftConfirmModal from "./DeleteDraftConfirmModal";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Loader2, Sparkles, FileText, Settings, Trash2 } from "lucide-react";

const CUSTOM_MODEL_VALUE = "__custom__";

const Dashboard = () => {
  const { user, logout } = useAuth();
  const queryClient = useQueryClient();
  const [topic, setTopic] = useState("");
  const [userPrompt, setUserPrompt] = useState("");
  const [generated, setGenerated] = useState<ContentDraftDetailPublic | null>(null);
  const [providerSlug, setProviderSlug] = useState("");
  const [modelId, setModelId] = useState("");
  const [useCustomModel, setUseCustomModel] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [temperature, setTemperature] = useState(0.7);
  const [systemPrompt, setSystemPrompt] = useState("");
  const [draftToDelete, setDraftToDelete] = useState<{ id: string; topic: string } | null>(
    null,
  );

  const aiQuery = useQuery({
    queryKey: ["settings", "ai"],
    queryFn: async () => {
      const { data, error } = await readAiConfigApiV1SettingsAiGet();
      if (error) throw error;
      return data;
    },
  });

  const platformQuery = useQuery({
    queryKey: ["settings", "platform"],
    queryFn: async () => {
      const { data, error } = await readPlatformConfigApiV1SettingsPlatformGet();
      if (error) throw error;
      return data;
    },
  });

  const envQuery = useQuery({
    queryKey: ["env-settings"],
    queryFn: async () => {
      const { data, error } = await getEnvSettingsApiV1GetEnvironmentGet();
      if (error) throw error;
      return data;
    },
  });

  const draftGenerationMaxSeconds = useMemo(() => {
    const raw = envQuery.data?.ai_draft_generation_max_seconds;
    const parsed = raw ? Number.parseInt(raw, 10) : Number.NaN;
    return Number.isFinite(parsed) ? parsed : 300;
  }, [envQuery.data?.ai_draft_generation_max_seconds]);

  const modelsCatalogQuery = useQuery({
    queryKey: ["settings", "ai-models", aiQuery.data?.ollama_base_url],
    queryFn: async () => {
      const { data, error } = await readAiModelsCatalogApiV1SettingsAiModelsGet({
        query: aiQuery.data?.ollama_base_url
          ? { ollama_base_url: aiQuery.data.ollama_base_url }
          : undefined,
      });
      if (error) throw error;
      return data;
    },
    enabled: aiQuery.isSuccess,
  });

  const draftsQuery = useQuery({
    queryKey: ["content-drafts"],
    queryFn: async () => {
      const { data, error } = await listContentDraftsApiV1ContentDraftsGet();
      if (error) throw error;
      return data;
    },
  });

  const configuredProviders = useMemo(
    () =>
      listConfiguredProviders(
        modelsCatalogQuery.data?.providers ?? [],
        aiQuery.data?.saved_api_keys,
      ),
    [modelsCatalogQuery.data?.providers, aiQuery.data?.saved_api_keys],
  );

  const currentProvider = configuredProviders.find((p) => p.slug === providerSlug);
  const providerModels = currentProvider?.models ?? [];

  useEffect(() => {
    if (!aiQuery.data || configuredProviders.length === 0) return;

    const savedProvider = configuredProviders.find((p) => p.slug === aiQuery.data.provider);
    const activeProvider = savedProvider ?? configuredProviders[0];
    setProviderSlug(activeProvider.slug);

    const knownModels = activeProvider.models.map((m) => m.id);
    const savedModel = aiQuery.data.model;
    if (savedModel && knownModels.includes(savedModel)) {
      setModelId(savedModel);
      setUseCustomModel(false);
    } else if (savedModel) {
      setModelId(savedModel);
      setUseCustomModel(true);
    } else if (activeProvider.default_model) {
      setModelId(activeProvider.default_model);
      setUseCustomModel(false);
    }

    setTemperature(aiQuery.data.temperature ?? 0.7);
    setSystemPrompt(aiQuery.data.system_prompt ?? "");
  }, [aiQuery.data, configuredProviders]);

  const saveSelectionMutation = useMutation({
    mutationFn: async (body: {
      provider: string;
      model: string;
      temperature?: number;
      system_prompt?: string | null;
    }) => {
      const { data, error } = await updateAiConfigApiV1SettingsAiPatch({ body });
      if (error) throw error;
      return data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(["settings", "ai"], data);
    },
  });

  const handleProviderChange = (slug: string) => {
    const entry = configuredProviders.find((p) => p.slug === slug);
    setProviderSlug(slug);
    const nextModel = entry?.default_model ?? entry?.models[0]?.id ?? "";
    setModelId(nextModel);
    setUseCustomModel(false);
    if (nextModel) {
      saveSelectionMutation.mutate({ provider: slug, model: nextModel });
    }
  };

  const handleModelSelect = (value: string) => {
    if (value === CUSTOM_MODEL_VALUE) {
      setUseCustomModel(true);
      return;
    }
    setUseCustomModel(false);
    setModelId(value);
    if (providerSlug && value) {
      saveSelectionMutation.mutate({ provider: providerSlug, model: value });
    }
  };

  const handleCustomModelBlur = () => {
    if (providerSlug && modelId) {
      saveSelectionMutation.mutate({ provider: providerSlug, model: modelId });
    }
  };

  const handleAdvancedSave = () => {
    if (!providerSlug || !modelId) return;
    saveSelectionMutation.mutate({
      provider: providerSlug,
      model: modelId,
      temperature,
      system_prompt: systemPrompt || null,
    });
  };

  const generateMutation = useMutation({
    mutationFn: async () => {
      if (providerSlug && modelId) {
        await saveSelectionMutation.mutateAsync({
          provider: providerSlug,
          model: modelId,
          temperature,
          system_prompt: systemPrompt || null,
        });
      }
      const { data, error } = await generateContentDraftApiV1ContentDraftsGeneratePost({
        body: { topic, user_prompt: userPrompt || undefined },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: (data) => {
      setGenerated(data ?? null);
      queryClient.invalidateQueries({ queryKey: ["content-drafts"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (draftId: string) => {
      const { error } = await deleteContentDraftApiV1ContentDraftsDraftIdDelete({
        path: { draft_id: draftId },
      });
      if (error) throw error;
    },
    onSuccess: (_data, draftId) => {
      if (generated?.id === draftId) {
        setGenerated(null);
      }
      setDraftToDelete(null);
      queryClient.invalidateQueries({ queryKey: ["content-drafts"] });
    },
  });

  const aiSettingsLoading = aiQuery.isLoading || modelsCatalogQuery.isLoading;
  const noConfiguredProviders = !aiSettingsLoading && configuredProviders.length === 0;

  return (
    <DashboardLayout currentUser={user} onLogout={logout}>
      <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-foreground">Create Content</h2>
            <p className="text-muted-foreground mt-1">
              Generate a DEV.to article and LinkedIn post from one topic.
            </p>
          </div>
          <Link
            to="/settings"
            className="inline-flex items-center gap-2 text-sm font-medium text-primary hover:underline"
          >
            <Settings className="w-4 h-4" />
            Configure providers
          </Link>
        </div>

        <div className="p-6 rounded-2xl border border-border bg-card space-y-4 max-w-2xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-primary" />
            </div>
            <h3 className="font-semibold text-foreground">Generate draft</h3>
          </div>

          {aiSettingsLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
              <Loader2 className="w-4 h-4 animate-spin" />
              Loading AI providers…
            </div>
          ) : noConfiguredProviders ? (
            <div className="p-4 rounded-xl bg-amber-500/10 text-amber-700 dark:text-amber-400 text-sm">
              No providers are configured yet. Add API keys or connect Ollama in{" "}
              <Link to="/settings" className="font-medium underline">
                Settings → AI Providers
              </Link>
              , then return here to choose a model.
            </div>
          ) : (
            <>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="home_provider">Provider</Label>
                  <select
                    id="home_provider"
                    value={providerSlug}
                    onChange={(e) => handleProviderChange(e.target.value)}
                    className="w-full rounded-xl border border-border bg-background px-4 py-3 text-sm"
                  >
                    {configuredProviders.map((provider) => (
                      <option key={provider.slug} value={provider.slug}>
                        {provider.label}
                        {provider.is_custom ? " (custom)" : ""}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="home_model">Model</Label>
                  <select
                    id="home_model"
                    value={useCustomModel ? CUSTOM_MODEL_VALUE : modelId}
                    onChange={(e) => handleModelSelect(e.target.value)}
                    className="w-full rounded-xl border border-border bg-background px-4 py-3 text-sm"
                    disabled={providerModels.length === 0 && !useCustomModel}
                  >
                    {providerModels.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.label}
                        {model.description ? ` — ${model.description}` : ""}
                      </option>
                    ))}
                    <option value={CUSTOM_MODEL_VALUE}>Other model (custom ID)…</option>
                  </select>
                  {useCustomModel && (
                    <Input
                      id="home_custom_model"
                      value={modelId}
                      placeholder="Exact model ID"
                      onChange={(e) => setModelId(e.target.value)}
                      onBlur={handleCustomModelBlur}
                    />
                  )}
                </div>
              </div>

              <button
                type="button"
                onClick={() => setShowAdvanced((open) => !open)}
                className="text-xs font-medium text-primary hover:underline"
              >
                {showAdvanced ? "Hide" : "Show"} advanced options
              </button>

              {showAdvanced && (
                <div className="space-y-4 border-t border-border pt-4">
                  <div className="space-y-2">
                    <Label htmlFor="home_temperature">Temperature ({temperature})</Label>
                    <input
                      id="home_temperature"
                      type="range"
                      min={0}
                      max={2}
                      step={0.1}
                      value={temperature}
                      onChange={(e) => setTemperature(parseFloat(e.target.value))}
                      onMouseUp={handleAdvancedSave}
                      onTouchEnd={handleAdvancedSave}
                      className="w-full"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="home_system_prompt">System prompt (optional)</Label>
                    <textarea
                      id="home_system_prompt"
                      rows={3}
                      className="w-full rounded-xl border border-border bg-background px-4 py-3 text-sm"
                      value={systemPrompt}
                      onChange={(e) => setSystemPrompt(e.target.value)}
                      onBlur={handleAdvancedSave}
                    />
                  </div>
                </div>
              )}
            </>
          )}

          <div className="space-y-2">
            <Label htmlFor="topic">Topic *</Label>
            <Input
              id="topic"
              placeholder="e.g. Building async APIs with FastAPI and ARQ"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="prompt">Additional instructions (optional)</Label>
            <textarea
              id="prompt"
              rows={3}
              className="w-full rounded-xl border border-border bg-background px-4 py-3 text-sm"
              placeholder="Tone, audience, key points to cover..."
              value={userPrompt}
              onChange={(e) => setUserPrompt(e.target.value)}
            />
          </div>

          {platformQuery.data?.linkedin_enabled === false && (
            <div className="p-3 rounded-xl bg-muted text-sm text-muted-foreground">
              LinkedIn is disabled in{" "}
              <Link to="/settings" className="font-medium text-primary hover:underline">
                Settings → Platforms
              </Link>
              . Enable it to generate a LinkedIn post with each draft.
            </div>
          )}

          {generateMutation.error && (
            <div className="p-3 rounded-xl bg-red-500/10 text-red-500 text-sm">
              {extractApiError(generateMutation.error)}
            </div>
          )}

          <Button
            onClick={() => generateMutation.mutate()}
            disabled={
              !topic.trim() ||
              generateMutation.isPending ||
              noConfiguredProviders ||
              !providerSlug ||
              !modelId
            }
          >
            {generateMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                Generating (up to {draftGenerationMaxSeconds}s)...
              </>
            ) : (
              "Generate draft"
            )}
          </Button>
        </div>

        {generated && (
          <div className="space-y-6">
            <div className="flex items-center justify-between gap-4">
              <h3 className="text-lg font-bold flex items-center gap-2">
                <FileText className="w-5 h-5 text-primary" />
                Preview — {generated.topic}
                <span className="text-xs font-normal uppercase text-muted-foreground ml-2">
                  {generated.status}
                </span>
              </h3>
              <Link
                to={`/drafts/${generated.id}`}
                className="text-sm font-medium text-primary hover:underline"
              >
                Open editor
              </Link>
            </div>

            {generated.devto_article && (
              <div className="p-6 rounded-2xl border border-border bg-card space-y-3">
                <h4 className="font-bold text-primary">DEV.to article</h4>
                <p className="text-xl font-semibold">{generated.devto_article.title}</p>
                <p className="text-xs text-muted-foreground">
                  Tags: {generated.devto_article.tags}
                </p>
                <pre className="text-sm whitespace-pre-wrap font-mono bg-muted/50 p-4 rounded-xl max-h-96 overflow-y-auto">
                  {generated.devto_article.body_markdown}
                </pre>
              </div>
            )}

            {generated.linkedin_post && (
              <div className="p-6 rounded-2xl border border-border bg-card space-y-3">
                <h4 className="font-bold text-primary">LinkedIn post</h4>
                <p className="text-sm whitespace-pre-wrap">
                  {generated.linkedin_post.teaser_text ||
                    "No post text was returned. Open the editor to write one."}
                </p>
              </div>
            )}

            {generated.linkedin_post === null &&
              platformQuery.data?.linkedin_enabled !== false && (
                <div className="p-4 rounded-xl bg-muted text-sm text-muted-foreground">
                  No LinkedIn post was saved for this draft. Check that LinkedIn is enabled
                  under Settings → Platforms.
                </div>
              )}

            {generated.cover_image_warning && (
              <div className="p-4 rounded-xl bg-amber-500/10 text-amber-800 dark:text-amber-300 text-sm">
                {generated.cover_image_warning}
              </div>
            )}
          </div>
        )}

        {draftsQuery.data && draftsQuery.data.data.length > 0 && (
          <div className="space-y-3">
            <h3 className="font-bold text-foreground">Recent drafts</h3>
            <ul className="divide-y divide-border rounded-xl border border-border bg-card">
              {draftsQuery.data.data.map((draft) => (
                <li key={draft.id} className="flex items-center">
                  <Link
                    to={`/drafts/${draft.id}`}
                    className="flex-1 px-4 py-3 flex justify-between items-center text-sm hover:bg-muted/50 transition-colors"
                  >
                    <span className="font-medium">{draft.topic}</span>
                    <span className="text-muted-foreground uppercase text-xs">
                      {draft.status}
                    </span>
                  </Link>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="mr-2 text-destructive hover:text-destructive"
                    aria-label={`Delete draft ${draft.topic}`}
                    onClick={() =>
                      setDraftToDelete({ id: draft.id, topic: draft.topic })
                    }
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {draftToDelete && (
        <DeleteDraftConfirmModal
          topic={draftToDelete.topic}
          isDeleting={deleteMutation.isPending}
          onClose={() => setDraftToDelete(null)}
          onConfirm={() => deleteMutation.mutate(draftToDelete.id)}
        />
      )}
    </DashboardLayout>
  );
};

export default Dashboard;
