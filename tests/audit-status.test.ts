import { test } from "node:test";
import assert from "node:assert/strict";
import { getAuditStatus } from "../lib/audit-status";
import { analysisCsv, localEvidenceChatAdapter, toChatContext } from "../lib/adapters";
import { createRealAnalysis, realDefaultSelection } from "../lib/real-data";

test("published conclusions apply only to the audited northeast and complete period", () => {
  for (const variableId of ["temperature", "precipitation", "rain5"] as const) {
    const audit = getAuditStatus(realDefaultSelection, variableId);
    assert.equal(audit?.status, "inconcluso");
    assert.ok(audit!.pHolm >= 0.05);
  }
  assert.equal(getAuditStatus(realDefaultSelection, "rain5-power-annual")?.status, "pendiente");
  assert.equal(getAuditStatus(realDefaultSelection, "temperature-min"), null);
  assert.equal(getAuditStatus({ ...realDefaultSelection, regionId: "mx-south-humid" }, "temperature"), null);
  assert.equal(getAuditStatus({ ...realDefaultSelection, start: 2000 }, "temperature"), null);
});

test("expanded app inference distinguishes its 18-test family from the historical 3-test audit", async () => {
  const full = createRealAnalysis(realDefaultSelection);
  const reply = await localEvidenceChatAdapter.reply(
    "¿Qué tan clara es la evidencia?", toChatContext(full, "temperature"),
  );
  assert.match(reply.text, /intervalo individual/);
  assert.match(reply.text, /inconclusa/);
  assert.match(reply.text, /p de Holm: 0\.484/);
  assert.equal(getAuditStatus(realDefaultSelection, "temperature")?.pHolm, .132);
  assert.doesNotMatch(reply.text, /Evidencia de aumento/);
  const csv = analysisCsv(full, "temperature");
  assert.match(csv, /"p_bootstrap_t","p_holm","family","family_size"/);
  assert.match(csv, /"monthly-18","18","inconclusive"/);

  const other = createRealAnalysis({ ...realDefaultSelection, regionId: "mx-south-humid" });
  const otherReply = await localEvidenceChatAdapter.reply(
    "¿Qué tan clara es la evidencia?", toChatContext(other, "temperature"),
  );
  assert.match(otherReply.text, /p de Holm/);
  assert.match(otherReply.text, /18 pruebas/);
  assert.match(analysisCsv(other, "temperature"), /"monthly-18","18"/);
});
