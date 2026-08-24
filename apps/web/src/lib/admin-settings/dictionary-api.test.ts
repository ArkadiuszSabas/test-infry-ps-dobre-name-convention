import assert from "node:assert/strict";
import test from "node:test";

import { adminCatalogClient } from "./api";
import { installFetchMock, jsonResponse } from "@/lib/api/test-helpers";

test("admin catalog client manages custom dictionaries, fields, and paged entries", async (t) => {
  const dictionaryId = "66666666-6666-6666-6666-666666666666";
  const fieldId = "77777777-7777-7777-7777-777777777777";
  const entryId = "88888888-8888-8888-8888-888888888888";
  const fetchMock = installFetchMock([
    jsonResponse({
      data: {
        dictionaries: [
          {
            created_at: "2026-06-25T10:00:00Z",
            description: "Business unit dictionary",
            entries_version: 1,
            external_id: "pion",
            id: dictionaryId,
            name: "Pion",
            schema_version: 1,
            status: "active",
            updated_at: "2026-06-25T10:00:00Z",
          },
        ],
      },
      meta: { total_count: 1 },
    }),
    jsonResponse({
      data: {
        fields: [
          {
            constraints: { max_length: 8 },
            created_at: "2026-06-25T10:00:00Z",
            data_type: "string",
            dictionary_id: dictionaryId,
            external_id: "code",
            format: {},
            id: fieldId,
            is_unique: true,
            label: "Code",
            normalization: { trim: true },
            required: true,
            sort_order: 0,
            status: "active",
            updated_at: "2026-06-25T10:00:00Z",
          },
        ],
      },
      meta: { dictionary_id: dictionaryId, field_count: 1 },
    }),
    jsonResponse({
      data: {
        entries: [
          {
            created_at: "2026-06-25T10:00:00Z",
            dictionary_id: dictionaryId,
            external_id: "finance",
            id: entryId,
            label: "Finance",
            sort_order: 0,
            status: "active",
            updated_at: "2026-06-25T10:00:00Z",
            values: { code: "FIN" },
          },
        ],
      },
      meta: {
        dictionary_id: dictionaryId,
        has_more: false,
        limit: 25,
        offset: 0,
        returned_count: 1,
        total_count: 1,
      },
    }),
    jsonResponse({
      data: {
        created_at: "2026-06-25T10:00:00Z",
        description: null,
        entries_version: 1,
        external_id: "regions",
        id: dictionaryId,
        name: "Regions",
        schema_version: 1,
        status: "active",
        updated_at: "2026-06-25T10:00:00Z",
      },
      meta: {},
    }),
    jsonResponse({
      data: {
        created_at: "2026-06-25T10:00:00Z",
        dictionary_id: dictionaryId,
        external_id: "finance_department",
        id: entryId,
        label: "Finance",
        sort_order: 0,
        status: "active",
        updated_at: "2026-06-25T11:00:00Z",
        values: { code: "FIN" },
      },
      meta: {},
    }),
    jsonResponse({
      data: {
        deleted: true,
        id: entryId,
      },
      meta: {},
    }),
  ]);
  t.after(fetchMock.restore);

  const dictionaries = await adminCatalogClient.listDictionaries({
    search: "pion",
    status: "active",
  });
  const fields = await adminCatalogClient.listDictionaryFields(dictionaryId);
  const entries = await adminCatalogClient.listDictionaryEntries({
    dictionaryId,
    limit: 25,
    offset: 0,
    search: "fin",
    status: "active",
  });
  await adminCatalogClient.createDictionary(
    {
      description: null,
      externalId: "regions",
      name: "Regions",
    },
    { csrfToken: "raw-csrf-token" },
  );
  await adminCatalogClient.updateDictionaryEntry(
    dictionaryId,
    entryId,
    {
      externalId: "finance_department",
      label: "Finance",
      sortOrder: 0,
      values: { code: "FIN" },
    },
    { csrfToken: "raw-csrf-token" },
  );
  await adminCatalogClient.deleteDictionaryEntry(dictionaryId, entryId, {
    csrfToken: "raw-csrf-token",
  });

  assert.equal(dictionaries.data.dictionaries[0]?.externalId, "pion");
  assert.equal(fields.data.fields[0]?.isUnique, true);
  assert.equal(entries.data.entries[0]?.values.code, "FIN");
  assert.equal(
    fetchMock.calls[0]?.input,
    "/api/docmind/dictionaries?search=pion&status=active",
  );
  assert.equal(
    fetchMock.calls[2]?.input,
    `/api/docmind/dictionaries/${dictionaryId}/entries?limit=25&offset=0&search=fin&status=active`,
  );
  assert.deepEqual(JSON.parse(String(fetchMock.calls[3]?.init.body)), {
    description: null,
    external_id: "regions",
    name: "Regions",
  });
  assert.equal(
    fetchMock.calls[4]?.input,
    `/api/docmind/dictionaries/${dictionaryId}/entries/${entryId}`,
  );
  assert.equal(fetchMock.calls[4]?.init.method, "PATCH");
  assert.deepEqual(JSON.parse(String(fetchMock.calls[4]?.init.body)), {
    external_id: "finance_department",
    label: "Finance",
    sort_order: 0,
    values: { code: "FIN" },
  });
  assert.equal(fetchMock.calls[5]?.init.method, "DELETE");
});
