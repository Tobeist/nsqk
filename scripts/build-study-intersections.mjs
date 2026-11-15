// Recalculate Natural Earth state intersections for the configured study boxes.
import { readFile, writeFile } from "node:fs/promises";
import clipping from "polygon-clipping";

const states = JSON.parse(await readFile("public/assets/region-states.json", "utf8"));
const config = JSON.parse(await readFile("config/study-boxes.json", "utf8"));
const intersections = Object.fromEntries(config.boxes.map(({ id, bbox }) => {
  const [west, south, east, north] = bbox;
  const box = [[
    [west, south], [east, south], [east, north], [west, north], [west, south],
  ]];
  return [id, states.features.flatMap((feature) => {
    if (!feature.properties.id) return [];
    const coordinates = clipping.intersection(feature.geometry.coordinates, box);
    return coordinates.length ? [{ id: feature.properties.id, coordinates }] : [];
  })];
}));

await writeFile("public/assets/study-intersections.json", JSON.stringify(intersections) + "\n");
for (const [id, features] of Object.entries(intersections))
  console.log(`${id}: ${features.map((feature) => feature.id).join(", ")}`);
