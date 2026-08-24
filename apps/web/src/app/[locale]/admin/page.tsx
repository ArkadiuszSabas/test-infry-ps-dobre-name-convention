import { setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { AdminPage } from "@/components/admin/admin-page";
import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/shell/app-shell";
import { isLocale } from "@/i18n/routing";

interface AdminRouteProps {
  params: Promise<{
    locale: string;
  }>;
}

export default async function AdminRoute({ params }: AdminRouteProps) {
  const { locale } = await params;

  if (!isLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);

  return (
    <AuthGuard routeId="admin">
      <AppShell>
        <AdminPage />
      </AppShell>
    </AuthGuard>
  );
}
