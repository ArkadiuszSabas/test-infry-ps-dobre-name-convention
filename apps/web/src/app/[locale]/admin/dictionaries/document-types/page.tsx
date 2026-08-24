import { setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { AdminDictionaryPage } from "@/components/admin/dictionaries/admin-dictionary-page";
import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/shell/app-shell";
import { isLocale } from "@/i18n/routing";

interface AdminDictionaryRouteProps {
  params: Promise<{
    locale: string;
  }>;
}

export default async function AdminDocumentTypesRoute({
  params,
}: AdminDictionaryRouteProps) {
  const { locale } = await params;

  if (!isLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);

  return (
    <AuthGuard routeId="adminDictionaries">
      <AppShell>
        <AdminDictionaryPage dictionaryId="documentTypes" />
      </AppShell>
    </AuthGuard>
  );
}
