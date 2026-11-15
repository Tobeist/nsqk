"use client";
import { useId, useMemo, useState, useSyncExternalStore } from "react";
import { line, scaleLinear, extent, curveLinear } from "d3";
import { getVariable } from "@/lib/catalog";
import { formatNumber } from "@/lib/format";
import type { Observation, VariableResult } from "@/lib/contracts";
const subscribeNarrow = (notify: () => void) => {
  const q = window.matchMedia("(max-width:700px)");
  q.addEventListener("change", notify);
  return () => q.removeEventListener("change", notify);
};
export function TrendChart({
  result,
  large = false,
  comparison = false,
}: {
  result: VariableResult;
  large?: boolean;
  comparison?: boolean;
}) {
  const narrow = useSyncExternalStore(
    subscribeNarrow,
    () => window.matchMedia("(max-width:700px)").matches,
    () => false,
  );
  const [hover, setHover] = useState<number | null>(null);
  const [showTrend, setShowTrend] = useState(true);
  const id = useId().replaceAll(":", "");
  const w = (large || comparison) && !narrow ? 1000 : 420,
    h = comparison ? 240 : large ? (narrow ? 290 : 420) : 220,
    m = { left: 52, right: 16, top: 26, bottom: 34 };
  const { x, y, seriesPath, trendPath } = useMemo(() => {
    const values = result.series
      .map((d) => d.value)
      .filter((v): v is number => v !== null);
    const [lo, hi] = extent(values) as [number, number],
      pad = (hi - lo) * 0.18 || 1;
    const x = scaleLinear()
      .domain(extent(result.series, (d) => d.year) as [number, number])
      .range([m.left, w - m.right]);
    const y = scaleLinear()
      .domain([lo - pad, hi + pad])
      .nice()
      .range([h - m.bottom, m.top]);
    const path = line<Observation>()
      .defined((d) => d.value !== null)
      .x((d) => x(d.year))
      .y((d) => y(d.value!))
      .curve(curveLinear);
    return {
      x,
      y,
      seriesPath: path(result.series) || "",
      trendPath: path(result.trend) || "",
    };
  }, [result, w, h, m.left, m.right, m.top, m.bottom]);
  const active = hover === null ? null : result.series[hover],
    color = getVariable(result.variableId).color;
  if (result.status === "no-data")
    return (
      <div className="no-chart">
        No hay serie disponible para esta combinación.
      </div>
    );
  const point = (index: number) =>
    setHover(Math.max(0, Math.min(result.series.length - 1, index)));
  return (
    <div className={`trend-chart ${large ? "large" : ""}`}>
      <div className="chart-unit">
        {result.unit} <span>· {result.annualLabel}</span>
      </div>
      <svg
        viewBox={`0 0 ${w} ${h}`}
        role="img"
        aria-label={`Serie anual de ${getVariable(result.variableId).name}; usa las flechas del teclado para consultar cada año.`}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
            e.preventDefault();
            point((hover ?? 0) + (e.key === "ArrowRight" ? 1 : -1));
          }
          if (e.key === "Escape") setHover(null);
        }}
        onPointerLeave={() => setHover(null)}
        onPointerMove={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const year = x.invert(((e.clientX - rect.left) / rect.width) * w);
          point(Math.round(year - result.series[0].year));
        }}
      >
        <defs>
          <linearGradient id={`area-${id}`} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor={color} stopOpacity=".10" />
            <stop offset="1" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        {y.ticks(4).map((t) => (
          <g key={t}>
            <line
              x1={m.left}
              x2={w - m.right}
              y1={y(t)}
              y2={y(t)}
              stroke="#283742"
              strokeDasharray="3 5"
            />
            <text x={m.left - 10} y={y(t) + 4} textAnchor="end">
              {formatNumber(t, result.unit === "m³/m³" ? 3 : 1)}
            </text>
          </g>
        ))}
        {x.ticks(5).map((t) => (
          <text key={t} x={x(t)} y={h - 10} textAnchor="middle">
            {t}
          </text>
        ))}
        <path
          d={seriesPath}
          fill="none"
          stroke={color}
          strokeWidth={large ? 2.7 : 2}
          strokeLinejoin="round"
        />
        {showTrend && (
          <path
            d={trendPath}
            fill="none"
            stroke="#e5e9e9"
            strokeWidth="1.5"
            strokeDasharray="5 5"
            opacity=".85"
          />
        )}
        {active && (
          <g>
            <line
              x1={x(active.year)}
              x2={x(active.year)}
              y1={m.top}
              y2={h - m.bottom}
              stroke="#a3bcc6"
              strokeDasharray="3 3"
            />
            {active.value !== null && (
              <circle
                cx={x(active.year)}
                cy={y(active.value)}
                r="4"
                fill={color}
                stroke="#0c1720"
                strokeWidth="2"
              />
            )}
            <g
              transform={`translate(${Math.min(w - 156, Math.max(m.left, x(active.year) - 60))},0)`}
            >
              <rect width="148" height="23" rx="5" fill="#253844" />
              <text x="74" y="16" textAnchor="middle" fill="#fff">
                {active.year} ·{" "}
                {active.value === null
                  ? "Sin dato"
                  : `${formatNumber(active.value, 3)} ${result.unit}`}
              </text>
            </g>
          </g>
        )}
      </svg>
      <div className="chart-legend">
        <span>
          <i style={{ background: color }} />
          Serie anual
        </span>
        <button
          onClick={() => setShowTrend((v) => !v)}
          aria-pressed={showTrend}
          className={!showTrend ? "muted" : ""}
        >
          <i className="dashed" />
          {showTrend ? "Tendencia lineal" : "Mostrar tendencia"}
        </button>
      </div>
      <p className="sr-only" aria-live="polite">
        {active
          ? `${active.year}: ${active.value === null ? "Sin dato" : `${formatNumber(active.value, 3)} ${result.unit}`}`
          : ""}
      </p>
      {result.series.some((d) => d.value === null) && (
        <p className="missing-note">Los huecos indican valores faltantes.</p>
      )}
    </div>
  );
}
