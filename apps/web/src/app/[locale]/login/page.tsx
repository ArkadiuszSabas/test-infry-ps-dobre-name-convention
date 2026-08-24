import { setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { LoginPage } from "@/components/auth/login-page";
import { isLocale } from "@/i18n/routing";
import { getPublicConfig } from "@/lib/config/public";

interface LoginRouteProps {
  params: Promise<{
    locale: string;
  }>;
  searchParams: Promise<{
    redirect_to?: string | string[];
  }>;
}

export default async function LoginRoute({
  params,
  searchParams,
}: LoginRouteProps) {
  const { locale } = await params;

  if (!isLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);

  const { redirect_to: redirectTo } = await searchParams;

  return (
    <LoginPage
      isEntraLoginEnabled={getPublicConfig().isEntraLoginEnabled}
      locale={locale}
      redirectTo={
        Array.isArray(redirectTo) ? redirectTo[0] : (redirectTo ?? null)
      }
    />
  );
}
