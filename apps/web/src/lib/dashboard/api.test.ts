import assert from "node:assert/strict";
import test from "node:test";

import { dashboardClient, mapDashboardOverview } from "./api";
import type { DashboardOverviewDto } from "./types";

test("dashboard mapper keeps one coherent overview window", () => {
  const result = mapDashboardOverview(overviewDto);

  assert.equal(result.windowDays, 7);
  assert.deepEqual(result.operationalStatus, {
    toReview: 2,
    processing: 1,
    requiresAttention: 1,
  });
  assert.deepEqual(result.activity[0], {
    date: "2026-07-28",
    accepted: 4,
    successfulOcr: 3,
    archived: 2,
  });
  assert.equal(result.ocrTiming.averageSeconds, 18.4);
  assert.equal(result.toReview[0]?.documentId, "document-1");
});

test("dashboard client requests exactly the selected overview window", async (t) => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = "";
  t.after(() => {
    globalThis.fetch = originalFetch;
  });
  globalThis.fetch = async (input) => {
    requestedUrl = String(input);
    return new Response(
      JSON.stringify({
        data: overviewDto,
        meta: {},
      }),
      {
        headers: { "content-type": "application/json" },
        status: 200,
      },
    );
  };

  const result = await dashboardClient.getOverview(7);

  assert.equal(requestedUrl, "/api/docmind/dashboard/overview?window_days=7");
  assert.equal(result.generatedAt, "2026-07-28T10:00:00Z");
});

const overviewDto: DashboardOverviewDto = {
  generated_at: "2026-07-28T10:00:00Z",
  window_days: 7,
  operational_status: {
    to_review: 2,
    processing: 1,
    requires_attention: 1,
  },
  activity: [
    {
      date: "2026-07-28",
      accepted: 4,
      successful_ocr: 3,
      archived: 2,
    },
  ],
  ocr_timing: {
    successful_sample_count: 3,
    min_seconds: 6.2,
    average_seconds: 18.4,
    max_seconds: 51.8,
    weighted_average_seconds_per_page: 4.1,
  },
  archive: {
    total: 20,
    added_in_window: 2,
  },
  to_review: [
    {
      document_id: "document-1",
      filename: "invoice.pdf",
      document_type: "Invoice",
      status: "waiting_for_review",
      problem_type: null,
      event_at: "2026-07-28T09:00:00Z",
    },
  ],
  requires_attention: [],
};
