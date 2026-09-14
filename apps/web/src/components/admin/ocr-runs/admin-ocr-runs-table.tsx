"use client";

import { useLocale, useTranslations } from "next-intl";

import { AdminOcrRunActions } from "@/components/admin/ocr-runs/admin-ocr-run-actions";
import { OcrRunStatusBadge } from "@/components/admin/ocr-runs/ocr-run-status-badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DataListRow,
  DataListSkeletonRows,
  DataListTable,
} from "@/components/ui/data-list";
import { TableEmptyState } from "@/components/ui/table-empty-state";
import {
  SortableTableHead,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TruncatedTableText,
} from "@/components/ui/table";
import type {
  AdminOcrRunSortField,
  AdminOcrRunSummaryDto,
  PublishedOcrPipelineOption,
} from "@/lib/admin-ocr-runs/types";
import { nextSortState, type SortState } from "@/lib/collection-view";
import {
  canRerunRun,
  formatAdminOcrRunTimesTitle,
  formatAdminOcrRunUpdatedAt,
  initiatorLabel,
  sourceLabel,
  uniqueSelectableRuns,
} from "@/lib/admin-ocr-runs/view-model";
import { cn } from "@/lib/utils";

const COLUMN_COUNT = 8;

interface AdminOcrRunsTableProps {
  hasActiveFilters: boolean;
  isError: boolean;
  isPending: boolean;
  langfuseProjectUrl: string | null;
  onCancel: (run: AdminOcrRunSummaryDto) => void;
  onRerun: (run: AdminOcrRunSummaryDto, pipelineId: string) => void;
  onSelect: (runId: string) => void;
  onSortChange: (sort: SortState<AdminOcrRunSortField>) => void;
  onToggleAll: (
    runs: readonly AdminOcrRunSummaryDto[],
    selected: boolean,
  ) => void;
  onToggleSelection: (run: AdminOcrRunSummaryDto, selected: boolean) => void;
  pendingDocumentIds: ReadonlySet<string>;
  pipelines: readonly PublishedOcrPipelineOption[];
  pipelinesLoading: boolean;
  runs: readonly AdminOcrRunSummaryDto[];
  selectedDocumentIds: ReadonlySet<string>;
  sort: SortState<AdminOcrRunSortField>;
}

