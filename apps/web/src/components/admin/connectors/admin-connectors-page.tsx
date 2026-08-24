"use client";

import { useQuery } from "@tanstack/react-query";
import { CableIcon, Settings2Icon } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import {
  CatalogNotice,
  getCatalogErrorMessage,
} from "@/components/admin/catalog/catalog-shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  DataListActions,
  DataListContent,
  DataListFilters,
  DataListGrid,
  DataListPanel,
  DataListRow,
  DataListSkeletonRows,
  DataListTable,
  DataListToolbar,
} from "@/components/ui/data-list";
import {
  DataListSearchFilter,
  DataListViewToggle,
  type DataListView,
} from "@/components/ui/data-list-filters";
import { EmptyState } from "@/components/ui/empty-state";
import { IconFrame } from "@/components/ui/icon-frame";
import { PageBackLink } from "@/components/ui/page-back-link";
import { PageHeader } from "@/components/ui/page-header";
import { PageShell } from "@/components/ui/page-shell";
import { PanelCard } from "@/components/ui/panel-card";
import { Skeleton } from "@/components/ui/skeleton";
import { TableEmptyState } from "@/components/ui/table-empty-state";
import {
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TruncatedTableText,
} from "@/components/ui/table";
import { Link } from "@/i18n/navigation";
import {
  listConfigurableConnectorInstances,
  type ConnectorInstanceDto,
} from "@/lib/connector-configurations/api";
import {
  connectorConfigurationLocale,
  getConnectorConfigurationExtension,
} from "@/lib/connector-configurations/extensions";
import { applyCollectionView } from "@/lib/collection-view";

interface ConnectorDisplayData {
  description: string | null;
  label: string;
}

export function AdminConnectorsPage() {
  const t = useTranslations("AdminConnectors");
  const collection = useTranslations("CollectionView");
  const locale = connectorConfigurationLocale(useLocale());
  const [search, setSearch] = useState("");
  const [view, setView] = useState<DataListView>("cards");
  const query = useQuery({
    queryFn: listConfigurableConnectorInstances,
    queryKey: ["connector-configurations"],
  });
  const visibleInstances = useMemo(
    () =>
      applyCollectionView(query.data ?? [], {
        search,
        searchAccessors: [
          (instance) => connectorDisplayData(instance, locale).label,
          (instance) => connectorDisplayData(instance, locale).description,
          (instance) => instance.connector_instance_id,
          (instance) => instance.status,
        ],
      }),
    [locale, query.data, search],
  );
  const hasSearch = search.trim().length > 0;
  const showCollection = query.isPending || Boolean(query.data?.length);

  return (
    <PageShell
      navigation={<PageBackLink href="/admin">{t("back")}</PageBackLink>}
    >
      <PageHeader
        description={t("description")}
        icon={CableIcon}
        title={t("title")}
      />
      <DataListPanel>
        <DataListToolbar>
          <DataListFilters>
            <DataListSearchFilter
              ariaLabel={t("search")}
              onValueChange={setSearch}
              placeholder={t("search")}
              value={search}
            />
          </DataListFilters>
          <DataListActions className="border-0 bg-transparent p-0 shadow-none">
            <DataListViewToggle
              ariaLabel={t("view.ariaLabel")}
              cardsLabel={t("view.cards")}
              listLabel={t("view.list")}
              onValueChange={setView}
              value={view}
            />
          </DataListActions>
        </DataListToolbar>
        <DataListContent>
          {query.isError ? (
            <CatalogNotice
              title={getCatalogErrorMessage(query.error, t("loadError"))}
              tone="danger"
            />
          ) : null}

          {!query.isPending && !query.isError && query.data?.length === 0 ? (
            <EmptyState description={t("empty")} title={t("emptyTitle")} />
          ) : null}

          {showCollection && view === "cards" ? (
            <ConnectorCardGrid
              hasSearch={hasSearch}
              instances={visibleInstances}
              isPending={query.isPending}
              locale={locale}
              noResultsDescription={collection("noResultsDescription")}
              noResultsTitle={collection("noResults")}
              statusLabel={(status) => t(`status.${status}`)}
            />
          ) : null}

          {showCollection && view === "list" ? (
            <ConnectorTable
              actionLabel={t("actions.configure")}
              hasSearch={hasSearch}
              instances={visibleInstances}
              isPending={query.isPending}
              locale={locale}
              noResultsDescription={collection("noResultsDescription")}
              noResultsTitle={collection("noResults")}
              statusLabel={(status) => t(`status.${status}`)}
              tableLabels={{
                actions: t("columns.actions"),
                connector: t("columns.connector"),
                status: t("columns.status"),
              }}
            />
          ) : null}
        </DataListContent>
      </DataListPanel>
    </PageShell>
  );
}

