import temperature from "../data/results/power_t2m_region_1992_2024.json";
import temperatureMin from "../data/results/power_t2m_min_region_1992_2024.json";
import temperatureMax from "../data/results/power_t2m_max_region_1992_2024.json";
import precipitation from "../data/results/giovanni_gpcp_1992_2024.json";
import precipitationPower from "../data/results/power_prectotcorr_region_1992_2024.json";
import rain5 from "../data/results/giovanni_rx5day_1992_2024.json";
import rain5PowerAnnual from "../data/results/power_rx5day_annual_region_1992_2024.json";
import chihuahuaTemperature from "../data/results/mx-chihuahua-interior/power_t2m_region_1992_2024.json";
import chihuahuaTemperatureMin from "../data/results/mx-chihuahua-interior/power_t2m_min_region_1992_2024.json";
import chihuahuaTemperatureMax from "../data/results/mx-chihuahua-interior/power_t2m_max_region_1992_2024.json";
import chihuahuaPrecipitation from "../data/results/mx-chihuahua-interior/giovanni_gpcp_1992_2024.json";
import chihuahuaPrecipitationPower from "../data/results/mx-chihuahua-interior/power_prectotcorr_region_1992_2024.json";
import chihuahuaRain5 from "../data/results/mx-chihuahua-interior/giovanni_rx5day_1992_2024.json";
import chihuahuaRain5PowerAnnual from "../data/results/mx-chihuahua-interior/power_rx5day_annual_region_1992_2024.json";
import southTemperature from "../data/results/mx-south-humid/power_t2m_region_1992_2024.json";
import southTemperatureMin from "../data/results/mx-south-humid/power_t2m_min_region_1992_2024.json";
import southTemperatureMax from "../data/results/mx-south-humid/power_t2m_max_region_1992_2024.json";
import southPrecipitation from "../data/results/mx-south-humid/giovanni_gpcp_1992_2024.json";
import southPrecipitationPower from "../data/results/mx-south-humid/power_prectotcorr_region_1992_2024.json";
import southRain5 from "../data/results/mx-south-humid/giovanni_rx5day_1992_2024.json";
import southRain5PowerAnnual from "../data/results/mx-south-humid/power_rx5day_annual_region_1992_2024.json";
import { getRegion, regions, type VariableId } from "./catalog";
import { selectionKey, type Analysis, type Selection, type VariableResult } from "./contracts";
import { seasonalTrend } from "./seasonal-trend";
import { annualTrend } from "./annual-trend";
import auditedFullPeriod from "../analysis/app/1992-2024.json";
import type { TrendBundle } from "./trend-evidence";

export const firstDataYear = 1992;
export const lastDataYear = 2024;
export const minimumAnalysisYears = 10;
export const minimumAnnualIndexYears = 20;
export const annualIndexId = "rain5-power-annual" as const;

export function minimumYearsForVariables(variables: VariableId[]) {
  return variables.includes(annualIndexId) ? minimumAnnualIndexYears : minimumAnalysisYears;
}

export const realDefaultSelection: Selection = {
  regionId: "mx-northeast",
  variables: ["temperature", "precipitation", "rain5"],
  start: 1992,
  end: 2024,
};

type MonthlyResult = {
  region_id?: string;
  n_months: number;
  monthly: Array<{ date: string; value?: number; t2m_c?: number }>;
};
type MonthlyVariableId =
  | "temperature" | "temperature-min" | "temperature-max"
  | "precipitation" | "precipitation-power" | "rain5";
type MonthlySource = {
  unit: string;
  source: string;
  limitations: string[];
};

