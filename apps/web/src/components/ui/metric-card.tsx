import type { ComponentProps, ReactNode } from "react";

import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface MetricCardProps extends ComponentProps<typeof Card> {
  label: ReactNode;
  value: ReactNode;
}

export function MetricCard({
  className,
  label,
  value,
  ...props
}: MetricCardProps) {
  return (
    <Card
      className={cn("rounded-lg border-border/80", className)}
      size="sm"
      {...props}
    >
      <CardHeader className="gap-2 px-4">
        <CardDescription className="text-xs font-medium">
          {label}
        </CardDescription>
        <CardTitle className="text-2xl font-semibold tracking-normal">
          {value}
        </CardTitle>
      </CardHeader>
    </Card>
  );
}
