import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import DashboardLayout from "./layout/DashboardLayout";
import {
  approveContentDraftApiV1ContentDraftsDraftIdApprovePost,
  deleteContentDraftApiV1ContentDraftsDraftIdDelete,
  getContentDraftApiV1ContentDraftsDraftIdGet,
  getContentDraftPublishStatusApiV1ContentDraftsDraftIdPublishStatusGet,
  rescheduleContentDraftApiV1ContentDraftsDraftIdSchedulePatch,
  retryContentDraftPublishApiV1ContentDraftsDraftIdRetryPublishPost,
  scheduleContentDraftApiV1ContentDraftsDraftIdSchedulePost,
  updateContentDraftApiV1ContentDraftsDraftIdPatch,
} from "../client/sdk.gen";
import type { ContentDraftStatus } from "../client/types.gen";
import { extractApiError } from "../lib/error-handler";
import DeleteDraftConfirmModal from "./DeleteDraftConfirmModal";
import DraftCoverImageEditor from "./DraftCoverImageEditor";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { ArrowLeft, CheckCircle2, ClipboardCopy, Loader2, RefreshCw, Save, Trash2 } from "lucide-react";

const EDITABLE_STATUSES: ContentDraftStatus[] = ["draft", "approved"];

const statusLabel = (status: ContentDraftStatus) => {
  switch (status) {
    case "draft":
      return "Draft";
    case "approved":
      return "Approved";
    case "scheduled":
      return "Scheduled";
    case "published":
      return "Published";
    case "partially_published":
      return "Partially published";
    case "failed":
      return "Failed";
    default:
      return status;
  }
};

const statusBadgeClass = (status: ContentDraftStatus) => {
  switch (status) {
    case "published":
      return "bg-green-500/10 text-green-600";
    case "partially_published":
      return "bg-amber-500/10 text-amber-700";
    case "failed":
      return "bg-red-500/10 text-red-600";
    case "scheduled":
      return "bg-blue-500/10 text-blue-600";
    case "approved":
      return "bg-primary/10 text-primary";
    default:
      return "bg-muted text-muted-foreground";
  }
};

const toDatetimeLocalValue = (iso: string) => {
  const date = new Date(iso);
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
};

const DraftEditorPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const queryClient = useQueryClient();

  const [devtoTitle, setDevtoTitle] = useState("");
  const [devtoBody, setDevtoBody] = useState("");
  const [devtoTags, setDevtoTags] = useState("");
  const [linkedinTeaser, setLinkedinTeaser] = useState("");
  const [initialized, setInitialized] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [scheduleAt, setScheduleAt] = useState("");
  const [clipboardMessage, setClipboardMessage] = useState<string | null>(null);

  const draftQuery = useQuery({
    queryKey: ["content-draft", id],
    enabled: Boolean(id),
    queryFn: async () => {
      const { data, error } = await getContentDraftApiV1ContentDraftsDraftIdGet({
        path: { draft_id: id! },
      });
      if (error) throw error;
      return data;
    },
  });

  const draftStatus = draftQuery.data?.status;
  const shouldPollPublishStatus =
    draftStatus === "scheduled" ||
    draftStatus === "failed" ||
    draftStatus === "partially_published";

  const publishStatusQuery = useQuery({
    queryKey: ["publish-status", id],
    enabled: Boolean(id) && Boolean(shouldPollPublishStatus),
    queryFn: async () => {
      const { data, error } =
        await getContentDraftPublishStatusApiV1ContentDraftsDraftIdPublishStatusGet({
          path: { draft_id: id! },
        });
      if (error) throw error;
      return data;
    },
    refetchInterval: draftStatus === "scheduled" ? 3000 : false,
  });

  useEffect(() => {
    if (!publishStatusQuery.data || !draftStatus) {
      return;
    }
    if (publishStatusQuery.data.draft_status !== draftStatus) {
      queryClient.invalidateQueries({ queryKey: ["content-draft", id] });
    }
  }, [draftStatus, id, publishStatusQuery.data, queryClient]);

  useEffect(() => {
    if (draftQuery.data && !initialized) {
      setDevtoTitle(draftQuery.data.devto_article?.title ?? "");
      setDevtoBody(draftQuery.data.devto_article?.body_markdown ?? "");
      setDevtoTags(draftQuery.data.devto_article?.tags ?? "");
      setLinkedinTeaser(draftQuery.data.linkedin_post?.teaser_text ?? "");
      setInitialized(true);
    }
  }, [draftQuery.data, initialized]);

  useEffect(() => {
    const scheduledAt =
      draftQuery.data?.publish_job?.scheduled_at ?? publishStatusQuery.data?.publish_job?.scheduled_at;
    if (draftQuery.data?.status === "scheduled" && scheduledAt) {
      setScheduleAt(toDatetimeLocalValue(scheduledAt));
    }
  }, [
    draftQuery.data?.status,
    draftQuery.data?.publish_job?.scheduled_at,
    publishStatusQuery.data?.publish_job?.scheduled_at,
  ]);

  const invalidateDraftQueries = () => {
    queryClient.invalidateQueries({ queryKey: ["content-draft", id] });
    queryClient.invalidateQueries({ queryKey: ["content-drafts"] });
    queryClient.invalidateQueries({ queryKey: ["publish-status", id] });
  };

  const saveMutation = useMutation({
    mutationFn: async () => {
      const { data, error } = await updateContentDraftApiV1ContentDraftsDraftIdPatch({
        path: { draft_id: id! },
        body: {
          devto_title: devtoTitle,
          devto_body_markdown: devtoBody,
          devto_tags: devtoTags,
          linkedin_teaser: linkedinTeaser,
        },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: invalidateDraftQueries,
  });

  const approveMutation = useMutation({
    mutationFn: async () => {
      const { data, error } = await approveContentDraftApiV1ContentDraftsDraftIdApprovePost({
        path: { draft_id: id! },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: invalidateDraftQueries,
  });

  const scheduleMutation = useMutation({
    mutationFn: async (scheduledAt: string | null) => {
      const { data, error } = await scheduleContentDraftApiV1ContentDraftsDraftIdSchedulePost({
        path: { draft_id: id! },
        body: scheduledAt ? { scheduled_at: scheduledAt } : {},
      });
      if (error) throw error;
      return data;
    },
    onSuccess: invalidateDraftQueries,
  });

  const rescheduleMutation = useMutation({
    mutationFn: async (scheduledAt: string) => {
      const { data, error } =
        await rescheduleContentDraftApiV1ContentDraftsDraftIdSchedulePatch({
          path: { draft_id: id! },
          body: { scheduled_at: scheduledAt },
        });
      if (error) throw error;
      return data;
    },
    onSuccess: invalidateDraftQueries,
  });

  const retryMutation = useMutation({
    mutationFn: async () => {
      const { data, error } =
        await retryContentDraftPublishApiV1ContentDraftsDraftIdRetryPublishPost({
          path: { draft_id: id! },
        });
      if (error) throw error;
      return data;
    },
    onSuccess: invalidateDraftQueries,
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      const { error } = await deleteContentDraftApiV1ContentDraftsDraftIdDelete({
        path: { draft_id: id! },
      });
      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["content-drafts"] });
      navigate("/");
    },
  });

  if (draftQuery.isLoading) {
    return (
      <DashboardLayout currentUser={user} onLogout={logout}>
        <div className="flex items-center justify-center py-20 text-muted-foreground">
          <Loader2 className="w-6 h-6 animate-spin mr-2" />
          Loading draft...
        </div>
      </DashboardLayout>
    );
  }

  if (draftQuery.error || !draftQuery.data) {
    return (
      <DashboardLayout currentUser={user} onLogout={logout}>
        <div className="space-y-4">
          <p className="text-red-500">
            {extractApiError(draftQuery.error ?? new Error("Draft not found"))}
          </p>
          <Button variant="outline" onClick={() => navigate("/")}>
            Back to dashboard
          </Button>
        </div>
      </DashboardLayout>
    );
  }

  const draft = draftQuery.data;
  const isEditable = EDITABLE_STATUSES.includes(draft.status);
  const linkedinClipboardText =
    draft.linkedin_clipboard_text ??
    publishStatusQuery.data?.linkedin_clipboard_text ??
    null;
  const publishJob = draft.publish_job ?? publishStatusQuery.data?.publish_job ?? null;
  const canReschedule =
    draft.status === "scheduled" && publishJob?.status === "pending";

  const handleCopyLinkedin = async () => {
    if (!linkedinClipboardText) {
      return;
    }
    await navigator.clipboard.writeText(linkedinClipboardText);
    setClipboardMessage("LinkedIn post copied to clipboard.");
    window.setTimeout(() => setClipboardMessage(null), 3000);
  };

  const toIsoSchedule = (localValue: string) => {
    if (!localValue) {
      return null;
    }
    return new Date(localValue).toISOString();
  };

  return (
    <DashboardLayout currentUser={user} onLogout={logout}>
      <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <Link
              to="/"
              className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Back
            </Link>
            <h2 className="text-2xl font-bold text-foreground">Edit draft</h2>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span
                className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${statusBadgeClass(draft.status)}`}
              >
                {statusLabel(draft.status)}
              </span>
              {publishJob?.devto_url && (
                <a
                  href={publishJob.devto_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-primary hover:underline"
                >
                  View on DEV.to
                </a>
              )}
            </div>
            <p className="text-muted-foreground mt-1">{draft.topic}</p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              className="text-destructive hover:text-destructive"
              onClick={() => setShowDeleteConfirm(true)}
              disabled={deleteMutation.isPending}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Delete draft
            </Button>
            <Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending || !isEditable}>
              {saveMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Save changes
                </>
              )}
            </Button>
          </div>
        </div>

        {saveMutation.isSuccess && (
          <div className="p-3 rounded-xl bg-green-500/10 text-green-600 text-sm">
            Draft saved successfully.
          </div>
        )}
        {saveMutation.error && (
          <div className="p-3 rounded-xl bg-red-500/10 text-red-500 text-sm">
            {extractApiError(saveMutation.error)}
          </div>
        )}
        {deleteMutation.error && (
          <div className="p-3 rounded-xl bg-red-500/10 text-red-500 text-sm">
            {extractApiError(deleteMutation.error)}
          </div>
        )}

        <div className="rounded-2xl border border-border bg-card p-6 space-y-4">
          <h3 className="font-bold text-primary">Publishing</h3>

          {draft.status === "draft" && (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Approve this draft when you are ready to publish. You can still edit after
                approval until you schedule.
              </p>
              <Button
                onClick={() => approveMutation.mutate()}
                disabled={approveMutation.isPending}
              >
                {approveMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    Approving...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4 mr-2" />
                    Approve draft
                  </>
                )}
              </Button>
            </div>
          )}

          {draft.status === "approved" && (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Publish to DEV.to now or pick a schedule time. LinkedIn uses copy-to-clipboard
                after DEV.to publishes.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
                <div className="space-y-2 flex-1">
                  <Label htmlFor="schedule-at">Schedule for (optional)</Label>
                  <Input
                    id="schedule-at"
                    type="datetime-local"
                    value={scheduleAt}
                    onChange={(event) => setScheduleAt(event.target.value)}
                  />
                </div>
                <Button
                  variant="outline"
                  onClick={() => scheduleMutation.mutate(toIsoSchedule(scheduleAt))}
                  disabled={scheduleMutation.isPending}
                >
                  {scheduleMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : null}
                  {scheduleAt ? "Schedule publish" : "Publish now"}
                </Button>
              </div>
            </div>
          )}

          {canReschedule && (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Update when this draft should publish to DEV.to.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
                <div className="space-y-2 flex-1">
                  <Label htmlFor="reschedule-at">Scheduled time</Label>
                  <Input
                    id="reschedule-at"
                    type="datetime-local"
                    value={scheduleAt}
                    onChange={(event) => setScheduleAt(event.target.value)}
                  />
                </div>
                <Button
                  variant="outline"
                  onClick={() => {
                    const iso = toIsoSchedule(scheduleAt);
                    if (!iso) {
                      return;
                    }
                    rescheduleMutation.mutate(iso);
                  }}
                  disabled={rescheduleMutation.isPending || !scheduleAt}
                >
                  {rescheduleMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : null}
                  Update schedule
                </Button>
                <Button
                  onClick={() => scheduleMutation.mutate(null)}
                  disabled={scheduleMutation.isPending}
                >
                  {scheduleMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : null}
                  Publish now
                </Button>
              </div>
            </div>
          )}

          {(draft.status === "scheduled" || publishJob) && (
            <div className="space-y-2 text-sm">
              <p>
                Publish job:{" "}
                <span className="font-medium">{publishJob?.status ?? "pending"}</span>
              </p>
              {publishJob?.status === "running" && (
                <p className="text-muted-foreground">
                  Publishing in progress — schedule cannot be changed.
                </p>
              )}
              {publishJob?.scheduled_at && (
                <p className="text-muted-foreground">
                  Scheduled for {new Date(publishJob.scheduled_at).toLocaleString()}
                </p>
              )}
              {publishJob?.error_message && (
                <p className="text-red-500">{publishJob.error_message}</p>
              )}
            </div>
          )}

          {draft.status === "failed" && (
            <Button
              variant="outline"
              onClick={() => retryMutation.mutate()}
              disabled={retryMutation.isPending}
            >
              {retryMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <RefreshCw className="w-4 h-4 mr-2" />
              )}
              Retry publish
            </Button>
          )}

          {linkedinClipboardText && (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">
                LinkedIn post with live article link:
              </p>
              <pre className="rounded-xl border border-border bg-muted/40 p-3 text-sm whitespace-pre-wrap">
                {linkedinClipboardText}
              </pre>
              <Button variant="outline" onClick={handleCopyLinkedin}>
                <ClipboardCopy className="w-4 h-4 mr-2" />
                Copy to clipboard
              </Button>
            </div>
          )}

          {clipboardMessage && (
            <p className="text-sm text-green-600">{clipboardMessage}</p>
          )}
          {approveMutation.error && (
            <p className="text-sm text-red-500">{extractApiError(approveMutation.error)}</p>
          )}
          {scheduleMutation.error && (
            <p className="text-sm text-red-500">{extractApiError(scheduleMutation.error)}</p>
          )}
          {rescheduleMutation.error && (
            <p className="text-sm text-red-500">{extractApiError(rescheduleMutation.error)}</p>
          )}
          {retryMutation.error && (
            <p className="text-sm text-red-500">{extractApiError(retryMutation.error)}</p>
          )}
        </div>

        {draft.cover_images && draft.cover_images.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {draft.cover_images.map((cover) => (
              <DraftCoverImageEditor
                key={cover.id}
                draftId={draft.id}
                cover={cover}
                disabled={!isEditable}
                onUpdated={() => {
                  queryClient.invalidateQueries({ queryKey: ["content-draft", id] });
                  queryClient.invalidateQueries({ queryKey: ["content-drafts"] });
                }}
              />
            ))}
          </div>
        )}

        {draft.devto_article && (
          <div className="space-y-4 p-6 rounded-2xl border border-border bg-card">
            <h3 className="font-bold text-primary">DEV.to article</h3>
            <div className="space-y-2">
              <Label htmlFor="devto-title">Title</Label>
              <Input
                id="devto-title"
                value={devtoTitle}
                onChange={(e) => setDevtoTitle(e.target.value)}
                disabled={!isEditable}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="devto-tags">Tags</Label>
              <Input
                id="devto-tags"
                value={devtoTags}
                onChange={(e) => setDevtoTags(e.target.value)}
                disabled={!isEditable}
              />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="devto-body">Markdown</Label>
                <textarea
                  id="devto-body"
                  className="min-h-[24rem] flex-1 w-full resize-none rounded-xl border border-border bg-background px-4 py-3 text-sm font-mono disabled:opacity-60"
                  value={devtoBody}
                  onChange={(e) => setDevtoBody(e.target.value)}
                  disabled={!isEditable}
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label>Preview</Label>
                <pre className="min-h-[24rem] flex-1 w-full rounded-xl border border-border bg-muted/50 px-4 py-3 text-sm whitespace-pre-wrap overflow-y-auto">
                  {devtoBody}
                </pre>
              </div>
            </div>
          </div>
        )}

        {draft.linkedin_post && (
          <div className="space-y-4 p-6 rounded-2xl border border-border bg-card">
            <h3 className="font-bold text-primary">LinkedIn post</h3>
            <textarea
              rows={4}
              className="w-full rounded-xl border border-border bg-background px-4 py-3 text-sm disabled:opacity-60"
              value={linkedinTeaser}
              onChange={(e) => setLinkedinTeaser(e.target.value)}
              disabled={!isEditable}
            />
            <p className="text-xs text-muted-foreground">
              {linkedinTeaser.length} characters
            </p>
          </div>
        )}
      </div>

      {showDeleteConfirm && (
        <DeleteDraftConfirmModal
          topic={draft.topic}
          isDeleting={deleteMutation.isPending}
          onClose={() => setShowDeleteConfirm(false)}
          onConfirm={() => deleteMutation.mutate()}
        />
      )}
    </DashboardLayout>
  );
};

export default DraftEditorPage;
