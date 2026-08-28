import { env } from "./env";

/** API base URL. Empty in dev uses the Vite proxy (same origin, no CORS). */
export const getApiBaseUrl = () => {
  if (env.VITE_API_URL) {
    return env.VITE_API_URL.replace(/\/$/, "");
  }
  if (import.meta.env.DEV) {
    return "";
  }
  return "http://localhost:8000";
};
