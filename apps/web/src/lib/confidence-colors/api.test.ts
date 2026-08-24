import assert from "node:assert/strict";
import test from "node:test";

import { installFetchMock, jsonResponse } from "@/lib/api/test-helpers";

import { confidenceColorsClient } from "./api";

test("reads admin and review confidence color settings", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse(settingsEnvelope()),
    jsonResponse(settingsEnvelope()),
  ]);
  t.after(fetchMock.restore);

  const adminSettings = await confidenceColorsClient.getAdminSettings();
  const reviewSettings = await confidenceColorsClient.getReviewSettings();

  assert.equal(adminSettings.bands[1]?.color, "orange");
  assert.deepEqual(reviewSettings, adminSettings);
  assert.equal(
    fetchMock.calls[0]?.input,
    "/api/docmind/admin/ocr/confidence-color-bands",
  );
  assert.equal(
    fetchMock.calls[1]?.input,
    "/api/docmind/ocr/confidence-color-bands",
  );
});

test("sends complete CSRF-protected confidence color configuration", async (t) => {
  const fetchMock = installFetchMock([jsonResponse(settingsEnvelope())]);
  t.after(fetchMock.restore);

  await confidenceColorsClient.updateAdminSettings(
    [
      { start: 0, end: 50, color: "red" },
      { start: 51, end: 75, color: "orange" },
      { start: 76, end: 100, color: "green" },
    ],
    "2026-07-28T10:00:00Z",
    { csrfToken: "raw-csrf-token" },
  );

  const request = fetchMock.calls[0];
  assert.equal(request?.init.method, "PUT");
  assert.equal(
    new Headers(request?.init.headers).get("X-CSRF-Token"),
    "raw-csrf-token",
  );
  assert.deepEqual(JSON.parse(String(request?.init.body)), {
    bands: [
      { start: 0, end: 50, color: "red" },
      { start: 51, end: 75, color: "orange" },
      { start: 76, end: 100, color: "green" },
    ],
    expected_updated_at: "2026-07-28T10:00:00Z",
  });
});

test("rejects an invalid settings response instead of applying unsafe colors", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse(
      settingsEnvelope({
        bands: [
          { start: 0, end: 20, color: "red" },
          { start: 22, end: 100, color: "green" },
        ],
      }),
    ),
  ]);
  t.after(fetchMock.restore);

  await assert.rejects(
    () => confidenceColorsClient.getReviewSettings(),
    /Invalid OCR confidence color settings response/,
  );
});

function settingsEnvelope(
  overrides: Partial<{
    bands: Array<{ start: number; end: number; color: string }>;
    schema_version: number;
    updated_at: string | null;
  }> = {},
) {
  return {
    data: {
      schema_version: 1,
      bands: [
        { start: 0, end: 50, color: "red" },
        { start: 51, end: 75, color: "orange" },
        { start: 76, end: 100, color: "green" },
      ],
      updated_at: null,
      ...overrides,
    },
    meta: {},
  };
}
