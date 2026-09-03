import assert from "node:assert/strict";
import test from "node:test";

import {
  getNormalizedPolygonVerticalCenter,
  toPdfPagePolygonGeometries,
  toPdfPolygonGeometry,
} from "./pdf-page-geometry";

test("maps every normalized polygon point into the rendered page geometry", () => {
  const geometry = toPdfPolygonGeometry(
    [0.1, 0.2, 0.9, 0.2, 0.8, 0.8, 0.2, 0.9],
    { height: 900, width: 600 },
  );

  assert.deepEqual(geometry, {
    height: 900,
    points: "60,180 540,180 480,720 120,810",
    width: 600,
  });
});

test("keeps polygons with up to eight points instead of reducing them to a rectangle", () => {
  const geometry = toPdfPolygonGeometry(
    [0, 0, 0.5, 0, 1, 0.2, 1, 0.8, 0.5, 1, 0, 1],
    { height: 100, width: 200 },
  );

  assert.equal(geometry?.points, "0,0 100,0 200,20 200,80 100,100 0,100");
});

test("does not create geometry when a polygon cannot describe a rendered page", () => {
  assert.equal(
    toPdfPolygonGeometry([0, 0, 1, 1, 0, 1], { height: 100, width: 200 }),
    null,
  );
  assert.equal(
    toPdfPolygonGeometry([0, 0, 1, 0, 1, 1, 0, 1], { height: 0, width: 200 }),
    null,
  );
  assert.equal(
    toPdfPolygonGeometry([-0.01, 0, 1, 0, 1, 1, 0, 1], {
      height: 100,
      width: 200,
    }),
    null,
  );
  assert.equal(
    toPdfPolygonGeometry([0, 0, 1, 0, Number.NaN, 1, 0, 1], {
      height: 100,
      width: 200,
    }),
    null,
  );
});

test("maps every renderable source selected for one page", () => {
  const polygons = toPdfPagePolygonGeometries(
    [
      {
        boundingPolygon: [0.1, 0.2, 0.4, 0.2, 0.4, 0.3, 0.1, 0.3],
        confidence: null,
        coordinateSystem: "normalized_0_1",
        kind: "ocr_line",
        orderIndex: 1,
        pageNumber: 2,
        sourceKey: null,
      },
      {
        boundingPolygon: [0.3, 0.4, 0.8, 0.4, 0.8, 0.6, 0.3, 0.6],
        confidence: null,
        coordinateSystem: "normalized_0_1",
        kind: "ocr_line",
        orderIndex: 2,
        pageNumber: 2,
        sourceKey: null,
      },
      {
        boundingPolygon: [0.1, 0.2, 0.4, 0.2, 0.4, 0.3, 0.1, 0.3],
        confidence: null,
        coordinateSystem: "normalized_0_1",
        kind: "ocr_line",
        orderIndex: 3,
        pageNumber: 3,
        sourceKey: null,
      },
    ],
    2,
    { height: 100, width: 200 },
  );

  assert.deepEqual(
    polygons.map((polygon) => polygon.points),
    ["20,20 80,20 80,30 20,30", "60,40 160,40 160,60 60,60"],
  );
});

test("centers the scroll target on the full vertical source extent", () => {
  const center = getNormalizedPolygonVerticalCenter([
    0.1, 0.2, 0.4, 0.3, 0.4, 0.7, 0.1, 0.6,
  ]);
  assert.ok(center !== null && Math.abs(center - 0.45) < Number.EPSILON);
  assert.equal(getNormalizedPolygonVerticalCenter(null), null);
  assert.equal(getNormalizedPolygonVerticalCenter([0, 0, 1, 1]), null);
  assert.equal(
    getNormalizedPolygonVerticalCenter([0, 0, 1, 1, 0, 2, 0, 0]),
    null,
  );
});

test("recalculates normalized geometry for a resized or zoomed page", () => {
  const polygon = [0.25, 0.1, 0.75, 0.1, 0.75, 0.3, 0.25, 0.3];
  assert.equal(
    toPdfPolygonGeometry(polygon, { width: 400, height: 800 })?.points,
    "100,80 300,80 300,240 100,240",
  );
  assert.equal(
    toPdfPolygonGeometry(polygon, { width: 800, height: 1600 })?.points,
    "200,160 600,160 600,480 200,480",
  );
});

test("does not map a source onto a different rendered page", () => {
  const source = {
    boundingPolygon: [0, 0, 1, 0, 1, 1, 0, 1],
    confidence: null,
    coordinateSystem: "normalized_0_1" as const,
    kind: "ocr_line",
    orderIndex: 0,
    pageNumber: 99,
    sourceKey: null,
  };
  assert.deepEqual(
    toPdfPagePolygonGeometries([source], 1, { width: 200, height: 100 }),
    [],
  );
});
