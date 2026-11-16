import { test } from "node:test";
import assert from "node:assert/strict";
import { createRealAnalysis, realDefaultSelection, defaultTrendBundle } from "../lib/real-data";
import { analysisCsv, localEvidenceChatAdapter, toChatContext, realAnalysisAdapter } from "../lib/adapters";
import { evidenceLabel, uncertainEvidence } from "../lib/format";
import { createMapLayer } from "../lib/map-layer";
import { analyzeOnServer } from "../lib/analysis-server";
import { POST } from "../app/api/analysis/route";
import { regions, type VariableId } from "../lib/catalog";

test("audited evidence, chart guide, map, chat and CSV share adjusted inference", async () => {
  const a = createRealAnalysis(realDefaultSelection);
  const s = a.results[0].statistics!;
  assert.ok(s.confidenceInterval[0] > 0);
  assert.equal(s.evidence?.pValue, .044);
  assert.equal(s.evidence?.pAdjusted, .484);
  assert.equal(s.evidence?.status, "inconclusive");
  assert.match(evidenceLabel(s), /inconclusa/);
  assert.equal(uncertainEvidence(createMapLayer([a], a, "temperature")[0].statistics!), true);
  const result = a.results[0];
  const actualGuideSlope = (result.trend.at(-1)!.value! - result.trend[0].value!) / 32 * 10;
  assert.ok(Math.abs(actualGuideSlope - s.slopePerDecade) < 1e-10);
  const csv = analysisCsv(a, "temperature");
  assert.match(csv, /p_holm/);
  assert.match(csv, /"0.484"/);
  assert.match(csv, /"inconclusive"/);
  assert.match(csv, new RegExp(a.provenance.audit!.fingerprint));
  const chat = await localEvidenceChatAdapter.reply("¿Es significativa?", toChatContext(a, "temperature"));
  assert.match(chat.text, /inconclusa/);
  assert.match(chat.text, /18 pruebas/);
  const enso = await localEvidenceChatAdapter.reply("¿Toma en cuenta El Niño y las estaciones?", toChatContext(a, "temperature"));
  assert.match(enso.text, /once indicadores de mes/);
  assert.match(enso.text, /Sin ENSO/);
});

test("all 21 audited series preserve region, definition and fixed hypothesis families", () => {
  const monthly: VariableId[] = ["temperature", "temperature-min", "temperature-max", "precipitation", "precipitation-power", "rain5"];
  for (const region of regions) {
    for (const variable of [...monthly, "rain5-power-annual" as const]) {
      const a = createRealAnalysis({ ...realDefaultSelection, regionId: region.id, variables: [variable] });
      const r = a.results[0];
      assert.equal(a.region.id, region.id);
      assert.ok(r.evidence);
      assert.equal(r.evidence?.familySize, variable === "rain5-power-annual" ? 3 : 18);
      assert.equal(r.evidence?.sampleSize, variable === "rain5-power-annual" ? 33 : 396);
      if (variable === "rain5-power-annual") assert.equal(r.evidence?.baseline, null);
    }
  }
  const one = createRealAnalysis({ ...realDefaultSelection, variables: ["temperature"] });
  assert.deepEqual(one.results[0].statistics, createRealAnalysis(realDefaultSelection).results[0].statistics);
  const pending = createRealAnalysis({ ...realDefaultSelection, variables: ["rain5-power-annual"] }).results[0].statistics!;
  assert.ok(pending.evidence!.pAdjusted! < .05);
  assert.match(evidenceLabel(pending), /Pendiente/);
  assert.equal(uncertainEvidence(pending), true);
});

test("a changed period must be computed; no silent full-period fallback", async () => {
  const selection = { ...realDefaultSelection, start: 2000, end: 2024 };
  assert.throws(() => createRealAnalysis(selection), /periodo/);
  const a = await analyzeOnServer(selection);
  assert.equal(a.selection.start, 2000);
  assert.equal(a.results[0].series.length, 25);
  assert.equal(a.results[0].statistics?.sampleSize, 300);
  assert.notEqual(a.results[0].statistics?.slopePerDecade, createRealAnalysis(realDefaultSelection).results[0].statistics?.slopePerDecade);
  assert.match(a.results[0].method.description, /2000–2024/);
  assert.equal(a.results[0].evidence?.familySize, 18);
  assert.match(analysisCsv(a, "temperature"), /2000-2024/);
  const c = new AbortController(); c.abort();
  await assert.rejects(realAnalysisAdapter.analyze(selection, c.signal), { name: "AbortError" });
});

test("API rejects invalid input before starting analysis", async () => {
  for (const body of [null, {}, { ...realDefaultSelection, start: "1992" }, { ...realDefaultSelection, variables: ["surface-moisture"] }, { ...realDefaultSelection, variables: ["rain5-power-annual"], start: 2010 }]) {
    const response = await POST(new Request("http://localhost/api/analysis", { method: "POST", body: JSON.stringify(body) }));
    assert.equal(response.status, 400);
  }
});

test("precomputed custom period works without Python in the deployed runtime", async () => {
  const original = process.env.PYTHON_BIN;
  process.env.PYTHON_BIN = "/nonexistent-nsqk-python";
  try {
    const response = await POST(new Request("http://localhost/api/analysis", { method: "POST", body: JSON.stringify({ ...realDefaultSelection, start: 2001 }) }));
    assert.equal(response.status, 200);
    const payload = await response.json();
    assert.deepEqual(payload.selection, { ...realDefaultSelection, start: 2001 });
    assert.equal(payload.provenance.audit.replicates, 4999);
    assert.equal(payload.results[0].statistics.sampleSize, 288);
  } finally {
    if (original === undefined) delete process.env.PYTHON_BIN; else process.env.PYTHON_BIN = original;
  }
});

test("precomputed boundary periods preserve monthly and annual hypothesis families", async () => {
  const monthly = await POST(new Request("http://localhost/api/analysis", {
    method: "POST", body: JSON.stringify({ ...realDefaultSelection, start: 1992, end: 2001 }),
  }));
  assert.equal(monthly.status, 200);
  const monthlyBody = await monthly.json();
  assert.equal(monthlyBody.results[0].statistics.sampleSize, 120);
  assert.equal(monthlyBody.results[0].evidence.familySize, 18);

  const annual = await POST(new Request("http://localhost/api/analysis", {
    method: "POST", body: JSON.stringify({ ...realDefaultSelection, variables: ["rain5-power-annual"], start: 1992, end: 2011 }),
  }));
  assert.equal(annual.status, 200);
  const annualBody = await annual.json();
  assert.equal(annualBody.results[0].statistics.sampleSize, 20);
  assert.equal(annualBody.results[0].evidence.familySize, 3);
});

test("a non-evaluable fit keeps observations and explains why inference is unavailable", () => {
  const bundle = structuredClone(defaultTrendBundle);
  bundle.results["mx-northeast"].temperature = { status: "not-evaluable", reasons: ["AR inestable"], family: "monthly-18", familySize: 18, pAdjusted: 1 };
  const a = createRealAnalysis(realDefaultSelection, bundle);
  assert.equal(a.results[0].statistics, null);
  assert.equal(a.results[0].status, "not-evaluable");
  assert.equal(a.results[0].series.length, 33);
  assert.deepEqual(a.results[0].trend, []);
  assert.match(analysisCsv(a, "temperature"), /not-evaluable/);
});
