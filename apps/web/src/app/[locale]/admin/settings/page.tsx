import { setRequestLocale } from "next-intl/server";
import { notFound, redirect } from "next/navigation";

import { isLocale } from "@/i18n/routing";

interface AdminSettingsRouteProps {
  params: Promise<{
    locale: string;
  }>;
}

export default async function AdminSettingsRoute({
  params,
}: AdminSettingsRouteProps) {
  const { locale } = await params;

  if (!isLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);
  redirect(`/${locale}/admin/dictionaries`);
}
