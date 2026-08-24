import { setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { AdminConnectorsPage } from "@/components/admin/connectors/admin-connectors-page";
import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/shell/app-shell";
import { isLocale } from "@/i18n/routing";

export default async function AdminConnectorsRoute({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  setRequestLocale(locale);
  return (
    <AuthGuard routeId="adminConnectors">
      <AppShell>
        <AdminConnectorsPage />
      </AppShell>
    </AuthGuard>
  );
}
