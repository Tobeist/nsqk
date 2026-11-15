import { signed, formatNumber } from "./format";
import { getVariable } from "./catalog";
import { createRealAnalysis } from "./real-data";
import { auditStatusExplanation, auditStatusLabel, getAuditStatus } from "./audit-status";
import type { AnalysisAdapter, ChatAdapter, ChatContext } from "./contracts";
export const realAnalysisAdapter: AnalysisAdapter = {
  async analyze(selection, signal) {
    if (signal?.aborted) throw new DOMException("Cancelado", "AbortError");
    return createRealAnalysis(selection);
  },
};
export const localEvidenceChatAdapter: ChatAdapter = {
  connected: true,
  mode: "real",
  async reply(question, context, signal) {
    if (signal?.aborted) throw new DOMException("Cancelado", "AbortError");
    const s = context.statistics;
    if (!s) return { text: "No hay datos para esta selección.", evidence: "method" };
    const q = question.toLowerCase();
    const audit = getAuditStatus(context.selection, context.variableId);
    const auditText = audit
      ? `La auditoría del periodo completo clasifica el resultado como ${auditStatusLabel(audit.status).toLowerCase()} (p de Holm ${formatNumber(audit.pHolm, 3)}). ${auditStatusExplanation(audit.status)}`
      : "Esta caja, variable o ventana de años no tiene una conclusión auditada; el resultado es exploratorio.";
    if (/causa|niño|enso|pdo|futuro|pron[oó]st|clim[aá]tico/.test(q))
      return { text: `Este análisis describe la serie y su incertidumbre. No permite atribuir causas ni pronosticar. La caja estudiada no representa estados completos ni todo México. ${auditText}`, evidence: "method" };
    if (/evidencia|intervalo|significativ|significancia|confian|segur|clara/.test(q))
      return { text: `El IC HAC del ajuste base (95 %) es ${signed(s.confidenceInterval[0], 3)} a ${signed(s.confidenceInterval[1], 3)} ${context.unit}/década e ${s.confidenceInterval[0] <= 0 && s.confidenceInterval[1] >= 0 ? "incluye" : "excluye"} cero. Este intervalo individual no es la conclusión final. ${auditText}`, evidence: "interval" };
    return { text: `La pendiente estimada del ajuste base es ${signed(s.slopePerDecade, 3)} ${context.unit} por década para ${context.selection.start}–${context.selection.end}. Se estimó con ${s.sampleSize} ${context.sampleUnit} mediante ${context.method.name}. La gráfica muestra ${context.annualLabel}. ${auditText}`, evidence: "slope" };
  },
};
export function toChatContext(
  analysis: import("./contracts").Analysis,
  variableId: import("./catalog").VariableId,
): ChatContext {
  const result = analysis.results.find((r) => r.variableId === variableId)!;
  return {
    analysisId: analysis.id,
    selection: analysis.selection,
    region: analysis.region,
    variableId,
    unit: result.unit,
    series: result.series,
    statistics: result.statistics,
    method: result.method,
    sampleUnit: result.sampleUnit,
    annualLabel: result.annualLabel,
    sources: analysis.provenance,
    mode: analysis.mode,
  };
}
export function analysisCsv(
  analysis: import("./contracts").Analysis,
  variableId: import("./catalog").VariableId,
) {
  const r = analysis.results.find((d) => d.variableId === variableId)!;
  const audit = getAuditStatus(analysis.selection, variableId);
  const quote = (s: unknown) => `"${String(s ?? "").replaceAll('"', '""')}"`;
  const headers = [
    "analysis_id",
    "mode",
    "region",
    "bbox_w_s_e_n",
    "variable",
    "unit",
    "year",
    "value",
    "annual_value_definition",
    "trend",
    "slope_per_decade",
    "ci95_low",
    "ci95_high",
    "method",
    "method_id",
    "sample_size",
    "sample_unit",
    "source",
    "updated_at",
    "audit_status",
    "audit_scope",
    "audit_estimate",
    "audit_unit",
    "audit_p_holm",
    "audit_ci95_low",
    "audit_ci95_high",
    "audit_method",
  ];
  return (
    "\uFEFF" +
    [
      headers,
      ...r.series.map((d, i) => [
        analysis.id,
        analysis.mode,
        analysis.region.name,
        analysis.region.bbox.join(" "),
        getVariable(variableId).name,
        r.unit,
        d.year,
        d.value,
        r.annualLabel,
        r.trend[i]?.value,
        r.statistics?.slopePerDecade,
        r.statistics?.confidenceInterval[0],
        r.statistics?.confidenceInterval[1],
        r.method.name,
        r.method.id,
        r.statistics?.sampleSize,
        r.sampleUnit,
        r.source,
        analysis.provenance.updatedAt,
        audit?.status ?? "sin auditoría",
        audit ? "mx-northeast; 1992-2024" : "",
        audit?.estimate,
        audit?.unit,
        audit?.pHolm,
        audit?.ciLow,
        audit?.ciHigh,
        audit?.model,
      ]),
    ]
      .map((row) => row.map(quote).join(","))
      .join("\r\n")
  );
}
