import assert from "node:assert/strict";
import test from "node:test";

import type { AdminOcrRunFacetsDto } from "@/lib/admin-ocr-runs/types";

import {
  adminOcrRunFacetScope,
  advanceAdminOcrRunFacetSnapshot,
  advanceAdminOcrRunFacetSnapshots,
} from "./use-stable-admin-ocr-run-facets";

test("facet scope ignores status, sorting, and paging", () => {
  const first = adminOcrRunFacetScope({
    limit: 25,
    offset: 0,
    sortBy: "updated_at",
    sortDirection: "asc",
    status: "pending",
    view: "active",
  });
  const second = adminOcrRunFacetScope({
    limit: 50,
    offset: 25,
    sortBy: "status",
    sortDirection: "desc",
    status: "running",
    view: "active",
  });

  assert.equal(first, second);
});

test("keeps the latest settled facets while a cached status page refetches", () => {
  const scope = "active";
  const currentFacets = facets({ pending: 5, running: 1 });
  const staleCachedFacets = facets({ pending: 6, running: 0 });
  const current = {
    dataUpdatedAt: 200,
    facets: currentFacets,
    scope,
  };

  const whileFetching = advanceAdminOcrRunFacetSnapshot(current, {
    dataUpdatedAt: 100,
    facets: staleCachedFacets,
    isFetching: true,
    scope,
  });
  const afterResponse = advanceAdminOcrRunFacetSnapshot(whileFetching, {
    dataUpdatedAt: 300,
    facets: currentFacets,
    isFetching: false,
    scope,
  });

  assert.equal(whileFetching, current);
  assert.equal(afterResponse.facets, currentFacets);
});

test("does not carry facets across operational views", () => {
  const current = {
    dataUpdatedAt: 200,
    facets: facets({ pending: 5, running: 1 }),
    scope: "active",
  };

  assert.deepEqual(
    advanceAdminOcrRunFacetSnapshot(current, {
      dataUpdatedAt: 100,
      facets: facets({ succeeded: 10 }),
      isFetching: true,
      scope: "history",
    }),
    { dataUpdatedAt: 0, scope: "history" },
  );
});

test("keeps the latest snapshot for each view across a round trip", () => {
  const activeScope = "active";
  const historyScope = "history";
  const currentActiveFacets = facets({ pending: 1, running: 1 });
  const staleActiveFacets = facets({ pending: 2, running: 1 });
  const historyFacets = facets({ cancelled: 10, succeeded: 18 });

  const withActive = advanceAdminOcrRunFacetSnapshots(
    {},
    {
      dataUpdatedAt: 200,
      facets: currentActiveFacets,
      isFetching: false,
      scope: activeScope,
    },
  );
  const whileHistoryLoads = advanceAdminOcrRunFacetSnapshots(withActive, {
    dataUpdatedAt: 0,
    facets: undefined,
    isFetching: true,
    scope: historyScope,
  });
  const withHistory = advanceAdminOcrRunFacetSnapshots(whileHistoryLoads, {
    dataUpdatedAt: 300,
    facets: historyFacets,
    isFetching: false,
    scope: historyScope,
  });
  const afterReturningToStaleActiveCache = advanceAdminOcrRunFacetSnapshots(
    withHistory,
    {
      dataUpdatedAt: 100,
      facets: staleActiveFacets,
      isFetching: true,
      scope: activeScope,
    },
  );

  assert.equal(
    afterReturningToStaleActiveCache[activeScope]?.facets,
    currentActiveFacets,
  );
  assert.equal(
    afterReturningToStaleActiveCache[historyScope]?.facets,
    historyFacets,
  );
});

function facets(
  statusCounts: AdminOcrRunFacetsDto["status_counts"],
): AdminOcrRunFacetsDto {
  return {
    connectors: [],
    sources: [],
    status_counts: statusCounts,
    status_total: Object.values(statusCounts).reduce(
      (total, count) => total + (count ?? 0),
      0,
    ),
  };
}
