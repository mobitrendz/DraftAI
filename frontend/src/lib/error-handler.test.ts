import { describe, it, expect } from "vitest";
import { extractApiError } from "./error-handler";

describe("error-handler - extractApiError", () => {
  it("extracts string detail from FastAPI HTTPException", () => {
    const error = {
      data: { detail: "User with this email already exists" },
    };
    expect(extractApiError(error)).toBe("User with this email already exists");
  });

  it("extracts and formats Pydantic validation errors (array of objects)", () => {
    const error = {
      data: {
        detail: [
          {
            loc: ["body", "email"],
            msg: "value is not a valid email address",
            type: "value_error.email",
          },
          {
            loc: ["body", "password"],
            msg: "field required",
            type: "value_error.missing",
          },
        ],
      },
    };
    expect(extractApiError(error)).toBe(
      "body.email: value is not a valid email address; body.password: field required",
    );
  });

  it("handles standard Error objects", () => {
    const error = new Error("Network timeout");
    expect(extractApiError(error)).toBe("Network timeout");
  });

  it("handles raw string errors", () => {
    expect(extractApiError("Something went wrong")).toBe(
      "Something went wrong",
    );
  });

  it("provides fallback for undefined errors", () => {
    expect(extractApiError(null)).toBe("An unexpected error occurred.");
    expect(extractApiError({})).toBe("An unknown network error occurred.");
  });

  it("handles @hey-api/client-fetch response structure", () => {
    const error = {
      error: { detail: "Unauthorized access" },
    };
    expect(extractApiError(error)).toBe("Unauthorized access");
  });
});
