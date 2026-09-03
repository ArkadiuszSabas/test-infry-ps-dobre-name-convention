import type { CurrentActor, KnownPermission } from "@/lib/auth/types";

export type AppRouteId =
  | "dashboard"
  | "inbox"
  | "archive"
  | "admin"
  | "adminUsers"
  | "adminDictionaries"
  | "adminApprovals"
  | "adminPipelines"
  | "adminOcrRuns"
  | "adminConnectors";

export type SidebarRouteId = Extract<
  AppRouteId,
  "dashboard" | "inbox" | "archive" | "admin"
>;

export type AdminEntryRouteId = Extract<
  AppRouteId,
  | "adminApprovals"
  | "adminConnectors"
  | "adminDictionaries"
  | "adminPipelines"
  | "adminOcrRuns"
  | "adminUsers"
>;

type RouteSection = "product" | "admin";
interface RouteAccessPolicy {
  anyPermissions?: readonly KnownPermission[];
}

interface RoutePolicy {
  id: AppRouteId;
  href: string;
  section: RouteSection;
  access: RouteAccessPolicy;
  sidebar?: {
    id: SidebarRouteId;
    order: number;
  };
}

export interface SidebarNavigationItem {
  id: SidebarRouteId;
  href: string;
  active: boolean;
}

export interface AdminEntryRoute {
  id: AdminEntryRouteId;
  href: string;
}

const routePolicies: readonly RoutePolicy[] = [
  {
    access: { anyPermissions: ["documents.read"] },
    href: "/",
    id: "dashboard",
    section: "product",
    sidebar: { id: "dashboard", order: 10 },
  },
  {
    access: { anyPermissions: ["documents.read"] },
    href: "/documents",
    id: "inbox",
    section: "product",
    sidebar: { id: "inbox", order: 20 },
  },
  {
    access: { anyPermissions: ["documents.read"] },
    href: "/archive",
    id: "archive",
    section: "product",
    sidebar: { id: "archive", order: 30 },
  },
  {
    access: {
      anyPermissions: ["admin.settings.manage"],
    },
    href: "/admin/ocr-runs",
    id: "adminOcrRuns",
    section: "admin",
  },
  {
    access: {
      anyPermissions: ["admin.users.manage", "admin.settings.manage"],
    },
    href: "/admin",
    id: "admin",
    section: "admin",
    sidebar: { id: "admin", order: 40 },
  },
  {
    access: {
      anyPermissions: ["admin.users.manage"],
    },
    href: "/admin/users",
    id: "adminUsers",
    section: "admin",
  },
  {
    access: {
      anyPermissions: ["admin.settings.manage"],
    },
    href: "/admin/dictionaries",
    id: "adminDictionaries",
    section: "admin",
  },
  {
    access: {
      anyPermissions: ["admin.settings.manage"],
    },
    href: "/admin/pipelines",
    id: "adminPipelines",
    section: "admin",
  },
  {
    access: {
      anyPermissions: ["admin.settings.manage"],
    },
    href: "/admin/approvals",
    id: "adminApprovals",
    section: "admin",
  },
  {
    access: { anyPermissions: ["admin.settings.manage"] },
    href: "/admin/connectors",
    id: "adminConnectors",
    section: "admin",
  },
];

export const adminEntryRouteIds = [
  "adminUsers",
  "adminDictionaries",
  "adminPipelines",
  "adminOcrRuns",
  "adminConnectors",
  "adminApprovals",
] as const satisfies readonly AdminEntryRouteId[];

export function getRoutePolicy(routeId: AppRouteId): RoutePolicy {
  const route = routePolicies.find((policy) => policy.id === routeId);

  if (!route) {
    throw new Error(`Unknown app route policy: ${routeId}`);
  }

  return route;
}

export function canAccessRoute(
  actor: CurrentActor | null,
  routeId: AppRouteId,
): boolean {
  if (!actor) {
    return false;
  }

  return canAccessRoutePolicy(actor, getRoutePolicy(routeId).access);
}

export function getSidebarNavigationItems(
  actor: CurrentActor | null,
  pathname: string,
): SidebarNavigationItem[] {
  return routePolicies
    .filter(
      (
        policy,
      ): policy is RoutePolicy & {
        sidebar: NonNullable<RoutePolicy["sidebar"]>;
      } => {
        return (
          Boolean(policy.sidebar) && canAccessRoutePolicy(actor, policy.access)
        );
      },
    )
    .sort((first, second) => first.sidebar.order - second.sidebar.order)
    .map((policy) => ({
      active: isPathWithinRoute(pathname, policy.href),
      href: policy.href,
      id: policy.sidebar.id,
    }));
}

export function getAccessibleAdminEntryRoutes(
  actor: CurrentActor | null,
): AdminEntryRoute[] {
  return adminEntryRouteIds
    .map((routeId) => ({
      href: getRoutePolicy(routeId).href,
      id: routeId,
    }))
    .filter((route) => canAccessRoute(actor, route.id));
}

export function normalizeLocalizedPathname(
  pathname: string,
  locale: string,
): string {
  const normalizedPathname = pathname.startsWith("/")
    ? pathname
    : `/${pathname}`;
  const localeRoot = `/${locale}`;

  if (normalizedPathname === localeRoot) {
    return "/";
  }

  if (normalizedPathname.startsWith(`${localeRoot}/`)) {
    return normalizedPathname.slice(localeRoot.length);
  }

  return normalizedPathname;
}

function canAccessRoutePolicy(
  actor: CurrentActor | null,
  policy: RouteAccessPolicy,
): boolean {
  if (!actor) {
    return false;
  }

  if (!policy.anyPermissions?.length) {
    return true;
  }

  const actorPermissions = new Set(actor.permissions);
  const hasPermission = policy.anyPermissions?.some((permission) =>
    actorPermissions.has(permission),
  );

  return Boolean(hasPermission);
}

function isPathWithinRoute(pathname: string, routeHref: string): boolean {
  if (routeHref === "/") {
    return pathname === "/";
  }

  return pathname === routeHref || pathname.startsWith(`${routeHref}/`);
}
