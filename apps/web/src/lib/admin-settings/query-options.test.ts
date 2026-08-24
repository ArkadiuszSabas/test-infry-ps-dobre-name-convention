import assert from "node:assert/strict";
import test from "node:test";

import { installFetchMock, jsonResponse } from "@/lib/api/test-helpers";
import { dictionaryEntryLookupQueryOptions } from "./query-options";

const DICTIONARY_ID = "77777777-7777-7777-7777-777777777777";

test("dictionary entry lookup query reads all active pages", async (t) => {
  const fetchMock = installFetchMock([
    jsonResponse(dictionaryEntryPage({ hasMore: true, offset: 0 })),
    jsonResponse(
      dictionaryEntryPage({
        entryId: "entry-2",
        hasMore: false,
        label: "Second entry",
        offset: 1,
      }),
    ),
  ]);
  t.after(fetchMock.restore);

  const options = dictionaryEntryLookupQueryOptions(DICTIONARY_ID);

  if (typeof options.queryFn !== "function") {
    throw new Error("Expected dictionary lookup query function.");
  }

  const result = await options.queryFn({
    signal: new AbortController().signal,
  } as never);

  assert.equal(result.data.entries.length, 2);
  assert.equal(result.meta.returnedCount, 2);
  assert.equal(result.meta.hasMore, false);
  assert.equal(
    fetchMock.calls[0]?.input,
    `/api/docmind/dictionaries/${DICTIONARY_ID}/entries?limit=100&offset=0&status=active`,
  );
  assert.equal(
    fetchMock.calls[1]?.input,
    `/api/docmind/dictionaries/${DICTIONARY_ID}/entries?limit=100&offset=1&status=active`,
  );
});

function dictionaryEntryPage({
  entryId = "entry-1",
  hasMore,
  label = "First entry",
  offset,
}: {
  entryId?: string;
  hasMore: boolean;
  label?: string;
  offset: number;
}) {
  return {
    data: {
      entries: [
        {
          created_at: "2026-07-03T10:00:00Z",
          dictionary_id: DICTIONARY_ID,
          external_id: entryId,
          id: entryId,
          label,
          sort_order: null,
          status: "active",
          updated_at: "2026-07-03T10:00:00Z",
          values: {},
        },
      ],
    },
    meta: {
      dictionary_id: DICTIONARY_ID,
      has_more: hasMore,
      limit: 100,
      offset,
      returned_count: 1,
      total_count: 2,
    },
  };
}
