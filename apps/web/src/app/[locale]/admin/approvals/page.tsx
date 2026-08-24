import { setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { AdminApprovalSettingsPage } from "@/components/admin/approval-settings/admin-approval-settings-page";
import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/shell/app-shell";
import { isLocale } from "@/i18n/routing";

interface AdminApprovalSettingsRouteProps {
  params: Promise<{ locale: string }>;
}

export default async function AdminApprovalSettingsRoute({
  params,
}: AdminApprovalSettingsRouteProps) {
  const { locale } = await params;
  if (!isLocale(locale)) {
    notFound();
  }
  setRequestLocale(locale);

  return (
    <AuthGuard routeId="adminApprovals">
      <AppShell>
        <AdminApprovalSettingsPage />
      </AppShell>
    </AuthGuard>
  );
}
