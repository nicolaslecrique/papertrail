# papertrail frontend

React 19 + TanStack Start (SSR) app that consumes the FastAPI backend through a
generated, typed client. Styled with Tailwind CSS v4 + shadcn/ui; server state via
TanStack Query. Package manager: **pnpm**.

```bash
pnpm install
pnpm dev            # http://localhost:3000, proxies /api to http://127.0.0.1:8000
```

Run the backend separately (`uv run uvicorn app.main:app --reload --port 8000`).

See [../docs/frontend.md](../docs/frontend.md) for the architecture (same-origin
`/api` proxy, selective SSR, auth), the generated API client + drift guard, how
shadcn/ui is vendored, and the tooling. Browser end-to-end tests live in
[../e2e/](../e2e/) (see [../docs/e2e-tests.md](../docs/e2e-tests.md)); this project
has no unit-test runner of its own.
