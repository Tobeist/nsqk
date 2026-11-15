"use client";
import { useEffect, useId, useState } from "react";
import { createPortal } from "react-dom";
import { area, line, scaleLinear } from "d3";
import { Download, Expand, FlaskConical } from "lucide-react";
import { getRegion, getVariable, type VariableId } from "@/lib/catalog";
import { Modal } from "./modal";
import { formatNumber } from "@/lib/format";
import { forecastCsv, forecastModelLabel, forecastValues, getForecast, type ForecastModelId, type ForecastResult } from "@/lib/forecast-data";
import { getSourceLinks } from "@/lib/source-links";
import styles from "./forecast-panel.module.css";

export function ForecastPanel(props: { regionId: string; variableId: VariableId; start: number; end: number }) {
  const result = getForecast(props.regionId, props.variableId, props.start, props.end);
  if (!result) return <p className={styles.unavailable}>{props.variableId === "rain5-power-annual" ? "No hay un modelo de predicción validado para este índice anual. Prueba una variable mensual." : "Predicción disponible con la serie completa 1992–2024."}</p>;
  return <ForecastExperiment key={`${props.regionId}:${props.variableId}`} {...props} result={result} />;
}
function ForecastExperiment({ result, regionId, variableId }: { result: ForecastResult; regionId: string; variableId: VariableId }) {
  const [mode, setMode] = useState<"projection" | "backtest">("projection");
  const [model, setModel] = useState<ForecastModelId>(result.selectedModel);
  const [expanded, setExpanded] = useState(false);
  const score = result.models.find((m) => m.id === model)!;
  const models = [...new Set<ForecastModelId>([result.selectedModel, "neural", "neural-enso", "climatology"])];
  const ensoSource = getSourceLinks(variableId)[1];
  function download() {
    const url = URL.createObjectURL(new Blob([forecastCsv(regionId, variableId, mode, model)], { type: "text/csv;charset=utf-8;" }));
    const link = document.createElement("a"); link.href = url;
    link.download = `prediction_${regionId}_${variableId}_${mode}_${model}.csv`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const controls = <>
    <div className={styles.tabs} role="group" aria-label="Vista de predicción">
      <button aria-pressed={mode === "projection"} onClick={() => setMode("projection")}>Proyección 2025</button>
      <button aria-pressed={mode === "backtest"} onClick={() => setMode("backtest")}>Comparar con datos reales</button>
    </div>
    <p className={styles.context}>{mode === "projection" ? "12 meses estimados desde diciembre de 2024." : "Prueba retrospectiva de 2021–2024, año por año."}</p>
    <div className={styles.models} role="group" aria-label="Modelo de predicción">
      {models.map((id) => <button key={id} aria-pressed={id === model} onClick={() => setModel(id)}>{forecastModelLabel[id]}{id === result.selectedModel ? <span>actual</span> : id === "neural-enso" ? <span>experimental</span> : null}</button>)}
    </div>
    {model === "neural-enso" && <p className={styles.context}>Incluye Niño 3.4, indicador de El Niño y La Niña. <a href={ensoSource.href} target="_blank" rel="noreferrer">Fuente: NOAA</a></p>}
  </>;
  return <><section className={styles.panel} aria-label="Predicción mensual">
    <div className={styles.heading}><h4><FlaskConical size={16} /> Predicción mensual</h4><div className={styles.actions}><button className="icon-button" aria-label="Ampliar predicción" onClick={() => setExpanded(true)}><Expand size={15} /></button><button className="icon-button" aria-label="Descargar predicciones" onClick={download}><Download size={15} /></button></div></div>
    {controls}
    <ForecastPlot key={`${mode}:${model}`} result={result} mode={mode} model={model} />
    <p className={styles.score}>Error histórico medio: <strong>{formatNumber(score.testMae, 2)} {result.unit}</strong></p>
    <p className={styles.comparison}>{score.skillVsClimatology === 0 ? "Referencia: el patrón habitual de cada mes." : `${formatNumber(Math.abs(score.skillVsClimatology) * 100, 0)} % ${score.skillVsClimatology > 0 ? "menos" : "más"} error que el patrón estacional en 2021–2024.`}{model === "neural-enso" ? " Experimento; se conserva el modelo anterior como predeterminado." : model === "neural" && model !== result.selectedModel ? " Red experimental; no ganó la selección." : ""}</p>
    <details className={styles.details}><summary>Cómo se probó y qué tan bien predice</summary>
      <p>Modelo elegido con 2016–2020. Error medido en 2021–2024, prediciendo cada año sólo con datos anteriores. Estos años ya se revisaron en versiones previas; no son una prueba nueva. Menor error es mejor.</p>
      <p>Red + ENSO sigue en evaluación: los resultados generales son mixtos. Ganador de validación al incluir el experimento: {forecastModelLabel[result.validationWinner]}. Se conserva el modelo de la versión anterior en todas las series hasta contar con una validación nueva.</p>
      <table><caption>Error medio mensual ({result.unit})</caption><thead><tr><th>Modelo</th><th>Validar</th><th>Probar</th></tr></thead><tbody>{result.models.map((m) => <tr key={m.id}><th scope="row">{forecastModelLabel[m.id]}</th><td>{formatNumber(m.validationMae, 2)}</td><td>{formatNumber(m.testMae, 2)}</td></tr>)}</tbody></table>
      <p>La banda apunta al 80 % con errores de validación. En la prueba cubrió {formatNumber(score.coverage80 * 100, 0)} % de los meses; es orientativa.</p>
      <p>La red original usa la historia de la variable y el mes del año. Red + ENSO añade Niño 3.4 hasta octubre del año anterior; para los meses desconocidos mantiene el último valor disponible. Es una suposición, no conocimiento del ENSO futuro.</p>
      <p>Datos hasta diciembre de 2024. La proyección de 2025 no es un pronóstico meteorológico actual ni una observación. Fuente: {result.source}.</p>
      <a href="https://github.com/Tobeist/nsqk/blob/main/docs/FORECAST_PROTOCOL.md" target="_blank" rel="noreferrer">Ver protocolo y reproducción</a>
    </details>
  </section>{expanded && createPortal(<Modal title="Explorador de predicción" wide onClose={() => setExpanded(false)}>
    <div className={styles.expanded}><h3>{getVariable(variableId).name} ({result.unit}) · {getRegion(regionId).name}</h3>
      {controls}
      <ForecastPlot key={`${mode}:${model}`} result={result} mode={mode} model={model} large />
      <p>Error histórico medio: <strong>{formatNumber(score.testMae, 2)} {result.unit}</strong> · prueba 2021–2024.</p>
      <p>Datos hasta diciembre de 2024 · rango orientativo, no un pronóstico actual.</p>
      <button className="secondary-button" onClick={download}><Download size={14} /> Descargar esta predicción</button>
    </div>
  </Modal>, document.body)}</>;
}
const monthNumber = (date: string) => Number(date.slice(0, 4)) * 12 + Number(date.slice(5, 7)) - 1;
const dateLabel = (date: string) => `${["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"][Number(date.slice(5, 7)) - 1]} ${date.slice(0, 4)}`;
function ForecastPlot({ result, mode, model, large = false }: { result: ForecastResult; mode: "projection" | "backtest"; model: ForecastModelId; large?: boolean }) {
  const id = useId().replaceAll(":", "");
  const [hover, setHover] = useState<number | null>(null);
  const [narrow, setNarrow] = useState(false);
  useEffect(() => {
    const media = window.matchMedia("(max-width: 700px)");
    const update = () => setNarrow(media.matches);
    update(); media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  const points = mode === "projection" ? [
    ...result.history.slice(-24).map((p) => ({ date: p.date, actual: p.value, value: null as number | null, lower: p.value, upper: p.value })),
    ...result.projection.map((p) => ({ date: p.date, actual: null as number | null, ...forecastValues(p, model, result.selectedModel) })),
  ] : result.holdout.map((p) => ({ date: p.date, actual: p.actual, ...forecastValues(p, model, result.selectedModel) }));
  const w = large && !narrow ? 900 : 440, h = large && !narrow ? 360 : 260, margin = { left: 49, right: 12, top: 15, bottom: 34 };
  const numbers = points.flatMap((p) => [p.actual, p.value, p.lower, p.upper]).filter((v): v is number => v !== null);
  const low = Math.min(...numbers), high = Math.max(...numbers), pad = (high - low) * .1 || 1;
  const x = scaleLinear().domain([monthNumber(points[0].date), monthNumber(points.at(-1)!.date)]).range([margin.left, w - margin.right]);
  const y = scaleLinear().domain([low - pad, high + pad]).nice().range([h - margin.bottom, margin.top]);
  type Point = typeof points[number];
  const path = (key: "actual" | "value") => line<Point>().defined((p) => p[key] !== null).x((p) => x(monthNumber(p.date))).y((p) => y(p[key]!))(points) ?? "";
  const band = area<Point>().defined((p) => p.value !== null).x((p) => x(monthNumber(p.date))).y0((p) => y(p.lower)).y1((p) => y(p.upper))(points) ?? "";
  const active = hover === null ? null : points[hover];
  const select = (index: number) => setHover(Math.max(0, Math.min(points.length - 1, index)));
  return <div className={styles.plot}>
    <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-labelledby={`${id}-title ${id}-desc`} tabIndex={0}
      onKeyDown={(e) => { if (e.key === "ArrowLeft" || e.key === "ArrowRight") { e.preventDefault(); select((hover ?? 0) + (e.key === "ArrowRight" ? 1 : -1)); } if (e.key === "Escape") setHover(null); }}
      onPointerLeave={() => setHover(null)} onPointerMove={(e) => { const r = e.currentTarget.getBoundingClientRect(); select(Math.round((x.invert((e.clientX - r.left) / r.width * w) - monthNumber(points[0].date)))); }}>
      <title id={`${id}-title`}>{mode === "projection" ? "Proyección mensual de 2025 desde datos hasta 2024" : "Predicción retrospectiva frente a observaciones 2021–2024"}</title>
      <desc id={`${id}-desc`}>Modelo: {forecastModelLabel[model]}. Línea coral: datos reales. Línea menta: estimación. Banda: rango orientativo. Usa las flechas para consultar cada mes.</desc>
      {y.ticks(4).map((tick) => <g key={tick}><line x1={margin.left} x2={w - margin.right} y1={y(tick)} y2={y(tick)} className={styles.grid} /><text x={margin.left - 8} y={y(tick) + 4} textAnchor="end">{formatNumber(tick, Math.abs(high - low) < 2 ? 1 : 0)}</text></g>)}
      {points.filter((p) => p.date.slice(5, 7) === "01").map((p) => <text key={p.date} x={x(monthNumber(p.date))} y={h - 10} textAnchor="middle">{p.date.slice(0, 4)}</text>)}
      <path d={band} fill="#8ce1cd" opacity=".13" />
      <path d={path("actual")} fill="none" stroke="#f2a58e" strokeWidth="1.8" />
      <path d={path("value")} fill="none" stroke="#8ce1cd" strokeWidth="2" strokeDasharray="5 3" />
      {mode === "projection" && <line x1={x(monthNumber("2024-12-01"))} x2={x(monthNumber("2024-12-01"))} y1={margin.top} y2={h - margin.bottom} stroke="#7e8e9e" strokeDasharray="2 4" />}
      {active && <line x1={x(monthNumber(active.date))} x2={x(monthNumber(active.date))} y1={margin.top} y2={h - margin.bottom} stroke="#e5ecef" opacity=".5" />}
    </svg>
    <div className={styles.legend}><span><i className={styles.observed} />Datos reales</span><span><i className={styles.predicted} />Estimación</span><span className={styles.range}>Rango orientativo</span></div>
    <p className={styles.readout} aria-live="polite">{active ? `${dateLabel(active.date)} · ${active.actual !== null ? `Real ${formatNumber(active.actual, 2)}` : "Sin observación"}${active.value !== null ? ` · Estimado ${formatNumber(active.value, 2)}` : ""} ${result.unit}` : `${result.unit} · consulta un mes con el cursor o las flechas`}</p>
  </div>;
}
