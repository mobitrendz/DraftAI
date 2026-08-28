import { z } from "zod";

/**
 * Validate environment variables at runtime using Zod.
 * This ensures that the application doesn't start with missing or invalid configuration.
 */

const envSchema = z.object({
  VITE_API_URL: z.string().default(""),
  VITE_ENV: z
    .enum(["development", "production", "test"])
    .default("development"),
});

// Parse and validate current environment variables
const parsedEnv = envSchema.safeParse(import.meta.env);

if (!parsedEnv.success) {
  console.error("❌ Invalid environment variables:", parsedEnv.error.format());
  throw new Error("Invalid environment variables");
}

export const env = parsedEnv.data;