const monthlySources: Record<MonthlyVariableId, MonthlySource> = {
  temperature: {
    unit: "°C", source: "NASA POWER T2M · MERRA-2",
    limitations: ["POWER T2M no se ha cotejado directamente con Giovanni T2M."],
  },
  "temperature-min": {
    unit: "°C", source: "NASA POWER T2M_MIN · MERRA-2",
    limitations: ["T2M_MIN mensual no cuenta noches cálidas ni tropicales."],
  },
  "temperature-max": {
    unit: "°C", source: "NASA POWER T2M_MAX · MERRA-2",
    limitations: ["T2M_MAX mensual no cuenta días ni duración de olas de calor."],
  },
  precipitation: {
    unit: "mm/día", source: "NASA Giovanni · GPCP satélite + pluviómetros",
    limitations: ["GPCP combina satélite y pluviómetros; no equivale a PRECTOTCORR de POWER."],
  },
  "precipitation-power": {
    unit: "mm/día", source: "NASA POWER PRECTOTCORR · MERRA-2",
    limitations: ["PRECTOTCORR es una tasa media mensual corregida; no equivale a GPCP ni a un acumulado mensual."],
  },
  rain5: {
    unit: "mm", source: "NASA Giovanni · MERRA-2 M2SMNXEDI RX5Day mensual",
    limitations: ["RX5Day de Giovanni es un índice mensual; no equivale al máximo anual derivado de POWER."],
  },
};

type AnnualResult = { region_id?: string; annual: Array<{ year: number; rx5day_mm: number }> };
type RegionData = { monthly: Record<MonthlyVariableId, MonthlyResult>; annual: AnnualResult };
const regionData: Record<string, RegionData> = {
  "mx-northeast": {
    monthly: {
      temperature, "temperature-min": temperatureMin, "temperature-max": temperatureMax,
      precipitation, "precipitation-power": precipitationPower, rain5,
    },
    annual: rain5PowerAnnual,
  },
  "mx-chihuahua-interior": {
    monthly: {
      temperature: chihuahuaTemperature, "temperature-min": chihuahuaTemperatureMin,
      "temperature-max": chihuahuaTemperatureMax, precipitation: chihuahuaPrecipitation,
      "precipitation-power": chihuahuaPrecipitationPower, rain5: chihuahuaRain5,
    },
    annual: chihuahuaRain5PowerAnnual,
  },
  "mx-south-humid": {
    monthly: {
      temperature: southTemperature, "temperature-min": southTemperatureMin,
      "temperature-max": southTemperatureMax, precipitation: southPrecipitation,
      "precipitation-power": southPrecipitationPower, rain5: southRain5,
    },
    annual: southRain5PowerAnnual,
  },
};

function isMonthlyVariable(id: VariableId): id is MonthlyVariableId {
  return Object.prototype.hasOwnProperty.call(monthlySources, id);
}

function createMonthlyResult(id: MonthlyVariableId, selection: Selection): VariableResult {
  const entry = monthlySources[id];
  const data = regionData[selection.regionId].monthly[id];
  if ((data.region_id ?? "mx-northeast") !== selection.regionId ||
      data.n_months !== 396 || data.monthly.length !== 396) {
    throw new Error(`Resultado incompleto para ${id}`);
  }
  const monthly = data.monthly.filter((row) => {
    const year = Number(row.date.slice(0, 4));
    return year >= selection.start && year <= selection.end;
  });
  const years = selection.end - selection.start + 1;
  const expectedMonths = years * 12;
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
  const series = Array.from({ length: years }, (_, i) => ({
    year: selection.start + i,
    value: values.slice(i * 12, i * 12 + 12).reduce((sum, value) => sum + value, 0) / 12,
  }));
  const centerYear = (selection.start + selection.end) / 2;
  const centerValue = series.reduce((sum, row) => sum + row.value, 0) / series.length;
  const intercept = centerValue - fit.slopePerDecade / 10 * centerYear;
  return {
    variableId: id,
    unit: entry.unit,
    source: entry.source,
    annualLabel: id === "rain5" ? "media anual del índice mensual" : "media anual de valores mensuales",
    sampleUnit: "meses",
    method: {
      id: "monthly-seasonal-hac12-v2",
      name: "Regresión mensual con estacionalidad y HAC(12)",
      description: `Pendiente e IC95% recalculados con ${expectedMonths} valores mensuales de ${selection.start}–${selection.end}: tiempo lineal, 11 indicadores de mes y errores HAC/Newey-West de 12 rezagos. La gráfica resume los meses en ${years} medias anuales; la recta conserva la pendiente mensual y se centra en esas medias.`,
    },
    limitations: entry.limitations,
    series,
    trend: series.map((row) => ({ year: row.year, value: intercept + fit.slopePerDecade / 10 * row.year })),
    statistics: {
      slopePerDecade: fit.slopePerDecade,
      confidenceInterval: fit.confidenceInterval,
      confidenceLevel: 0.95,
      intercept,
      sampleSize: fit.sampleSize,
    },
    status: "ready",
  };
}

