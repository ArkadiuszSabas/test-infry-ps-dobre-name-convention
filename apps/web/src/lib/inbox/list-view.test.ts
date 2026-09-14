import assert from "node:assert/strict";
import test from "node:test";

import {
  ALL_DOCUMENT_TYPES_VALUE,
  ALL_STATUSES_VALUE,
  nextInboxDocumentsSort,
  parseInboxDocumentListUrlState,
  toInboxDocumentListSearchParams,
} from "./list-view";

test("Inbox list URL state uses the shared backend contract", () => {
  const state = parseInboxDocumentListUrlState(
    new URLSearchParams(
      "search=invoice&status=received&document_type_id=type-1&sort_by=name&sort_direction=asc&offset=50",
    ),
    false,
  );

  assert.deepEqual(state, {
    archived: false,
    documentTypeFilter: "type-1",
    documentTypeId: "type-1",
    limit: 50,
    offset: 50,
    search: "invoice",
    sortBy: "name",
    sortDirection: "asc",
    status: "received",
    statusFilter: "received",
  });
  assert.equal(
    toInboxDocumentListSearchParams(state).toString(),
    "limit=50&offset=50&sort_by=name&sort_direction=asc&search=invoice&document_type_id=type-1&status=received",
  );
});

test("Inbox list URL state defaults filters and resets sort direction predictably", () => {
  const state = parseInboxDocumentListUrlState(new URLSearchParams(), true);

  assert.equal(state.archived, true);
  assert.equal(state.documentTypeFilter, ALL_DOCUMENT_TYPES_VALUE);
  assert.equal(state.statusFilter, ALL_STATUSES_VALUE);
  assert.deepEqual(nextInboxDocumentsSort("created", "desc", "name"), {
    sortBy: "name",
    sortDirection: "asc",
  });
  assert.deepEqual(nextInboxDocumentsSort("name", "asc", "name"), {
    sortBy: "name",
    sortDirection: "desc",
  });
});
