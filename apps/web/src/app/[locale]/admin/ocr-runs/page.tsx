import { setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { AdminOcrRunsPage } from "@/components/admin/ocr-runs/admin-ocr-runs-page";
import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/shell/app-shell";
import { isLocale } from "@/i18n/routing";
import { getLangfuseProjectUrl } from "@/lib/admin-ocr-runs/langfuse-server";

export const dynamic = "force-dynamic";

interface AdminOcrRunsRouteProps {
  params: Promise<{ locale: string }>;
}

export default async function AdminOcrRunsRoute({
  params,
}: AdminOcrRunsRouteProps) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  setRequestLocale(locale);

  return (
    <AuthGuard routeId="adminOcrRuns">
      <AppShell>
        <AdminOcrRunsPage langfuseProjectUrl={getLangfuseProjectUrl()} />
      </AppShell>
    </AuthGuard>
  );
}
