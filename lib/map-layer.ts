import { scaleDiverging, interpolateRgbBasis } from "d3";
import { regions, type VariableId } from "./catalog";
import type { Analysis, Statistics } from "./contracts";
export interface MapRegionValue {
  regionId: string;
  statistics: Statistics | null;
  state: "analyzed" | "no-data" | "not-analyzed";
  color: string;
}
export const mapLimits: Partial<Record<VariableId, number>> = {
  temperature: 0.6,
  precipitation: 0.4,
  "surface-moisture": 0.02,
};
export function mapColor(value: number, id: VariableId) {
  const limit = mapLimits[id] ?? 1;
  return scaleDiverging<string>()
    .domain([-limit, 0, limit])
    .interpolator(interpolateRgbBasis(["#80bcec", "#a7b5bf", "#f2a58e"]))
    .clamp(true)(value);
}
export function createMapLayer(
  history: Analysis[],
  current: Analysis | null,
  id: VariableId,
): MapRegionValue[] {
  return regions.map((region) => {
    const a = history.findLast(
      (a) =>
        a.region.id === region.id &&
        a.selection.start === current?.selection.start &&
        a.selection.end === current?.selection.end &&
        a.results.some((r) => r.variableId === id),
    );
    const r = a?.results.find((r) => r.variableId === id);
    return {
      regionId: region.id,
      statistics: r?.statistics ?? null,
      state: !r ? "not-analyzed" : r.statistics ? "analyzed" : "no-data",
      color: r?.statistics
        ? mapColor(r.statistics.slopePerDecade, id)
        : "#688395",
    };
  });
}
