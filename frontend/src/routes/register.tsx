import { useMutation } from "@tanstack/react-query";
import { Link, createFileRoute } from "@tanstack/react-router";
import { useState } from "react";

import { registerMutation } from "@/client/@tanstack/react-query.gen";
import { AuthShell } from "@/components/auth-shell";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
              }}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              required
              value={password}
              onChange={(event) => {
                setPassword(event.target.value);
              }}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirm">Confirm password</Label>
            <Input
              id="confirm"
              type="password"
              autoComplete="new-password"
              required
              value={confirm}
              onChange={(event) => {
                setConfirm(event.target.value);
              }}
            />
          </div>
          {mismatch ? (
            <Alert variant="destructive">
              <AlertDescription>Passwords do not match.</AlertDescription>
            </Alert>
          ) : null}
          {register.isError ? (
            <Alert variant="destructive">
              <AlertDescription>
                {apiErrorMessage(register.error)}
              </AlertDescription>
            </Alert>
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
