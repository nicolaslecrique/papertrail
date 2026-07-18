import { Link } from "@tanstack/react-router";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

/** Styled fallback shown while a route's loader is in flight. */
export function RoutePending() {
  return (
    <p className="py-8 text-center text-sm text-muted-foreground">Loading…</p>
  );
}

/** Styled fallback for an unmatched URL (router `defaultNotFoundComponent`). */
export function RouteNotFound() {
  return (
    <div className="mx-auto max-w-sm space-y-4 py-8">
      <Alert>
        <AlertTitle>Page not found</AlertTitle>
        <AlertDescription>
          The page you’re looking for doesn’t exist.
        </AlertDescription>
      </Alert>
      <Button asChild variant="outline">
        <Link to="/">Back to home</Link>
      </Button>
    </div>
  );
}

/** Styled fallback for a thrown route error (router `defaultErrorComponent`). */
export function RouteError() {
  return (
    <div className="mx-auto max-w-sm space-y-4 py-8">
      <Alert variant="destructive">
        <AlertTitle>Something went wrong</AlertTitle>
        <AlertDescription>
          An unexpected error occurred. Please try again.
        </AlertDescription>
      </Alert>
      <Button asChild variant="outline">
        <Link to="/">Back to home</Link>
      </Button>
    </div>
  );
}
