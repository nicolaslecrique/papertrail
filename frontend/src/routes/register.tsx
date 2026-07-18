import { useMutation } from "@tanstack/react-query";
import { Link, createFileRoute } from "@tanstack/react-router";
import { useState } from "react";

import { registerMutation } from "@/client/@tanstack/react-query.gen";
import { AuthShell } from "@/components/auth-shell";
import { Field, FormError } from "@/components/form";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { apiErrorMessage } from "@/lib/errors";

export const Route = createFileRoute("/register")({
  ssr: false,
  component: RegisterPage,
});

function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [mismatch, setMismatch] = useState(false);
  const register = useMutation(registerMutation());

  return (
    <AuthShell
      title="Create your account"
      footer={
        <p className="text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link to="/login" className="underline">
            Sign in
          </Link>
        </p>
      }
    >
      {register.isSuccess ? (
        <Alert>
          <AlertDescription>{register.data.message}</AlertDescription>
        </Alert>
      ) : (
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (password !== confirm) {
              setMismatch(true);
              return;
            }
            setMismatch(false);
            register.mutate({ body: { email, password } });
          }}
        >
          <Field
            label="Email"
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => {
              setEmail(event.target.value);
            }}
          />
          <Field
            label="Password"
            id="password"
            type="password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(event) => {
              setPassword(event.target.value);
            }}
          />
          <Field
            label="Confirm password"
            id="confirm"
            type="password"
            autoComplete="new-password"
            required
            value={confirm}
            onChange={(event) => {
              setConfirm(event.target.value);
            }}
          />
          {mismatch ? <FormError>Passwords do not match.</FormError> : null}
          {register.isError ? (
            <FormError>{apiErrorMessage(register.error)}</FormError>
          ) : null}
          <Button
            type="submit"
            className="w-full"
            disabled={register.isPending}
          >
            Create account
          </Button>
        </form>
      )}
    </AuthShell>
  );
}