export function AdminOcrRunsTable({
  hasActiveFilters,
  isError,
  isPending,
  langfuseProjectUrl,
  onCancel,
  onRerun,
  onSelect,
  onSortChange,
  onToggleAll,
  onToggleSelection,
  pendingDocumentIds,
  pipelines,
  pipelinesLoading,
  runs,
  selectedDocumentIds,
  sort,
}: AdminOcrRunsTableProps) {
  const t = useTranslations("AdminOcrRuns");
  const locale = useLocale();
  const collection = useTranslations("CollectionView");
  const selectableRuns = uniqueSelectableRuns(runs);
  const selectedVisibleCount = selectableRuns.filter((run) =>
    selectedDocumentIds.has(run.document_id),
  ).length;
  const selectAllState =
    selectedVisibleCount === 0
      ? false
      : selectedVisibleCount === selectableRuns.length
        ? true
        : "indeterminate";

  function sortLabel(column: AdminOcrRunSortField, label: string) {
    const nextDirection =
      sort.column === column && sort.direction === "asc" ? "desc" : "asc";
    return collection(`sort.${nextDirection}`, { column: label });
  }

  return (
    <DataListTable
      className="border-spacing-y-1"
      containerClassName="overflow-x-hidden"
    >
      <TableHeader>
        <TableRow className="border-0 hover:bg-transparent">
          <TableHead className="w-10">
            <Checkbox
              aria-label={t("bulk.selectAll")}
              checked={selectAllState}
              disabled={selectableRuns.length === 0}
              onCheckedChange={(checked) =>
                onToggleAll(selectableRuns, checked === true)
              }
            />
          </TableHead>
          <SortableTableHead
            active={sort.column === "document_name"}
            className="w-[20%]"
            direction={sort.direction}
            onSort={() => onSortChange(nextSortState(sort, "document_name"))}
            sortLabel={sortLabel("document_name", t("columns.document"))}
          >
            {t("columns.document")}
          </SortableTableHead>
          <SortableTableHead
            active={sort.column === "status"}
            className="w-[10%]"
            direction={sort.direction}
            onSort={() => onSortChange(nextSortState(sort, "status"))}
            sortLabel={sortLabel("status", t("columns.status"))}
          >
            {t("columns.status")}
          </SortableTableHead>
          <SortableTableHead
            active={sort.column === "pipeline_name"}
            className="w-[14%]"
            direction={sort.direction}
            onSort={() => onSortChange(nextSortState(sort, "pipeline_name"))}
            sortLabel={sortLabel("pipeline_name", t("columns.pipeline"))}
          >
            {t("columns.pipeline")}
          </SortableTableHead>
          <TableHead className="w-[12%]">{t("columns.progress")}</TableHead>
          <TableHead className="w-[14%]">
            {t("columns.sourceAndInitiator")}
          </TableHead>
          <SortableTableHead
            active={sort.column === "updated_at"}
            className="w-[11%]"
            direction={sort.direction}
            onSort={() => onSortChange(nextSortState(sort, "updated_at"))}
            sortLabel={sortLabel("updated_at", t("columns.updated"))}
          >
            {t("columns.updated")}
          </SortableTableHead>
          <TableHead className="w-44 text-right">
            {t("columns.actions")}
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {isPending ? (
          <DataListSkeletonRows columns={COLUMN_COUNT} rows={8} />
        ) : null}
        {!isPending && !isError && runs.length === 0 ? (
          <TableEmptyState
            columns={COLUMN_COUNT}
            description={
              hasActiveFilters
                ? t("emptyFilteredDescription")
                : t("emptyDescription")
            }
            title={hasActiveFilters ? t("emptyFiltered") : t("empty")}
          />
        ) : null}
        {!isPending
          ? runs.map((run) => {
              const rerunnable = canRerunRun(run);
              const selected = selectedDocumentIds.has(run.document_id);
              return (
                <DataListRow
                  className={cn(selected && "bg-accent/60 hover:bg-accent/70")}
                  key={run.id}
                >
                  <TableCell className="w-10">
                    <Checkbox
                      aria-label={t("bulk.selectFor", {
                        name: run.document_name,
                      })}
                      checked={selected}
                      disabled={!rerunnable}
                      onCheckedChange={(checked) =>
                        onToggleSelection(run, checked === true)
                      }
                    />
                  </TableCell>
                  <TableCell className="w-[20%]" title={run.document_id}>
                    <div className="flex min-w-0 flex-col gap-1">
                      <TruncatedTableText
                        className="font-medium"
                        value={run.document_name}
                      />
                      <TruncatedTableText
                        className="text-xs text-muted-foreground"
                        value={run.document_type_name}
                      />
                    </div>
                  </TableCell>
                  <TableCell className="w-[10%]">
                    <OcrRunStatusBadge
                      label={t(`statuses.${run.status}`)}
                      status={run.status}
                    />
                  </TableCell>
                  <TableCell className="w-[14%]">
                    <TruncatedTableText
                      value={`${run.pipeline_name ?? run.pipeline_id} · v${run.pipeline_version}`}
                    />
                  </TableCell>
                  <TableCell className="w-[12%]">
                    <TruncatedTableText value={run.current_step_name ?? "—"} />
                    <span className="text-xs text-muted-foreground">
                      {run.completed_step_count}/{run.total_step_count}
                    </span>
                  </TableCell>
                  <TableCell className="w-[14%]">
                    <TruncatedTableText value={sourceLabel(run)} />
                    <TruncatedTableText
                      className="text-xs text-muted-foreground"
                      value={initiatorLabel(run)}
                    />
                  </TableCell>
                  <TableCell
                    className="w-[11%]"
                    title={formatAdminOcrRunTimesTitle(run, locale, {
                      completed: t("detail.completed"),
                      created: t("detail.created"),
                      started: t("detail.started"),
                      updated: t("detail.updated"),
                    })}
                  >
                    <time dateTime={run.updated_at}>
                      {formatAdminOcrRunUpdatedAt(run.updated_at, locale)}
                    </time>
                  </TableCell>
                  <TableCell className="w-44">
                    <AdminOcrRunActions
                      langfuseProjectUrl={langfuseProjectUrl}
                      onCancel={onCancel}
                      onRerun={onRerun}
                      onSelect={onSelect}
                      pending={pendingDocumentIds.has(run.document_id)}
                      pipelines={pipelines}
                      pipelinesLoading={pipelinesLoading}
                      run={run}
                    />
                  </TableCell>
                </DataListRow>
              );
            })
          : null}
      </TableBody>
    </DataListTable>
  );
}
