import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Dashboard from "./Dashboard";
import { useAuth, Role } from "../contexts/AuthContext";
import * as sdk from "../client/sdk.gen";
import {
  createMockAiConfig,
  createMockAiModelsCatalog,
  createMockContentDraft,
  createMockContentDraftDetail,
  createMockContentDraftsList,
} from "../test/factories";

vi.mock("../client/sdk.gen", () => ({
  listContentDraftsApiV1ContentDraftsGet: vi.fn(),
  generateContentDraftApiV1ContentDraftsGeneratePost: vi.fn(),
  readAiConfigApiV1SettingsAiGet: vi.fn(),
  readAiModelsCatalogApiV1SettingsAiModelsGet: vi.fn(),
  updateAiConfigApiV1SettingsAiPatch: vi.fn(),
}));

vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(),
  Role: { SUPER: "SUPER", ADMIN: "ADMIN", USER: "USER" },
  AuthProvider: ({ children }: any) => <div>{children}</div>,
}));

const renderDashboard = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

describe("Dashboard Component", () => {
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
    vi.mocked(sdk.readAiConfigApiV1SettingsAiGet).mockResolvedValue({
      data: createMockAiConfig({ saved_api_keys: { openai: true } }),
    } as any);
    vi.mocked(sdk.readAiModelsCatalogApiV1SettingsAiModelsGet).mockResolvedValue({
      data: createMockAiModelsCatalog(),
    } as any);
    vi.mocked(sdk.updateAiConfigApiV1SettingsAiPatch).mockResolvedValue({
      data: createMockAiConfig({ saved_api_keys: { openai: true } }),
    } as any);
    vi.mocked(sdk.listContentDraftsApiV1ContentDraftsGet).mockResolvedValue({
      data: createMockContentDraftsList(),
    } as any);
    vi.mocked(sdk.generateContentDraftApiV1ContentDraftsGeneratePost).mockResolvedValue({
      data: createMockContentDraftDetail(),
    } as any);
  });

  it("renders generate draft UI with provider and model selectors", async () => {
    renderDashboard();

    expect(screen.getByText(/Create Content/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByLabelText(/^Provider$/i)).toBeInTheDocument();
    });
    expect(screen.getByLabelText(/^Model$/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Generate draft/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Configure providers/i })).toHaveAttribute(
      "href",
      "/settings",
    );
  });

  it("shows only configured providers", async () => {
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByLabelText(/^Provider$/i)).toBeInTheDocument();
    });

    const providerSelect = screen.getByLabelText(/^Provider$/i) as HTMLSelectElement;
    const labels = Array.from(providerSelect.options).map((o) => o.text);
    expect(labels.some((l) => l.includes("OpenAI"))).toBe(true);
    expect(labels.some((l) => l.includes("Google Gemini"))).toBe(false);
  });

  it("prompts to configure providers when none are ready", async () => {
    vi.mocked(sdk.readAiConfigApiV1SettingsAiGet).mockResolvedValue({
      data: createMockAiConfig({ saved_api_keys: {} }),
    } as any);
    vi.mocked(sdk.readAiModelsCatalogApiV1SettingsAiModelsGet).mockResolvedValue({
      data: {
        ...createMockAiModelsCatalog(),
        providers: createMockAiModelsCatalog().providers.filter(
          (p) => p.requires_api_key !== false && !p.is_custom,
        ),
      },
    } as any);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText(/No providers are configured yet/i)).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /Generate draft/i })).toBeDisabled();
  });

  it("disables generate button when topic is empty", async () => {
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByLabelText(/^Provider$/i)).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /Generate draft/i })).toBeDisabled();
  });

  it("lists recent drafts", async () => {
    vi.mocked(sdk.listContentDraftsApiV1ContentDraftsGet).mockResolvedValue({
      data: createMockContentDraftsList([
        createMockContentDraft({ topic: "First draft" }),
        createMockContentDraft({ id: "draft-2", topic: "Second draft" }),
      ]),
    } as any);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("Recent drafts")).toBeInTheDocument();
    });
    expect(screen.getByText("First draft")).toBeInTheDocument();
    expect(screen.getByText("Second draft")).toBeInTheDocument();
  });

  it("generates draft and shows preview", async () => {
    const detail = createMockContentDraftDetail({
      topic: "Building with FastAPI",
    });
    vi.mocked(sdk.generateContentDraftApiV1ContentDraftsGeneratePost).mockResolvedValue({
      data: detail,
    } as any);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByLabelText(/^Provider$/i)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/Topic/i), {
      target: { value: "Building with FastAPI" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Generate draft/i }));

    await waitFor(() => {
      expect(sdk.generateContentDraftApiV1ContentDraftsGeneratePost).toHaveBeenCalledWith({
        body: { topic: "Building with FastAPI", user_prompt: undefined },
      });
    });

    expect(screen.getByText(/Preview — Building with FastAPI/i)).toBeInTheDocument();
    expect(screen.getByText("DEV.to article")).toBeInTheDocument();
  });

  it("shows error when generation fails", async () => {
    vi.mocked(sdk.generateContentDraftApiV1ContentDraftsGeneratePost).mockResolvedValue({
      error: { detail: "OpenAI API key required. Add your key in Settings → AI Agent." },
    } as any);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByLabelText(/^Provider$/i)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/Topic/i), {
      target: { value: "Should fail" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Generate draft/i }));

    await waitFor(() => {
      expect(screen.getByText(/OpenAI API key required/i)).toBeInTheDocument();
    });
  });
});
