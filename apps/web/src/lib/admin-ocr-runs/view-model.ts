import type {
  AdminOcrRunListFilters,
  AdminOcrRunSummaryDto,
  AdminOcrRunView,
  OcrRunStatus,
  PublishedOcrPipelineOption,
} from "./types";

export const ADMIN_OCR_RUN_PAGE_SIZE = 25;
const statuses = new Set<OcrRunStatus>([
  "pending",
  "running",
  "cancelling",
  "succeeded",
  "partial_failed",
  "failed",
  "cancelled",
]);
const staleDurations: Record<string, number> = {
  "15m": 15 * 60_000,
  "1h": 60 * 60_000,
  "6h": 6 * 60 * 60_000,
  "24h": 24 * 60 * 60_000,
};

export const adminOcrRunStatusesByView: Record<
  AdminOcrRunView,
  readonly OcrRunStatus[]
> = {
  active: ["pending", "running", "cancelling"],
  history: ["succeeded", "partial_failed", "failed", "cancelled"],
};

export interface AdminOcrRunFilterOption {
  label: string;
  value: string;
}

export type AdminOcrRunDatePreset = "24h" | "7d" | "30d";

export interface AdminOcrRunUrlState {
  view: AdminOcrRunView;
  status?: OcrRunStatus;
  pipelineId?: string;
  documentTypeId?: string;
  source?: string;
  connector?: string;
  createdFrom?: string;
  createdTo?: string;
  stale?: string;
  search?: string;
  offset: number;
}

export function parseAdminOcrRunUrlState(
  params: Pick<URLSearchParams, "get">,
): AdminOcrRunUrlState {
  const status = params.get("status");
  const offset = Number.parseInt(params.get("offset") ?? "0", 10);
  return {
    connector: text(params.get("connector")),
    createdFrom: text(params.get("created_from")),
    createdTo: text(params.get("created_to")),
    documentTypeId: text(params.get("document_type_id")),
    offset: Number.isFinite(offset) && offset >= 0 ? offset : 0,
    pipelineId: text(params.get("pipeline_id")),
    search: text(params.get("search")),
    source: text(params.get("source")),
    stale: text(params.get("stale")),
    status:
      status && statuses.has(status as OcrRunStatus)
        ? (status as OcrRunStatus)
        : undefined,
    view: params.get("view") === "history" ? "history" : "active",
  };
}

export function toListFilters(
  state: AdminOcrRunUrlState,
): AdminOcrRunListFilters {
  const duration = state.stale ? staleDurations[state.stale] : undefined;
  return {
    connector: state.connector,
    createdFrom: dateBoundary(state.createdFrom, false),
    createdTo: dateBoundary(state.createdTo, true),
    documentTypeId: state.documentTypeId,
    limit: ADMIN_OCR_RUN_PAGE_SIZE,
    offset: state.offset,
    pipelineId: state.pipelineId,
    search: state.search,
    source: state.source,
    staleMs: duration,
    status: state.status,
    view: state.view,
  };
}

export function canCancelRun(
  run: Pick<AdminOcrRunSummaryDto, "status">,
): boolean {
  return run.status === "pending" || run.status === "running";
}

export function canRerunRun(
  run: Pick<AdminOcrRunSummaryDto, "status">,
): boolean {
  return ["succeeded", "partial_failed", "failed", "cancelled"].includes(
    run.status,
  );
}

export function initiatorLabel(run: AdminOcrRunSummaryDto): string {
  return (
    run.started_by_actor_login ??
    run.started_by_actor_id ??
    run.started_by_actor_type
  );
}

export function sourceLabel(run: AdminOcrRunSummaryDto): string {
  return (
    run.connector_display_name ??
    run.connector_instance_id ??
    run.document_connector ??
    run.document_source ??
    "—"
  );
}

export function hasActiveAdminOcrRunFilters(
  state: AdminOcrRunUrlState,
): boolean {
  return Boolean(
    state.connector ||
    state.createdFrom ||
    state.createdTo ||
    state.documentTypeId ||
    state.pipelineId ||
    state.search ||
    state.source ||
    state.stale ||
    state.status,
  );
}

