import { setRequestLocale } from "next-intl/server";

import { AuthGuard } from "@/components/auth/auth-guard";
import { DashboardPage } from "@/components/dashboard/dashboard-page";
import { AppShell } from "@/components/shell/app-shell";
import { isLocale } from "@/i18n/routing";

interface HomeProps {
  params: Promise<{
    locale: string;
  }>;
}

export default async function Home({ params }: HomeProps) {
  const { locale } = await params;

  if (isLocale(locale)) {
    setRequestLocale(locale);
  }

  return (
    <AuthGuard>
      <AppShell>
        <DashboardPage />
      </AppShell>
    </AuthGuard>
  );
}
