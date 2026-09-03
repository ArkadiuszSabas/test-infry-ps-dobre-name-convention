"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ActivityIcon, FilterXIcon, RefreshCwIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { AdminOcrRunDetailSheet } from "@/components/admin/ocr-runs/admin-ocr-run-detail-sheet";
import { AdminOcrRunsBulkActions } from "@/components/admin/ocr-runs/admin-ocr-runs-bulk-actions";
import { AdminOcrRunsFilters } from "@/components/admin/ocr-runs/admin-ocr-runs-filters";
import { AdminOcrRunsPagination } from "@/components/admin/ocr-runs/admin-ocr-runs-pagination";
import { AdminOcrRunsTable } from "@/components/admin/ocr-runs/admin-ocr-runs-table";
import { useAdminOcrRunQueueActions } from "@/components/admin/ocr-runs/use-admin-ocr-run-queue-actions";
import { Button } from "@/components/ui/button";
import { ConfirmActionDialog } from "@/components/ui/confirm-action-dialog";
import {
  DataListActions,
  DataListContent,
  DataListPanel,
  DataListToolbar,
} from "@/components/ui/data-list";
import { Notice } from "@/components/ui/notice";
import { PageBackLink } from "@/components/ui/page-back-link";
import { PageHeader } from "@/components/ui/page-header";
import { PageShell } from "@/components/ui/page-shell";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCsrfProtectedAction } from "@/hooks/auth/use-csrf-protected-action";
import { adminOcrRunsClient } from "@/lib/admin-ocr-runs/api";
import {
  adminOcrRunDetailQueryOptions,
  adminOcrRunListQueryOptions,
  adminOcrRunQueryKeys,
  publishedOcrPipelineQueryOptions,
} from "@/lib/admin-ocr-runs/query-options";
import type {
  AdminOcrRunSummaryDto,
  AdminOcrRunView,
} from "@/lib/admin-ocr-runs/types";
import {
  ADMIN_OCR_RUN_PAGE_SIZE,
  type AdminOcrRunUrlState,
  hasActiveAdminOcrRunFilters,
  parseAdminOcrRunUrlState,
  toListFilters,
} from "@/lib/admin-ocr-runs/view-model";
import { systemCatalogOptionsQueryOptions } from "@/lib/system-catalogs/query-options";
import { cn } from "@/lib/utils";

const urlKeys: Record<Exclude<keyof AdminOcrRunUrlState, "view">, string> = {
  connector: "connector",
  createdFrom: "created_from",
  createdTo: "created_to",
  documentTypeId: "document_type_id",
  offset: "offset",
  pipelineId: "pipeline_id",
  search: "search",
  source: "source",
  stale: "stale",
  status: "status",
};

interface AdminOcrRunsPageProps {
  langfuseProjectUrl: string | null;
}

