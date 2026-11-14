import temperature from "../data/results/power_t2m_region_1992_2024.json";
import temperatureMin from "../data/results/power_t2m_min_region_1992_2024.json";
import temperatureMax from "../data/results/power_t2m_max_region_1992_2024.json";
import precipitation from "../data/results/giovanni_gpcp_1992_2024.json";
import precipitationPower from "../data/results/power_prectotcorr_region_1992_2024.json";
import rain5 from "../data/results/giovanni_rx5day_1992_2024.json";
import rain5PowerAnnual from "../data/results/power_rx5day_annual_region_1992_2024.json";
import { getRegion, type VariableId } from "./catalog";
import { selectionKey, type Analysis, type Selection, type VariableResult } from "./contracts";
import { seasonalTrend } from "./seasonal-trend";
import { annualTrend } from "./annual-trend";

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
  n_months: number;
  monthly: Array<{ date: string; value?: number; t2m_c?: number }>;
};
type MonthlyVariableId =
  | "temperature" | "temperature-min" | "temperature-max"
  | "precipitation" | "precipitation-power" | "rain5";
type MonthlySource = {
  data: MonthlyResult;
  unit: string;
  source: string;
  limitations: string[];
};

const monthlySources: Record<MonthlyVariableId, MonthlySource> = {
  temperature: {
    data: temperature, unit: "°C", source: "NASA POWER T2M · MERRA-2",
    limitations: ["POWER T2M no se ha cotejado directamente con Giovanni T2M."],
  },
  "temperature-min": {
    data: temperatureMin, unit: "°C", source: "NASA POWER T2M_MIN · MERRA-2",
    limitations: ["T2M_MIN mensual no cuenta noches cálidas ni tropicales."],
  },
  "temperature-max": {
    data: temperatureMax, unit: "°C", source: "NASA POWER T2M_MAX · MERRA-2",
    limitations: ["T2M_MAX mensual no cuenta días ni duración de olas de calor."],
  },
  precipitation: {
    data: precipitation, unit: "mm/día", source: "NASA Giovanni · GPCP satélite + pluviómetros",
    limitations: ["GPCP combina satélite y pluviómetros; no equivale a PRECTOTCORR de POWER."],
  },
  "precipitation-power": {
    data: precipitationPower, unit: "mm/día", source: "NASA POWER PRECTOTCORR · MERRA-2",
    limitations: ["PRECTOTCORR es una tasa media mensual corregida; no equivale a GPCP ni a un acumulado mensual."],
  },
  rain5: {
    data: rain5, unit: "mm", source: "NASA Giovanni · MERRA-2 M2SMNXEDI RX5Day mensual",
    limitations: ["RX5Day de Giovanni es un índice mensual; no equivale al máximo anual derivado de POWER."],
  },
};

function isMonthlyVariable(id: VariableId): id is MonthlyVariableId {
  return Object.prototype.hasOwnProperty.call(monthlySources, id);
}

function createMonthlyResult(id: MonthlyVariableId, selection: Selection): VariableResult {
  const entry = monthlySources[id];
  const data = entry.data;
  if (data.n_months !== 396 || data.monthly.length !== 396) {
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
  const annual = rain5PowerAnnual.annual.filter((row) =>
    row.year >= selection.start && row.year <= selection.end,
  );
  if (rain5PowerAnnual.annual.length !== 33 || annual.length !== years ||
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

export function createRealAnalysis(selection: Selection): Analysis {
  if (selection.regionId !== "mx-northeast" ||
      !Number.isInteger(selection.start) || !Number.isInteger(selection.end) ||
      selection.start < firstDataYear || selection.end > lastDataYear ||
      selection.end - selection.start + 1 < minimumYearsForVariables(selection.variables) ||
      selection.variables.length < 1 || selection.variables.length > 3 ||
      new Set(selection.variables).size !== selection.variables.length ||
      selection.variables.some((id) => !isMonthlyVariable(id) && id !== annualIndexId)) {
    throw new Error("Selecciona la caja disponible, hasta tres variables integradas y un periodo válido: mínimo diez años, o veinte si incluye RX5day anual de POWER.");
  }
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
      resolution: "Caja 101–99° O, 25–27° N. POWER y Giovanni usan mallas y agregaciones distintas; no representa todo el noreste de México.",
      limitations: [
        "Resultados exploratorios para una sola caja; no son tendencias de una región administrativa.",
        "Sin corrección por múltiples pruebas, ENSO/PDO ni atribución causal.",
        "Las variables proceden de productos y escalas temporales distintos; no se comparan sus pendientes numéricamente de forma directa.",
      ],
    },
  };
}
