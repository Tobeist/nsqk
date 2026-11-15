import { test } from "node:test";
import assert from "node:assert/strict";
import { forecastBundle, forecastValues, forecastCsv, getForecast } from "../lib/forecast-data";

test("forecast chart and CSV share real trajectories with a distinct future/data boundary", () => {
  const r = getForecast("mx-northeast", "temperature", 1992, 2024)!;
  assert.equal(r.selectedModel, "neural");
  assert.equal(r.projection.length, 12);
  assert.equal(r.holdout.length, 48);
  const first = r.projection[0];
  assert.equal(first.date, "2025-01-01");
  assert.deepEqual(forecastValues(first, "neural", r.selectedModel), { value: first.value, lower: first.lower, upper: first.upper });
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
      for (const model of [r.selectedModel, "neural", "climatology"] as const) {
        const mae = r.holdout.reduce((sum, p) => sum + Math.abs(forecastValues(p, model, r.selectedModel).value - p.actual), 0) / 48;
        assert.ok(Math.abs(mae - r.models.find((m) => m.id === model)!.testMae) < 1e-9, `${rid}/${vid}/${model}`);
      }
      for (const p of r.holdout) assert.ok(p.trainedThrough < p.date);
      assert.equal(r.selectedModel, r.models.reduce((best, m) => m.validationMae < best.validationMae ? m : best).id);
    }
  }
  assert.equal(count, 18);
});

test("unsupported variable or period cannot reuse the full-series forecast", () => {
  assert.equal(getForecast("mx-northeast", "rain5-power-annual", 1992, 2024), null);
  assert.equal(getForecast("mx-northeast", "temperature", 2000, 2024), null);
  assert.equal(getForecast("missing", "temperature", 1992, 2024), null);
});
