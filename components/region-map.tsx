"use client";
import { useId, useMemo } from "react";
import { geoMercator, geoPath } from "d3";
import { Navigation } from "lucide-react";
import { stateFeatures, getIntersectedStates, getStateNames } from "@/lib/geography";
import { signed, evidenceLabel, uncertainEvidence } from "@/lib/format";
import type { MapRegionValue } from "@/lib/map-layer";
import type { Region, Variable } from "@/lib/catalog";

const width = 680;
const height = 430;

export function RegionMap({
  region,
  value,
  variable,
}: {
  region: Region;
  value?: MapRegionValue;
  variable: Variable;
}) {
  const id = useId().replaceAll(":", "");
  const [west, south, east, north] = region.bbox;
  const activeStates = getIntersectedStates(region.id);
  const activeIds = new Set(activeStates.map((feature) => feature.properties.id));
  const stateNames = getStateNames(region.id);
  const projection = useMemo(() => geoMercator().fitExtent(
    [[45, 30], [width - 45, height - 35]],
    { type: "MultiPoint", coordinates: [[west - 2, south - 2], [east + 2, north + 2]] },
  ), [west, south, east, north]);
  const path = geoPath(projection).digits(3);
  // D3 can produce sub-pixel float differences between Node and the browser.
  // Serialize every SVG coordinate at the same precision on both sides.
  const project = (lon: number, lat: number) => {
    const [x, y] = projection([lon, lat])!;
    return [Number(x.toFixed(3)), Number(y.toFixed(3))] as const;
  };
  const projectedRing = (ring: number[][]) => ring.map(([lon, lat], index) => {
    const [x, y] = project(lon, lat);
    return `${index ? "L" : "M"}${x.toFixed(3)},${y.toFixed(3)}`;
  }).join("") + "Z";
  const [left, top] = project(west, north);
  const [right, bottom] = project(east, south);
  const [centerX, centerY] = project(region.lon, region.lat);
  const footprint = `M${left},${top}H${right}V${bottom}H${left}Z`;
  const ready = value?.state === "analyzed";
  const color = ready ? value.color : "#8299a8";
  const uncertain = !!value?.statistics && uncertainEvidence(value.statistics);
  const longitudeLines = Array.from({ length: east - west + 7 }, (_, i) => west - 3 + i);
  const latitudeLines = Array.from({ length: north - south + 7 }, (_, i) => south - 3 + i);

  return (
    <div className="regional-map">
      <svg viewBox={`0 0 ${width} ${height}`} role="img"
        aria-labelledby={`map-title-${id} map-description-${id}`}>
        <title id={`map-title-${id}`}>{`${region.name} y límites de ${stateNames.join(", ")}`}</title>
        <desc id={`map-description-${id}`}>
          {`El recuadro [${region.bbox.join(", ")}] representa el análisis regional; los límites estatales son contexto, sin resultados por estado completo. ${ready ? `Pendiente del recuadro: ${signed(value.statistics!.slopePerDecade, 3)} ${variable.unit} por década. ${evidenceLabel(value.statistics!)}.` : "Sin análisis visible para esta selección."}`}
        </desc>
        <defs>
          <clipPath id={`map-clip-${id}`}><rect width={width} height={height} /></clipPath>
          <pattern id={`map-uncertainty-${id}`} width="8" height="8"
            patternUnits="userSpaceOnUse" patternTransform="rotate(35)">
            <path d="M0 0V8" stroke="#091b25" strokeWidth="2" opacity=".5" />
          </pattern>
        </defs>
        <g clipPath={`url(#map-clip-${id})`}>
          {longitudeLines.map((lon) => {
            const [x] = project(lon, region.lat);
            return <g key={lon}>
              <line x1={x} x2={x} y1="0" y2={height} className="map-grid" />
              <text x={x + 5} y={height - 11} className="map-coordinate">{Math.abs(lon)}° O</text>
            </g>;
          })}
          {latitudeLines.map((lat) => {
            const [, y] = project(region.lon, lat);
            return <g key={lat}>
              <line x1="0" x2={width} y1={y} y2={y} className="map-grid" />
              <text x="14" y={y - 6} className="map-coordinate">{lat}° N</text>
            </g>;
          })}
          {stateFeatures.map((feature) => (
            <path key={feature.properties.id} d={path(feature) || ""}
              className={activeIds.has(feature.properties.id) ? "state-area intersects" : "state-area"}>
              <title>{`${feature.properties.name ?? "Estado"}${activeIds.has(feature.properties.id) ? " · intersecta la caja; sin resultado estatal" : ""}`}</title>
            </path>
          ))}
          {ready && activeStates.map((feature) => (
            <path key={feature.properties.id}
              d={feature.intersection.coordinates.map((polygon) => polygon.map(projectedRing).join("")).join("")}
              fill={color} fillOpacity=".94" fillRule="evenodd" />
          ))}
          {ready && uncertain && <path d={footprint} fill={`url(#map-uncertainty-${id})`} />}
          <path d={footprint} fill="none" stroke="#f6fafb" strokeWidth="2"
            strokeDasharray={uncertain ? "6 4" : undefined} vectorEffect="non-scaling-stroke" />
          {stateFeatures.filter((feature) => {
            const [lon, lat] = feature.properties.label;
            return feature.properties.name && !activeIds.has(feature.properties.id) &&
              lon >= west - 3 && lon <= east + 3 && lat >= south - 3 && lat <= north + 3;
          }).map((feature) => {
            const [x, y] = project(...feature.properties.label);
            return <text className="map-neighbor-label" key={feature.properties.id}
              x={x} y={y} textAnchor="middle">{feature.properties.name}</text>;
          })}
          <text x={centerX} y={centerY - 3} textAnchor="middle" className="map-box-label">ÁREA</text>
          <text x={centerX} y={centerY + 14} textAnchor="middle" className="map-box-label">ANALIZADA</text>
        </g>
      </svg>
      <div className="map-north"><Navigation size={14} /><span>N</span></div>
      <div className="map-geographic-note"><i /><span>Estados que intersectan la caja</span></div>
    </div>
  );
}
