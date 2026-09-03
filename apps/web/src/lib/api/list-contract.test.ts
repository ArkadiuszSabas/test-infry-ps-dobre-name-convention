import assert from "node:assert/strict";
import test from "node:test";

import {
  buildListQueryKey,
  getListPresentationState,
  mapListPageMeta,
  parseListQuery,
  toListSearchParams,
  updateListQuery,
} from "./list-contract";

const config = {
  defaultSortBy: "created_at",
  sortFields: ["created_at", "name"],
} as const;

test("parseListQuery reads valid URL state using shared parameter names", () => {
  const query = parseListQuery(
    new URLSearchParams(
      "search=+invoice+&sort_by=name&sort_direction=desc&limit=25&offset=50",
    ),
    config,
  );

  assert.deepEqual(query, {
    search: "invoice",
    sortBy: "name",
    sortDirection: "desc",
    limit: 25,
    offset: 50,
  });
});

test("parseListQuery replaces invalid URL state with endpoint defaults", () => {
  const query = parseListQuery(
    new URLSearchParams(
      "search=+++&sort_by=unknown&sort_direction=sideways&limit=500&offset=-1",
    ),
    config,
  );

  assert.deepEqual(query, {
    sortBy: "created_at",
    sortDirection: "asc",
    limit: 50,
    offset: 0,
  });
});

test("toListSearchParams emits shared and endpoint-specific filters", () => {
  const params = toListSearchParams(
    {
      search: " invoice ",
      sortBy: "created_at",
      sortDirection: "asc",
      limit: 50,
      offset: 0,
      status: "active",
      tenant: undefined,
      type: ["pdf", "image"],
    },
    (query) => ({
      status: query.status,
      tenant: query.tenant,
      type: query.type,
    }),
  );

  assert.equal(
    params.toString(),
    "limit=50&offset=0&sort_by=created_at&sort_direction=asc&search=invoice&status=active&type=pdf&type=image",
  );
});

test("criteria changes reset offset while page navigation preserves it", () => {
  const query = {
    sortBy: "created_at",
    sortDirection: "asc" as const,
    limit: 25,
    offset: 50,
    status: "active",
  };

  assert.equal(updateListQuery(query, { status: "inactive" }).offset, 0);
  assert.equal(updateListQuery(query, { offset: 75 }).offset, 75);
});

test("query keys contain the complete typed list query", () => {
  const query = {
    sortBy: "name",
    sortDirection: "desc" as const,
    limit: 10,
    offset: 20,
    status: "active",
  };

  assert.deepEqual(buildListQueryKey(["dictionaries", "entries"], query), [
    "dictionaries",
    "entries",
    query,
  ]);
});

test("mapListPageMeta maps the standard API metadata once", () => {
  assert.deepEqual(
    mapListPageMeta({
      total: 23,
      returned_count: 10,
      limit: 10,
      offset: 10,
      has_more: true,
    }),
    {
      total: 23,
      returnedCount: 10,
      limit: 10,
      offset: 10,
      hasMore: true,
    },
  );
});

test("presentation state distinguishes loading, error, empty and refreshing", () => {
  assert.deepEqual(
    getListPresentationState({
      hasError: false,
      isFetching: true,
      isPending: true,
      returnedCount: 0,
    }),
    { kind: "loading" },
  );
  assert.deepEqual(
    getListPresentationState({
      hasError: true,
      isFetching: false,
      isPending: false,
      returnedCount: 0,
    }),
    { kind: "error" },
  );
  assert.deepEqual(
    getListPresentationState({
      hasError: false,
      isFetching: false,
      isPending: false,
      returnedCount: 0,
    }),
    { kind: "empty" },
  );
  assert.deepEqual(
    getListPresentationState({
      hasError: false,
      isFetching: true,
      isPending: false,
      returnedCount: 2,
    }),
    { kind: "ready", isRefreshing: true },
  );
});
