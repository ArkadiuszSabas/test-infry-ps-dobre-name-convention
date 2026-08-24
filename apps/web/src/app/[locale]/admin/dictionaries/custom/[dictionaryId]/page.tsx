import { setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { AuthGuard } from "@/components/auth/auth-guard";
import { CustomDictionaryDetailPage } from "@/components/admin/dictionaries/custom-dictionary-detail-page";
import { AppShell } from "@/components/shell/app-shell";
import { isLocale } from "@/i18n/routing";

interface CustomDictionaryPageProps {
  params: Promise<{
    locale: string;
    dictionaryId: string;
  }>;
}

export default async function CustomDictionaryPage({
  params,
}: CustomDictionaryPageProps) {
  const { dictionaryId, locale } = await params;

  if (!isLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);

  return (
    <AuthGuard routeId="adminDictionaries">
      <AppShell>
        <CustomDictionaryDetailPage dictionaryId={dictionaryId} />
      </AppShell>
    </AuthGuard>
  );
}
