import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";

import { DevObservability } from "@/components/observability/dev-observability";
import { AppProviders } from "@/components/providers/app-providers";
import { TooltipProvider } from "@/components/ui/tooltip";
import { isLocale, routing } from "@/i18n/routing";

import "../globals.css";

interface LocaleLayoutProps {
  children: ReactNode;
  params: Promise<{
    locale: string;
  }>;
}

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export async function generateMetadata({
  params,
}: Omit<LocaleLayoutProps, "children">): Promise<Metadata> {
  const { locale } = await params;
  const activeLocale = isLocale(locale) ? locale : routing.defaultLocale;
  const t = await getTranslations({
    locale: activeLocale,
    namespace: "Metadata",
  });

  return {
    title: t("title"),
    description: t("description"),
  };
}

export default async function LocaleLayout({
  children,
  params,
}: LocaleLayoutProps) {
  const { locale } = await params;

  if (!isLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);

  return (
    <html lang={locale} className="h-full antialiased">
      <body className="flex h-full flex-col overflow-hidden">
        <NextIntlClientProvider>
          <AppProviders>
            <TooltipProvider>{children}</TooltipProvider>
          </AppProviders>
        </NextIntlClientProvider>
        {process.env.NODE_ENV === "development" ? <DevObservability /> : null}
      </body>
    </html>
  );
}
