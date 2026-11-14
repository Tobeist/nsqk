import { getRegion, getVariable, type VariableId } from "./catalog";
import {
  selectionKey,
  type Analysis,
  type Observation,
  type Selection,
  type Statistics,
} from "./contracts";
export const defaultSelection: Selection = {
  regionId: "mx-northeast",
  variables: ["temperature"],
  start: 1984,
  end: 2024,
};
// Synthetic annual fixtures, unrelated to NASA observations. Never use as scientific evidence.
const noise = [
  0.52, -0.71, 0.28, -0.19, 0.87, -0.38, -0.92, 0.13, 0.63, -0.31, 0.21, -0.64,
  0.91, 0.37, -0.47, 0.73, -0.16, -0.84, 0.42, -0.27, 0.68,
];
function annualSeries(variable: VariableId, regionId: string): Observation[] {
  const r = [
    "mx-northeast",
    "mx-northwest",
    "us-texas",
    "us-california",
  ].indexOf(regionId);
  return Array.from({ length: 41 }, (_, i) => {
    const n = noise[(i + r * 3) % noise.length] + Math.sin(i * 1.73) * 0.17;
    const value =
      variable === "temperature"
        ? 21.3 - r * 1.25 + i * (r === 1 ? 0.037 : 0.041) + n * 0.36
        : variable === "precipitation"
          ? 2.1 - r * 0.22 + i * 0.001 + n * 0.48
          : 0.26 - r * 0.018 - i * 0.0009 + n * 0.009;
    return {
      year: 1984 + i,
      value:
        (variable === "precipitation" && i === 17) ||
        (variable === "surface-moisture" && i === 9)
          ? null
          : Number(value.toFixed(4)),
    };
  });
}
// OLS is used ONLY to make synthetic UI fixtures internally consistent.
// Annual independent-error t intervals are illustrative, not a validated climate method.
export function fixtureStatistics(series: Observation[]): Statistics | null {
  const points = series.filter(
    (d): d is Observation & { value: number } => d.value !== null,
  );
  if (points.length < 3) return null;
  const n = points.length,
    xbar = points.reduce((a, d) => a + d.year, 0) / n,
    ybar = points.reduce((a, d) => a + d.value, 0) / n;
  const sxx = points.reduce((a, d) => a + (d.year - xbar) ** 2, 0);
  const slope =
    points.reduce((a, d) => a + (d.year - xbar) * (d.value - ybar), 0) / sxx;
  const intercept = ybar - slope * xbar;
  const sse = points.reduce(
    (a, d) => a + (d.value - (intercept + slope * d.year)) ** 2,
    0,
  );
  const sst = points.reduce((a, d) => a + (d.value - ybar) ** 2, 0);
  // Two-sided t(.975, df), Cornish-Fisher approximation, sufficient for fixture n >= 11.
  const df = n - 2,
    z = 1.95996398454;
  const t =
    z +
    (z ** 3 + z) / (4 * df) +
    (5 * z ** 5 + 16 * z ** 3 + 3 * z) / (96 * df ** 2) +
    (3 * z ** 7 + 19 * z ** 5 + 17 * z ** 3 - 15 * z) / (384 * df ** 3);
  const margin = t * Math.sqrt(sse / (n - 2) / sxx) * 10;
  return {
    slopePerDecade: slope * 10,
    confidenceInterval: [slope * 10 - margin, slope * 10 + margin],
    confidenceLevel: 0.95,
    intercept,
    rSquared: sst ? 1 - sse / sst : 1,
    sampleSize: n,
  };
}
export function createDemoAnalysis(selection: Selection): Analysis {
  if (
    !getRegion(selection.regionId) ||
    selection.start < 1984 ||
    selection.end > 2024 ||
    selection.end - selection.start < 10 ||
    !selection.variables.length ||
    selection.variables.length > 3 ||
    selection.variables.some((id) => !getVariable(id)?.available)
  )
    throw new Error(
      "Selecciona de 1 a 3 variables y un periodo de al menos 10 años entre 1984 y 2024.",
    );
  const results = selection.variables.map((variableId) => {
    const noData =
      variableId === "surface-moisture" &&
      selection.regionId === "us-california";
    const series = noData
      ? []
      : annualSeries(variableId, selection.regionId).filter(
          (d) => d.year >= selection.start && d.year <= selection.end,
        );
    const statistics = fixtureStatistics(series);
    return {
      variableId,
      unit: getVariable(variableId).unit,
      series,
      statistics,
      trend: statistics
        ? series.map((d) => ({
            year: d.year,
            value:
              statistics.intercept + (statistics.slopePerDecade / 10) * d.year,
          }))
        : [],
      status: noData ? ("no-data" as const) : ("ready" as const),
    };
  });
  return {
    id: `demo-v1:${selectionKey(selection)}`,
    selection: structuredClone(selection),
    region: getRegion(selection.regionId),
    results,
    mode: "demo",
    method: {
      id: "fixture-ols-v1",
      name: "Regresión lineal · fixture v1",
      description:
        "Serie anual sintética determinista. Ajuste OLS e intervalo t bilateral del 95 % con errores independientes. Es un ejemplo de interfaz; no un método climático validado. No se aplicaron controles de estacionalidad ni ENSO/PDO.",
    },
    provenance: {
      source: "Fixtures sintéticas locales · Trend Detectives",
      updatedAt: "2026-11-14",
      resolution:
        "Sin resolución observacional. Cajas de demostración de 2° × 2°; no son fronteras administrativas.",
      limitations: [
        "No son observaciones NASA ni hallazgos ambientales.",
        "El intervalo sólo ilustra incertidumbre de regresión bajo independencia; no incluye errores de producto ni autocorrelación.",
        "No permite atribuir causas, aislar ENSO/PDO ni hacer pronósticos.",
        "Las regiones habilitadas no representan cobertura completa de México o Estados Unidos.",
      ],
    },
  };
}
export function evidenceLabel(s: Statistics) {
  const [lo, hi] = s.confidenceInterval;
  return lo > 0
    ? "Evidencia de aumento"
    : hi < 0
      ? "Evidencia de disminución"
      : "Evidencia inconclusa";
}
export const formatNumber = (value: number, digits = 2) =>
  value.toLocaleString("es-MX", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
export const signed = (value: number, digits = 2) =>
  `${value > 0 ? "+" : ""}${formatNumber(value, digits)}`;
