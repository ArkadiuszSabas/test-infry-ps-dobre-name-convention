import assert from "node:assert/strict";
import test from "node:test";

import {
  buildPipelineFilterOptions,
  canCancelRun,
  canRerunRun,
  formatAdminOcrRunTimesTitle,
  formatAdminOcrRunUpdatedAt,
  getAdminOcrRunDatePresetRange,
  hasActiveAdminOcrRunFilters,
  parseAdminOcrRunUrlState,
  toListFilters,
} from "./view-model";
import type { AdminOcrRunSummaryDto } from "./types";

test("admin OCR URL state validates values and derives stale cutoff", () => {
  const state = parseAdminOcrRunUrlState(
    new URLSearchParams(
      "view=history&status=failed&stale=1h&offset=25&search=invoice",
    ),
  );
  const filters = toListFilters(state);

  assert.equal(filters.view, "history");
  assert.equal(filters.status, "failed");
  assert.equal(filters.staleMs, 3_600_000);
  assert.equal(filters.search, "invoice");
  assert.equal(filters.offset, 25);
  assert.equal(filters.sortBy, "completed_at");
  assert.equal(filters.sortDirection, "desc");
});

test("admin OCR URL state validates and forwards explicit sorting", () => {
  const filters = toListFilters(
    parseAdminOcrRunUrlState(
      new URLSearchParams("sort_by=document_name&sort_direction=asc"),
    ),
  );
  const invalid = toListFilters(
    parseAdminOcrRunUrlState(
      new URLSearchParams("sort_by=raw_sql&sort_direction=sideways"),
    ),
  );

  assert.equal(filters.sortBy, "document_name");
  assert.equal(filters.sortDirection, "asc");
  assert.equal(invalid.sortBy, "updated_at");
  assert.equal(invalid.sortDirection, "asc");
});

test("admin OCR URL state retains the document type filter", () => {
  const state = parseAdminOcrRunUrlState(
    new URLSearchParams("document_type_id=type-123"),
  );

  assert.equal(state.documentTypeId, "type-123");
  assert.equal(toListFilters(state).documentTypeId, "type-123");
});

test("admin OCR cancellation is limited to pending and running states", () => {
  assert.equal(canCancelRun({ status: "running" }), true);
  assert.equal(canCancelRun({ status: "cancelling" }), false);
  assert.equal(canCancelRun({ status: "failed" }), false);
});

test("admin OCR rerun is limited to terminal states", () => {
  assert.equal(canRerunRun({ status: "succeeded" }), true);
  assert.equal(canRerunRun({ status: "cancelled" }), true);
  assert.equal(canRerunRun({ status: "running" }), false);
  assert.equal(canRerunRun({ status: "cancelling" }), false);
});

test("admin OCR presentation options use real run and pipeline values", () => {
  assert.deepEqual(
    buildPipelineFilterOptions([
      {
        id: "pipeline-1",
        isDefault: true,
        name: "OCR Agentic",
        publishedVersion: 3,
      },
    ]),
    [{ label: "OCR Agentic · v3", value: "pipeline-1" }],
  );
});

test("admin OCR presentation state counts filters and builds date presets", () => {
  assert.equal(
    hasActiveAdminOcrRunFilters(
      parseAdminOcrRunUrlState(new URLSearchParams("view=history")),
    ),
    false,
  );
  assert.equal(
    hasActiveAdminOcrRunFilters(
      parseAdminOcrRunUrlState(
        new URLSearchParams("view=history&source=email"),
      ),
    ),
    true,
  );
  assert.deepEqual(
    getAdminOcrRunDatePresetRange("7d", new Date(2026, 7, 28, 12)),
    { createdFrom: "2026-08-21", createdTo: "2026-08-28" },
  );
});

test("admin OCR presentation formats the compact update and full time tooltip", () => {
  const run = runFixture();
  const compact = formatAdminOcrRunUpdatedAt(run.updated_at, "en-GB");
  const title = formatAdminOcrRunTimesTitle(run, "en-GB", {
    completed: "Completed",
    created: "Created",
    started: "Started",
    updated: "Updated",
  });

  assert.match(compact, /28 Aug 2026/);
  assert.match(title, /^Created: .+\nStarted: .+\nUpdated: .+\nCompleted: .+$/);
});

function runFixture(
  overrides: Partial<AdminOcrRunSummaryDto> = {},
): AdminOcrRunSummaryDto {
  return {
    completed_at: "2026-08-28T09:45:00Z",
    completed_step_count: 2,
    connector_correlation_id: "corr-1",
    connector_display_name: "Primary Connector",
    connector_instance_id: "primary-connector",
    created_at: "2026-08-28T09:00:00Z",
    current_step_name: null,
    current_step_status: null,
    document_connector: "sharepoint",
    document_id: "document-1",
    document_name: "invoice.pdf",
    document_source: "sharepoint",
    document_type_id: "invoice",
    document_type_name: "Invoice",
    id: "run-1",
    latest_attempt: null,
    pipeline_id: "pipeline-1",
    pipeline_name: "OCR Agentic",
    pipeline_version: 3,
    started_at: "2026-08-28T09:01:00Z",
    started_by_actor_id: "admin-1",
    started_by_actor_login: "admin@example.test",
    started_by_actor_type: "human",
    status: "succeeded",
    total_step_count: 2,
    updated_at: "2026-08-28T09:30:00Z",
    ...overrides,
  };
}
