import { Suspense } from "react";

import { ActorSummary } from "@/components/shell/actor-summary";
import { PageShellNavigationSlot } from "@/components/ui/page-shell-navigation";
import { SidebarTrigger } from "@/components/ui/sidebar";

export function AppTopBar() {
  return (
    <header
      className="flex h-14 shrink-0 items-center justify-between gap-4 rounded-xl border bg-background px-4 shadow-sm"
      data-slot="app-top-bar"
    >
      <div className="flex min-w-0 items-center gap-3">
        <SidebarTrigger size="icon-lg" variant="outline" />
        <PageShellNavigationSlot />
      </div>
      <div className="ml-auto flex min-w-0 items-center justify-end">
        <Suspense fallback={null}>
          <ActorSummary
            contentAlign="end"
            contentSide="bottom"
            textClassName="block"
            triggerClassName="h-10 rounded-lg px-2"
          />
        </Suspense>
      </div>
    </header>
  );
}
