import type { ComponentType, ReactNode } from "react";

import { IconFrame } from "@/components/ui/icon-frame";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  actions?: ReactNode;
  className?: string;
  description: string;
  descriptionClassName?: string;
  icon: ComponentType<{ className?: string }>;
  title: ReactNode;
}

export function PageHeader({
  actions,
  className,
  description,
  descriptionClassName,
  icon: Icon,
  title,
}: PageHeaderProps) {
  return (
    <header
      className={cn(
        "flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between",
        className,
      )}
    >
      <div className="flex min-w-0 items-start gap-4">
        <IconFrame icon={Icon} size="lg" />
        <div className="flex min-h-15 min-w-0 flex-col justify-between">
          <h1 className="text-3xl leading-9 font-semibold tracking-normal">
            {title}
          </h1>
          <p
            className={cn(
              "max-w-3xl text-sm leading-5 text-muted-foreground",
              descriptionClassName,
            )}
          >
            {description}
          </p>
        </div>
      </div>
      {actions ? (
        <div className="flex shrink-0 flex-wrap items-center gap-2 xl:justify-end">
          {actions}
        </div>
      ) : null}
    </header>
  );
}
