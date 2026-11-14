import data from "../public/assets/region-states.json";
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
export const geographySource = "Natural Earth · límites estatales 1:10m";
