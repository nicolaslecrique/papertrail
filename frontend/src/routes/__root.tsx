import type { QueryClient } from "@tanstack/react-query";
import {
  HeadContent,
  Link,
  Scripts,
  createRootRouteWithContext,
} from "@tanstack/react-router";

import appCss from "../styles.css?url";

interface RouterContext {
  queryClient: QueryClient;
}

export const Route = createRootRouteWithContext<RouterContext>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "papertrail" },
    ],
    links: [{ rel: "stylesheet", href: appCss }],
  }),
  shellComponent: RootDocument,
});

function RootDocument({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body className="min-h-screen bg-background text-foreground">
        <header className="border-b">
          <nav className="mx-auto flex max-w-3xl items-center gap-4 p-4 text-sm">
            <Link to="/" className="font-semibold">
              papertrail
            </Link>
            <div className="ml-auto flex gap-4">
              <Link to="/login" className="hover:underline">
                Sign in
              </Link>
              <Link to="/register" className="hover:underline">
                Register
              </Link>
              <Link to="/dashboard" className="hover:underline">
                Dashboard
              </Link>
            </div>
          </nav>
        </header>
        <main className="mx-auto max-w-3xl p-4">{children}</main>
        <Scripts />
      </body>
    </html>
  );
}
