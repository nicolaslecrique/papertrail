import { useMutation } from "@tanstack/react-query";
import { Link, createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef } from "react";

import { verifyVerifyMutation } from "@/client/@tanstack/react-query.gen";
import { AuthShell } from "@/components/auth-shell";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { apiErrorMessage } from "@/lib/errors";

export const Route = createFileRoute("/verify")({
  validateSearch: (search: Record<string, unknown>): { token: string } => ({
    token: typeof search.token === "string" ? search.token : "",
  }),
  ssr: false,
  component: VerifyPage,
});

function VerifyPage() {
  const { token } = Route.useSearch();
  const verify = useMutation(verifyVerifyMutation());
  const { mutate } = verify;
  const started = useRef(false);

  useEffect(() => {
    if (started.current || !token) {
      return;
    }
    started.current = true;
    mutate({ body: { token } });
  }, [token, mutate]);

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
      {verify.isSuccess ? (
        <Alert>
          <AlertDescription>
            Your email is confirmed. You can now sign in.
          </AlertDescription>
        </Alert>
      ) : verify.isError ? (
        <Alert variant="destructive">
          <AlertDescription>{apiErrorMessage(verify.error)}</AlertDescription>
        </Alert>
      ) : (
        <p className="text-sm text-muted-foreground">Confirming…</p>
      )}
    </AuthShell>
  );
}
