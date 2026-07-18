import { useMutation } from "@tanstack/react-query";
import { Link, createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";

import { authJwtCookieLoginMutation } from "@/client/@tanstack/react-query.gen";
import { AuthShell } from "@/components/auth-shell";
import { Field, FormError } from "@/components/form";
import { Button } from "@/components/ui/button";
import { apiErrorMessage } from "@/lib/errors";

// Client-rendered: the auth screens are the interactive app shell, not public
// content, so they opt out of SSR (public/content routes stay server-rendered).
export const Route = createFileRoute("/login")({
  ssr: false,
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const login = useMutation(authJwtCookieLoginMutation());

  return (
    <AuthShell
      title="Sign in"
      footer={
        <div className="space-y-1 text-sm text-muted-foreground">
          <p>
            No account?{" "}
            <Link to="/register" className="underline">
              Register
            </Link>
          </p>
          <p>
            <Link to="/forgot-password" className="underline">
              Forgot your password?
            </Link>
          </p>
        </div>
      }
    >
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          login.mutate(
            { body: { username: email, password } },
            {
              onSuccess: () => {
                void navigate({ to: "/dashboard" });
              },
            },
          );
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
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => {
            setPassword(event.target.value);
          }}
        />
        {login.isError ? (
          <FormError>{apiErrorMessage(login.error)}</FormError>
        ) : null}
        <Button type="submit" className="w-full" disabled={login.isPending}>
          Sign in
        </Button>
      </form>
    </AuthShell>
  );
}
