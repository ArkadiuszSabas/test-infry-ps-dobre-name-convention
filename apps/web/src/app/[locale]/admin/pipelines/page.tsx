import { setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { AdminOcrPipelinesPage } from "@/components/admin/ocr-pipelines/admin-ocr-pipelines-page";
import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/shell/app-shell";
import { isLocale } from "@/i18n/routing";

interface AdminPipelinesRouteProps {
  params: Promise<{
    locale: string;
  }>;
}

export default async function AdminPipelinesRoute({
  params,
}: AdminPipelinesRouteProps) {
  const { locale } = await params;

  if (!isLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);

  return (
    <AuthGuard routeId="adminPipelines">
      <AppShell>
        <AdminOcrPipelinesPage />
      </AppShell>
    </AuthGuard>
  );
}