export function getAdminOcrRunStatusCount(
  runs: readonly AdminOcrRunSummaryDto[],
  status?: OcrRunStatus,
): number {
  return status
    ? runs.filter((run) => run.status === status).length
    : runs.length;
}

export function buildPipelineFilterOptions(
  pipelines: readonly PublishedOcrPipelineOption[],
): AdminOcrRunFilterOption[] {
  return pipelines.map((pipeline) => ({
    label: `${pipeline.name} · v${pipeline.publishedVersion}`,
    value: pipeline.id,
  }));
}

export function buildSourceFilterOptions(
  runs: readonly AdminOcrRunSummaryDto[],
  selected?: string,
): AdminOcrRunFilterOption[] {
  return uniqueOptions(
    runs.flatMap((run) =>
      run.document_source
        ? [{ label: run.document_source, value: run.document_source }]
        : [],
    ),
    selected,
  );
}

export function buildConnectorFilterOptions(
  runs: readonly AdminOcrRunSummaryDto[],
  selected?: string,
): AdminOcrRunFilterOption[] {
  return uniqueOptions(
    runs.flatMap((run) => {
      const value = run.connector_instance_id ?? run.document_connector;
      if (!value) return [];
      return [
        {
          label: run.connector_display_name
            ? `${run.connector_display_name} · ${value}`
            : value,
          value,
        },
      ];
    }),
    selected,
  );
}

export function getAdminOcrRunDatePresetRange(
  preset: AdminOcrRunDatePreset,
  now = new Date(),
): Pick<AdminOcrRunUrlState, "createdFrom" | "createdTo"> {
  const durationDays = preset === "24h" ? 1 : preset === "7d" ? 7 : 30;
  const from = new Date(now);
  from.setDate(from.getDate() - durationDays);
  return {
    createdFrom: formatDateInput(from),
    createdTo: formatDateInput(now),
  };
}

export function formatAdminOcrRunUpdatedAt(
  value: string,
  locale: string,
): string {
  return new Intl.DateTimeFormat(locale, {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

export function formatAdminOcrRunTimesTitle(
  run: Pick<
    AdminOcrRunSummaryDto,
    "completed_at" | "created_at" | "started_at" | "updated_at"
  >,
  locale: string,
  labels: {
    completed: string;
    created: string;
    started: string;
    updated: string;
  },
): string {
  const format = (value: string | null) =>
    value
      ? new Intl.DateTimeFormat(locale, {
          dateStyle: "short",
          timeStyle: "medium",
        }).format(new Date(value))
      : "—";
  return [
    `${labels.created}: ${format(run.created_at)}`,
    `${labels.started}: ${format(run.started_at)}`,
    `${labels.updated}: ${format(run.updated_at)}`,
    `${labels.completed}: ${format(run.completed_at)}`,
  ].join("\n");
}

export function uniqueSelectableRuns(
  runs: readonly AdminOcrRunSummaryDto[],
): AdminOcrRunSummaryDto[] {
  const byDocument = new Map<string, AdminOcrRunSummaryDto>();
  for (const run of runs) {
    if (canRerunRun(run) && !byDocument.has(run.document_id)) {
      byDocument.set(run.document_id, run);
    }
  }
  return [...byDocument.values()];
}

function uniqueOptions(
  options: readonly AdminOcrRunFilterOption[],
  selected?: string,
): AdminOcrRunFilterOption[] {
  const byValue = new Map(options.map((option) => [option.value, option]));
  if (selected && !byValue.has(selected)) {
    byValue.set(selected, { label: selected, value: selected });
  }
  return [...byValue.values()].sort((left, right) =>
    left.label.localeCompare(right.label),
  );
}

function formatDateInput(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function text(value: string | null): string | undefined {
  const normalized = value?.trim();
  return normalized || undefined;
}

function dateBoundary(
  value: string | undefined,
  end: boolean,
): string | undefined {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return undefined;
  }
  return new Date(
    `${value}T${end ? "23:59:59.999" : "00:00:00.000"}Z`,
  ).toISOString();
}
