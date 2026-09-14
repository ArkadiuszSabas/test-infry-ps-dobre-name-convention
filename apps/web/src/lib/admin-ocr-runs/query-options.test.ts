import assert from "node:assert/strict";
import test from "node:test";
import { QueryClient } from "@tanstack/react-query";

import {
  adminOcrRunListQueryOptions,
  adminOcrRunQueryKeys,
  getAdminOcrRunListRefetchInterval,
  invalidateAdminOcrRunLists,
  keepPreviousAdminOcrRunPageForView,
} from "./query-options";
import type { AdminOcrRunListEnvelope } from "./types";

test("admin OCR polling is always enabled for active runs", () => {
  const base = { limit: 25, offset: 0 } as const;
  const active = adminOcrRunListQueryOptions({ ...base, view: "active" });
  const history = adminOcrRunListQueryOptions({ ...base, view: "history" });

  assert.equal(typeof active.refetchInterval, "function");
  assert.equal(active.refetchIntervalInBackground, false);
  assert.equal(typeof active.placeholderData, "function");
  assert.equal(typeof history.placeholderData, "function");
  assert.equal(typeof history.refetchInterval, "function");
  assert.equal(getAdminOcrRunListRefetchInterval("active", undefined), 1_000);
});

test("history polls through cancelling and stops after cancelled", () => {
  const cancelling = historyPage("cancelling");
  const cancelled = historyPage("cancelled");

  assert.equal(getAdminOcrRunListRefetchInterval("history", cancelling), 1_000);
  assert.equal(getAdminOcrRunListRefetchInterval("history", cancelled), false);
  assert.equal(getAdminOcrRunListRefetchInterval("history", undefined), false);
});

test("admin OCR pages are retained only within the same view", () => {
  const page = { data: "previous" };
  const activeKey = adminOcrRunQueryKeys.list({
    limit: 25,
    offset: 0,
    view: "active",
  });
  const historyKey = adminOcrRunQueryKeys.list({
    limit: 25,
    offset: 0,
    view: "history",
  });

  assert.equal(
    keepPreviousAdminOcrRunPageForView("active", page, activeKey),
    page,
  );
  assert.equal(
    keepPreviousAdminOcrRunPageForView("history", page, activeKey),
    undefined,
  );
  assert.equal(
    keepPreviousAdminOcrRunPageForView("history", page, historyKey),
    page,
  );
});

test("run start invalidation marks every admin OCR list stale", async () => {
  const queryClient = new QueryClient();
  const activeKey = adminOcrRunQueryKeys.list({
    limit: 25,
    offset: 0,
    view: "active",
  });
  const historyKey = adminOcrRunQueryKeys.list({
    limit: 25,
    offset: 0,
    view: "history",
  });
  queryClient.setQueryData(activeKey, { data: "active" });
  queryClient.setQueryData(historyKey, { data: "history" });

  await invalidateAdminOcrRunLists(queryClient);

  assert.equal(queryClient.getQueryState(activeKey)?.isInvalidated, true);
  assert.equal(queryClient.getQueryState(historyKey)?.isInvalidated, true);
});

function historyPage(
  status: "cancelling" | "cancelled",
): AdminOcrRunListEnvelope {
  return {
    data: {
      runs: [
        {
          completed_at: status === "cancelled" ? "2026-09-08T12:00:00Z" : null,
          completed_step_count: 1,
          connector_correlation_id: null,
          connector_display_name: null,
          connector_instance_id: null,
          created_at: "2026-09-08T11:00:00Z",
          current_step_name: null,
          current_step_status: null,
          document_connector: null,
          document_id: "document-1",
          document_name: "invoice.pdf",
          document_source: null,
          document_type_id: "document-type-1",
          document_type_name: "Invoice",
          id: "run-1",
          latest_attempt: null,
          pipeline_id: "pipeline-1",
          pipeline_name: "OCR",
          pipeline_version: 1,
          started_at: "2026-09-08T11:01:00Z",
          started_by_actor_id: null,
          started_by_actor_login: null,
          started_by_actor_type: "system",
          status,
          total_step_count: 1,
          updated_at: "2026-09-08T12:00:00Z",
        },
      ],
    },
    meta: {
      facets: {
        connectors: [],
        sources: [],
        status_counts: { cancelled: 1 },
        status_total: 1,
      },
      has_more: false,
      limit: 25,
      offset: 0,
      returned_count: 1,
      total: 1,
    },
  };
}
