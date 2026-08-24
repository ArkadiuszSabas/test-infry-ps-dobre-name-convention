import type { ComponentProps } from "react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function PanelCard({
  className,
  ...props
}: ComponentProps<typeof Card>) {
  return (
    <Card
      className={cn(
        "rounded-lg border-border/80 shadow-[var(--shadow-card)]",
        className,
      )}
      {...props}
    />
  );
}
