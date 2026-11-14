import {
  createDemoAnalysis,
  formatNumber,
  signed,
  evidenceLabel,
} from "./fixtures";
import { getVariable } from "./catalog";
import type { AnalysisAdapter, ChatAdapter, ChatContext } from "./contracts";
function pause(ms: number, signal?: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(new DOMException("Cancelado", "AbortError"));
      },
      { once: true },
    );
  });
}
export const demoAnalysisAdapter: AnalysisAdapter = {
  async analyze(selection, signal) {
    await pause(700, signal);
    return createDemoAnalysis(selection);
  },
};
export function demoReply(question: string, c: ChatContext) {
  const s = c.statistics,
    variable = getVariable(c.variableId);
  if (!s)
    return {
      text: "Esta combinación no tiene una serie de demostración disponible. No puedo estimar una tendencia ni interpretar evidencia inexistente.",
      evidence: "method" as const,
    };
  const q = question.toLowerCase(),
    prefix = `En este ejemplo de ${variable.name.toLowerCase()} para ${c.region.name} (${c.selection.start}–${c.selection.end}), `;
  if (
    /causa|concluir|niño|enso|pdo|futuro|pron[oó]st|ma[ñn]ana|clim[aá]tico/.test(
      q,
    )
  )
    return {
      text:
        prefix +
        "no podemos atribuir el cambio a una causa, separar El Niño de otras influencias ni predecir el futuro. Los datos son sintéticos y el ajuste describe sólo el periodo elegido. Harían falta observaciones, validación y un método científico apropiado.",
      evidence: "method" as const,
    };
  if (/evidencia|clara|intervalo|segur|signific|confian|real/.test(q)) {
    const crosses =
      s.confidenceInterval[0] <= 0 && s.confidenceInterval[1] >= 0;
    return {
      text:
        prefix +
        `el intervalo del 95 % va de ${signed(s.confidenceInterval[0], 3)} a ${signed(s.confidenceInterval[1], 3)} ${c.unit}/década. ${crosses ? "Incluye cero: la dirección no queda resuelta por este ajuste. Eso no demuestra ausencia de cambio." : "Excluye cero: el ajuste ilustra evidencia de " + (s.slopePerDecade > 0 ? "aumento" : "disminución") + ". Eso no identifica su causa."} Este intervalo supone errores independientes y es sólo demostrativo.`,
      evidence: "interval" as const,
    };
  }
  return {
    text:
      prefix +
      `la pendiente es ${signed(s.slopePerDecade, 3)} ${c.unit} por década: la recta ajustada cambia esa cantidad cada diez años. No significa que todos los años cambien igual. ${evidenceLabel(s)} en esta fixture, con ${s.sampleSize} valores anuales. El promedio de la serie es ${formatNumber(c.series.filter((d) => d.value !== null).reduce((a, d) => a + d.value!, 0) / s.sampleSize, 3)} ${c.unit}. Son cifras sintéticas, no un hallazgo ambiental.`,
    evidence: "slope" as const,
  };
}
export const mockChatAdapter: ChatAdapter = {
  connected: true,
  mode: "demo",
  async reply(question, context, signal) {
    await pause(850, signal);
    return demoReply(question, context);
  },
};
// Future server adapters implement these interfaces. There is no operational Claude/NASA endpoint.
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
        analysis.provenance.source,
        analysis.provenance.updatedAt,
      ]),
    ]
      .map((row) => row.map(quote).join(","))
      .join("\r\n")
  );
}
