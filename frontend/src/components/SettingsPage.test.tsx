import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import SettingsPage from "./SettingsPage";
import * as sdk from "../client/sdk.gen";
import {
  createMockAiConfig,
  createMockAiModelsCatalog,
  createMockPlatformConfig,
} from "../test/factories";

vi.mock("../client/sdk.gen", () => ({
  readPlatformConfigApiV1SettingsPlatformGet: vi.fn(),
  updatePlatformConfigApiV1SettingsPlatformPatch: vi.fn(),
  readAiConfigApiV1SettingsAiGet: vi.fn(),
  readAiModelsCatalogApiV1SettingsAiModelsGet: vi.fn(),
  updateAiConfigApiV1SettingsAiPatch: vi.fn(),
  createCustomAiProviderApiV1SettingsAiProvidersPost: vi.fn(),
  deleteCustomAiProviderApiV1SettingsAiProvidersProviderIdDelete: vi.fn(),
  refreshProviderModelsApiV1SettingsAiProvidersProviderSlugRefreshModelsPost: vi.fn(),
}));

const renderSettingsPage = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <SettingsPage />
    </QueryClientProvider>,
  );
};

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(sdk.readPlatformConfigApiV1SettingsPlatformGet).mockResolvedValue({
      data: createMockPlatformConfig(),
    } as any);
    vi.mocked(sdk.readAiConfigApiV1SettingsAiGet).mockResolvedValue({
      data: createMockAiConfig(),
    } as any);
    vi.mocked(sdk.readAiModelsCatalogApiV1SettingsAiModelsGet).mockResolvedValue({
      data: createMockAiModelsCatalog(),
    } as any);
    vi.mocked(sdk.updatePlatformConfigApiV1SettingsPlatformPatch).mockResolvedValue({
      data: createMockPlatformConfig({ has_devto_api_key: true }),
    } as any);
    vi.mocked(sdk.updateAiConfigApiV1SettingsAiPatch).mockResolvedValue({
      data: createMockAiConfig({
        saved_api_keys: { openai: true },
      }),
    } as any);
  });

  it("shows loading spinner while settings load", () => {
    vi.mocked(sdk.readPlatformConfigApiV1SettingsPlatformGet).mockImplementation(
      () => new Promise(() => {}) as any,
    );
    vi.mocked(sdk.readAiConfigApiV1SettingsAiGet).mockImplementation(
      () => new Promise(() => {}) as any,
    );
    vi.mocked(sdk.readAiModelsCatalogApiV1SettingsAiModelsGet).mockImplementation(
      () => new Promise(() => {}) as any,
    );

    renderSettingsPage();
    expect(document.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("renders AI Providers tab with connected providers only", async () => {
    renderSettingsPage();

    await waitFor(() => {
      expect(screen.getByText("Configuration")).toBeInTheDocument();
    });
    expect(screen.queryByText("OpenAI")).not.toBeInTheDocument();
    expect(screen.getByText("Ollama (local)")).toBeInTheDocument();
    expect(screen.getByText("qwen3:8b")).toBeInTheDocument();
    expect(screen.getByText("Cover image model")).toBeInTheDocument();
    expect(
      screen.getByText(/Connect Gemini or OpenAI in Add provider/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Save provider settings/i }),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText(/^Model$/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/^Provider$/i)).not.toBeInTheDocument();
  });

  it("lists unconfigured providers inside Add provider", async () => {
    renderSettingsPage();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Add provider" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Show add provider" }));

    const providerSelect = screen.getByLabelText(/^Provider$/i) as HTMLSelectElement;
    const options = Array.from(providerSelect.options).map((option) => option.text);
    expect(options).toContain("OpenAI");
    expect(options).toContain("Google Gemini");
    expect(options).not.toContain("Ollama (local)");
  });

  it("adds a built-in provider from Add provider", async () => {
    renderSettingsPage();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Add provider" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Show add provider" }));
    fireEvent.change(screen.getByLabelText(/^Provider$/i), {
      target: { value: "openai" },
    });
    fireEvent.change(screen.getByLabelText(/OpenAI API key/i), {
      target: { value: "sk-test-openai" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^Connect provider$/i }));

    await waitFor(() => {
      expect(sdk.updateAiConfigApiV1SettingsAiPatch).toHaveBeenCalledWith({
        body: {
          provider_api_keys: { openai: "sk-test-openai" },
        },
      });
    });
  });

  it("saves OpenAI API key without changing active model selection", async () => {
    vi.mocked(sdk.readAiConfigApiV1SettingsAiGet).mockResolvedValue({
      data: createMockAiConfig({ saved_api_keys: { openai: true } }),
    } as any);

    renderSettingsPage();

    await waitFor(() => {
      expect(screen.getByLabelText(/OpenAI API key/i)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText(/OpenAI API key/i), {
      target: { value: "sk-test-openai" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Save provider settings/i }));

    await waitFor(() => {
      expect(sdk.updateAiConfigApiV1SettingsAiPatch).toHaveBeenCalledWith({
        body: expect.objectContaining({
          provider_api_keys: { openai: "sk-test-openai" },
        }),
      });
    });

    const body = vi.mocked(sdk.updateAiConfigApiV1SettingsAiPatch).mock.calls[0][0].body;
    expect(body).not.toHaveProperty("provider");
    expect(body).not.toHaveProperty("model");
    expect(screen.getByText("Settings saved successfully.")).toBeInTheDocument();
  });

  it("switches to Platforms tab", async () => {
    renderSettingsPage();

    await waitFor(() => {
      expect(screen.getByText("Configuration")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Platforms/i }));

    expect(screen.getByText("Enable DEV.to")).toBeInTheDocument();
    expect(screen.getByText("Enable LinkedIn")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Save platform settings/i }),
    ).toBeInTheDocument();
  });

  it("shows saved key indicator when API key already stored", async () => {
    vi.mocked(sdk.readAiConfigApiV1SettingsAiGet).mockResolvedValue({
      data: createMockAiConfig({ saved_api_keys: { openai: true } }),
    } as any);

    renderSettingsPage();

    await waitFor(() => {
      expect(screen.getByText("(saved)")).toBeInTheDocument();
    });
  });

  it("shows only cover image models with saved provider API keys", async () => {
    vi.mocked(sdk.readAiConfigApiV1SettingsAiGet).mockResolvedValue({
      data: createMockAiConfig({ saved_api_keys: { gemini: true } }),
    } as any);

    renderSettingsPage();

    await waitFor(() => {
      expect(screen.getByLabelText(/Cover image model/i)).toBeInTheDocument();
    });

    const select = screen.getByLabelText(/Cover image model/i) as HTMLSelectElement;
    const options = Array.from(select.options).map((option) => option.text);
    expect(options.some((text) => text.includes("Gemini 3 Pro Image"))).toBe(true);
    expect(options.some((text) => text.includes("DALL-E 3"))).toBe(false);
  });

  it("refreshes provider models when refresh is clicked", async () => {
    vi.mocked(
      sdk.refreshProviderModelsApiV1SettingsAiProvidersProviderSlugRefreshModelsPost,
    ).mockResolvedValue({
      data: {
        slug: "ollama",
        models: [
          { id: "qwen3:8b", label: "qwen3:8b" },
          { id: "gemma4:12b", label: "gemma4:12b" },
        ],
        added_count: 1,
        total_count: 2,
        message: "Added 1 new model(s).",
      },
    } as any);

    renderSettingsPage();

    await waitFor(() => {
      expect(screen.getByText("Ollama (local)")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Refresh models/i }));

    await waitFor(() => {
      expect(
        sdk.refreshProviderModelsApiV1SettingsAiProvidersProviderSlugRefreshModelsPost,
      ).toHaveBeenCalledWith({
        path: { provider_slug: "ollama" },
        query: undefined,
      });
    });
    expect(screen.getByText("Added 1 new model(s).")).toBeInTheDocument();
  });

  it("displays API error when save fails", async () => {
    vi.mocked(sdk.updateAiConfigApiV1SettingsAiPatch).mockResolvedValue({
      error: { detail: "OpenAI API key required" },
    } as any);

    renderSettingsPage();

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Save provider settings/i }),
      ).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Save provider settings/i }));

    await waitFor(() => {
      expect(screen.getByText("OpenAI API key required")).toBeInTheDocument();
    });
  });

  it("requires provider name confirmation before removing a custom provider", async () => {
    vi.mocked(
      sdk.deleteCustomAiProviderApiV1SettingsAiProvidersProviderIdDelete,
    ).mockResolvedValue({} as any);
    vi.mocked(sdk.readAiModelsCatalogApiV1SettingsAiModelsGet).mockResolvedValue({
      data: {
        ...createMockAiModelsCatalog(),
        providers: [
          ...createMockAiModelsCatalog().providers,
          {
            slug: "custom-lm-studio",
            label: "My LM Studio",
            default_model: "local-model",
            requires_api_key: true,
            is_custom: true,
            provider_id: "provider-1",
            models: [{ id: "local-model", label: "Local Model" }],
          },
        ],
      },
    } as any);

    renderSettingsPage();

    await waitFor(() => {
      expect(screen.getByText("My LM Studio")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /^Remove$/i }));

    expect(screen.getByText("Remove provider?")).toBeInTheDocument();
    const removeButton = screen.getByRole("button", { name: "Remove provider" });
    expect(removeButton).toBeDisabled();

    fireEvent.change(screen.getByLabelText(/Type My LM Studio to confirm/i), {
      target: { value: "My LM Studio" },
    });
    fireEvent.click(removeButton);

    await waitFor(() => {
      expect(
        sdk.deleteCustomAiProviderApiV1SettingsAiProvidersProviderIdDelete,
      ).toHaveBeenCalledWith({
        path: { provider_id: "provider-1" },
      });
    });
  });

  it("requires provider name confirmation before removing a saved API key", async () => {
    vi.mocked(sdk.readAiConfigApiV1SettingsAiGet).mockResolvedValue({
      data: createMockAiConfig({ saved_api_keys: { openai: true } }),
    } as any);

    renderSettingsPage();

    await waitFor(() => {
      expect(screen.getByText("OpenAI")).toBeInTheDocument();
    });

    fireEvent.click(screen.getAllByRole("button", { name: /^Remove$/i })[0]);

    expect(screen.getByText("Remove API key?")).toBeInTheDocument();
    const removeButton = screen.getByRole("button", { name: "Remove API key" });
    expect(removeButton).toBeDisabled();

    fireEvent.change(screen.getByLabelText(/Type OpenAI to confirm/i), {
      target: { value: "OpenAI" },
    });
    fireEvent.click(removeButton);

    await waitFor(() => {
      expect(sdk.updateAiConfigApiV1SettingsAiPatch).toHaveBeenCalledWith({
        body: {
          provider_api_keys: { openai: "" },
        },
      });
    });
  });
});
