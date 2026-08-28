import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import DraftEditorPage from "./DraftEditorPage";
import { useAuth, Role } from "../contexts/AuthContext";
import * as sdk from "../client/sdk.gen";
import { createMockContentDraftDetail } from "../test/factories";

vi.mock("../client/sdk.gen", () => ({
  getContentDraftApiV1ContentDraftsDraftIdGet: vi.fn(),
  updateContentDraftApiV1ContentDraftsDraftIdPatch: vi.fn(),
  deleteContentDraftApiV1ContentDraftsDraftIdDelete: vi.fn(),
  approveContentDraftApiV1ContentDraftsDraftIdApprovePost: vi.fn(),
  scheduleContentDraftApiV1ContentDraftsDraftIdSchedulePost: vi.fn(),
  rescheduleContentDraftApiV1ContentDraftsDraftIdSchedulePatch: vi.fn(),
  getContentDraftPublishStatusApiV1ContentDraftsDraftIdPublishStatusGet: vi.fn(),
  retryContentDraftPublishApiV1ContentDraftsDraftIdRetryPublishPost: vi.fn(),
}));

vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(),
  Role: { SUPER: "SUPER", ADMIN: "ADMIN", USER: "USER" },
  AuthProvider: ({ children }: any) => <div>{children}</div>,
}));

const renderEditor = (draftId = "draft-1") => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/drafts/${draftId}`]}>
        <Routes>
          <Route path="/drafts/:id" element={<DraftEditorPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

describe("DraftEditorPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useAuth).mockReturnValue({
      user: {
        id: "user-1",
        email: "user@test.com",
        role: "user",
        full_name: "Normal User",
        is_active: true,
      },
      role: Role.USER,
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      hasPermission: vi.fn((r) => r === Role.USER),
      accessDenied: false,
      setAccessDenied: vi.fn(),
      token: "fake-token",
    });
    vi.mocked(sdk.getContentDraftApiV1ContentDraftsDraftIdGet).mockResolvedValue({
      data: createMockContentDraftDetail({
        cover_images: [
          {
            id: "cover-devto",
            platform: "devto",
            storage_key: "covers/draft-1/devto.png",
            prompt_used: "Abstract tech illustration",
            provider: "pillow-template",
            image_url: "/api/v1/public/covers/draft-1/devto.png?v=1",
          },
          {
            id: "cover-linkedin",
            platform: "linkedin",
            storage_key: null,
            prompt_used: "Abstract tech illustration",
            provider: null,
            image_url: null,
          },
        ],
      }),
    } as any);
    vi.mocked(sdk.updateContentDraftApiV1ContentDraftsDraftIdPatch).mockResolvedValue({
      data: createMockContentDraftDetail({
        devto_article: {
          id: "devto-1",
          title: "Updated title",
          body_markdown: "# Updated",
          tags: "python",
          cover_image_id: null,
        },
      }),
    } as any);
    vi.mocked(sdk.deleteContentDraftApiV1ContentDraftsDraftIdDelete).mockResolvedValue({
      data: undefined,
    } as any);
  });

  it("loads draft and shows edit fields", async () => {
    renderEditor();

    expect(await screen.findByText(/Edit draft/i)).toBeInTheDocument();
    expect(screen.getByDisplayValue("Test Article Title")).toBeInTheDocument();
    expect(screen.getByDisplayValue(/This is test content/i)).toBeInTheDocument();
  });

  it("shows editable cover upload controls", async () => {
    renderEditor();

    expect(await screen.findByText(/DEV.to cover/i)).toBeInTheDocument();
    expect(screen.getByText(/LinkedIn cover/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Replace image/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Upload image/i })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /Regenerate/i })).toHaveLength(2);
    expect(screen.getAllByDisplayValue("Abstract tech illustration")).toHaveLength(2);
  });

  it("saves draft changes", async () => {
    renderEditor();

    const titleInput = await screen.findByDisplayValue("Test Article Title");
    fireEvent.change(titleInput, {
      target: { value: "Updated title" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Save changes/i }));

    await waitFor(() => {
      expect(sdk.updateContentDraftApiV1ContentDraftsDraftIdPatch).toHaveBeenCalled();
    });
  });

  it("shows delete confirmation and deletes draft", async () => {
    renderEditor();

    fireEvent.click(await screen.findByRole("button", { name: /Delete draft/i }));
    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(within(dialog).getByText(/This action cannot be undone/i)).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole("button", { name: /^Delete draft$/i }));

    await waitFor(() => {
      expect(sdk.deleteContentDraftApiV1ContentDraftsDraftIdDelete).toHaveBeenCalledWith({
        path: { draft_id: "draft-1" },
      });
    });
  });
});
