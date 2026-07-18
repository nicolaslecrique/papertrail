import { Link, createFileRoute } from "@tanstack/react-router";

import { verifyVerify } from "@/client";
import { AuthShell } from "@/components/auth-shell";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { apiErrorMessage } from "@/lib/errors";

type VerifyResult =
  | { status: "missing" }
  | { status: "ok" }
  | { status: "error"; message: string };

export const Route = createFileRoute("/verify")({
  validateSearch: (search: Record<string, unknown>): { token: string } => ({
    token: typeof search.token === "string" ? search.token : "",
  }),
  ssr: false,
  loaderDeps: ({ search }) => ({ token: search.token }),
  // Confirm in the loader (once, deterministically) rather than from an effect —
  // no run-once ref and no StrictMode double-fire.
  loader: async ({ deps }): Promise<VerifyResult> => {
    if (!deps.token) {
      return { status: "missing" };
    }
    const { error } = await verifyVerify({ body: { token: deps.token } });
    return error === undefined
      ? { status: "ok" }
      : { status: "error", message: apiErrorMessage(error) };
  },
  component: VerifyPage,
});

function VerifyPage() {
  const result = Route.useLoaderData();

  return (
    <AuthShell
      title="Confirming your email"
      footer={
        <p className="text-sm text-muted-foreground">
          <Link to="/login" className="underline">
            Go to sign in
          </Link>
        </p>
      }
    >
      {result.status === "ok" ? (
        <Alert>
          <AlertDescription>
            Your email is confirmed. You can now sign in.
          </AlertDescription>
        </Alert>
      ) : (
        <Alert variant="destructive">
          <AlertDescription>
            {result.status === "missing"
              ? "This confirmation link is missing its token. Open the most recent link from your email."
              : result.message}
          </AlertDescription>
        </Alert>
      )}
    </AuthShell>
  );
}
