import { setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { AdminUsersPage } from "@/components/admin/users/admin-users-page";
import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/shell/app-shell";
import { isLocale } from "@/i18n/routing";

interface AdminUsersRouteProps {
  params: Promise<{
    locale: string;
  }>;
}

export default async function AdminUsersRoute({
  params,
}: AdminUsersRouteProps) {
  const { locale } = await params;

  if (!isLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);

  return (
    <AuthGuard routeId="adminUsers">
      <AppShell>
        <AdminUsersPage />
      </AppShell>
    </AuthGuard>
  );
}
