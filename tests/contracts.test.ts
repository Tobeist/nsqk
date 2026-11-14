import { test } from "node:test";
import assert from "node:assert/strict";
import { createRealAnalysis, realDefaultSelection } from "../lib/real-data";
import { analysisCsv, localEvidenceChatAdapter, toChatContext } from "../lib/adapters";
import temperature from "../data/results/power_t2m_region_1992_2024.json";
import precipitation from "../data/results/giovanni_gpcp_1992_2024.json";
import rain5 from "../data/results/giovanni_rx5day_1992_2024.json";
import temperatureMin from "../data/results/power_t2m_min_region_1992_2024.json";
import temperatureMax from "../data/results/power_t2m_max_region_1992_2024.json";
import precipitationPower from "../data/results/power_prectotcorr_region_1992_2024.json";
import rain5PowerAnnual from "../data/results/power_rx5day_annual_region_1992_2024.json";

test("MVP uses the three processed NASA series and their monthly statistics", () => {
  const analysis = createRealAnalysis(realDefaultSelection);
  assert.equal(analysis.mode, "real");
  assert.equal(analysis.results.length, 3);
  for (const result of analysis.results) {
    assert.equal(result.status, "ready");
    assert.equal(result.series.length, 33);
    assert.equal(result.statistics?.sampleSize, 396);
    assert.ok(result.source?.startsWith("NASA "));
  }
  assert.ok(analysis.results[0].statistics!.confidenceInterval[0] > 0);
  assert.ok(analysis.results[1].statistics!.confidenceInterval[0] < 0);
  assert.ok(analysis.results[2].statistics!.confidenceInterval[0] < 0);
  for (const [index, source] of [temperature, precipitation, rain5].entries()) {
    const expectedSlope = "trend_per_decade" in source ? source.trend_per_decade : source.trend_c_per_decade;
    const expectedInterval = "trend_ci95_per_decade" in source ? source.trend_ci95_per_decade : source.trend_ci95_c_per_decade;
    const actual = analysis.results[index].statistics!;
    assert.ok(Math.abs(actual.slopePerDecade - expectedSlope) < 1e-9);
    assert.ok(Math.abs(actual.confidenceInterval[0] - expectedInterval[0]) < 1e-9);
    assert.ok(Math.abs(actual.confidenceInterval[1] - expectedInterval[1]) < 1e-9);
  }
});

test("selected years recalculate the annual series, trend, interval and explanation", async () => {
  const selection = { ...realDefaultSelection, start: 2000, end: 2014 };
  const analysis = createRealAnalysis(selection);
  const full = createRealAnalysis(realDefaultSelection);
  for (let i = 0; i < 3; i++) {
    const result = analysis.results[i];
    assert.equal(result.series.length, 15);
    assert.equal(result.series[0].year, 2000);
    assert.equal(result.series.at(-1)?.year, 2014);
    assert.equal(result.statistics?.sampleSize, 180);
    assert.notEqual(result.statistics?.slopePerDecade, full.results[i].statistics?.slopePerDecade);
    assert.notDeepEqual(result.statistics?.confidenceInterval, full.results[i].statistics?.confidenceInterval);
  }
  const csv = analysisCsv(analysis, "temperature");
  assert.match(csv, /2000-2014/);
  assert.doesNotMatch(csv, /"1999"/);
  const reply = await localEvidenceChatAdapter.reply("¿Qué significa la pendiente?", toChatContext(analysis, "temperature"));
  assert.match(reply.text, /2000–2014/);
  assert.match(reply.text, /180 meses/);
});

