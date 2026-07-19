# Frontend (`frontend/`)

The user-facing app is a self-contained **React 19 + TanStack Start** project in
`frontend/`, separate from the Python backend. It talks to the FastAPI REST API
only through a **generated, typed client**, and is styled with **Tailwind CSS v4**
and **shadcn/ui**. Package manager is **pnpm**.

## How it fits together

```
Browser ─▶ TanStack Start (Nitro) server ─serves─▶ React app
   │           └─ proxies /api ─▶ FastAPI (uvicorn) ─▶ Postgres
   └──────────────── one origin (the httponly auth cookie stays first-party) ──┘
```

- **Same origin.** The browser only ever talks to the Start server; `/api` is
  **proxied** to FastAPI. Dev uses Nitro's `devProxy`, production bakes the same
  rule via Nitro `routeRules` (both in `vite.config.ts`, target overridable with
  `API_PROXY_TARGET`). This keeps the httponly JWT cookie first-party, so no CORS
  and no token handling in JS.
- **Selective SSR.** Public/content routes are server-rendered (so future
  per-record pages are search-indexable and produce rich link previews); the
  interactive auth screens and dashboard opt out with `ssr: false` (they run in the
  browser, where the cookie is available). See any route in `src/routes/`.
- **Auth.** Login/logout/register/verify/reset all go through the generated client
  to fastapi-users' endpoints; the dashboard's `beforeLoad` calls `/api/users/me`
  and redirects to `/login` on 401.

## Run it

```bash
cd frontend
pnpm install
pnpm dev            # http://localhost:3000, proxies /api to http://127.0.0.1:8000
```

Run the backend separately (`uv run uvicorn app.main:app --reload --port 8000`).

## The generated API client (@hey-api/openapi-ts)

`src/client/` is **generated** from the committed `openapi.json` at the repo root —
never edit it by hand. TanStack Query artifacts (`…Options()` / `…Mutation()`) come
from the `@tanstack/react-query` plugin; baseUrl + `credentials: "include"` are set
in `src/lib/api-config.ts`. Config lives in `openapi-ts.config.ts`.

When you change a backend route or Pydantic model, regenerate both the schema and
the client, then commit them:

```bash
uv run python scripts/export-openapi.py      # backend → openapi.json
cd frontend && pnpm gen:api                  # openapi.json → src/client/
```

`check.sh` re-runs exactly these and fails if the committed `openapi.json` /
`src/client` are stale, so the generated client can never silently fall behind the
backend. Cleaner client symbol names come from the backend's
`generate_unique_id_function` (see `app/main.py`).

## shadcn/ui is vendored

`src/components/ui/` holds shadcn components, treated as an **external vendor
folder**: kept pristine so they can be re-pulled/updated from the shadcn reference.
They're excluded from ESLint, Knip, and dependency-cruiser. Add or update
components with the CLI (do not hand-edit):

```bash
cd frontend && pnpm dlx shadcn@latest add <component>
```

`components.json` points the CLI at `src/styles.css` (the Tailwind v4 entry, which
holds the theme tokens) and the `@/*` alias.

## Tooling (strict)

All run by `check.sh` (and locally via the `package.json` scripts):

- **`tsc --noEmit`** — strict, plus `noUncheckedIndexedAccess` / `noImplicitOverride`.
- **ESLint** (`eslint . --max-warnings 0`) — typescript-eslint `strictTypeChecked`
  + `stylisticTypeChecked` (type-aware), React + React Hooks, the TanStack
  Router/Query plugins, and `eslint-plugin-better-tailwindcss` (Tailwind v4). The
  generated `src/client` and vendored `src/components/ui` are ignored.
- **Prettier** (`prettier-plugin-tailwindcss` sorts classes).
- **Knip** — unused files / exports / dependencies.
- **dependency-cruiser** — no circular deps, no orphans, and the vendored `ui/`
  folder may not import app code.

Generated files (`src/client`, `src/routeTree.gen.ts`) are excluded from the
linters; `routeTree.gen.ts` is gitignored and regenerated (`pnpm gen:routes`).
