import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router";

import {
  authJwtCookieLogoutMutation,
  usersCurrentUserOptions,
} from "@/client/@tanstack/react-query.gen";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const Route = createFileRoute("/dashboard")({
  // Client-rendered: the auth check runs in the browser, where the httponly
  // cookie is sent to /api. Public/content routes stay server-rendered.
  ssr: false,
  // One fetch of /api/users/me: the loader primes the query cache (and gates
  // access), and the component reads the loaded user straight back.
  loader: async ({ context }) => {
    try {
      return await context.queryClient.ensureQueryData(
        usersCurrentUserOptions(),
      );
    } catch {
      // TanStack Router controls flow by throwing a redirect (not an Error).
      // eslint-disable-next-line @typescript-eslint/only-throw-error
      throw redirect({ to: "/login" });
    }
  },
  component: DashboardPage,
});

function DashboardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const user = Route.useLoaderData();
  const logout = useMutation(authJwtCookieLogoutMutation());

  return (
    <div className="mx-auto max-w-sm py-8">
      <Card>
        <CardHeader>
          <CardTitle>Dashboard</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p data-testid="user-email">
            Signed in as <strong>{user.email}</strong>
          </p>
          <Button
            variant="outline"
            disabled={logout.isPending}
            onClick={() => {
              logout.mutate(
                {},
                {
                  onSuccess: () => {
                    queryClient.clear();
                    void navigate({ to: "/login" });
                  },
                },
              );
            }}
          >
            Sign out
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
