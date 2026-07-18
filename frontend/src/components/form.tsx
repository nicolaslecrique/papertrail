import type { ComponentProps, ReactNode } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface FieldProps extends ComponentProps<typeof Input> {
  label: string;
  id: string;
}

/** A labelled input — the label/input pair every auth form repeats. */
export function Field({ label, id, ...inputProps }: FieldProps) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} {...inputProps} />
    </div>
  );
}

/** A destructive alert for form-level errors (validation or API failures). */
export function FormError({ children }: { children: ReactNode }) {
  return (
    <Alert variant="destructive">
      <AlertDescription>{children}</AlertDescription>
    </Alert>
  );
}
