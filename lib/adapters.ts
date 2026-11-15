import { signed, evidenceLabel } from "./format";
import { getVariable } from "./catalog";
import { createRealAnalysis } from "./real-data";
import { selectionKey, type Analysis, type AnalysisAdapter, type ChatAdapter, type ChatContext } from "./contracts";
export const realAnalysisAdapter: AnalysisAdapter = {
  async analyze(selection, signal) {
    if (signal?.aborted) throw new DOMException("Cancelado", "AbortError");
    if (selection.start === 1992 && selection.end === 2024) return createRealAnalysis(selection);
    const response = await fetch("/api/analysis", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(selection), signal,
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "No se pudo calcular el periodo seleccionado.");
    const analysis = payload as Analysis;
    if (selectionKey(analysis.selection) !== selectionKey(selection) || !analysis.provenance.audit) {
      throw new Error("El resultado no corresponde a la selección. Vuelve a analizar.");
    }
    return analysis;
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
    if (/causa|niño|enso|pdo|estacion|estaci[oó]n|calendario|futuro|pron[oó]st|clim[aá]tico/.test(q))
      return { text: `${s.evidence?.baseline ? `La regresión incluye once indicadores de mes y Niño 3.4 contemporáneo: controla el calendario estacional y parte de la variación asociada a ENSO. Sin ENSO: ${signed(s.evidence.baseline.slopePerDecade, 3)}; con ENSO: ${signed(s.slopePerDecade, 3)} ${context.unit}/década.` : "El índice anual se analiza sin ajuste ENSO."} No controla todos los factores naturales, no establece causas ni permite pronosticar. La caja no representa estados completos.`, evidence: "method" };
    if (/evidencia|intervalo|significativ|significancia|confian|segur|clara/.test(q))
      return { text: `El intervalo individual del 95 % es ${signed(s.confidenceInterval[0], 3)} a ${signed(s.confidenceInterval[1], 3)} ${context.unit}/década. ${evidenceLabel(s)} en esta caja y periodo. ${s.evidence ? `p de bootstrap-t AR: ${s.evidence.pValue}; p de Holm: ${s.evidence.pAdjusted} (${s.evidence.familySize} pruebas). ${s.evidence.reasons.join(" ")} El intervalo individual no determina por sí solo la certeza tras pruebas múltiples.` : "Resultado de referencia sin auditoría integrada."} Un intervalo que incluye cero no demuestra ausencia de cambio.`, evidence: "interval" };
    return { text: `La pendiente estimada es ${signed(s.slopePerDecade, 3)} ${context.unit} por década para ${context.selection.start}–${context.selection.end}. Se estimó con ${s.sampleSize} ${context.sampleUnit} mediante ${context.method.name}. La gráfica muestra ${context.annualLabel}. ${context.sources.limitations[0]}`, evidence: "slope" };
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
    "period_start", "period_end", "p_bootstrap_t", "p_holm", "family", "family_size",
    "evidence_status", "evidence_reasons", "slope_without_enso", "p_holm_without_enso",
    "ci_definition", "bootstrap_replicates", "bootstrap_seed", "audit_version", "input_fingerprint",
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
        analysis.selection.start, analysis.selection.end,
        r.evidence?.pValue, r.evidence?.pAdjusted,
        r.evidence?.family, r.evidence?.familySize,
        r.evidence?.status, r.evidence?.reasons.join(" ") ?? r.limitations.join(" "),
        r.statistics?.evidence?.baseline?.slopePerDecade, r.statistics?.evidence?.baseline?.pAdjusted,
        r.evidence ? "Individual 95%; bootstrap-t AR; no simultáneo" : "Referencia: aproximación normal HAC",
        analysis.provenance.audit?.replicates, analysis.provenance.audit?.seed,
        analysis.provenance.audit?.version, analysis.provenance.audit?.fingerprint,
      ]),
    ]
      .map((row) => row.map(quote).join(","))
      .join("\r\n")
  );
}
