import { test } from "node:test";
import assert from "node:assert/strict";
import { createDemoAnalysis, defaultSelection } from "../lib/fixtures";
import { analysisCsv, demoReply, toChatContext } from "../lib/adapters";
import { conversationKey, selectionKey } from "../lib/contracts";
test("fixtures have coherent slope, trend, and honest confidence states", () => {
  const a = createDemoAnalysis({
    ...defaultSelection,
    variables: ["temperature", "precipitation", "surface-moisture"],
  });
  const [temp, rain, soil] = a.results;
  assert.ok(temp.statistics!.confidenceInterval[0] > 0);
  assert.ok(
    rain.statistics!.confidenceInterval[0] < 0 &&
      rain.statistics!.confidenceInterval[1] > 0,
  );
  assert.ok(soil.statistics!.confidenceInterval[1] < 0);
  assert.equal(rain.series.find((d) => d.year === 2001)!.value, null);
  for (const result of a.results) {
    const s = result.statistics!;
    assert.equal(
      s.sampleSize,
      result.series.filter((d) => d.value !== null).length,
    );
    for (const d of result.trend)
      assert.ok(
        Math.abs(d.value! - (s.intercept + (s.slopePerDecade / 10) * d.year)) <
          1e-10,
      );
  }
});
test("analysis IDs are deterministic and chat contexts separate region, period, and variable", () => {
  const a = createDemoAnalysis(defaultSelection),
    b = createDemoAnalysis({ ...defaultSelection, regionId: "us-texas" }),
    c = createDemoAnalysis({ ...defaultSelection, start: 1994 });
  assert.equal(a.id, createDemoAnalysis(defaultSelection).id);
  assert.notEqual(a.id, b.id);
  assert.notEqual(a.id, c.id);
  assert.notEqual(
    conversationKey(a.id, "temperature"),
    conversationKey(a.id, "precipitation"),
  );
  assert.equal(
    selectionKey({
      ...defaultSelection,
      variables: ["temperature", "precipitation"],
    }),
    selectionKey({
      ...defaultSelection,
      variables: ["precipitation", "temperature"],
    }),
  );
});
test("inconclusive chat and CSV use the exact visible analysis", () => {
  const a = createDemoAnalysis({
    ...defaultSelection,
    variables: ["precipitation"],
  });
  const context = toChatContext(a, "precipitation");
  const reply = demoReply("¿Qué tan clara es la evidencia?", context);
  assert.match(reply.text, /Incluye cero/);
  assert.match(reply.text, /sólo demostrativo/);
  const csv = analysisCsv(a, "precipitation");
  assert.match(csv, /"2001","",/);
  assert.match(csv, /"demo"/);
  assert.match(csv, /Fixtures sintéticas locales/);
  assert.match(
    demoReply("¿Se debe a El Niño?", context).text,
    /no podemos atribuir/,
  );
});
test("unavailable combinations and invalid periods do not invent results", () => {
  const a = createDemoAnalysis({
    ...defaultSelection,
    regionId: "us-california",
    variables: ["surface-moisture"],
  });
  assert.equal(a.results[0].status, "no-data");
  assert.equal(a.results[0].statistics, null);
  assert.deepEqual(a.results[0].series, []);
  assert.throws(() => createDemoAnalysis({ ...defaultSelection, start: 2024 }));
  assert.throws(() =>
    createDemoAnalysis({ ...defaultSelection, variables: [] }),
  );
  assert.throws(() =>
    createDemoAnalysis({ ...defaultSelection, variables: ["warm-nights"] }),
  );
});

test("map colors accumulate executed regions and never mix periods or variables", async () => {
  const { createMapLayer, mapColor } = await import("../lib/map-layer");
  const a = createDemoAnalysis(defaultSelection),
    b = createDemoAnalysis({ ...defaultSelection, regionId: "us-texas" }),
    c = createDemoAnalysis({ ...defaultSelection, start: 1994 });
  assert.equal(
    createMapLayer([a, b], b, "temperature").filter(
      (v) => v.state === "analyzed",
    ).length,
    2,
  );
  assert.equal(
    createMapLayer([a, b, c], c, "temperature").filter(
      (v) => v.state === "analyzed",
    ).length,
    1,
  );
  assert.equal(
    createMapLayer([a, b], b, "precipitation").filter(
      (v) => v.state === "analyzed",
    ).length,
    0,
  );
  assert.notEqual(mapColor(-0.4, "temperature"), mapColor(0.4, "temperature"));
});
