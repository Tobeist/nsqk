"use client";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useRef, useState } from "react";
import {
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Compass,
  Droplets,
  Expand,
  ExternalLink,
  FileText,
  Layers3,
  Leaf,
  LoaderCircle,
  MapPin,
  MessageCircle,
  Orbit,
  Plus,
  RotateCcw,
  Send,
  ShieldCheck,
  Thermometer,
  TrendingUp,
  X,
} from "lucide-react";
import { animate } from "animejs";
import {
  getRegion,
  getVariable,
  regions,
  variables,
  type Family,
  type Variable,
  type VariableId,
} from "@/lib/catalog";
import {
  conversationKey,
  selectionKey,
  type Analysis,
  type ChatMessage,
  type Selection,
} from "@/lib/contracts";
import { evidenceLabel, formatNumber, signed } from "@/lib/format";
import {
  annualIndexId,
  createRealAnalysis,
  firstDataYear,
  lastDataYear,
  minimumAnnualIndexYears,
  minimumYearsForVariables,
  realDefaultSelection,
} from "@/lib/real-data";
import {
  analysisCsv,
  realAnalysisAdapter,
  localEvidenceChatAdapter,
  toChatContext,
} from "@/lib/adapters";
import { createMapLayer, getMapLimit } from "@/lib/map-layer";
import { RegionMap } from "./region-map";
import { stateNames } from "@/lib/geography";
import { TrendChart } from "./chart";
import { Modal } from "./modal";
const Globe = dynamic(() => import("./globe"), {
  ssr: false,
  loading: () => (
    <div className="globe-loading">
      <LoaderCircle className="spin" size={24} />
      <span>Cargando cartografía…</span>
    </div>
  ),
});
const families: Family[] = ["Calor", "Lluvia", "Suelo"];
const FamilyIcon = { Calor: Thermometer, Lluvia: Droplets, Suelo: Leaf };
const suggestions = [
  "¿Qué significa esta pendiente?",
  "¿Qué tan clara es la evidencia?",
  "¿Qué no puedo concluir?",
];
const availableYears = Array.from(
  { length: lastDataYear - firstDataYear + 1 },
  (_, i) => firstDataYear + i,
);
type MobileTab = "explore" | "results" | "chat";
export function Explorer() {
  const [draft, setDraft] = useState<Selection>(realDefaultSelection);
  const [analysis, setAnalysis] = useState<Analysis | null>(() =>
    createRealAnalysis(realDefaultSelection),
  );
  const [history, setHistory] = useState<Analysis[]>(() => [
    createRealAnalysis(realDefaultSelection),
  ]);
  const [activeId, setActiveId] = useState<VariableId>("temperature");
  const [mapView, setMapView] = useState<"regional" | "globe">("regional");
  const [family, setFamily] = useState<Family>("Calor");
  const [mobileTab, setMobileTab] = useState<MobileTab>("explore");
  const [rightTab, setRightTab] = useState<"results" | "chat">("results");
  const [loading, setLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState("");
  const [selectionMessage, setSelectionMessage] = useState("");
  const [modal, setModal] = useState<
    "evidence" | "chart" | "compare" | "about" | null
  >(null);
  const [evidenceFocus, setEvidenceFocus] = useState("");
  const [threads, setThreads] = useState<Record<string, ChatMessage[]>>({});
  const [chatBusy, setChatBusy] = useState<Record<string, boolean>>({});
  const [chatErrors, setChatErrors] = useState<Record<string, string>>({});
  const resultRef = useRef<HTMLDivElement>(null);
  const regionRef = useRef<HTMLDivElement>(null);
  const requestRef = useRef<AbortController | null>(null);
  const region = getRegion(draft.regionId);
  const result = analysis?.results.find((r) => r.variableId === activeId);
  const activeVariable = getVariable(activeId);
  const dirty = analysis
    ? selectionKey(draft) !== selectionKey(analysis.selection)
    : true;
  const contextKey = analysis ? conversationKey(analysis.id, activeId) : "none";
  const messages = threads[contextKey] ?? [];
  const openEvidence = (focus = "") => {
    setEvidenceFocus(focus);
    setModal("evidence");
  };
  function chooseRegion(id: string) {
    if (id !== "mx-northeast") return;
    setDraft((d) => ({ ...d, regionId: id }));
    setSelectionMessage("");
    if (
      regionRef.current &&
      !window.matchMedia("(prefers-reduced-motion: reduce)").matches
    )
      animate(regionRef.current, {
        opacity: [0.55, 1],
        translateY: [4, 0],
        duration: 230,
        ease: "outCubic",
      });
  }
  function toggleVariable(id: VariableId) {
    if (!draft.variables.includes(id) && draft.variables.length >= 3) {
      setSelectionMessage(
        "Tu selección admite hasta tres variables. Quita una para añadir otra.",
      );
      return;
    }
    if (id === annualIndexId && !draft.variables.includes(id) &&
        draft.end - draft.start + 1 < minimumAnnualIndexYears) {
      setSelectionMessage("RX5day anual de POWER requiere al menos 20 años. Amplía el periodo para seleccionarlo.");
      return;
    }
    setSelectionMessage("");
    setDraft((d) => ({
      ...d,
      variables: d.variables.includes(id)
        ? d.variables.filter((v) => v !== id)
        : [...d.variables, id],
    }));
  }
  async function analyze() {
    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    setAnalysisError("");
    setLoading(true);
    const snapshot = structuredClone(draft);
    try {
      const next = await realAnalysisAdapter.analyze(
        snapshot,
        controller.signal,
      );
      setAnalysis(next);
      setHistory((h) => [...h.filter((a) => a.id !== next.id), next]);
      const newlyAdded = snapshot.variables.find(
        (id) => !analysis?.selection.variables.includes(id),
      );
      setActiveId(
        newlyAdded ?? (snapshot.variables.includes(activeId)
          ? activeId
          : snapshot.variables[0]),
      );
      setRightTab("results");
      setMobileTab("results");
      scrollToSection();
      if (
        resultRef.current &&
        !window.matchMedia("(prefers-reduced-motion: reduce)").matches
      )
        animate(resultRef.current, {
          opacity: [0.4, 1],
          translateY: [7, 0],
          duration: 280,
          ease: "outCubic",
        });
    } catch (e) {
      if (e instanceof Error && e.name !== "AbortError")
        setAnalysisError(e.message);
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }
  function download() {
    if (!analysis || !result) return;
    const blob = new Blob([analysisCsv(analysis, activeId)], {
        type: "text/csv;charset=utf-8;",
      }),
      url = URL.createObjectURL(blob),
      a = document.createElement("a");
    a.href = url;
    a.download = `trend-detectives_${analysis.region.id}_${activeId}_${analysis.selection.start}-${analysis.selection.end}.csv`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async function send(question: string, retry = false) {
    if (!analysis || !result || chatBusy[contextKey]) return;
    const key = contextKey,
      context = toChatContext(analysis, activeId);
    const id = crypto.randomUUID();
    if (!retry)
      setThreads((t) => ({
        ...t,
        [key]: [...(t[key] ?? []), { id, role: "user", text: question }],
      }));
    setChatBusy((b) => ({ ...b, [key]: true }));
    setChatErrors((e) => ({ ...e, [key]: "" }));
    try {
      const response = await localEvidenceChatAdapter.reply(question, context);
      setThreads((t) => ({
        ...t,
        [key]: [
          ...(t[key] ?? []),
          { ...response, id: crypto.randomUUID(), role: "assistant" },
        ],
      }));
    } catch (e) {
      setChatErrors((v) => ({
        ...v,
        [key]: e instanceof Error ? e.message : "Ocurrió un error.",
      }));
    } finally {
      setChatBusy((b) => ({ ...b, [key]: false }));
    }
  }
  const scrollToSection = () => {
    if (window.matchMedia("(max-width:700px)").matches)
      requestAnimationFrame(() =>
        window.scrollTo({ top: 0, behavior: "instant" }),
      );
  };
  const switchRight = (tab: "results" | "chat") => {
    setRightTab(tab);
    setMobileTab(tab);
    scrollToSection();
  };
  const mapLayer = createMapLayer(history, analysis, activeId);
  const mapLimit = mapLayer[0]?.limit ?? getMapLimit(activeId);
  const stat = result?.statistics;
  const inconclusive =
    stat && stat.confidenceInterval[0] <= 0 && stat.confidenceInterval[1] >= 0;
  return (
    <div className="app-shell">
      <a className="skip-link" href="#analysis-panel">
        Saltar al análisis
      </a>
      <header className="app-header">
        <Link className="brand" href="/" aria-label="Trend Detectives, inicio">
          <Orbit size={31} strokeWidth={1.4} />
          <span>
            trend<span className="brand-light">detectives</span>
            <span className="brand-dot">.</span>
          </span>
        </Link>
        <div className="header-center">
          <span className="header-divider" />
          <span className="workspace-label">Explorador ambiental</span>
        </div>
        <div className="header-actions">
          <span className="demo-status">
            <i />
            Datos NASA · análisis exploratorio
          </span>
          <button
            className="icon-button help-button"
            aria-label="Acerca del proyecto y los datos"
            onClick={() => setModal("about")}
          >
            <CircleHelp size={18} />
          </button>
        </div>
      </header>
      <div className="mobile-nav" aria-label="Secciones">
        <button
          className={mobileTab === "explore" ? "active" : ""}
          onClick={() => {
            setMobileTab("explore");
            scrollToSection();
          }}
        >
          <Compass size={16} />
          Explorar
        </button>
        <button
          className={mobileTab === "results" ? "active" : ""}
          onClick={() => switchRight("results")}
        >
          <TrendingUp size={16} />
          Resultados
        </button>
        <button
          className={mobileTab === "chat" ? "active" : ""}
          onClick={() => switchRight("chat")}
        >
          <MessageCircle size={16} />
          Chat
        </button>
      </div>
      <main className="workspace">
        <aside
          className={`filters-panel ${mobileTab === "explore" ? "mobile-visible" : ""}`}
          aria-label="Configurar análisis"
        >
          <div className="filter-scroll">
            <h1>Configurar análisis</h1>
            <p className="panel-intro">Variables y periodo de estudio.</p>
            <div className="section-title">
              <h2>Variables ambientales</h2>
              <span>{draft.variables.length}/3</span>
            </div>
            <div className="family-tabs" aria-label="Familia de variables">
              {families.map((f) => {
                const Icon = FamilyIcon[f];
                return (
                  <button
                    key={f}
                    className={family === f ? "selected" : ""}
                    aria-pressed={family === f}
                    onClick={() => setFamily(f)}
                  >
                    <Icon size={15} />
                    {f}
                  </button>
                );
              })}
            </div>
            <div className="variable-list">
              {variables
                .filter((v) => v.family === family && v.available)
                .map((v) => (
                  <VariableChoice
                    key={v.id}
                    variable={v}
                    selected={draft.variables.includes(v.id)}
                    onToggle={() => toggleVariable(v.id)}
                  />
                ))}
              <details className="pending-variables">
                <summary>
                  <span>
                    Ver{" "}
                    {
                      variables.filter(
                        (v) => v.family === family && !v.available,
                      ).length
                    }{" "}
                    variables por integrar
                  </span>
                  <ChevronDown size={13} />
                </summary>
                <div>
                  {variables
                    .filter((v) => v.family === family && !v.available)
                    .map((v) => (
                      <VariableChoice
                        key={v.id}
                        variable={v}
                        selected={false}
                        onToggle={() => {}}
                      />
                    ))}
                </div>
              </details>
            </div>
            {selectionMessage && (
              <p role="status" className="field-message">
                {selectionMessage}
              </p>
            )}
            <div className="selected-summary">
              {draft.variables.length > 0 ? (
                draft.variables.map((id) => (
                  <button
                    key={id}
                    onClick={() => toggleVariable(id)}
                    title={`Quitar ${getVariable(id).name}`}
                  >
                    <span style={{ background: getVariable(id).color }} />
                    {getVariable(id).short}
                    <X size={11} />
                  </button>
                ))
              ) : (
                <span>Selecciona al menos una variable.</span>
              )}
            </div>
            <div className="period-section">
              <div className="section-title">
                <h2>Periodo de estudio</h2>
                <span className="quiet-icon">
                  <Layers3 size={14} />
                </span>
              </div>
              <div className="year-fields">
                <label>
                  Desde
                  <select
                    aria-label="Año inicial"
                    value={draft.start}
                    onChange={(e) => {
                      setDraft((d) => ({ ...d, start: Number(e.target.value) }));
                      setSelectionMessage("");
                    }}
                  >
                    {availableYears.map((year) => (
                      <option
                        key={year}
                        value={year}
                        disabled={year > draft.end - minimumYearsForVariables(draft.variables) + 1}
                      >
                        {year}
                      </option>
                    ))}
                  </select>
                  <ChevronDown size={13} />
                </label>
                <span>—</span>
                <label>
                  Hasta
                  <select
                    aria-label="Año final"
                    value={draft.end}
                    onChange={(e) => {
                      setDraft((d) => ({ ...d, end: Number(e.target.value) }));
                      setSelectionMessage("");
                    }}
                  >
                    {availableYears.map((year) => (
                      <option
                        key={year}
                        value={year}
                        disabled={year < draft.start + minimumYearsForVariables(draft.variables) - 1}
                      >
                        {year}
                      </option>
                    ))}
                  </select>
                  <ChevronDown size={13} />
                </label>
              </div>
              <div className="period-track">
                <span
                  style={{
                    left: `${((draft.start - firstDataYear) / availableYears.length) * 100}%`,
                    width: `${((draft.end - draft.start + 1) / availableYears.length) * 100}%`,
                  }}
                />
              </div>
              <p className="period-note">
                {draft.end >= draft.start ? draft.end - draft.start + 1 : 0}{" "}
                años · mínimo {minimumYearsForVariables(draft.variables)} · datos {firstDataYear}–
                {lastDataYear}
              </p>
            </div>
            <div className="scope-note">
              <ShieldCheck size={16} />
              <p>
                <strong>Una lectura con contexto.</strong> Magnitud e
                incertidumbre, sin atribución causal ni pronósticos.
              </p>
            </div>
          </div>
          <div className="filter-bottom">
            <div className={`draft-status ${dirty ? "pending" : ""}`}>
              <i />
              {dirty ? "Selección lista para analizar" : "Selección analizada"}
            </div>
            <button
              className="analyze-button"
              onClick={analyze}
              disabled={loading || draft.variables.length === 0}
            >
              {loading ? (
                <>
                  <LoaderCircle className="spin" size={16} />
                  Preparando análisis…
                </>
              ) : (
                <>
                  Analizar selección
                  <ArrowRight size={17} />
                </>
              )}
            </button>
            {analysisError && (
              <div className="analysis-error" role="alert">
                {analysisError}
                <button onClick={analyze}>Reintentar</button>
              </div>
            )}
            <span className="local-note">
              Tendencia e intervalo recalculados con los datos elegidos
            </span>
          </div>
        </aside>
        <section
          className={`earth-panel ${mobileTab === "explore" ? "mobile-visible" : ""}`}
          aria-label="Explorador geográfico"
        >
          <div className="earth-heading">
            <div>
              <h2>Área de estudio</h2>
              <p>Una caja que cruza {stateNames.length} estados.</p>
            </div>
            <div className="map-view-switch" aria-label="Vista del mapa">
              <button
                aria-pressed={mapView === "regional"}
                onClick={() => setMapView("regional")}
              >
                Estados
              </button>
              <button
                aria-pressed={mapView === "globe"}
                onClick={() => setMapView("globe")}
              >
                Planeta 3D
              </button>
            </div>
          </div>
          {mapView === "regional" ? (
            <RegionMap value={mapLayer[0]} variable={activeVariable} />
          ) : (
            <Globe
              regionId={draft.regionId}
              onSelect={chooseRegion}
              layer={mapLayer}
            />
          )}
          <div className="states-context">
            <div>
              {stateNames.map((name) => (
                <span key={name}>{name === "Texas" ? "Texas (EE. UU.)" : name}</span>
              ))}
            </div>
            <p>
              El color de la tendencia corresponde sólo al recuadro, que cruza parte de Texas. Sin resultados por estado.
            </p>
          </div>
          <div className="map-legend" aria-label="Leyenda del mapa">
            <div>
              <span>Cambio por década · {activeVariable.short}</span>
              <strong>{activeVariable.unit}/década</strong>
            </div>
            <div className="map-color-ramp" />
            <div className="map-scale-labels">
              <span>
                {signed(-mapLimit, activeId === "surface-moisture" ? 3 : 1)}
              </span>
              <span>0</span>
              <span>
                {signed(mapLimit, activeId === "surface-moisture" ? 3 : 1)}
              </span>
            </div>
            <p>
              {analysis
                ? `${analysis.selection.start}–${analysis.selection.end} · ${mapLayer.filter((v) => v.state === "analyzed").length}/1 caja analizada`
                : "Analiza una selección para colorear su área."}
              <span>Datos NASA</span>
            </p>
            <div className="map-certainty">
              <i />
              Sin analizar / sin datos <span className="dash-swatch" />
              IC incluye cero
            </div>
          </div>
          <div className="region-selector" ref={regionRef}>
            <div className="region-selector-label">
              <MapPin size={14} />
              <label htmlFor="region">REGIÓN DE ESTUDIO</label>
              <span>1 caja con datos</span>
            </div>
            <div className="region-select-row">
              <span className="country-code">{region.countryCode}</span>
              <select
                id="region"
                value={draft.regionId}
                onChange={(e) => chooseRegion(e.target.value)}
              >
                {regions
                  .filter((r) => r.id === "mx-northeast")
                  .map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))}
              </select>
              <ChevronDown size={17} />
            </div>
            <div className="region-detail">
              <span>{region.extent}</span>
              <span>Caja de 2° × 2°</span>
            </div>
          </div>
          <div className="coverage">
            <div>
              <i className="coverage-on" />
              México
            </div>
            <p>
              La caja noreste tiene datos procesados. No representa todo México.
            </p>
          </div>
        </section>
        <aside
          id="analysis-panel"
          className={`analysis-panel ${mobileTab !== "explore" ? "mobile-visible" : ""}`}
          tabIndex={-1}
          aria-label="Resultados y conversación"
        >
          <div className="analysis-tabs">
            <button
              className={rightTab === "results" ? "active" : ""}
              onClick={() => switchRight("results")}
            >
              <TrendingUp size={15} />
              Análisis
            </button>
            <button
              className={rightTab === "chat" ? "active" : ""}
              onClick={() => switchRight("chat")}
            >
              <MessageCircle size={15} />
              Conversación
              {messages.length > 0 && <span>{messages.length}</span>}
            </button>
            <button
              className="icon-button new-analysis"
              title="Limpiar análisis visible"
              aria-label="Limpiar análisis visible"
              onClick={() => {
                setAnalysis(null);
                setRightTab("results");
                setMobileTab("results");
              }}
            >
              <Plus size={16} />
            </button>
          </div>
          {dirty && analysis && (
            <div className="pending-banner" role="status">
              <span>
                <i />
                Cambios pendientes
              </span>
              <p>
                El resultado sigue mostrando {analysis.region.name},{" "}
                {analysis.selection.start}–{analysis.selection.end}.
              </p>
            </div>
          )}
          <div className="analysis-scroll" ref={resultRef} aria-busy={loading}>
            {!analysis ? (
              <div className="empty-state">
                <div className="empty-orbit">
                  <Orbit size={40} strokeWidth={1} />
                </div>
                <span className="section-kicker">TU SIGUIENTE HALLAZGO</span>
                <h2>
                  Haz tu primera pregunta
                  <br />a los datos.
                </h2>
                <p>
                  Elige una región, al menos una variable y un periodo. Después,
                  pulsa Analizar.
                </p>
                <button
                  className="text-button"
                  onClick={() => {
                    setMobileTab("explore");
                    scrollToSection();
                  }}
                >
                  Configurar selección
                  <ArrowLeft size={14} />
                </button>
                {rightTab === "chat" && (
                  <p className="chat-disclaimer">
                    El chat necesita un análisis para construir su contexto.
                  </p>
                )}
              </div>
            ) : (
              <>
                <div className="result-context">
                  <h2>{analysis.region.name}</h2>
                  <p>
                    <MapPin size={12} />
                    {analysis.region.country}
                    <span>·</span>
                    {analysis.selection.start}–{analysis.selection.end}
                    <span>·</span>
                    {analysis.selection.end - analysis.selection.start + 1} años
                  </p>
                </div>
                <div
                  className="result-variable-tabs"
                  aria-label="Variable activa del resultado"
                >
                  {analysis.results.map((r) => (
                    <button
                      key={r.variableId}
                      aria-pressed={activeId === r.variableId}
                      onClick={() => setActiveId(r.variableId)}
                      className={activeId === r.variableId ? "active" : ""}
                    >
                      <i
                        style={{ background: getVariable(r.variableId).color }}
                      />
                      {getVariable(r.variableId).short}
                    </button>
                  ))}
                </div>
                {analysis.results.length > 1 && (
                  <button
                    className="compare-series-button"
                    onClick={() => setModal("compare")}
                  >
                    <Layers3 size={13} />
                    Comparar {analysis.results.length} series juntas
                    <Expand size={12} />
                  </button>
                )}
                {rightTab === "chat" ? (
                  <ChatView
                    key={contextKey}
                    messages={messages}
                    busy={chatBusy[contextKey]}
                    error={chatErrors[contextKey]}
                    disabled={result?.status === "no-data"}
                    onSend={send}
                    onEvidence={openEvidence}
                    onRetry={() => {
                      const last = messages.findLast((m) => m.role === "user");
                      if (last) send(last.text, true);
                    }}
                    context={`${activeVariable.short} · ${analysis.selection.start}–${analysis.selection.end}`}
                  />
                ) : result?.status === "no-data" ? (
                  <div className="empty-state no-data">
                    <Layers3 size={35} />
                    <h3>Esta combinación aún no tiene datos.</h3>
                    <p>
                      Esta variable todavía no tiene una serie procesada para la
                      caja seleccionada.
                    </p>
                    <button
                      className="secondary-button"
                      onClick={() => openEvidence("method")}
                    >
                      Ver disponibilidad
                      <FileText size={14} />
                    </button>
                  </div>
                ) : stat && result ? (
                  <>
                    <div className="result-summary">
                      <div className="variable-eyebrow">
                        <span style={{ color: activeVariable.color }}>
                          {activeVariable.name}
                        </span>
                      </div>
                      <h3>
                        {inconclusive
                          ? "La dirección aún no es concluyente."
                          : stat.slopePerDecade > 0
                            ? "Una señal de aumento en la serie."
                            : "Una señal de disminución en la serie."}
                      </h3>
                      <p>
                        {inconclusive
                          ? "La estimación es " +
                            (stat.slopePerDecade >= 0
                              ? "positiva"
                              : "negativa") +
                            ", pero su intervalo incluye cero."
                          : "El intervalo de este ajuste excluye cero."}{" "}
                        <span>
                          Resultado exploratorio; revisa fuente y método.
                        </span>
                      </p>
                    </div>
                    <div className="metric-row">
                      <div>
                        <span className="metric-label">CAMBIO POR DÉCADA</span>
                        <div
                          className="main-metric"
                          style={{ color: activeVariable.color }}
                        >
                          {signed(
                            stat.slopePerDecade,
                            activeId === "surface-moisture" ? 3 : 2,
                          )}
                          <span>{result.unit}</span>
                        </div>
                      </div>
                      <span
                        className={`evidence-status ${inconclusive ? "uncertain" : ""}`}
                      >
                        <span>
                          {inconclusive ? "±" : <TrendingUp size={12} />}
                        </span>
                        {inconclusive ? "Inconclusa" : "IC excluye cero"}
                      </span>
                    </div>
                    <button
                      className="interval-row"
                      onClick={() => openEvidence("interval")}
                    >
                      <span>Intervalo de confianza del 95 %</span>
                      <strong>
                        {signed(
                          stat.confidenceInterval[0],
                          activeId === "surface-moisture" ? 3 : 2,
                        )}{" "}
                        a{" "}
                        {signed(
                          stat.confidenceInterval[1],
                          activeId === "surface-moisture" ? 3 : 2,
                        )}{" "}
                        <span>{result.unit}/década</span>
                      </strong>
                      <CircleHelp size={13} />
                    </button>
                    <div className="chart-heading">
                      <h4>La historia, año a año</h4>
                      <button
                        className="icon-button"
                        aria-label="Ampliar gráfica"
                        onClick={() => setModal("chart")}
                      >
                        <Expand size={15} />
                      </button>
                    </div>
                    <TrendChart result={result} />
                    <div className="result-actions">
                      <button
                        className="secondary-button"
                        onClick={() => openEvidence()}
                      >
                        <FileText size={14} />
                        Ver evidencia
                        <ArrowUpRight size={13} />
                      </button>
                      <button
                        className="download-button"
                        onClick={download}
                        aria-label="Descargar CSV del análisis visible"
                      >
                        <ArrowDownToLine size={15} />
                        CSV
                      </button>
                    </div>
                    <details className="method-preview">
                      <summary>
                        <ChevronRight size={13} />
                        Cómo leer este resultado
                      </summary>
                      <p>
                        {evidenceLabel(stat)} bajo los supuestos del ajuste.
                        La pendiente describe dirección y magnitud;
                        el intervalo describe incertidumbre. No explica causas.{" "}
                        {result.method.description}
                      </p>
                    </details>
                    <div className="chat-invitation">
                      <div className="chat-invitation-title">
                        <MessageCircle size={18} />
                        <h3>Pregunta sobre este análisis</h3>
                        <span>DATOS NASA</span>
                      </div>
                      <p>Entiende la señal. Revisa sus límites.</p>
                      <button
                        onClick={() => {
                          switchRight("chat");
                          send(suggestions[0]);
                        }}
                      >
                        {suggestions[0]}
                        <ArrowUpRight size={14} />
                      </button>
                      <button
                        className="chat-open"
                        onClick={() => switchRight("chat")}
                      >
                        Abrir conversación
                        <ArrowRight size={14} />
                      </button>
                      <span className="chat-disclaimer">
                        Explicaciones locales del resultado · sin Claude
                      </span>
                    </div>
                  </>
                ) : null}
              </>
            )}
          </div>
          <div className="result-footnote">
            <span className="tiny-square" />
            Prototipo independiente · Space Apps 2026
            <button
              onClick={() => setModal("about")}
              aria-label="Más información del prototipo"
            >
              <ExternalLink size={12} />
            </button>
          </div>
        </aside>
      </main>
      <footer className="app-footer">
        <span>
          <span className="cyan-dot" />
          Fuentes: NASA POWER · GPCP · MERRA-2
        </span>
        <span>
          Análisis regional exploratorio
          <span className="footer-tag">MX · caja noreste</span>
        </span>
      </footer>
      {modal === "chart" && analysis && result && (
        <Modal
          title="Serie temporal ampliada"
          wide
          onClose={() => setModal(null)}
        >
          <div className="expanded-context">
            <span className="demo-pill">Datos NASA</span>
            <h3>{activeVariable.name}</h3>
            <p>
              {analysis.region.name} · {analysis.selection.start}–
              {analysis.selection.end} · {result.unit}
            </p>
          </div>
          <TrendChart result={result} large />
          {stat && (
            <div className="expanded-stat">
              <strong>
                {signed(stat.slopePerDecade, 3)} {result.unit}/década
              </strong>
              <span>
                IC 95 %: {signed(stat.confidenceInterval[0], 3)} a{" "}
                {signed(stat.confidenceInterval[1], 3)} · {evidenceLabel(stat)}
              </span>
            </div>
          )}
          <div className="modal-actions">
            <button className="secondary-button" onClick={() => openEvidence()}>
              <FileText size={15} />
              Ver evidencia
            </button>
            <button className="secondary-button" onClick={download}>
              <ArrowDownToLine size={15} />
              Descargar CSV
            </button>
          </div>
        </Modal>
      )}
      {modal === "compare" && analysis && (
        <Modal
          title="Variables en el mismo periodo"
          wide
          onClose={() => setModal(null)}
        >
          <div className="expanded-context">
            <span className="demo-pill">Datos NASA</span>
            <h3>{analysis.region.name}</h3>
            <p>
              {analysis.selection.start}–{analysis.selection.end} · Mismo eje
              temporal, unidades y escalas verticales independientes.
            </p>
          </div>
          <div className="comparison-charts">
            {analysis.results.map((r) => (
              <section key={r.variableId}>
                <h4 style={{ color: getVariable(r.variableId).color }}>
                  {getVariable(r.variableId).name} <span>{r.unit}</span>
                </h4>
                {r.status === "no-data" ? (
                  <p>Sin datos para esta combinación.</p>
                ) : (
                  <TrendChart result={r} comparison />
                )}
              </section>
            ))}
          </div>
          <p className="comparison-note">
            Las variables se muestran en paralelo. No se suman ni se calcula
            aquí una correlación, un índice combinado o atribución causal. Los
            dos RX5day tienen definiciones temporales y fuentes distintas.
          </p>
        </Modal>
      )}
      {modal === "evidence" && analysis && result && (
        <Modal
          title="Evidencia del análisis"
          wide
          onClose={() => setModal(null)}
        >
          <Evidence
            analysis={analysis}
            variableId={activeId}
            focus={evidenceFocus}
            onDownload={download}
          />
        </Modal>
      )}
      {modal === "about" && (
        <Modal
          title="Un laboratorio en construcción"
          onClose={() => setModal(null)}
        >
          <div className="about-content">
            <span className="demo-pill">
              Prototipo de interfaz · 14 nov 2026
            </span>
            <p>
              Trend Detectives es un proyecto independiente para NASA Space Apps
              Challenge 2026. Esta interfaz no implica respaldo oficial de NASA.
            </p>
            <h3>Qué estás viendo</h3>
            <p>
              Series NASA procesadas para una caja del noreste de México. La
              gráfica muestra valores anuales; las pendientes e intervalos se
              calculan según el método de cada variable. Las respuestas son
              explicaciones locales, sin llamadas a Claude.
            </p>
            <h3>El mapa sí tiene geografía real</h3>
            <p>
              Cartografía de{" "}
              <a
                href="https://www.naturalearthdata.com/about/terms-of-use/"
                target="_blank"
                rel="noreferrer"
              >
                Natural Earth (dominio público)
              </a>
              . Sólo una caja tiene datos climáticos; no representa fronteras
              administrativas ni cobertura nacional.
            </p>
            <h3>Lo que sigue</h3>
            <p>
              Añadir más regiones con agregación espacial validada y más
              variables oficiales de NASA.
            </p>
          </div>
        </Modal>
      )}
    </div>
  );
}
function ChatView({
  messages,
  busy,
  error,
  disabled,
  onSend,
  onEvidence,
  onRetry,
  context,
}: {
  messages: ChatMessage[];
  busy?: boolean;
  error?: string;
  disabled?: boolean;
  onSend: (q: string) => void;
  onEvidence: (f?: string) => void;
  onRetry: () => void;
  context: string;
}) {
  const [input, setInput] = useState("");
  function submit(e: React.SubmitEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!input.trim() || busy) return;
    onSend(input.trim());
    setInput("");
  }
  return (
    <div className="chat-view">
      <div className="chat-title">
        <MessageCircle size={20} />
        <h3>Pregunta sobre este análisis</h3>
      </div>
      <p className="chat-context-label">Contexto: {context}</p>
      <div className="chat-notice">
        <span className="demo-pill">Explicación local</span>
        <p>
          Respuestas deterministas basadas en la pendiente, el intervalo y las
          limitaciones del análisis visible. No hay un modelo de IA conectado.
        </p>
      </div>
      {disabled ? (
        <div className="error-box">
          No hay una serie disponible para conversar sobre esta combinación.
        </div>
      ) : (
        <>
          <div className="suggested-questions">
            {suggestions.map((q) => (
              <button disabled={busy} key={q} onClick={() => onSend(q)}>
                {q}
                <ArrowUpRight size={13} />
              </button>
            ))}
          </div>
          <div
            className="messages"
            aria-live="polite"
            aria-relevant="additions text"
          >
            {messages.map((m) => (
              <div className={`message ${m.role}`} key={m.id}>
                <span className="message-role">
                  {m.role === "user" ? "TÚ" : "EXPLICACIÓN LOCAL"}
                </span>
                <p>{m.text}</p>
                {m.evidence && (
                  <button onClick={() => onEvidence(m.evidence)}>
                    <FileText size={12} />
                    Ver evidencia
                    <ArrowUpRight size={12} />
                  </button>
                )}
              </div>
            ))}
            {busy && (
              <div className="chat-loading">
                <LoaderCircle className="spin" size={14} />
                Preparando explicación…
              </div>
            )}
          </div>
          {error && (
            <div className="error-box" role="alert">
              <p>{error}</p>
              <button className="text-button" onClick={onRetry}>
                Reintentar respuesta
                <RotateCcw size={13} />
              </button>
            </div>
          )}
        </>
      )}
      <form className="chat-composer" onSubmit={submit}>
        <label className="sr-only" htmlFor="chat-input">
          Tu pregunta sobre este análisis
        </label>
        <textarea
          id="chat-input"
          rows={2}
          value={input}
          maxLength={1500}
          disabled={busy || disabled}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              e.currentTarget.form?.requestSubmit();
            }
          }}
          placeholder="¿Qué te gustaría entender?"
        />
        <div>
          <span>Enter para enviar · Shift + Enter para salto</span>
          <button
            type="submit"
            className="send-button"
            aria-label="Enviar pregunta"
            disabled={busy || disabled || !input.trim()}
          >
            <Send size={15} />
          </button>
        </div>
      </form>
      <p className="chat-limit">
        Las respuestas pertenecen sólo a este análisis y esta variable. No son
        asesoría científica validada.
      </p>
    </div>
  );
}
function Evidence({
  analysis,
  variableId,
  focus,
  onDownload,
}: {
  analysis: Analysis;
  variableId: VariableId;
  focus: string;
  onDownload: () => void;
}) {
  const r = analysis.results.find((d) => d.variableId === variableId)!,
    v = getVariable(variableId),
    s = r.statistics;
  return (
    <div className="evidence-content">
      <div className="evidence-intro">
        <span className="demo-pill">Datos NASA</span>
        <p>
          Estos resultados provienen de datos NASA procesados para una caja de
          prueba. Son exploratorios y no permiten atribuir causas.
        </p>
      </div>
      <dl className="evidence-grid">
        <div>
          <dt>Variable y unidad</dt>
          <dd>
            {v.name} · {v.unit}
          </dd>
        </div>
        <div>
          <dt>Región y extensión</dt>
          <dd>
            {analysis.region.name}
            <small>
              {analysis.region.extent} · bbox [{analysis.region.bbox.join(", ")}
              ]
            </small>
          </dd>
        </div>
        <div>
          <dt>Periodo y frecuencia</dt>
          <dd>
            {analysis.selection.start}–{analysis.selection.end} · anual
            <small>
              {s?.sampleSize ?? 0} {r.sampleUnit} en el modelo · {r.series.length} años
              en la tabla · {r.series.filter((d) => d.value === null).length}{" "}
              faltantes anuales
            </small>
            <small>{r.annualLabel}</small>
          </dd>
        </div>
        <div>
          <dt>Fuente utilizada</dt>
          <dd>
            {r.source}
            <small>
              Procesamiento local · actualizado {analysis.provenance.updatedAt}
            </small>
          </dd>
        </div>
        <div>
          <dt>Producto integrado</dt>
          <dd>{v.plannedSource}</dd>
        </div>
        <div>
          <dt>Resolución</dt>
          <dd>{analysis.provenance.resolution}</dd>
        </div>
      </dl>
      {s && (
        <div
          className={`evidence-statistics ${focus === "slope" || focus === "interval" ? "highlighted" : ""}`}
        >
          <div>
            <span>Pendiente estimada</span>
            <strong>
              {signed(s.slopePerDecade, 4)} {v.unit}/década
            </strong>
          </div>
          <div>
            <span>Intervalo bilateral del 95 %</span>
            <strong>
              {signed(s.confidenceInterval[0], 4)} a{" "}
              {signed(s.confidenceInterval[1], 4)} {v.unit}/década
            </strong>
          </div>
          <p>
            {evidenceLabel(s)} bajo este modelo. Un intervalo que cruza
            cero no confirma la dirección y tampoco demuestra ausencia de
            cambio.
          </p>
        </div>
      )}
      <div
        className={`evidence-method ${focus === "method" ? "highlighted" : ""}`}
      >
        <h3>Método y límites</h3>
        <p>{r.method.description}</p>
        <ul>
          {[...r.limitations, ...analysis.provenance.limitations].map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      </div>
      <div className="evidence-table-heading">
        <h3>Datos que alimentan esta gráfica</h3>
        <button
          className="secondary-button"
          onClick={onDownload}
          disabled={!r.series.length}
        >
          <ArrowDownToLine size={14} />
          Descargar CSV
        </button>
      </div>
      <div className="evidence-table">
        <table>
          <caption className="sr-only">
            Resumen anual de la serie NASA y guía de tendencia
          </caption>
          <thead>
            <tr>
              <th>Año</th>
              <th>Serie ({v.unit})</th>
              <th>Guía de tendencia ({v.unit})</th>
            </tr>
          </thead>
          <tbody>
            {r.series.map((d, i) => (
              <tr key={d.year}>
                <td>{d.year}</td>
                <td>
                  {d.value === null ? "Sin dato" : formatNumber(d.value, 4)}
                </td>
                <td>
                  {r.trend[i]?.value !== undefined
                    ? formatNumber(r.trend[i].value!, 4)
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!r.series.length && (
          <p className="no-data-text">Sin datos para esta combinación.</p>
        )}
      </div>
      <p className="analysis-id">ID estable: {analysis.id}</p>
    </div>
  );
}

function VariableChoice({
  variable: v,
  selected,
  onToggle,
}: {
  variable: Variable;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <label
      className={`variable-option ${selected ? "is-selected" : ""} ${!v.available ? "unavailable" : ""}`}
    >
      <input
        type="checkbox"
        checked={selected}
        disabled={!v.available}
        onChange={onToggle}
      />
      <div className="variable-top">
        <span className="custom-check">{selected && <Check size={12} />}</span>
        <span className="variable-name">{v.name}</span>
      </div>
      <p>{v.description}</p>
      <div className="variable-meta">
        <span>{v.unit}</span>
        <span>
          {v.available ? "Datos disponibles" : "Pendiente de integrar"}
        </span>
      </div>
    </label>
  );
}
