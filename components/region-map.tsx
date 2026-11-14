"use client";
import { useId } from "react";
import { geoMercator, geoPath, geoCentroid } from "d3";
import { Navigation } from "lucide-react";
import { stateFeatures, intersectedStates, stateNames } from "@/lib/geography";
import { signed } from "@/lib/format";
import type { MapRegionValue } from "@/lib/map-layer";
import type { Variable } from "@/lib/catalog";
const width = 680,
  height = 430;
const projection = geoMercator().fitExtent(
  [
    [58, 30],
    [width - 58, height - 35],
  ],
  {
    type: "FeatureCollection",
    features: intersectedStates.filter(
      (f) => f.properties.country === "México",
    ),
  },
);
const path = geoPath(projection);
const box = [
  [-101, 25],
  [-99, 25],
  [-99, 27],
  [-101, 27],
  [-101, 25],
] as [number, number][];
const projectedRing = (ring: number[][]) =>
  ring
    .map(
      (point, i) =>
        `${i ? "L" : "M"}${projection(point as [number, number])!.join(",")}`,
    )
    .join(" ") + "Z";
const footprint =
  box
    .map((point, i) => `${i ? "L" : "M"}${projection(point)!.join(",")}`)
    .join(" ") + "Z";
const labelPositions: Record<string, [number, number]> = {
  "MX-COA": [-102.2, 27.5],
  "MX-NLE": [-99.9, 24.65],
  "MX-TAM": [-97.9, 24.3],
  "US-TX": [-99.3, 28.7],
};
export function RegionMap({
  value,
  variable,
}: {
  value?: MapRegionValue;
  variable: Variable;
}) {
  const id = useId().replaceAll(":", "");
  const ready = value?.state === "analyzed",
    color = ready ? value.color : "#8299a8";
  const uncertain =
    !!value?.statistics &&
    value.statistics.confidenceInterval[0] <= 0 &&
    value.statistics.confidenceInterval[1] >= 0;
  const center = projection([-100, 26])!;
  return (
    <div className="regional-map">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-labelledby={`map-title-${id} map-description-${id}`}
      >
        <title
          id={`map-title-${id}`}
        >{`Caja de estudio y límites de ${stateNames.join(", ")}`}</title>
        <desc
          id={`map-description-${id}`}
        >{`Los estados se resaltan como referencia geográfica. Sólo el recuadro de 101 a 99 grados oeste y 25 a 27 grados norte tiene un análisis regional; no hay resultados por estado completo. ${ready ? `Pendiente del recuadro: ${signed(value.statistics!.slopePerDecade, 3)} ${variable.unit} por década.` : "Sin análisis visible."}`}</desc>
        <defs>
          <clipPath id={`map-clip-${id}`}>
            <rect width={width} height={height} />
          </clipPath>
          <pattern
            id={`map-uncertainty-${id}`}
            width="8"
            height="8"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(35)"
          >
            <path d="M0 0V8" stroke="#091b25" strokeWidth="2" opacity=".5" />
          </pattern>
        </defs>
        <g clipPath={`url(#map-clip-${id})`}>
          {Array.from({ length: 9 }, (_, i) => -105 + i).map((lon) => {
            const x = projection([lon, 26])![0];
            return (
              <g key={lon}>
                <line x1={x} x2={x} y1="0" y2={height} className="map-grid" />
                <text x={x + 5} y={height - 11} className="map-coordinate">
                  {Math.abs(lon)}° O
                </text>
              </g>
            );
          })}
          {[23, 24, 25, 26, 27, 28, 29, 30].map((lat) => {
            const y = projection([-100, lat])![1];
            return (
              <g key={lat}>
                <line x1="0" x2={width} y1={y} y2={y} className="map-grid" />
                <text x="14" y={y - 6} className="map-coordinate">
                  {lat}° N
                </text>
              </g>
            );
          })}
          {stateFeatures.map((f) => (
            <path
              key={f.properties.id}
              d={path(f) || ""}
              className={
                f.properties.intersects ? "state-area intersects" : "state-area"
              }
            >
              <title>{`${f.properties.id === "US-TX" ? "Texas (EE. UU.)" : f.properties.name}${f.properties.intersects ? " · intersecta la caja; sin resultado estatal" : ""}`}</title>
            </path>
          ))}
          {ready &&
            intersectedStates.map((f) => (
              <path
                key={f.properties.id}
                d={f.intersection.coordinates
                  .map((p) => p.map(projectedRing).join(" "))
                  .join(" ")}
                fill={color}
                fillOpacity=".94"
                fillRule="evenodd"
              />
            ))}
          {ready && uncertain && (
            <path d={footprint} fill={`url(#map-uncertainty-${id})`} />
          )}
          <path
            d={footprint}
            fill="none"
            stroke="#f6fafb"
            strokeWidth="2"
            strokeDasharray={uncertain ? "6 4" : undefined}
            vectorEffect="non-scaling-stroke"
          />
          {stateFeatures
            .filter(
              (f) =>
                !f.properties.intersects &&
                ["MX-CHH", "MX-DUR", "MX-ZAC", "MX-SLP"].includes(
                  f.properties.id,
                ),
            )
            .map((f) => {
              const p = projection(geoCentroid(f))!;
              return (
                <text
                  className="map-neighbor-label"
                  key={f.properties.id}
                  x={p[0]}
                  y={p[1]}
                  textAnchor="middle"
                >
                  {f.properties.id === "US-TX" ? "Texas (EE. UU.)" : f.properties.name}
                </text>
              );
            })}
          {intersectedStates.map((f) => {
            const p = projection(
              labelPositions[f.properties.id] ?? f.properties.label,
            )!;
            return (
              <g key={f.properties.id}>
                <text
                  x={p[0]}
                  y={p[1]}
                  textAnchor="middle"
                  className="map-state-name"
                >
                  {f.properties.id === "US-TX" ? "Texas (EE. UU.)" : f.properties.name}
                </text>
              </g>
            );
          })}
          <text
            x={center[0]}
            y={center[1] - 3}
            textAnchor="middle"
            className="map-box-label"
          >
            ÁREA
          </text>
          <text
            x={center[0]}
            y={center[1] + 14}
            textAnchor="middle"
            className="map-box-label"
          >
            ANALIZADA
          </text>
        </g>
      </svg>
      <div className="map-north">
        <Navigation size={14} />
        <span>N</span>
      </div>
      <div className="map-geographic-note">
        <i />
        <span>Estados que intersecta la caja</span>
      </div>
    </div>
  );
}
