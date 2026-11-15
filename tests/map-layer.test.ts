// Historical HAC calculation checks. Production inference is tested in app-evidence.test.ts.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createReferenceAnalysis as createRealAnalysis, realDefaultSelection } from "../lib/real-data";
import { createMapLayer, getMapLimit } from "../lib/map-layer";
import { getIntersectedStates, getStateNames, intersectedStates, stateNames } from "../lib/geography";
import { regions } from "../lib/catalog";
test("Reference: RX5Day legend covers executed slopes, including a shorter high-magnitude period", () => {
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

test("Reference: all three study boxes have geographic intersections inside their own bounds", () => {
  for (const region of regions) {
    const [west, south, east, north] = region.bbox;
    const states = getIntersectedStates(region.id);
    assert.ok(states.length > 0);
    assert.equal(getStateNames(region.id).length, states.length);
    for (const state of states)
      for (const polygon of state.intersection.coordinates)
        for (const ring of polygon)
          for (const [lon, lat] of ring) {
            assert.ok(lon >= west - 1e-9 && lon <= east + 1e-9);
            assert.ok(lat >= south - 1e-9 && lat <= north + 1e-9);
          }
  }
  assert.deepEqual(getStateNames("mx-chihuahua-interior"), ["Chihuahua"]);
  assert.deepEqual(getStateNames("mx-south-humid"), ["Chiapas", "Estado de Veracruz", "Oaxaca", "Tabasco"]);
});
test("Reference: state highlights describe the requested footprint and never expand the analyzed area", () => {
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
