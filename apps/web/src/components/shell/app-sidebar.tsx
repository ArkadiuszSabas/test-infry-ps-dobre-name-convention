"use client";

import {
  ArchiveIcon,
  FileTextIcon,
  HomeIcon,
  SettingsIcon,
} from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { usePathname } from "next/navigation";

import { BrandMark } from "@/components/ui/brand-mark";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar";
import { useCurrentActor } from "@/hooks/auth/use-current-actor";
import { Link } from "@/i18n/navigation";
import {
  getSidebarNavigationItems,
  normalizeLocalizedPathname,
  type SidebarRouteId,
} from "@/lib/navigation/route-policy";

const navigationIcons: Record<SidebarRouteId, typeof HomeIcon> = {
  admin: SettingsIcon,
  archive: ArchiveIcon,
  dashboard: HomeIcon,
  inbox: FileTextIcon,
};

export function AppSidebar({
  hideAdminNavigation = false,
}: {
  hideAdminNavigation?: boolean;
}) {
  const t = useTranslations("Sidebar");
  const locale = useLocale();
  const pathname = usePathname();
  const { actor } = useCurrentActor();
  const navigationItems = getSidebarNavigationItems(
    actor,
    normalizeLocalizedPathname(pathname, locale),
  ).filter((item) => !hideAdminNavigation || item.id !== "admin");

  return (
    <Sidebar variant="floating" collapsible="icon">
      <SidebarHeader className="px-4 pt-7 pb-6">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild className="h-11 px-1">
              <Link href="/" aria-label={t("dashboardAria")}>
                <BrandMark />
                <span className="grid flex-1 text-left leading-tight">
                  <span className="truncate text-xl font-semibold tracking-normal">
                    DocMind.Ai
                  </span>
                </span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent className="px-3">
        <SidebarGroup className="p-0">
          <SidebarGroupContent>
            <SidebarMenu className="gap-2">
              {navigationItems.map((item) => {
                const label = t(`navigation.${item.id}`);
                const Icon = navigationIcons[item.id];

                return (
                  <SidebarMenuItem key={item.id}>
                    <SidebarMenuButton
                      asChild
                      isActive={item.active}
                      className="h-11 rounded-lg px-3 text-[15px] text-sidebar-foreground/90 data-[active=true]:bg-primary data-[active=true]:text-primary-foreground data-[active=true]:shadow-[var(--shadow-card-soft)]"
                    >
                      <Link
                        href={item.href}
                        aria-current={item.active ? "page" : undefined}
                      >
                        <Icon />
                        <span>{label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarRail />
    </Sidebar>
  );
}
