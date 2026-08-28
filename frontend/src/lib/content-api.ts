import type { ContentDraftDetailPublic } from "../client/types.gen";
import { getApiBaseUrl } from "../config";
import { auth } from "./auth";
import { env } from "../env";

export function resolveCoverImageUrl(imageUrl: string | null | undefined): string | null {
  if (!imageUrl) {
    return null;
  }
  if (imageUrl.startsWith("http://") || imageUrl.startsWith("https://")) {
    return imageUrl;
  }
  const base = getApiBaseUrl();
  const path = imageUrl.startsWith("/") ? imageUrl : `/${imageUrl}`;
  return `${base}${path}`;
}

export async function uploadDraftCoverImage(
  draftId: string,
  coverId: string,
  file: File,
): Promise<ContentDraftDetailPublic> {
  const formData = new FormData();
  formData.append("file", file);

  const token = auth.getToken();
  const response = await fetch(
    `${env.VITE_API_URL}/api/v1/content/drafts/${draftId}/covers/${coverId}/image`,
    {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    },
  );

  if (!response.ok) {
    let detail = "Failed to upload cover image.";
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        detail = payload.detail;
      }
    } catch {
      // ignore JSON parse errors
    }
    throw new Error(detail);
  }

  return (await response.json()) as ContentDraftDetailPublic;
}

export async function regenerateDraftCoverImage(
  draftId: string,
  coverId: string,
  prompt: string,
): Promise<ContentDraftDetailPublic> {
  const token = auth.getToken();
  const response = await fetch(
    `${env.VITE_API_URL}/api/v1/content/drafts/${draftId}/covers/${coverId}/regenerate`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ prompt }),
    },
  );

  if (!response.ok) {
    let detail = "Failed to regenerate cover image.";
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        detail = payload.detail;
      }
    } catch {
      // ignore JSON parse errors
    }
    throw new Error(detail);
  }

  return (await response.json()) as ContentDraftDetailPublic;
}