test("three added POWER monthly variables reproduce the versioned statistics", () => {
  const analysis = createRealAnalysis({
    ...realDefaultSelection,
    variables: ["temperature-min", "temperature-max", "precipitation-power"],
  });
  for (const [index, source] of [temperatureMin, temperatureMax, precipitationPower].entries()) {
    const result = analysis.results[index];
    assert.equal(result.sampleUnit, "meses");
    assert.equal(result.statistics?.sampleSize, 396);
    assert.ok(Math.abs(result.statistics!.slopePerDecade - source.trend_per_decade) < 1e-9);
    assert.ok(Math.abs(result.statistics!.confidenceInterval[0] - source.trend_ci95_per_decade[0]) < 1e-9);
    assert.ok(Math.abs(result.statistics!.confidenceInterval[1] - source.trend_ci95_per_decade[1]) < 1e-9);
  }
  assert.match(analysisCsv(analysis, "precipitation-power"), /NASA POWER PRECTOTCORR/);
});

test("derived annual RX5day keeps its annual HAC(3) method and 20-year minimum", async () => {
  const selection = { ...realDefaultSelection, variables: ["rain5", "rain5-power-annual"] as Array<"rain5" | "rain5-power-annual"> };
  const full = createRealAnalysis(selection);
  const monthly = full.results[0];
  const annual = full.results[1];
  assert.equal(monthly.sampleUnit, "meses");
  assert.equal(monthly.method.id, "monthly-seasonal-hac12-v2");
  assert.equal(annual.sampleUnit, "años");
  assert.equal(annual.method.id, "annual-ols-hac3-v1");
  assert.equal(annual.statistics?.sampleSize, 33);
  assert.ok(Math.abs(annual.statistics!.slopePerDecade - rain5PowerAnnual.trend_mm_per_decade) < 1e-9);
  assert.ok(Math.abs(annual.statistics!.confidenceInterval[0] - rain5PowerAnnual.ci95_mm_per_decade[0]) < 1e-9);
  assert.ok(Math.abs(annual.statistics!.confidenceInterval[1] - rain5PowerAnnual.ci95_mm_per_decade[1]) < 1e-9);
  assert.throws(() => createRealAnalysis({ ...selection, start: 2006, end: 2024 }));
  const shorter = createRealAnalysis({ ...selection, start: 2005, end: 2024 }).results[1];
  assert.equal(shorter.statistics?.sampleSize, 20);
  assert.notEqual(shorter.statistics?.slopePerDecade, annual.statistics?.slopePerDecade);
  const csv = analysisCsv(full, "rain5-power-annual");
  assert.match(csv, /annual-ols-hac3-v1/);
  assert.match(csv, /máximo anual de cinco días/);
  const reply = await localEvidenceChatAdapter.reply("¿Qué significa esta pendiente?", toChatContext(full, "rain5-power-annual"));
  assert.match(reply.text, /33 años/);
  assert.match(reply.text, /HAC\(3\)/);
  assert.doesNotMatch(reply.text, /meses, estacionalidad/);
});

test("unsupported region, short or unavailable time window, or pending variable cannot reuse the northeast result", () => {
  assert.throws(() => createRealAnalysis({ ...realDefaultSelection, regionId: "mx-northwest" }));
  assert.throws(() => createRealAnalysis({ ...realDefaultSelection, start: 2016 }));
  assert.throws(() => createRealAnalysis({ ...realDefaultSelection, start: 1991 }));
  assert.throws(() => createRealAnalysis({ ...realDefaultSelection, end: 2025 }));
  assert.throws(() => createRealAnalysis({ ...realDefaultSelection, variables: ["surface-moisture"] }));
});

test("download and local explanation identify the actual source", async () => {
  const analysis = createRealAnalysis(realDefaultSelection);
  const csv = analysisCsv(analysis, "precipitation");
  assert.match(csv, /"real"/);
  assert.match(csv, /NASA Giovanni · GPCP/);
  assert.doesNotMatch(csv, /Fixtures sintéticas/);
  const reply = await localEvidenceChatAdapter.reply("¿Qué tan clara es la evidencia?", toChatContext(analysis, "rain5"));
  assert.match(reply.text, /incluye cero/i);
});
