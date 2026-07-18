import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";

import { greetingOptions } from "@/client/@tanstack/react-query.gen";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export const Route = createFileRoute("/")({ component: Home });

function Home() {
  const [name, setName] = useState("world");
  const greeting = useQuery(greetingOptions({ query: { name } }));

  return (
    <section className="space-y-6 py-8">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">papertrail</h1>
        <p className="text-muted-foreground">
          A tool to study the manipulation of science by lobbies.
        </p>
      </div>
      <div className="max-w-sm space-y-2">
        <Label htmlFor="name">Your name</Label>
        <Input
          id="name"
          value={name}
          onChange={(event) => {
            setName(event.target.value);
          }}
        />
        <p data-testid="greeting" className="text-lg">
          {greeting.isError
            ? "Couldn’t load the greeting. Please try again."
            : (greeting.data?.message ?? "…")}
        </p>
      </div>
    </section>
  );
}