function createAnnualResult(selection: Selection): VariableResult {
  const years = selection.end - selection.start + 1;
  if (years < minimumAnnualIndexYears) {
    throw new Error("RX5day anual de POWER requiere al menos veinte años completos.");
  }
  const data = regionData[selection.regionId].annual;
  const annual = data.annual.filter((row) =>
    row.year >= selection.start && row.year <= selection.end,
  );
  if ((data.region_id ?? "mx-northeast") !== selection.regionId ||
      data.annual.length !== 33 || annual.length !== years ||
      annual.some((row, i) => row.year !== selection.start + i || !Number.isFinite(row.rx5day_mm))) {
    throw new Error("Serie anual de POWER incompleta o inválida.");
  }
  const series = annual.map((row) => ({ year: row.year, value: row.rx5day_mm }));
  const fit = annualTrend(series.map((row) => row.value));
  const centerYear = (selection.start + selection.end) / 2;
  const centerValue = series.reduce((sum, row) => sum + row.value, 0) / years;
  const intercept = centerValue - fit.slopePerDecade / 10 * centerYear;
  return {
    variableId: annualIndexId,
    unit: "mm",
    source: "Índice derivado de NASA POWER PRECTOTCORR diario · MERRA-2",
    annualLabel: "máximo anual de cinco días",
    sampleUnit: "años",
    method: {
      id: "annual-ols-hac3-v1",
      name: "Regresión anual con HAC(3)",
      description: `Pendiente e IC95% recalculados con ${years} máximos anuales de ${selection.start}–${selection.end}: tiempo lineal e incertidumbre HAC/Newey-West de 3 rezagos anuales. Cada valor es la media regional ponderada de los máximos de cinco días por celda, calculados desde PRECTOTCORR diario. Este índice derivado no es el RX5Day mensual de Giovanni.`,
    },
    limitations: [
      "Índice calculado por el equipo a partir de POWER diario; no es el producto RX5Day de Giovanni.",
      "La elección de tres rezagos anuales aún requiere análisis de sensibilidad.",
    ],
    series,
    trend: series.map((row) => ({ year: row.year, value: intercept + fit.slopePerDecade / 10 * row.year })),
    statistics: {
      slopePerDecade: fit.slopePerDecade,
      confidenceInterval: fit.confidenceInterval,
      confidenceLevel: 0.95,
      intercept,
      sampleSize: fit.sampleSize,
    },
    status: "ready",
  };
}

export function validateSelection(selection: Selection) {
  if (!regions.some((region) => region.id === selection.regionId) || !regionData[selection.regionId] ||
      !Number.isInteger(selection.start) || !Number.isInteger(selection.end) ||
      selection.start < firstDataYear || selection.end > lastDataYear ||
      selection.end - selection.start + 1 < minimumYearsForVariables(selection.variables) ||
      selection.variables.length < 1 || selection.variables.length > 3 ||
      new Set(selection.variables).size !== selection.variables.length ||
      selection.variables.some((id) => !isMonthlyVariable(id) && id !== annualIndexId)) {
    throw new Error("Selecciona una de las tres cajas, hasta tres variables integradas y un periodo válido: mínimo diez años, o veinte si incluye RX5day anual de POWER.");
  }
}

// Reference calculation retained for regression/parity checks, never used as app inference.
export function createReferenceAnalysis(selection: Selection): Analysis {
  validateSelection(selection);
  const results = selection.variables.map((id) =>
    id === annualIndexId ? createAnnualResult(selection) : createMonthlyResult(id as MonthlyVariableId, selection),
  );
  return {
    id: `real-v3:${selectionKey(selection)}`,
    selection: structuredClone(selection),
    region: getRegion(selection.regionId),
    results,
    mode: "real",
    provenance: {
      source: "NASA POWER (T2M, PRECTOTCORR, índice derivado) y NASA Giovanni (GPCP, RX5Day)",
      updatedAt: "2026-11-14",
      resolution: `Caja [${getRegion(selection.regionId).bbox.join(", ")}]. POWER y Giovanni usan mallas y agregaciones distintas; no representa estados completos.`,
      limitations: [
        "Resultados exploratorios para una caja de estudio; no son tendencias de una región administrativa.",
        "Sin corrección por múltiples pruebas, ENSO/PDO ni atribución causal.",
        "Las variables proceden de productos y escalas temporales distintos; no se comparan sus pendientes numéricamente de forma directa.",
      ],
    },
  };
}

