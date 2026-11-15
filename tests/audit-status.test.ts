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

test("chat and CSV distinguish the base HAC result from the audited conclusion", async () => {
  const full = createRealAnalysis(realDefaultSelection);
  const reply = await localEvidenceChatAdapter.reply(
    "¿Qué tan clara es la evidencia?", toChatContext(full, "temperature"),
  );
  assert.match(reply.text, /IC HAC del ajuste base/);
  assert.match(reply.text, /inconcluso \(p de Holm 0\.132\)/);
  assert.doesNotMatch(reply.text, /Evidencia de aumento/);
  const csv = analysisCsv(full, "temperature");
  assert.match(csv, /"audit_status","audit_scope","audit_estimate","audit_unit","audit_p_holm"/);
  assert.match(csv, /"inconcluso","mx-northeast; 1992-2024"/);

  const other = createRealAnalysis({ ...realDefaultSelection, regionId: "mx-south-humid" });
  const otherReply = await localEvidenceChatAdapter.reply(
    "¿Qué tan clara es la evidencia?", toChatContext(other, "temperature"),
  );
  assert.match(otherReply.text, /no tiene una conclusión auditada/);
  assert.doesNotMatch(otherReply.text, /p de Holm/);
  assert.match(analysisCsv(other, "temperature"), /"sin auditoría",""/);
});
