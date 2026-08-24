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
  searchParams: Promise<{
    documentTypeId?: string | string[];
  }>;
}

export default async function AdminAttributeMatrixRoute({
  params,
  searchParams,
}: AdminDictionaryRouteProps) {
  const { locale } = await params;
  const { documentTypeId } = await searchParams;

  if (!isLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);

  return (
    <AuthGuard routeId="adminDictionaries">
      <AppShell>
        <AdminDictionaryPage
          dictionaryId="attributeMatrix"
          initialDocumentTypeId={firstSearchParam(documentTypeId)}
        />
      </AppShell>
    </AuthGuard>
  );
}

function firstSearchParam(value: string | string[] | undefined) {
  if (Array.isArray(value)) {
    return value[0] ?? null;
  }

  return value ?? null;
}
