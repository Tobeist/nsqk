import { signed, evidenceLabel } from "./format";
import { getVariable } from "./catalog";
import { createRealAnalysis } from "./real-data";
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
    if (/causa|niño|enso|pdo|futuro|pron[oó]st|clim[aá]tico/.test(q))
      return { text: "Este análisis describe la serie y su incertidumbre. No permite atribuir causas, aislar ENSO/PDO ni pronosticar. La caja estudiada tampoco representa todo el noreste de México.", evidence: "method" };
    if (/evidencia|intervalo|significativ|significancia|confian|segur|clara/.test(q))
      return { text: `El intervalo del 95 % es ${signed(s.confidenceInterval[0], 3)} a ${signed(s.confidenceInterval[1], 3)} ${context.unit}/década. ${evidenceLabel(s)} en esta caja y periodo. Un intervalo que incluye cero no demuestra ausencia de cambio. Son resultados exploratorios sin corrección por múltiples pruebas.`, evidence: "interval" };
    return { text: `La pendiente estimada es ${signed(s.slopePerDecade, 3)} ${context.unit} por década para ${context.selection.start}–${context.selection.end}. Se estimó con ${s.sampleSize} meses, estacionalidad y errores HAC(12). La gráfica muestra promedios anuales para facilitar la lectura. ${context.sources.limitations[0]}`, evidence: "slope" };
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
    method: analysis.method,
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
    "trend",
    "slope_per_decade",
    "ci95_low",
    "ci95_high",
    "method",
    "source",
    "updated_at",
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
        r.trend[i]?.value,
        r.statistics?.slopePerDecade,
        r.statistics?.confidenceInterval[0],
        r.statistics?.confidenceInterval[1],
        analysis.method.name,
        r.source ?? analysis.provenance.source,
        analysis.provenance.updatedAt,
      ]),
    ]
      .map((row) => row.map(quote).join(","))
      .join("\r\n")
  );
}
