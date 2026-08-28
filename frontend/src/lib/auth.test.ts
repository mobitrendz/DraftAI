import { describe, it, expect, vi, beforeEach } from "vitest";
import { auth } from "./auth";
import { client } from "../client/client.gen";

// Mock the client
vi.mock("../client/client.gen", () => ({
  client: {
    setConfig: vi.fn(),
  },
}));

describe("Auth Utility", () => {
  beforeEach(() => {
    // Mock localStorage
    const storage: Record<string, string> = {};
    (globalThis as any).localStorage = {
      getItem: vi.fn((key) => storage[key] || null),
      setItem: vi.fn((key, value) => {
        storage[key] = value;
      }),
      removeItem: vi.fn((key) => {
        delete storage[key];
      }),
      clear: vi.fn(() => {
        for (const key in storage) delete storage[key];
      }),
      length: 0,
      key: vi.fn(),
    } as any;
    vi.clearAllMocks();
  });

  it("sets the token correctly", () => {
    const token = "test-token";
    auth.setToken(token);

    expect(localStorage.getItem("auth_token")).toBe(token);
    expect(client.setConfig).toHaveBeenCalledWith({
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  });

  it("clears the token correctly", () => {
    localStorage.setItem("auth_token", "old-token");
    auth.clearToken();

    expect(localStorage.getItem("auth_token")).toBeNull();
    expect(client.setConfig).toHaveBeenCalledWith({
      headers: {
        Authorization: undefined,
      },
    });
  });

  it("checks authentication status", () => {
    expect(auth.isAuthenticated()).toBe(false);
    localStorage.setItem("auth_token", "valid-token");
    expect(auth.isAuthenticated()).toBe(true);
  });

  it("initializes from localStorage", () => {
    const token = "saved-token";
    localStorage.setItem("auth_token", token);
    auth.initialize();

    expect(client.setConfig).toHaveBeenCalledWith({
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  });
});
