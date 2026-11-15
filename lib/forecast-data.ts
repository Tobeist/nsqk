import artifact from "../analysis/forecast/app-forecast.json";
import type { VariableId } from "./catalog";

export type ForecastModelId = "climatology" | "seasonal-naive" | "trend" | "neural";
export interface ForecastScore {
  id: ForecastModelId;
  label: string;
  validationMae: number;
  testMae: number;
  testRmse: number;
  testBias: number;
  coverage80: number;
  skillVsClimatology: number;
  testByYear: { year: number; mae: number }[];
}
export interface ForecastPoint {
  date: string;
  value: number;
  lower: number;
  upper: number;
  neuralValue: number;
  neuralLower: number;
  neuralUpper: number;
  climatologyValue: number;
  climatologyLower: number;
  climatologyUpper: number;
}
export interface BacktestPoint extends ForecastPoint {
  actual: number;
  trainedThrough: string;
}
export interface ForecastResult {
  unit: string;
  source: string;
  selectedModel: ForecastModelId;
  models: ForecastScore[];
  projection: ForecastPoint[];
  history: { date: string; value: number }[];
  holdout: BacktestPoint[];
  neuralBeatsSelectedOnTest: boolean;
}
export interface ForecastBundle {
  version: string;
  sourceStart: string;
  sourceEnd: string;
  projectionStart: string;
  projectionEnd: string;
  fingerprint: string;
  results: Record<string, Partial<Record<VariableId, ForecastResult>>>;
}
export const forecastBundle = artifact as unknown as ForecastBundle;
export const forecastModelLabel: Record<ForecastModelId, string> = {
  climatology: "Patrón estacional", "seasonal-naive": "Repetir último año",
  trend: "Estación + tendencia", neural: "Red neuronal",
};
export function getForecast(regionId: string, variableId: VariableId, start: number, end: number) {
  if (start !== 1992 || end !== 2024) return null;
  return forecastBundle.results[regionId]?.[variableId] ?? null;
}
export function forecastValues(point: ForecastPoint, model: ForecastModelId, selected: ForecastModelId) {
  if (model === selected) return { value: point.value, lower: point.lower, upper: point.upper };
  if (model === "neural") return { value: point.neuralValue, lower: point.neuralLower, upper: point.neuralUpper };
  if (model === "climatology") return { value: point.climatologyValue, lower: point.climatologyLower, upper: point.climatologyUpper };
  throw new Error("Este modelo no tiene una trayectoria exportada.");
}
export function forecastCsv(regionId: string, variableId: VariableId, mode: "projection" | "backtest", model: ForecastModelId) {
  const result = getForecast(regionId, variableId, 1992, 2024);
  if (!result) throw new Error("No hay predicción validada para esta selección.");
  const rows = mode === "projection" ? result.projection : result.holdout;
  const quote = (value: unknown) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  return "\uFEFF" + [
    ["region_id", "variable_id", "record_type", "date", "observed", "prediction", "lower_orientative_80", "upper_orientative_80", "unit", "model", "trained_through", "validation_period", "test_period", "fingerprint"],
    ...rows.map((point) => {
      const fit = forecastValues(point, model, result.selectedModel);
      return [regionId, variableId, mode === "projection" ? "projection_from_2024" : "retrospective_test", point.date,
        "actual" in point ? point.actual : "", fit.value, fit.lower, fit.upper, result.unit, model,
        "trainedThrough" in point ? point.trainedThrough : forecastBundle.sourceEnd, "2016-2020", "2021-2024", forecastBundle.fingerprint];
    }),
  ].map((row) => row.map(quote).join(",")).join("\r\n");
}
