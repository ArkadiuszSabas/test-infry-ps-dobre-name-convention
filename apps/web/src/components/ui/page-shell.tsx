import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

import { PageShellNavigationMount } from "./page-shell-navigation";

interface PageShellProps {
  children: ReactNode;
  className?: string;
  navigation?: ReactNode;
}

export function PageShell({ children, className, navigation }: PageShellProps) {
  return (
    <>
      <PageShellNavigationMount>{navigation}</PageShellNavigationMount>
      <div
        className={cn(
          "mx-auto flex w-full flex-col gap-5 px-8 py-5 sm:px-10 lg:px-12 lg:py-6",
          className,
        )}
      >
        {children}
      </div>
    </>
  );
}
