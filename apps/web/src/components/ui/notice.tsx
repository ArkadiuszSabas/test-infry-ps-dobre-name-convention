import type { ComponentProps } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

type NoticeTone = "default" | "danger";

interface NoticeProps extends Omit<ComponentProps<typeof Alert>, "variant"> {
  description?: string;
  title: string;
  tone?: NoticeTone;
}

export function Notice({
  description,
  role,
  title,
  tone = "default",
  ...props
}: NoticeProps) {
  return (
    <Alert
      role={role ?? (tone === "danger" ? "alert" : "status")}
      variant={tone === "danger" ? "destructive" : "default"}
      {...props}
    >
      <AlertTitle>{title}</AlertTitle>
      {description ? <AlertDescription>{description}</AlertDescription> : null}
    </Alert>
  );
}
