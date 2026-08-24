import assert from "node:assert/strict";
import test from "node:test";

import {
  applyCollectionView,
  filterItemsBySearch,
  nextSortState,
  sortItems,
  type SortState,
} from "./collection-view";

interface Row {
  createdAt: string;
  label: string;
  score: number;
}

const rows: Row[] = [
  { createdAt: "2026-02-10T09:30:00Z", label: "beta", score: 12 },
  { createdAt: "2026-01-05T09:30:00Z", label: "Alpha", score: 4 },
  { createdAt: "2026-03-01T09:30:00Z", label: "gamma", score: 8 },
];

test("sortItems sorts text A-Z with stable casing", () => {
  assert.deepEqual(
    sortItems(rows, (row) => row.label).map((row) => row.label),
    ["Alpha", "beta", "gamma"],
  );
});

test("nextSortState toggles ASC and DESC for an active column", () => {
  const current: SortState<"label" | "score"> = {
    column: "label",
    direction: "asc",
  };

  assert.deepEqual(nextSortState(current, "label"), {
    column: "label",
    direction: "desc",
  });
  assert.deepEqual(nextSortState(current, "score"), {
    column: "score",
    direction: "asc",
  });
});

test("filterItemsBySearch matches labels case-insensitively", () => {
  assert.deepEqual(
    filterItemsBySearch(rows, "ALP", [(row) => row.label]).map(
      (row) => row.label,
    ),
    ["Alpha"],
  );
});

test("sortItems handles numbers and dates", () => {
  assert.deepEqual(
    sortItems(rows, (row) => row.score, "desc").map((row) => row.score),
    [12, 8, 4],
  );
  assert.deepEqual(
    sortItems(rows, (row) => row.createdAt).map((row) => row.label),
    ["Alpha", "beta", "gamma"],
  );
});

test("applyCollectionView returns an empty result for unmatched search", () => {
  assert.deepEqual(
    applyCollectionView(rows, {
      search: "missing",
      searchAccessors: [(row) => row.label],
      sort: { accessor: (row) => row.label },
    }),
    [],
  );
});
