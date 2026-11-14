import temperature from "../data/results/power_t2m_region_1992_2024.json";
import precipitation from "../data/results/giovanni_gpcp_1992_2024.json";
import rain5 from "../data/results/giovanni_rx5day_1992_2024.json";
import { getRegion, type VariableId } from "./catalog";
import { selectionKey, type Analysis, type Selection, type VariableResult } from "./contracts";
import { seasonalTrend } from "./seasonal-trend";

export const firstDataYear = 1992;
export const lastDataYear = 2024;
export const minimumAnalysisYears = 10;

export const realDefaultSelection: Selection = {
  regionId: "mx-northeast",
  variables: ["temperature", "precipitation", "rain5"],
  start: 1992,
  end: 2024,
};

type MonthlyResult = {
  n_months: number;
  monthly: Array<{ date: string; value?: number; t2m_c?: number }>;
};

const sources: Record<"temperature" | "precipitation" | "rain5", {
  data: MonthlyResult;
  unit: string;
  source: string;
}> = {
  temperature: { data: temperature, unit: "°C", source: "NASA POWER T2M · MERRA-2" },
  precipitation: { data: precipitation, unit: "mm/día", source: "NASA Giovanni · GPCP satélite + pluviómetros" },
  rain5: { data: rain5, unit: "mm", source: "NASA Giovanni · MERRA-2 M2SMNXEDI RX5Day mensual" },
};

export function createRealAnalysis(selection: Selection): Analysis {
  if (selection.regionId !== "mx-northeast" ||
      !Number.isInteger(selection.start) || !Number.isInteger(selection.end) ||
      selection.start < firstDataYear || selection.end > lastDataYear ||
      selection.end - selection.start + 1 < minimumAnalysisYears ||
      selection.variables.length < 1 || selection.variables.length > 3 ||
      new Set(selection.variables).size !== selection.variables.length ||
      selection.variables.some((id) => !(id in sources))) {
    throw new Error("Selecciona la caja disponible, al menos diez años completos entre 1992 y 2024 y una de las tres variables integradas.");
  }
  const results: VariableResult[] = selection.variables.map((id) => {
    const entry = sources[id as keyof typeof sources];
    const data = entry.data;
    if (data.n_months !== 396 || data.monthly.length !== 396) {
      throw new Error(`Resultado incompleto para ${id}`);
    }
    const monthly = data.monthly.filter((row) => {
      const year = Number(row.date.slice(0, 4));
      return year >= selection.start && year <= selection.end;
    });
    const expectedMonths = (selection.end - selection.start + 1) * 12;
    if (monthly.length !== expectedMonths) throw new Error(`Serie mensual incompleta para ${id}`);
    const values = monthly.map((row, i) => {
      const expectedDate = `${selection.start + Math.floor(i / 12)}-${String(i % 12 + 1).padStart(2, "0")}-01`;
      const value = row.value ?? row.t2m_c;
      if (row.date !== expectedDate || value === undefined || !Number.isFinite(value)) {
        throw new Error(`Mes faltante o inválido para ${id}: ${expectedDate}`);
      }
      return value;
    });
    const fit = seasonalTrend(values);
    const series = Array.from({ length: expectedMonths / 12 }, (_, i) => ({
      year: selection.start + i,
      value: values.slice(i * 12, i * 12 + 12).reduce((sum, value) => sum + value, 0) / 12,
    }));
    const centerYear = (selection.start + selection.end) / 2;
    const centerValue = series.reduce((sum, row) => sum + row.value, 0) / series.length;
    const intercept = centerValue - fit.slopePerDecade / 10 * centerYear;
    return {
      variableId: id as VariableId,
      unit: entry.unit,
      source: entry.source,
      series,
      trend: series.map((row) => ({ year: row.year, value: intercept + fit.slopePerDecade / 10 * row.year })),
      statistics: {
        slopePerDecade: fit.slopePerDecade,
        confidenceInterval: fit.confidenceInterval,
        confidenceLevel: 0.95,
        intercept,
        sampleSize: fit.sampleSize,
      },
      status: "ready" as const,
    };
  });
  return {
    id: `real-v2:${selectionKey(selection)}`,
    selection: structuredClone(selection),
    region: getRegion(selection.regionId),
    results,
    mode: "real",
    method: {
      id: "monthly-seasonal-hac12-v2",
      name: "Regresión mensual con estacionalidad y HAC(12)",
      description: `Pendiente e IC95% recalculados con ${(selection.end - selection.start + 1) * 12} valores mensuales del periodo ${selection.start}–${selection.end}: tiempo lineal, 11 indicadores de mes y errores HAC/Newey-West de 12 rezagos. La gráfica resume los meses en ${selection.end - selection.start + 1} promedios anuales; su recta es una guía visual centrada en esos promedios. Sin ajuste por pruebas múltiples ni ENSO/PDO.`,
    },
    provenance: {
      source: "NASA POWER (T2M) y NASA Giovanni (GPCP, MERRA-2 RX5Day)",
      updatedAt: "2026-11-14",
      resolution: "Caja 101–99° O, 25–27° N. POWER y Giovanni usan mallas y agregaciones distintas; no representa todo el noreste de México.",
      limitations: [
        "Resultados exploratorios para una sola caja; no son tendencias de una región administrativa.",
        "La gráfica anual resume datos mensuales; las pendientes e intervalos proceden del modelo mensual.",
        "RX5Day de Giovanni es un índice mensual, no el índice anual derivado de POWER.",
        "Sin corrección por múltiples pruebas, ENSO/PDO ni atribución causal.",
      ],
    },
  };
}
