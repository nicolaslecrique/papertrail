import { defineConfig } from "@hey-api/openapi-ts";

// Generates the typed API client from the backend's committed OpenAPI schema
// (../openapi.json, exported by scripts/export-openapi.py). Offline and
// deterministic: check.sh regenerates this and fails if src/client drifts.
export default defineConfig({
  input: "../openapi.json",
  output: {
    path: "src/client",
    // The client is generated code — keep it out of the formatter/linter's way.
    indexFile: true,
  },
  plugins: [
    {
      // The Fetch API client (runtime bundled with @hey-api/openapi-ts).
      name: "@hey-api/client-fetch",
      // Our baseUrl + credentials come from this file at client init time.
      runtimeConfigPath: "./src/lib/api-config.ts",
    },
    // TanStack Query artifacts: *Options() for queries, *Mutation() for writes.
    "@tanstack/react-query",
  ],
});
