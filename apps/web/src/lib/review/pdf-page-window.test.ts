import assert from "node:assert/strict";
import test from "node:test";

import {
  createEstimatedPdfPageSizes,
  getActivePdfPageNumbers,
  getNearbyPdfPageNumbers,
  getVisiblePdfPageNumber,
} from "./pdf-page-window";

test("prepares a 100-page layout from estimates", () => {
  const pageSizes = createEstimatedPdfPageSizes(100);

  assert.equal(pageSizes.length, 100);
  assert.deepEqual(pageSizes[0], { height: 792, width: 612 });
  assert.deepEqual(pageSizes[99], { height: 792, width: 612 });
});

test("selects the page with the largest visible area", () => {
  const pageBounds = [
    { bottom: 900, pageNumber: 1, top: 100 },
    { bottom: 1720, pageNumber: 2, top: 920 },
    { bottom: 2540, pageNumber: 3, top: 1740 },
  ];

  assert.equal(
    getVisiblePdfPageNumber({
      pageBounds,
      viewportBottom: 1500,
      viewportTop: 700,
    }),
    2,
  );
  assert.equal(
    getVisiblePdfPageNumber({
      pageBounds,
      viewportBottom: 3000,
      viewportTop: 2600,
    }),
    null,
  );
});

test("bounds rendered pages and prioritizes the selected source page", () => {
  const nearbyPageNumbers = getNearbyPdfPageNumbers({
    bufferPixels: 200,
    maximumPageCount: 3,
    pageBounds: [
      { bottom: 7200, pageNumber: 7, top: 6200 },
      { bottom: 1200, pageNumber: 1, top: 200 },
      { bottom: 5200, pageNumber: 5, top: 4200 },
      { bottom: 3200, pageNumber: 3, top: 2200 },
      { bottom: 4200, pageNumber: 4, top: 3200 },
      { bottom: 6200, pageNumber: 6, top: 5200 },
      { bottom: 2200, pageNumber: 2, top: 1200 },
    ],
    viewportBottom: 4300,
    viewportTop: 3300,
  });

  assert.deepEqual(nearbyPageNumbers, [4, 5, 3]);
  assert.deepEqual(
    [...getActivePdfPageNumbers(new Set(nearbyPageNumbers), 7)].sort(
      (first, second) => first - second,
    ),
    [3, 4, 5, 7],
  );
});
