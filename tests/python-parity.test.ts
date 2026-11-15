import { test } from "node:test";
import assert from "node:assert/strict";
import { createRealAnalysis, realDefaultSelection } from "../lib/real-data";
import { analysisCsv } from "../lib/adapters";
import fixture from "../analysis/results/parity_fixture.json";

type Entry = {
  slope_per_decade: number;
  ci95: [number, number];
  n_months: number;
  annual_means: number[];
  annual_ols_intercept: number;
  annual_ols_slope_per_year: number;
};
type Window = { start: number; end: number } & Record<"t2m" | "gpcp" | "rx5d", Entry>;
const python = fixture as unknown as Record<"W0" | "W3", Window>;
const ids = { t2m: "temperature", gpcp: "precipitation", rx5d: "rain5" } as const;
const close = (a: number, b: number, message: string) => assert.ok(Math.abs(a - b) < 1e-9, `${message}: ${a} vs ${b}`);

// Regenerate the fixture with `python scripts/trend_audit.py` after changing the data or the model.
for (const label of ["W0", "W3"] as const) {
  test(`Python audit, app statistics, chart series and CSV export agree for ${label}`, () => {
    const { start, end } = python[label];
    const analysis = createRealAnalysis({ ...realDefaultSelection, start, end });
    for (const [key, id] of Object.entries(ids) as [keyof typeof ids, (typeof ids)[keyof typeof ids]][]) {
      const expected = python[label][key];
      const result = analysis.results.find((r) => r.variableId === id)!;
      const stats = result.statistics!;
      assert.equal(stats.sampleSize, expected.n_months);
      close(stats.slopePerDecade, expected.slope_per_decade, `${key} slope`);
      close(stats.confidenceInterval[0], expected.ci95[0], `${key} ci low`);
      close(stats.confidenceInterval[1], expected.ci95[1], `${key} ci high`);
      result.series.forEach((row, i) => {
        close(row.value as number, expected.annual_means[i], `${key} annual mean ${row.year}`);
        // The drawn line is the least-squares fit of the annual means, with the monthly-model slope.
        close(result.trend[i].value as number, expected.annual_ols_intercept + expected.annual_ols_slope_per_year * row.year, `${key} trend ${row.year}`);
      });
      close(10 * expected.annual_ols_slope_per_year, expected.slope_per_decade, `${key} annual-means slope`);
      const [header, first] = analysisCsv(analysis, id).replace("﻿", "").split("\r\n").map((line) => line.slice(1, -1).split('","'));
      const column = (name: string) => Number(first[header.indexOf(name)]);
      close(column("slope_per_decade"), expected.slope_per_decade, `${key} csv slope`);
      close(column("ci95_low"), expected.ci95[0], `${key} csv ci low`);
      close(column("ci95_high"), expected.ci95[1], `${key} csv ci high`);
    }
  });
}
