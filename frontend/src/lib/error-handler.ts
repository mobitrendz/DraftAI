/**
 * Centralized error handling for FastAPI backend responses.
 * Specifically extracts the 'detail' key from FastAPI HTTPException responses.
 */

export interface ApiError {
  detail: string | Array<{ loc: string[]; msg: string; type: string }>;
  status?: number;
}

export const extractApiError = (error: any): string => {
  if (!error) return "An unexpected error occurred.";

  // If it's a string, return it
  if (typeof error === "string") return error;

  // Handle Fetch / @hey-api error objects
  const data = error.data || error.error || error;

  if (data && data.detail) {
    if (typeof data.detail === "string") {
      return data.detail;
    }

    // Handle Pydantic validation errors (array of objects)
    if (Array.isArray(data.detail)) {
      return data.detail
        .map(
          (err: { loc?: (string | number)[]; msg: string }) =>
            `${err.loc?.join(".") || "error"}: ${err.msg}`,
        )
        .join("; ");
    }
  }

  // Fallback to standard error message
  return error.message || "An unknown network error occurred.";
};
