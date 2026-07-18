import { useMutation } from "@tanstack/react-query";
import { Link, createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";

import { resetResetPasswordMutation } from "@/client/@tanstack/react-query.gen";
import { AuthShell } from "@/components/auth-shell";
import { Field, FormError } from "@/components/form";
import { Button } from "@/components/ui/button";
import { apiErrorMessage } from "@/lib/errors";

export const Route = createFileRoute("/reset-password")({
  validateSearch: (search: Record<string, unknown>): { token: string } => ({
    token: typeof search.token === "string" ? search.token : "",
  }),
  ssr: false,
  component: ResetPasswordPage,
});

function ResetPasswordPage() {
  const { token } = Route.useSearch();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const reset = useMutation(resetResetPasswordMutation());

  return (
    <AuthShell
      title="Choose a new password"
      footer={
        <p className="text-sm text-muted-foreground">
          <Link to="/login" className="underline">
            Back to sign in
          </Link>
        </p>
      }
    >
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          reset.mutate(
            { body: { token, password } },
            {
              onSuccess: () => {
                void navigate({ to: "/login" });
              },
            },
          );
        }}
      >
        <Field
          label="New password"
          id="password"
          type="password"
          autoComplete="new-password"
          required
          value={password}
          onChange={(event) => {
            setPassword(event.target.value);
          }}
        />
        {reset.isError ? (
          <FormError>{apiErrorMessage(reset.error)}</FormError>
        ) : null}
        <Button type="submit" className="w-full" disabled={reset.isPending}>
          Update password
        </Button>
      </form>
    </AuthShell>
  );
}
