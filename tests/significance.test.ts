import { test } from "node:test";
import assert from "node:assert/strict";
import { getSignificance } from "../lib/significance";
import { createRealAnalysis, realDefaultSelection } from "../lib/real-data";
import { analysisCsv, claudeChatAdapter, toChatContext } from "../lib/adapters";

test("an individual positive CI does not imply Holm significance", () => {
  const a = createRealAnalysis(realDefaultSelection);
  assert.ok(a.results[0].statistics!.confidenceInterval[0] > 0);
  assert.equal(getSignificance(a.results[0].evidence).significant, false);
  assert.match(analysisCsv(a, "temperature"), /"false","No estadísticamente significativo","0.05"/);
});

test("a significant test can still require independent validation", () => {
  const a = createRealAnalysis({ ...realDefaultSelection, variables: ["rain5-power-annual"] });
  assert.equal(a.results[0].evidence?.status, "pending");
  assert.equal(getSignificance(a.results[0].evidence).significant, true);
  assert.match(getSignificance(a.results[0].evidence).description, /no establece causas/);
  assert.equal(getSignificance({ status: "consistent", reasons: [], pAdjusted: .05 }).significant, false);
  assert.equal(getSignificance({ status: "not-evaluable", reasons: [], pAdjusted: 1 }).significant, null);
  assert.equal(getSignificance().significant, null);
});

test("Claude client sends selection and history, never client statistics or secrets", async (t) => {
  const a = createRealAnalysis(realDefaultSelection);
  let sent: Record<string, unknown> = {};
  t.mock.method(globalThis, "fetch", async (_url: string, init: RequestInit) => {
    sent = JSON.parse(init.body as string);
    return Response.json({ provider: "claude", analysisId: a.id, text: "Respuesta", model: "test-model" });
  });
  const reply = await claudeChatAdapter.reply("¿Es significativo?", toChatContext(a, "temperature"), undefined, [{ role: "user", text: "Hola" }]);
  assert.equal(reply.provider, "claude");
  assert.equal(sent.statistics, undefined);
  assert.equal(sent.apiKey, undefined);
  assert.equal(sent.variableId, "temperature");
  assert.deepEqual(sent.history, [{ role: "user", text: "Hola" }]);
});

test("Claude client refuses a response from a different period", async (t) => {
  const a = createRealAnalysis(realDefaultSelection);
  t.mock.method(globalThis, "fetch", async () => Response.json({ provider: "claude", analysisId: "other-period", text: "Respuesta" }));
  await assert.rejects(claudeChatAdapter.reply("¿Es significativo?", toChatContext(a, "temperature")), /no corresponde/);
});
