import { setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { ConnectorConfigurationEditor } from "@/components/admin/connectors/connector-configuration-editor";
import { AdminConnectorsPage } from "@/components/admin/connectors/admin-connectors-page";
import { AuthGuard } from "@/components/auth/auth-guard";
import { AppShell } from "@/components/shell/app-shell";
import { isLocale } from "@/i18n/routing";

export default async function ConnectorConfigurationRoute({
  params,
}: {
  params: Promise<{ locale: string; connectorInstanceId: string }>;
}) {
  const { connectorInstanceId, locale } = await params;
  if (!isLocale(locale)) notFound();
  setRequestLocale(locale);
  return (
    <AuthGuard routeId="adminConnectors">
      <AppShell>
        <AdminConnectorsPage />
        <ConnectorConfigurationEditor
          connectorInstanceId={connectorInstanceId}
        />
      </AppShell>
    </AuthGuard>
  );
}
