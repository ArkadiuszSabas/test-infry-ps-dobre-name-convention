import { setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { AuthGuard } from "@/components/auth/auth-guard";
import { InboxPage } from "@/components/inbox/inbox-page";
import { AppShell } from "@/components/shell/app-shell";
import { isLocale } from "@/i18n/routing";

interface DocumentsRouteProps {
  params: Promise<{
    locale: string;
  }>;
}

export default async function DocumentsRoute({ params }: DocumentsRouteProps) {
  const { locale } = await params;

  if (!isLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);

  return (
    <AuthGuard routeId="inbox">
      <AppShell>
        <InboxPage />
      </AppShell>
    </AuthGuard>
  );
}