function ConnectorCardGrid({
  hasSearch,
  instances,
  isPending,
  locale,
  noResultsDescription,
  noResultsTitle,
  statusLabel,
}: {
  hasSearch: boolean;
  instances: readonly ConnectorInstanceDto[];
  isPending: boolean;
  locale: "en" | "pl";
  noResultsDescription: string;
  noResultsTitle: string;
  statusLabel: (status: ConnectorInstanceDto["status"]) => string;
}) {
  return (
    <DataListGrid>
      {isPending
        ? Array.from({ length: 3 }, (_, index) => (
            <PanelCard key={index} size="sm">
              <CardContent className="flex flex-col gap-3 p-4">
                <Skeleton className="h-5 w-40" />
                <Skeleton className="h-4 w-52" />
                <Skeleton className="h-12 w-full" />
              </CardContent>
            </PanelCard>
          ))
        : null}
      {instances.map((instance) => (
        <ConnectorCard
          instance={instance}
          key={instance.connector_instance_id}
          locale={locale}
          statusLabel={statusLabel}
        />
      ))}
      {!isPending && instances.length === 0 && hasSearch ? (
        <EmptyState
          className="md:col-span-2 xl:col-span-3"
          description={noResultsDescription}
          title={noResultsTitle}
        />
      ) : null}
    </DataListGrid>
  );
}

function ConnectorCard({
  instance,
  locale,
  statusLabel,
}: {
  instance: ConnectorInstanceDto;
  locale: "en" | "pl";
  statusLabel: (status: ConnectorInstanceDto["status"]) => string;
}) {
  const display = connectorDisplayData(instance, locale);

  return (
    <Link
      className="rounded-lg focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
      href={`/admin/connectors/${instance.connector_instance_id}`}
    >
      <PanelCard
        className="h-full transition-colors hover:bg-accent/60"
        size="sm"
      >
        <CardHeader className="flex flex-row items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <IconFrame icon={CableIcon} size="sm" />
            <div className="min-w-0">
              <CardTitle className="truncate">{display.label}</CardTitle>
              <p className="mt-1 truncate text-xs text-muted-foreground">
                {instance.connector_instance_id}
              </p>
            </div>
          </div>
          <Badge variant="outline">{statusLabel(instance.status)}</Badge>
        </CardHeader>
        {display.description ? (
          <CardContent>
            <p className="min-h-10 text-muted-foreground">
              {display.description}
            </p>
          </CardContent>
        ) : null}
      </PanelCard>
    </Link>
  );
}

function ConnectorTable({
  actionLabel,
  hasSearch,
  instances,
  isPending,
  locale,
  noResultsDescription,
  noResultsTitle,
  statusLabel,
  tableLabels,
}: {
  actionLabel: string;
  hasSearch: boolean;
  instances: readonly ConnectorInstanceDto[];
  isPending: boolean;
  locale: "en" | "pl";
  noResultsDescription: string;
  noResultsTitle: string;
  statusLabel: (status: ConnectorInstanceDto["status"]) => string;
  tableLabels: { actions: string; connector: string; status: string };
}) {
  return (
    <DataListTable>
      <TableHeader>
        <TableRow className="border-0 hover:bg-transparent">
          <TableHead>{tableLabels.connector}</TableHead>
          <TableHead>{tableLabels.status}</TableHead>
          <TableHead className="text-right">{tableLabels.actions}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {isPending ? <DataListSkeletonRows columns={3} /> : null}
        {!isPending && instances.length === 0 && hasSearch ? (
          <TableEmptyState
            columns={3}
            description={noResultsDescription}
            title={noResultsTitle}
          />
        ) : null}
        {instances.map((instance) => {
          const display = connectorDisplayData(instance, locale);

          return (
            <DataListRow key={instance.connector_instance_id}>
              <TableCell className="w-[58%]">
                <div className="flex items-center gap-3">
                  <IconFrame icon={CableIcon} size="sm" />
                  <div className="min-w-0">
                    <TruncatedTableText
                      className="font-medium"
                      value={display.label}
                    />
                    {display.description ? (
                      <TruncatedTableText
                        className="mt-1 text-xs text-muted-foreground"
                        value={display.description}
                      />
                    ) : null}
                    <TruncatedTableText
                      className="mt-1 text-xs text-muted-foreground"
                      value={instance.connector_instance_id}
                    />
                  </div>
                </div>
              </TableCell>
              <TableCell>
                <Badge variant="outline">{statusLabel(instance.status)}</Badge>
              </TableCell>
              <TableCell>
                <div className="flex justify-end">
                  <Button asChild size="sm" variant="secondary">
                    <Link
                      href={`/admin/connectors/${instance.connector_instance_id}`}
                    >
                      <Settings2Icon data-icon="inline-start" />
                      {actionLabel}
                    </Link>
                  </Button>
                </div>
              </TableCell>
            </DataListRow>
          );
        })}
      </TableBody>
    </DataListTable>
  );
}

function connectorDisplayData(
  instance: ConnectorInstanceDto,
  locale: "en" | "pl",
): ConnectorDisplayData {
  const messages = getConnectorConfigurationExtension(
    instance.connector_instance_id,
  )?.messages[locale];

  return {
    description:
      messages?.cardDescription ?? instance.safe_metadata.description,
    label: messages?.cardTitle ?? instance.safe_metadata.label,
  };
}
