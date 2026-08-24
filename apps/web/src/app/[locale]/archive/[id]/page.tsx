import { setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { AuthGuard } from "@/components/auth/auth-guard";
import { InboxDocumentDetailPage } from "@/components/inbox/inbox-document-detail-page";
import { AppShell } from "@/components/shell/app-shell";
import { isLocale } from "@/i18n/routing";

interface ArchiveDocumentRouteProps {
  params: Promise<{
    id: string;
    locale: string;
  }>;
  searchParams: Promise<{
    approval?: string | string[];
  }>;
}

export default async function ArchiveDocumentRoute({
  params,
  searchParams,
}: ArchiveDocumentRouteProps) {
  const { id, locale } = await params;
  const { approval } = await searchParams;

  if (!isLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);

  return (
    <AuthGuard routeId="archive">
      <AppShell>
        <InboxDocumentDetailPage
          approvalCompleted={approval === "completed"}
          documentId={id}
          mode="archive"
        />
      </AppShell>
    </AuthGuard>
  );
}
