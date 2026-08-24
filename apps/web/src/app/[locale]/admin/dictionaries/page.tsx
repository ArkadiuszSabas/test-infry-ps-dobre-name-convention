import { setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { AdminDictionariesPage } from "@/components/admin/dictionaries/admin-dictionaries-page";
import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/shell/app-shell";
import { isLocale } from "@/i18n/routing";

interface AdminDictionariesRouteProps {
  params: Promise<{
    locale: string;
  }>;
}

export default async function AdminDictionariesRoute({
  params,
}: AdminDictionariesRouteProps) {
  const { locale } = await params;

  if (!isLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);

  return (
    <AuthGuard routeId="adminDictionaries">
      <AppShell>
        <AdminDictionariesPage />
      </AppShell>
    </AuthGuard>
  );
}