export const defaultTrendBundle = auditedFullPeriod as unknown as TrendBundle;

export function createRealAnalysis(selection: Selection, bundle: TrendBundle = defaultTrendBundle): Analysis {
  validateSelection(selection);
  if (bundle.start !== selection.start || bundle.end !== selection.end ||
      bundle.version !== "app-seasonal-enso-sieve-v1" || bundle.replicates !== 4999) {
    throw new Error("Falta calcular la auditoría para este periodo. Vuelve a analizar la selección.");
  }
  const analysis = createReferenceAnalysis(selection);
  analysis.id = `${bundle.version}:${bundle.fingerprint}:${selectionKey(selection)}`;
  analysis.provenance.audit = {
    version: bundle.version, fingerprint: bundle.fingerprint,
    replicates: bundle.replicates, seed: bundle.seed,
  };
  analysis.provenance.limitations = [
    "Resultados para la caja y el periodo elegidos; no representan estados completos ni atribuyen causas.",
    "Calendario mensual y Niño 3.4 controlan variación estacional y ENSO; no todos los factores naturales. El índice anual no ajusta ENSO.",
    "IC95% individuales por bootstrap-t AR; la certeza usa p de Holm sobre 18 series mensuales o tres anuales. Elegir periodos después de ver los resultados introduce sesgo adicional.",
    "Diagnósticos de escalones exploratorios; sus fechas no establecen un cambio físico ni de procesamiento. Los productos y sus agregaciones no son intercambiables.",
  ];
  analysis.results = analysis.results.map((result) => {
    const evidence = bundle.results[selection.regionId]?.[result.variableId];
    if (!evidence) throw new Error(`No hay auditoría de ${result.variableId} para esta caja y periodo.`);
    result.evidence = evidence;
    const annual = result.sampleUnit === "años";
    result.method = {
      id: `${bundle.version}:${annual ? "annual" : "monthly"}`,
      name: annual ? "Regresión anual · bootstrap-t AR · Holm(3)" : "Regresión mensual + ENSO · bootstrap-t AR · Holm(18)",
      description: `${selection.start}–${selection.end}: ${annual ? "máximos anuales, tiempo lineal y HAC(2), sin ajuste ENSO" : "tiempo lineal, once indicadores de mes, Niño 3.4 contemporáneo y HAC(12)"}. Incertidumbre con ${bundle.replicates.toLocaleString("es-MX")} réplicas de bootstrap-t AR; IC95% individual y p ajustado por Holm. ${annual ? "La recta conserva la pendiente anual." : "La gráfica resume los datos en medias anuales; la recta es una guía centrada en ellas con la pendiente mensual ajustada, no una predicción."}`,
    };
    result.limitations = [...result.limitations.filter((s) => !s.includes("tres rezagos")), ...evidence.reasons];
    if (evidence.status === "not-evaluable") {
      return { ...result, statistics: null, trend: [], status: "not-evaluable" as const };
    }
    const slope = evidence.slopePerDecade;
    const ci = evidence.confidenceInterval;
    if (slope === undefined || !Number.isFinite(slope) || !ci || ci.some((v) => !Number.isFinite(v)) ||
        evidence.pAdjusted === undefined || evidence.sampleSize !== result.statistics?.sampleSize) {
      throw new Error("Resultado de auditoría incompleto o incompatible con la serie.");
    }
    const centerYear = (selection.start + selection.end) / 2;
    const mean = result.series.reduce((sum, row) => sum + row.value!, 0) / result.series.length;
    const intercept = mean - slope / 10 * centerYear;
    result.statistics = {
      slopePerDecade: slope, confidenceInterval: ci, confidenceLevel: .95,
      intercept, sampleSize: evidence.sampleSize!, evidence,
    };
    result.trend = result.series.map(({ year }) => ({ year, value: intercept + slope / 10 * year }));
    return result;
  });
  return analysis;
}
