// Natural Earth admin-1 boundaries, public domain. No climate observations are generated here.
import { readFile, writeFile } from "node:fs/promises";
import clipping from "polygon-clipping";
const input = process.argv[2];
if (!input)
  throw new Error(
    "Usage: node scripts/build-region-map.mjs /path/to/ne_10m_admin_1_states_provinces.geojson",
  );
const world = JSON.parse(await readFile(input, "utf8"));
const bbox = [-101, 25, -99, 27],
  box = [
    [
      [bbox[0], bbox[1]],
      [bbox[2], bbox[1]],
      [bbox[2], bbox[3]],
      [bbox[0], bbox[3]],
      [bbox[0], bbox[1]],
    ],
  ];
const nearby = world.features.filter(
  (f) =>
    f.properties.adm0_a3 === "MEX" ||
    (f.bbox &&
      f.bbox[0] <= bbox[2] &&
      f.bbox[2] >= bbox[0] &&
      f.bbox[1] <= bbox[3] &&
      f.bbox[3] >= bbox[1]),
);
const features = nearby.map((f) => {
  const intersection = clipping.intersection(f.geometry.coordinates, box);
  const coordinates = f.geometry.coordinates;
  const name =
    f.properties.iso_3166_2 === "MX-COA"
      ? "Coahuila"
      : f.properties.iso_3166_2 === "MX-DIF"
        ? "Ciudad de México"
        : f.properties.name_es || f.properties.name;
  return {
    type: "Feature",
    properties: {
      id: f.properties.iso_3166_2,
      name,
      country: f.properties.adm0_a3 === "MEX" ? "México" : "Estados Unidos",
      intersects: intersection.length > 0,
      label: [f.properties.longitude, f.properties.latitude],
    },
    geometry: { type: f.geometry.type, coordinates },
    intersection: { type: "MultiPolygon", coordinates: intersection },
  };
});
const result = {
  type: "FeatureCollection",
  source: "Natural Earth admin-1, 1:10m · public domain",
  bbox,
  features,
};
await writeFile("public/assets/region-states.json", JSON.stringify(result));
console.log(
  "Intersects:",
  features
    .filter((f) => f.properties.intersects)
    .map((f) => f.properties.name)
    .join(", "),
);
