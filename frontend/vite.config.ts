import { defineConfig } from "vite";

import { tanstackStart } from "@tanstack/react-start/plugin/vite";

import viteReact from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { nitro } from "nitro/vite";

// The browser talks only to this (TanStack Start / Nitro) server; /api is proxied
// to FastAPI so the app and API share an origin, keeping the httponly auth cookie
// first-party. `devProxy` covers `pnpm dev` (and the e2e run); `routeRules` bakes
// the same proxy into the production server (`pnpm start`). Override the target
// with API_PROXY_TARGET (e.g. the e2e run points it at the test API port).
const apiTarget = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";

const config = defineConfig({
  resolve: { tsconfigPaths: true },
  plugins: [
    nitro({
      rollupConfig: { external: [/^@sentry\//] },
      devProxy: {
        "/api": { target: `${apiTarget}/api`, changeOrigin: true },
      },
      routeRules: {
        "/api/**": { proxy: { to: `${apiTarget}/api/**` } },
      },
    }),
    tailwindcss(),
    tanstackStart(),
    viteReact(),
  ],
});

export default config;
