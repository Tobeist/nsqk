import { test } from "node:test";
import assert from "node:assert/strict";
import { createRealAnalysis, realDefaultSelection } from "../lib/real-data";
import { createMapLayer, getMapLimit } from "../lib/map-layer";
import { intersectedStates, stateNames } from "../lib/geography";
test("RX5Day legend covers executed slopes, including a shorter high-magnitude period", () => {
  for (const [start, end] of [
    [1992, 2024],
    [2000, 2014],
    [2015, 2024],
  ]) {
    const a = createRealAnalysis({ ...realDefaultSelection, start, end });
    const layer = createMapLayer([a], a, "rain5")[0];
    assert.ok(layer.limit >= Math.abs(layer.statistics!.slopePerDecade));
    assert.equal(
      layer.limit,
      getMapLimit("rain5", layer.statistics!.slopePerDecade),
    );
  }
});
test("state highlights describe the requested footprint and never expand the analyzed area", () => {
  assert.deepEqual(
    [...stateNames].sort(),
    ["Coahuila", "Nuevo León", "Tamaulipas", "Texas"].sort(),
  );
  for (const state of intersectedStates) {
    assert.ok(state.intersection.coordinates.length > 0);
    for (const polygon of state.intersection.coordinates)
      for (const ring of polygon)
        for (const [lon, lat] of ring) {
          assert.ok(lon >= -101 && lon <= -99);
          assert.ok(lat >= 25 && lat <= 27);
        }
  }
});
