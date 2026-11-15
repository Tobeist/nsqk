import { test } from "node:test";
import assert from "node:assert/strict";
import { forecastBundle, forecastValues, forecastCsv, getForecast } from "../lib/forecast-data";

test("forecast chart and CSV share real trajectories with a distinct future/data boundary", () => {
  const r = getForecast("mx-northeast", "temperature", 1992, 2024)!;
  assert.equal(r.projection.length, 12);
  assert.equal(r.holdout.length, 48);
  const first = r.projection[0];
  assert.equal(first.date, "2025-01-01");
  assert.deepEqual(forecastValues(first, "neural", r.selectedModel), { value: first.neuralValue, lower: first.neuralLower, upper: first.neuralUpper });
  assert.notEqual(forecastValues(first, "climatology", r.selectedModel).value, first.value);
  const csv = forecastCsv("mx-northeast", "temperature", "projection", "neural");
  assert.match(csv, /projection_from_2024/);
  assert.match(csv, /2024-12-01/);
  assert.match(csv, new RegExp(String(first.neuralValue)));
  assert.equal(csv.split("\r\n").length, 13);
});

test("all 18 test errors agree with exported out-of-year predictions", () => {
  let count = 0;
  for (const [rid, entries] of Object.entries(forecastBundle.results)) {
    for (const [vid, result] of Object.entries(entries)) {
      const r = result!; count++;
      for (const model of [r.selectedModel, "neural", "neural-enso", "climatology"] as const) {
        const mae = r.holdout.reduce((sum, p) => sum + Math.abs(forecastValues(p, model, r.selectedModel).value - p.actual), 0) / 48;
        assert.ok(Math.abs(mae - r.models.find((m) => m.id === model)!.testMae) < 1e-9, `${rid}/${vid}/${model}`);
      }
      for (const p of r.holdout) {
        assert.ok(p.trainedThrough < p.date);
        assert.equal(p.ensoKnownThrough, `${Number(p.date.slice(0, 4)) - 1}-10-01`);
      }
      const incumbent = r.models.filter((m) => m.id !== "neural-enso");
      assert.equal(r.selectedModel, incumbent.reduce((best, m) => m.validationMae < best.validationMae ? m : best).id);
      assert.equal(r.validationWinner, r.models.reduce((best, m) => m.validationMae < best.validationMae ? m : best).id);
      assert.equal(r.deploymentPolicy, "retain-v1-until-independent-validation");
    }
  }
  assert.equal(count, 18);
});

test("ENSO trajectory and CSV retain their own predictions and historical input cutoff", () => {
  const r = getForecast("mx-chihuahua-interior", "temperature-max", 1992, 2024)!;
  for (const p of [...r.holdout, ...r.projection]) {
    assert.deepEqual(forecastValues(p, "neural-enso", r.selectedModel), {
      value: p.ensoValue, lower: p.ensoLower, upper: p.ensoUpper,
    });
  }
  const csv = forecastCsv("mx-chihuahua-interior", "temperature-max", "projection", "neural-enso");
  const [header, first] = csv.replace(/^\uFEFF/, "").split("\r\n").map((row) => row.split(",").map((v) => v.slice(1, -1)));
  const row = Object.fromEntries(header.map((key, index) => [key.replace("\uFEFF", ""), first[index]]));
  assert.equal(row.prediction, String(r.projection[0].ensoValue));
  assert.equal(row.uses_historical_enso, "true");
  assert.equal(row.enso_known_through, "2024-10-01");
  assert.equal(row.unknown_enso_strategy, "persistence");
  const plainCsv = forecastCsv("mx-chihuahua-interior", "temperature-max", "projection", "neural");
  assert.doesNotMatch(plainCsv, /2024-10-01/);
  assert.match(plainCsv, /"false","",""/);
});

test("unsupported variable or period cannot reuse the full-series forecast", () => {
  assert.equal(getForecast("mx-northeast", "rain5-power-annual", 1992, 2024), null);
  assert.equal(getForecast("mx-northeast", "temperature", 2000, 2024), null);
  assert.equal(getForecast("missing", "temperature", 1992, 2024), null);
});
