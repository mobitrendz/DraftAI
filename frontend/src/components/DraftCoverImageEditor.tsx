import { useEffect, useRef, useState } from "react";
import type { CoverImagePublic } from "../client/types.gen";
import {
  regenerateDraftCoverImage,
  resolveCoverImageUrl,
  uploadDraftCoverImage,
} from "../lib/content-api";
import { Button } from "./ui/button";
import { Label } from "./ui/label";
import { Loader2, RefreshCw, Upload } from "lucide-react";

const ACCEPTED_IMAGE_TYPES = "image/png,image/jpeg,image/webp";

type DraftCoverImageEditorProps = {
  draftId: string;
  cover: CoverImagePublic;
  disabled?: boolean;
  onUpdated: () => void;
};

const platformLabel = (platform: CoverImagePublic["platform"]) =>
  platform === "devto" ? "DEV.to" : "LinkedIn";

const platformCoverSizeHint = (platform: CoverImagePublic["platform"]) =>
  platform === "devto" ? "1000×420 px" : "1200×627 px";

const DraftCoverImageEditor = ({
  draftId,
  cover,
  disabled = false,
  onUpdated,
}: DraftCoverImageEditorProps) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(
    resolveCoverImageUrl(cover.image_url),
  );
  const [provider, setProvider] = useState<string | null>(cover.provider ?? null);
  const [prompt, setPrompt] = useState(cover.prompt_used ?? "");
  const [uploading, setUploading] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [warning, setWarning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isBusy = uploading || regenerating;

  useEffect(() => {
    if (isBusy) {
      return;
    }
    setPreviewUrl(resolveCoverImageUrl(cover.image_url));
    setProvider(cover.provider ?? null);
    setPrompt(cover.prompt_used ?? "");
  }, [cover.image_url, cover.prompt_used, cover.provider, cover.id, isBusy]);

  const applyUpdatedCover = (updatedDraft: Awaited<ReturnType<typeof uploadDraftCoverImage>>) => {
    const updatedCover = updatedDraft.cover_images?.find((item) => item.id === cover.id);
    setPreviewUrl(resolveCoverImageUrl(updatedCover?.image_url));
    if (updatedCover?.prompt_used) {
      setPrompt(updatedCover.prompt_used);
    }
    if (updatedCover?.provider) {
      setProvider(updatedCover.provider);
    }
    if (updatedDraft.cover_image_warning) {
      setWarning(updatedDraft.cover_image_warning);
    }
    onUpdated();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }

    setUploading(true);
    setError(null);
    setWarning(null);
    try {
      const updatedDraft = await uploadDraftCoverImage(draftId, cover.id, file);
      applyUpdatedCover(updatedDraft);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const handleRegenerate = async () => {
    const trimmedPrompt = prompt.trim();
    if (!trimmedPrompt) {
      setError("Enter a prompt before regenerating the cover image.");
      return;
    }

    setRegenerating(true);
    setError(null);
    setWarning(null);
    try {
      const updatedDraft = await regenerateDraftCoverImage(
        draftId,
        cover.id,
        trimmedPrompt,
      );
      applyUpdatedCover(updatedDraft);
    } catch (regenerateError) {
      setError(
        regenerateError instanceof Error
          ? regenerateError.message
          : "Regeneration failed.",
      );
    } finally {
      setRegenerating(false);
    }
  };

  return (
    <div className="rounded-2xl border border-border bg-card p-4 space-y-3">
      <div className="flex items-center justify-between gap-3">
        <h4 className="text-sm font-semibold uppercase text-muted-foreground">
          {platformLabel(cover.platform)} cover
          <span className="ml-2 font-normal normal-case text-xs">
            ({platformCoverSizeHint(cover.platform)})
          </span>
        </h4>
        {provider && (
          <span className="text-xs text-muted-foreground">{provider}</span>
        )}
      </div>

      {previewUrl ? (
        <img
          key={previewUrl}
          src={previewUrl}
          alt={`${platformLabel(cover.platform)} cover`}
          className="w-full rounded-xl object-cover max-h-48"
        />
      ) : (
        <div className="flex min-h-32 items-center justify-center rounded-xl border border-dashed border-border bg-muted/30 px-4 text-center text-sm text-muted-foreground">
          No cover image yet. Regenerate with AI or upload a PNG, JPEG, or WebP file below.
        </div>
      )}

      <div className="space-y-2">
        <Label htmlFor={`cover-prompt-${cover.id}`}>Image prompt</Label>
        <textarea
          id={`cover-prompt-${cover.id}`}
          rows={3}
          className="w-full resize-y rounded-xl border border-border bg-background px-4 py-3 text-sm disabled:opacity-60"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder="Describe the cover image you want..."
          disabled={disabled || isBusy}
        />
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_IMAGE_TYPES}
        className="hidden"
        onChange={handleFileChange}
      />

      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
        <Button
          type="button"
          variant="default"
          disabled={disabled || isBusy || !prompt.trim()}
          onClick={handleRegenerate}
        >
          {regenerating ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
              Regenerating...
            </>
          ) : (
            <>
              <RefreshCw className="w-4 h-4 mr-2" />
              Regenerate
            </>
          )}
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={disabled || isBusy}
          onClick={() => inputRef.current?.click()}
        >
          {uploading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
              Uploading...
            </>
          ) : (
            <>
              <Upload className="w-4 h-4 mr-2" />
              {previewUrl ? "Replace image" : "Upload image"}
            </>
          )}
        </Button>
        <p className="text-xs text-muted-foreground sm:basis-full">
          Regenerate uses your cover image model from Settings. Upload accepts PNG, JPEG, or WebP up to 5 MB.
        </p>
      </div>

      {warning && <p className="text-sm text-amber-600">{warning}</p>}
      {error && <p className="text-sm text-red-500">{error}</p>}
    </div>
  );
};

export default DraftCoverImageEditor;