export function AdminOcrRunsPage({
  langfuseProjectUrl,
}: AdminOcrRunsPageProps) {
  const t = useTranslations("AdminOcrRuns");
  const queryClient = useQueryClient();
  const runCsrfProtectedAction = useCsrfProtectedAction();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const state = parseAdminOcrRunUrlState(searchParams);
  const filters = toListFilters(state);
  const listQuery = useQuery(adminOcrRunListQueryOptions(filters));
  const pipelinesQuery = useQuery(publishedOcrPipelineQueryOptions());
  const documentTypesQuery = useQuery(
    systemCatalogOptionsQueryOptions("document_type"),
  );
  const queueActions = useAdminOcrRunQueueActions();
  const [bulkPipelineId, setBulkPipelineId] = useState<string | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [cancelTarget, setCancelTarget] =
    useState<AdminOcrRunSummaryDto | null>(null);
  const detailQuery = useQuery(adminOcrRunDetailQueryOptions(selectedRunId));

  const cancelMutation = useMutation({
    mutationFn: (runId: string) =>
      runCsrfProtectedAction((csrfToken) =>
        adminOcrRunsClient.cancel(runId, { csrfToken }),
      ),
    onSuccess: async () => {
      setCancelTarget(null);
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: adminOcrRunQueryKeys.lists(),
        }),
        queryClient.invalidateQueries({
          queryKey: adminOcrRunQueryKeys.details(),
        }),
      ]);
    },
  });

  function updateUrl(patch: Partial<AdminOcrRunUrlState>) {
    queueActions.clearSelection();
    queueActions.clearFeedback();
    const params = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(patch)) {
      const urlKey =
        key === "view" ? "view" : urlKeys[key as keyof typeof urlKeys];
      if (
        value === undefined ||
        value === "" ||
        (key === "offset" && value === 0)
      ) {
        params.delete(urlKey);
      } else {
        params.set(urlKey, String(value));
      }
    }
    router.replace(`${pathname}${params.size ? `?${params.toString()}` : ""}`, {
      scroll: false,
    });
  }

  function clearFilters() {
    queueActions.clearSelection();
    queueActions.clearFeedback();
    const params = new URLSearchParams();
    if (state.view === "history") params.set("view", "history");
    router.replace(`${pathname}${params.size ? `?${params}` : ""}`, {
      scroll: false,
    });
  }

  const page = listQuery.data;
  const pipelines = pipelinesQuery.data ?? [];
  const runs = page?.data.runs ?? [];
  const hasActiveFilters = hasActiveAdminOcrRunFilters(state);
  const selectedBulkPipelineId =
    (bulkPipelineId && pipelines.some((item) => item.id === bulkPipelineId)
      ? bulkPipelineId
      : pipelines.find((item) => item.isDefault)?.id) ??
    pipelines[0]?.id ??
    null;

  return (
    <PageShell
      navigation={<PageBackLink href="/admin">{t("back")}</PageBackLink>}
    >
      <PageHeader
        actions={
          <Button
            disabled={listQuery.isFetching}
            onClick={() => listQuery.refetch()}
            size="sm"
            variant="outline"
          >
            <RefreshCwIcon
              className={listQuery.isFetching ? "animate-spin" : undefined}
            />
            {t("refresh")}
          </Button>
        }
        description={t("description")}
        icon={ActivityIcon}
        title={t("title")}
      />

      <Tabs
        onValueChange={(value) =>
          updateUrl({
            offset: 0,
            status: undefined,
            view: value as AdminOcrRunView,
          })
        }
        value={state.view}
      >
        <TabsList aria-label={t("tabs.label")}>
          <TabsTrigger value="active">{t("tabs.active")}</TabsTrigger>
          <TabsTrigger value="history">{t("tabs.history")}</TabsTrigger>
        </TabsList>
      </Tabs>

      {pipelinesQuery.isError || documentTypesQuery.isError ? (
        <Notice
          description={t("supportingDataErrorDescription")}
          title={t("supportingDataError")}
          tone="danger"
        />
      ) : null}
      {listQuery.isError ? (
        <Notice
          description={t("loadErrorDescription")}
          title={t("loadError")}
          tone="danger"
        />
      ) : null}

      <DataListPanel>
        <DataListToolbar
          className={cn(
            "gap-2 p-3",
            queueActions.selectedRuns.length > 0 && "lg:flex-col",
          )}
        >
          <AdminOcrRunsFilters
            documentTypes={documentTypesQuery.data?.data.options ?? []}
            documentTypesLoading={documentTypesQuery.isPending}
            onChange={updateUrl}
            pipelines={pipelines}
            pipelinesLoading={pipelinesQuery.isPending}
            runs={runs}
            state={state}
          />
          {hasActiveFilters || queueActions.selectedRuns.length > 0 ? (
            <DataListActions>
              {hasActiveFilters ? (
                <Button onClick={clearFilters} size="sm" variant="ghost">
                  <FilterXIcon />
                  {t("filters.clear")}
                </Button>
              ) : null}
              {queueActions.selectedRuns.length > 0 ? (
                <AdminOcrRunsBulkActions
                  isQueueing={queueActions.queueManyPending}
                  onClearSelection={queueActions.clearSelection}
                  onPipelineChange={setBulkPipelineId}
                  onQueueSelected={() =>
                    selectedBulkPipelineId &&
                    queueActions.queueMany(selectedBulkPipelineId)
                  }
                  pipelines={pipelines}
                  pipelinesLoading={pipelinesQuery.isPending}
                  selectedCount={queueActions.selectedRuns.length}
                  selectedPipelineId={selectedBulkPipelineId}
                />
              ) : null}
            </DataListActions>
          ) : null}
        </DataListToolbar>
        <DataListContent className="gap-2 p-3">
          <div aria-live="polite" className="min-h-4 text-xs">
            {queueActions.feedback ? (
              <p
                className={cn(
                  "truncate text-muted-foreground",
                  queueActions.feedback.kind === "error" && "text-destructive",
                )}
                title={t(`queueFeedback.${queueActions.feedback.kind}`, {
                  failed: queueActions.feedback.failed,
                  queued: queueActions.feedback.queued,
                })}
              >
                {t(`queueFeedback.${queueActions.feedback.kind}`, {
                  failed: queueActions.feedback.failed,
                  queued: queueActions.feedback.queued,
                })}
              </p>
            ) : null}
          </div>
          <AdminOcrRunsTable
            hasActiveFilters={hasActiveFilters}
            isError={listQuery.isError}
            isPending={listQuery.isPending}
            langfuseProjectUrl={langfuseProjectUrl}
            onCancel={(run) => {
              cancelMutation.reset();
              setCancelTarget(run);
            }}
            onRerun={queueActions.queueOne}
            onSelect={setSelectedRunId}
            onToggleAll={queueActions.toggleAll}
            onToggleSelection={queueActions.toggleSelection}
            pendingDocumentIds={queueActions.pendingDocumentIds}
            pipelines={pipelines}
            pipelinesLoading={pipelinesQuery.isPending}
            runs={runs}
            selectedDocumentIds={queueActions.selectedDocumentIds}
          />
          <AdminOcrRunsPagination
            canGoNext={page?.meta.has_more ?? false}
            canGoPrevious={state.offset > 0}
            isFetching={listQuery.isFetching}
            onGoNext={() =>
              updateUrl({ offset: state.offset + ADMIN_OCR_RUN_PAGE_SIZE })
            }
            onGoPrevious={() =>
              updateUrl({
                offset: Math.max(0, state.offset - ADMIN_OCR_RUN_PAGE_SIZE),
              })
            }
            returnedCount={page?.meta.returned_count ?? 0}
          />
        </DataListContent>
      </DataListPanel>

      <AdminOcrRunDetailSheet
        onOpenChange={(open) => !open && setSelectedRunId(null)}
        open={Boolean(selectedRunId)}
        query={detailQuery}
      />
      <ConfirmActionDialog
        cancelLabel={t("cancelDialog.back")}
        confirmLabel={t("cancelDialog.confirm")}
        description={t("cancelDialog.description", {
          name: cancelTarget?.document_name ?? "",
        })}
        error={
          cancelMutation.isError ? (
            <Notice
              description={t("cancelDialog.errorDescription")}
              title={t("cancelDialog.error")}
              tone="danger"
            />
          ) : undefined
        }
        isPending={cancelMutation.isPending}
        onConfirm={() => cancelTarget && cancelMutation.mutate(cancelTarget.id)}
        onOpenChange={(open) => !open && setCancelTarget(null)}
        open={Boolean(cancelTarget)}
        title={t("cancelDialog.title")}
      />
    </PageShell>
  );
}
