import { setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { AuthGuard } from "@/components/auth/auth-guard";
import { InboxDocumentDetailPage } from "@/components/inbox/inbox-document-detail-page";
import { AppShell } from "@/components/shell/app-shell";
import { isLocale } from "@/i18n/routing";

interface DocumentDetailRouteProps {
  params: Promise<{
    id: string;
    locale: string;
  }>;
}

export default async function DocumentDetailRoute({
  params,
}: DocumentDetailRouteProps) {
  const { id, locale } = await params;

  if (!isLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);

  return (
    <AuthGuard routeId="inbox">
      <AppShell>
        <InboxDocumentDetailPage documentId={id} />
      </AppShell>
    </AuthGuard>
  );
}
