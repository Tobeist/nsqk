import { scaleDiverging, interpolateRgb, piecewise } from "d3";
import { regions, type VariableId } from "./catalog";
import type { Analysis, Statistics } from "./contracts";
export interface MapRegionValue {
  regionId: string;
  statistics: Statistics | null;
  state: "analyzed" | "no-data" | "not-analyzed";
  color: string;
  limit: number;
}
const minimumLimits: Partial<Record<VariableId, number>> = {
  temperature: 0.5,
  "temperature-min": 0.5,
  "temperature-max": 0.5,
  precipitation: 0.25,
  "precipitation-power": 0.25,
  rain5: 5,
  "rain5-power-annual": 10,
  "surface-moisture": 0.02,
};
export function getMapLimit(id: VariableId, magnitude = 0) {
  const target = Math.max(minimumLimits[id] ?? 1, Math.abs(magnitude));
  const base = 10 ** Math.floor(Math.log10(target));
  return (
    [1, 2, 5, 10].map((n) => n * base).find((n) => n >= target) ?? 10 * base
  );
}
export function mapColor(
  value: number,
  id: VariableId,
  limit = getMapLimit(id, value),
) {
  return scaleDiverging<string>()
    .domain([-limit, 0, limit])
    .interpolator(piecewise(interpolateRgb, ["#209fff", "#c6d1d5", "#ff8b22"]))
    .clamp(true)(value);
}
export function createMapLayer(
  history: Analysis[],
  current: Analysis | null,
  id: VariableId,
): MapRegionValue[] {
  const matches = history.filter(
    (a) =>
      a.selection.start === current?.selection.start &&
      a.selection.end === current?.selection.end,
  );
  const magnitude = Math.max(
    0,
    ...matches.flatMap((a) =>
      a.results
        .filter((r) => r.variableId === id)
        .map((r) => Math.abs(r.statistics?.slopePerDecade ?? 0)),
    ),
  );
  const limit = getMapLimit(id, magnitude);
  return regions.map((region) => {
    const a = matches.findLast(
      (a) =>
        a.region.id === region.id && a.results.some((r) => r.variableId === id),
    );
    const r = a?.results.find((r) => r.variableId === id);
    return {
      regionId: region.id,
      statistics: r?.statistics ?? null,
      state: !r ? "not-analyzed" : r.statistics ? "analyzed" : "no-data",
      color: r?.statistics
        ? mapColor(r.statistics.slopePerDecade, id, limit)
        : "#688395",
      limit,
    };
  });
}
