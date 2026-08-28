import { defineConfig } from "@hey-api/openapi-ts";
import { existsSync } from "node:fs";

const input = existsSync("./openapi.json")
  ? "./openapi.json"
  : "http://localhost:8000/openapi.json";

export default defineConfig({
  input,
  output: "src/client",
  plugins: [
    "@hey-api/client-fetch",
    "@hey-api/typescript",
    {
      name: "@hey-api/sdk",
      asSDK: true,
    },
    "@tanstack/react-query",
  ],
});
