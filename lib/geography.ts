import data from "../public/assets/region-states.json";
import studyIntersections from "../public/assets/study-intersections.json";
import type { Feature, Geometry, MultiPolygon } from "geojson";
export interface StateProperties {
  id: string;
  name: string;
  country: string;
  intersects: boolean;
  label: [number, number];
}
export type StateFeature = Feature<Geometry, StateProperties> & {
  intersection: MultiPolygon;
};
export const stateFeatures = data.features as unknown as StateFeature[];
export const intersectedStates = stateFeatures.filter(
  (f) => f.properties.intersects,
);
export const stateNames = intersectedStates
  .map((f) => f.properties.name)
  .sort((a, b) => a.localeCompare(b, "es"));
const regionIntersections = studyIntersections as Record<string, Array<{
  id: string;
  coordinates: MultiPolygon["coordinates"];
}>>;
const statesById = new Map(stateFeatures.map((feature) => [feature.properties.id, feature]));
export function getIntersectedStates(regionId: string): StateFeature[] {
  return (regionIntersections[regionId] ?? []).map(({ id, coordinates }) => ({
    ...statesById.get(id)!,
    intersection: { type: "MultiPolygon", coordinates },
  }));
}
export function getStateNames(regionId: string): string[] {
  return getIntersectedStates(regionId)
    .map((feature) => feature.properties.name)
    .sort((a, b) => a.localeCompare(b, "es"));
}
const studyStateIds = new Set(Object.values(regionIntersections).flat().map(({ id }) => id));
export const studyStateFeatures = stateFeatures.filter((feature) => studyStateIds.has(feature.properties.id));
export const geographySource = "Natural Earth · límites estatales 1:10m";
