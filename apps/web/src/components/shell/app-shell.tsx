import { cookies } from "next/headers";
import { type CSSProperties, type ReactNode } from "react";

import { AppSidebar } from "@/components/shell/app-sidebar";
import { AppTopBar } from "@/components/shell/app-top-bar";
import { UnsavedChangesProvider } from "@/components/system-catalogs/unsaved-changes-provider";
import { SidebarProvider } from "@/components/ui/sidebar";

const SIDEBAR_COOKIE_NAME = "sidebar_state";

interface AppShellProps {
  children: ReactNode;
  hideAdminNavigation?: boolean;
}

export async function AppShell({
  children,
  hideAdminNavigation = false,
}: AppShellProps) {
  const cookieStore = await cookies();
  const defaultOpen = cookieStore.get(SIDEBAR_COOKIE_NAME)?.value !== "false";

  return (
    <SidebarProvider
      className="h-svh overflow-hidden bg-muted"
      defaultOpen={defaultOpen}
      style={
        {
          "--sidebar-width": "15.5rem",
        } as CSSProperties
      }
    >
      <UnsavedChangesProvider>
        <AppSidebar hideAdminNavigation={hideAdminNavigation} />
        <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2 p-2 md:pl-0">
          <AppTopBar />
          <main
            className="min-h-0 flex-1 overflow-auto rounded-xl border bg-background shadow-sm"
            data-slot="app-main"
          >
            {children}
          </main>
        </div>
      </UnsavedChangesProvider>
    </SidebarProvider>
  );
}
