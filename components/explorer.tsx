"use client";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronDown,
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
  SlidersHorizontal,
  RotateCcw,
  Send,
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
import { getSignificance } from "@/lib/significance";
import { getSourceLinks } from "@/lib/source-links";
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
  claudeChatAdapter,
  toChatContext,
} from "@/lib/adapters";
import { createMapLayer, getMapLimit } from "@/lib/map-layer";
import { RegionMap } from "./region-map";
import { TrendChart } from "./chart";
const ForecastPanel = dynamic(
  () => import("./forecast-panel").then((m) => m.ForecastPanel),
  {
    loading: () => <p className="experiment-context">Cargando experimento…</p>,
  },
);
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
const families: Family[] = ["Calor", "Lluvia"];
const initialSelection: Selection = {
  ...realDefaultSelection,
  variables: ["temperature"],
};
const FamilyIcon = { Calor: Thermometer, Lluvia: Droplets, Suelo: Leaf };
const suggestions = [
  "¿Qué cambió aquí?",
  "¿Qué tan clara es la evidencia?",
  "¿Qué debo tomar en cuenta?",
];
const availableYears = Array.from(
  { length: lastDataYear - firstDataYear + 1 },
  (_, i) => firstDataYear + i,
);
type MobileTab = "explore" | "results" | "chat";
export function Explorer() {
  const [draft, setDraft] = useState<Selection>(initialSelection);
  const [analysis, setAnalysis] = useState<Analysis | null>(() =>
    createRealAnalysis(initialSelection),
  );
  const [history, setHistory] = useState<Analysis[]>(() => [
    createRealAnalysis(initialSelection),
  ]);
  const [activeId, setActiveId] = useState<VariableId>("temperature");
  const [mapView, setMapView] = useState<"regional" | "globe">("regional");
  const [family, setFamily] = useState<Family>("Calor");
  const [mobileTab, setMobileTab] = useState<MobileTab>("results");
  const [rightTab, setRightTab] = useState<"results" | "chat">("results");
  const [loading, setLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState("");
  const [selectionMessage, setSelectionMessage] = useState("");
  const [modal, setModal] = useState<
    "evidence" | "chart" | "compare" | "forecast" | "about" | null
  >(null);
  const [evidenceFocus, setEvidenceFocus] = useState("");
  const [threads, setThreads] = useState<Record<string, ChatMessage[]>>({});
  const [chatBusy, setChatBusy] = useState<Record<string, boolean>>({});
  const [chatErrors, setChatErrors] = useState<Record<string, string>>({});
  const [claudeConnection, setClaudeConnection] = useState<
    "checking" | "configured" | "unconfigured" | "unavailable"
  >("checking");
  const [claudeModel, setClaudeModel] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/chat", { signal: controller.signal, cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Estado no disponible");
        const data = await response.json();
        setClaudeConnection(data.configured ? "configured" : "unconfigured");
        setClaudeModel(typeof data.model === "string" ? data.model : "");
      })
      .catch(() => {
        if (!controller.signal.aborted) setClaudeConnection("unavailable");
      });
    return () => controller.abort();
  }, []);
  const resultRef = useRef<HTMLDivElement>(null);
  const studyRef = useRef<HTMLDivElement>(null);
  const settingsRef = useRef<HTMLDetailsElement>(null);
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
    if (!regions.some((candidate) => candidate.id === id)) return;
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
    if (
      id === annualIndexId &&
      !draft.variables.includes(id) &&
      draft.end - draft.start + 1 < minimumAnnualIndexYears
    ) {
      setSelectionMessage(
        "RX5day anual de POWER requiere al menos 20 años. Amplía el periodo para seleccionarlo.",
      );
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
      if (controller.signal.aborted) return;
      setAnalysis(next);
      setHistory((h) => [...h.filter((a) => a.id !== next.id), next]);
      const newlyAdded = snapshot.variables.find(
        (id) => !analysis?.selection.variables.includes(id),
      );
      setActiveId(
        newlyAdded ??
          (snapshot.variables.includes(activeId)
            ? activeId
            : snapshot.variables[0]),
      );
      setRightTab("results");
      setMobileTab("results");
      if (settingsRef.current) settingsRef.current.open = false;
      studyRef.current?.scrollTo({ top: 0 });
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
      const previous =
        retry && messages.at(-1)?.role === "user"
          ? messages.slice(0, -1)
          : messages;
      const response = await claudeChatAdapter.reply(
        question,
        context,
        undefined,
        previous,
      );
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
    resultRef.current?.scrollTo({ top: 0 });
    scrollToSection();
  };
  const mapLayer = createMapLayer(history, analysis, activeId);
  const mapLimit = mapLayer[0]?.limit ?? getMapLimit(activeId);
  const stat = result?.statistics;
  const significance = getSignificance(result?.evidence);
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
          Preguntar
        </button>
      </div>
      <main className="workspace">
        <aside
          className={`study-panel ${mobileTab === "explore" ? "mobile-visible" : ""}`}
          aria-label="Elegir lugar y datos"
        >
          <div className="study-scroll" ref={studyRef}>
            <section className="earth-panel" aria-label="Área de estudio">
              <h1>Área de estudio</h1>
              <div className="region-selector" ref={regionRef}>
                <div className="region-selector-label">
                  <MapPin size={14} />
                  <label htmlFor="region">Lugar de estudio</label>
                  <span>{regions.length} áreas disponibles</span>
                </div>
                <div className="region-select-row">
                  <span className="country-code">{region.countryCode}</span>
                  <select
                    id="region"
                    value={draft.regionId}
                    onChange={(e) => chooseRegion(e.target.value)}
                  >
                    {regions.map((r) => (
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
              <details className="selection-settings" ref={settingsRef}>
                <summary>
                  <SlidersHorizontal size={16} />
                  <span>
                    Cambiar datos
                    <small>
                      {draft.variables.length === 1
                        ? getVariable(draft.variables[0]).short
                        : `${draft.variables.length} variables`}{" "}
                      · {draft.start}–{draft.end}
                    </small>
                  </span>
                  <ChevronDown size={16} />
                </summary>
                <div className="filters-panel">
                  <div className="filter-scroll">
                    <div className="section-title">
                      <h2>Variables ambientales</h2>
                      <span>{draft.variables.length}/3</span>
                    </div>
                    <div
                      className="family-tabs"
                      aria-label="Familia de variables"
                    >
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
                            {f === "Calor" ? "Temperatura" : f}
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
                            <span
                              style={{ background: getVariable(id).color }}
                            />
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
                              setDraft((d) => ({
                                ...d,
                                start: Number(e.target.value),
                              }));
                              setSelectionMessage("");
                            }}
                          >
                            {availableYears.map((year) => (
                              <option
                                key={year}
                                value={year}
                                disabled={
                                  year >
                                  draft.end -
                                    minimumYearsForVariables(draft.variables) +
                                    1
                                }
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
                              setDraft((d) => ({
                                ...d,
                                end: Number(e.target.value),
                              }));
                              setSelectionMessage("");
                            }}
                          >
                            {availableYears.map((year) => (
                              <option
                                key={year}
                                value={year}
                                disabled={
                                  year <
                                  draft.start +
                                    minimumYearsForVariables(draft.variables) -
                                    1
                                }
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
                        {draft.end >= draft.start
                          ? draft.end - draft.start + 1
                          : 0}{" "}
                        años · mínimo{" "}
                        {minimumYearsForVariables(draft.variables)} · datos{" "}
                        {firstDataYear}–{lastDataYear}
                      </p>
                    </div>
                  </div>
                </div>
              </details>
              {mapView === "regional" ? (
                <RegionMap
                  region={region}
                  value={
                    dirty
                      ? undefined
                      : mapLayer.find((entry) => entry.regionId === region.id)
                  }
                  variable={activeVariable}
                />
              ) : (
                <Globe
                  regionId={draft.regionId}
                  onSelect={chooseRegion}
                  layer={mapLayer}
                />
              )}
              <p className="area-scope">
                Sólo se analiza el recuadro; los estados sirven para ubicarlo.
              </p>
              <details className="map-scale-details">
                <summary>
                  Ver escala de colores <ChevronDown size={14} />
                </summary>
                <div className="map-legend" aria-label="Leyenda del mapa">
                  <div>
                    <span>Cambio por década · {activeVariable.short}</span>
                    <strong>{activeVariable.unit}/década</strong>
                  </div>
                  <div className="map-color-ramp" />
                  <div className="map-scale-labels">
                    <span>
                      {signed(
                        -mapLimit,
                        activeId === "surface-moisture" ? 3 : 1,
                      )}
                    </span>
                    <span>0</span>
                    <span>
                      {signed(
                        mapLimit,
                        activeId === "surface-moisture" ? 3 : 1,
                      )}
                    </span>
                  </div>
                  <p>
                    {analysis
                      ? `${analysis.selection.start}–${analysis.selection.end} · ${mapLayer.filter((v) => v.state === "analyzed").length}/${regions.length} cajas analizadas`
                      : "Analiza una selección para colorear su área."}
                    <span>Datos NASA</span>
                  </p>
                  <div className="map-certainty">
                    <i />
                    Sin analizar / sin datos <span className="dash-swatch" />
                    Evidencia no concluyente
                  </div>
                </div>
              </details>
            </section>
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
                  Calculando evidencia…
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
            <span className="local-note">Datos NASA · 1992–2024</span>
          </div>
        </aside>
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
              Resultado
            </button>
            <button
              className={rightTab === "chat" ? "active" : ""}
              onClick={() => switchRight("chat")}
            >
              <MessageCircle size={15} />
              Preguntar a la IA
              {messages.length > 0 && <span>{messages.length}</span>}
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
                <h2>Explora un cambio ambiental.</h2>
                <p>
                  Elige una región, al menos una variable y un periodo. Después,
                  pulsa Analizar.
                </p>
                <button
                  className="text-button"
                  onClick={() => {
                    setMobileTab("explore");
                    if (settingsRef.current) settingsRef.current.open = true;
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
                {analysis.results.length > 1 && (
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
                          style={{
                            background: getVariable(r.variableId).color,
                          }}
                        />
                        {getVariable(r.variableId).short}
                      </button>
                    ))}
                  </div>
                )}
                {rightTab === "chat" ? (
                  <ChatView
                    key={contextKey}
                    messages={messages}
                    busy={chatBusy[contextKey]}
                    error={chatErrors[contextKey]}
                    disabled={
                      !result?.statistics || claudeConnection !== "configured"
                    }
                    connection={claudeConnection}
                    model={claudeModel}
                    onSend={send}
                    onEvidence={openEvidence}
                    onRetry={() => {
                      const last = messages.findLast((m) => m.role === "user");
                      if (last) send(last.text, true);
                    }}
                    context={`${activeVariable.name} · ${analysis.region.name} · ${analysis.selection.start}–${analysis.selection.end}`}
                  />
                ) : result && result.status !== "ready" ? (
                  <div className="empty-state no-data">
                    <Layers3 size={35} />
                    <h3>
                      {result.status === "not-evaluable"
                        ? "No se pudo validar este ajuste."
                        : "Esta combinación aún no tiene datos."}
                    </h3>
                    <p>
                      {result.status === "not-evaluable"
                        ? result.evidence?.reasons.join(" ")
                        : "Esta variable todavía no tiene una serie procesada para la caja seleccionada."}
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
                    <section
                      className="reading-summary"
                      aria-label="Cambio estimado y evidencia"
                    >
                      <h3>{activeVariable.name}</h3>
                      <div className="reading-metrics">
                        <div className="change-value">
                          <span>Cambio cada 10 años</span>
                          <strong style={{ color: activeVariable.color }}>
                            {signed(
                              stat.slopePerDecade,
                              activeId === "surface-moisture" ? 3 : 2,
                            )}{" "}
                            <small>{result.unit}</small>
                          </strong>
                        </div>
                        <div className="change-evidence">
                          <span>¿Es significativo?</span>
                          <strong
                            className={
                              significance.significant
                                ? "is-significant"
                                : "is-inconclusive"
                            }
                          >
                            {significance.significant === true
                              ? "Sí"
                              : significance.significant === false
                                ? "No"
                                : "Sin evaluar"}
                          </strong>
                          <p>
                            {stat.evidence?.status === "pending"
                              ? "Un posible salto en la serie aún necesita comprobarse."
                              : stat.evidence?.status === "sensitive"
                                ? "La estimación cambia al elegir otros años."
                                : significance.significant === false
                                  ? "La evidencia no alcanza para confirmar este cambio."
                                  : "El cambio supera la prueba estadística."}
                          </p>
                        </div>
                      </div>
                    </section>
                    <div className="chart-heading">
                      <h4>Evolución de los datos</h4>
                      <button
                        className="icon-button"
                        aria-label="Ampliar gráfica"
                        onClick={() => setModal("chart")}
                      >
                        <Expand size={16} />
                      </button>
                    </div>
                    <TrendChart result={result} overview />
                    <div className="reading-actions">
                      <button
                        className="secondary-button"
                        onClick={() => openEvidence("interval")}
                      >
                        <FileText size={15} /> Datos y método
                      </button>
                      <button
                        className="text-button"
                        onClick={() => switchRight("chat")}
                      >
                        <MessageCircle size={15} /> Explicar este resultado
                      </button>
                      <SourceLinks variableId={activeId} />
                    </div>
                    <details className="advanced-tools">
                      <summary>
                        Herramientas avanzadas <ChevronDown size={15} />
                      </summary>
                      <div>
                        <button onClick={() => setModal("forecast")}>
                          Predicción experimental <ArrowUpRight size={14} />
                        </button>
                        {analysis.results.length > 1 && (
                          <button onClick={() => setModal("compare")}>
                            Comparar {analysis.results.length} variables{" "}
                            <Layers3 size={14} />
                          </button>
                        )}
                        <button
                          onClick={download}
                          aria-label="Descargar CSV del análisis visible"
                        >
                          Descargar datos CSV <ArrowDownToLine size={14} />
                        </button>
                        <button
                          onClick={() => {
                            setMapView((v) =>
                              v === "regional" ? "globe" : "regional",
                            );
                            setMobileTab("explore");
                            scrollToSection();
                          }}
                        >
                          {mapView === "regional"
                            ? "Explorar mapa en 3D"
                            : "Volver al mapa regional"}{" "}
                          <Orbit size={14} />
                        </button>
                        <button
                          onClick={() => {
                            requestRef.current?.abort();
                            setLoading(false);
                            setAnalysis(null);
                          }}
                        >
                          Limpiar resultado <X size={14} />
                        </button>
                      </div>
                    </details>
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
          <span className="footer-tag">
            MX · {analysis?.region.name ?? region.name}
          </span>
        </span>
      </footer>
      {modal === "chart" && analysis && result && (
        <Modal
          title="Evolución de los datos"
          wide
          onClose={() => setModal(null)}
        >
          <div className="expanded-context">
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
                {significance.significant
                  ? "Significativo"
                  : "No significativo"}
                {stat.evidence?.status === "pending"
                  ? " · Posible salto por comprobar"
                  : stat.evidence?.status === "sensitive"
                    ? " · Depende del periodo"
                    : ""}
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
      {modal === "forecast" && analysis && result && (
        <Modal
          title="Predicción experimental"
          wide
          onClose={() => setModal(null)}
        >
          <h3 className="experiment-heading">{activeVariable.name}</h3>
          <p className="experiment-context">
            {analysis.region.name}. Experimento con datos hasta 2024; no es un
            pronóstico actual.
          </p>
          <ForecastPanel
            regionId={analysis.region.id}
            variableId={activeId}
            start={analysis.selection.start}
            end={analysis.selection.end}
          />
        </Modal>
      )}
      {modal === "compare" && analysis && (
        <Modal
          title="Variables en el mismo periodo"
          wide
          onClose={() => setModal(null)}
        >
          <div className="expanded-context">
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
        <Modal title="Datos y método" wide onClose={() => setModal(null)}>
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
          title="Acerca de Trend Detectives"
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
            <h3>Para quién está pensado</h3>
            <p>
              Estudiantes, docentes y personas que quieren explorar datos
              ambientales sin empezar por un programa estadístico. Los datos y
              el método siguen disponibles para quienes quieran profundizar.
            </p>
            <h3>Qué estás viendo</h3>
            <p>
              Series NASA procesadas para tres cajas de México. La gráfica
              muestra valores anuales; las pendientes e intervalos se calculan
              según el método de cada variable. Las respuestas son explicaciones
              con Claude sobre la caja, el periodo y la variable visibles. La
              significancia la calcula el motor estadístico; Claude explica sus
              resultados y límites.
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
              . Las cajas tienen datos climáticos; no representan fronteras
              administrativas ni cobertura nacional.
            </p>
            <h3>Lo que sigue</h3>
            <p>
              Comparar regiones con control de incertidumbre y añadir más
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
  connection,
  model,
}: {
  messages: ChatMessage[];
  busy?: boolean;
  error?: string;
  disabled?: boolean;
  onSend: (q: string) => void;
  onEvidence: (f?: string) => void;
  onRetry: () => void;
  context: string;
  connection: "checking" | "configured" | "unconfigured" | "unavailable";
  model: string;
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
        <h3>Entiende este resultado</h3>
      </div>
      <p className="chat-context-label">Contexto: {context}</p>
      <div className="chat-notice">
        <span className="demo-pill">Claude</span>
        <p>
          {connection === "checking"
            ? "Comprobando disponibilidad…"
            : connection === "unconfigured"
              ? "Claude necesita configurarse para responder."
              : connection === "unavailable"
                ? "Claude no está disponible. Recarga para reintentar."
                : "Pregunta qué cambió o qué significa el resultado."}
        </p>
        {connection === "configured" && (
          <details className="chat-privacy">
            <summary>Datos compartidos</summary>
            <small>
              Preguntas y datos de esta selección se envían a Anthropic. Modelo:{" "}
              {model}.
            </small>
          </details>
        )}
      </div>
      {disabled ? (
        <div className="error-box">
          {connection !== "configured"
            ? "La conversación estará disponible cuando Claude esté configurado y responda el servidor."
            : "No hay un ajuste válido para conversar sobre esta combinación."}
        </div>
      ) : (
        <>
          {messages.length === 0 && (
            <div className="suggested-questions">
              {suggestions.map((q) => (
                <button disabled={busy} key={q} onClick={() => onSend(q)}>
                  {q}
                  <ArrowUpRight size={13} />
                </button>
              ))}
            </div>
          )}
          <div
            className="messages"
            aria-live="polite"
            aria-relevant="additions text"
          >
            {messages.map((m) => (
              <div className={`message ${m.role}`} key={m.id}>
                <span className="message-role">
                  {m.role === "user"
                    ? "TÚ"
                    : m.provider === "claude"
                      ? "CLAUDE"
                      : "EXPLICACIÓN LOCAL"}
                </span>
                {m.provider === "claude" &&
                m.verifiedSummary &&
                m.explanation ? (
                  <>
                    <ExplanationText text={m.explanation} />
                    <details className="verified-chat-summary">
                      <summary>Ver resultado calculado</summary>
                      <p>{m.verifiedSummary}</p>
                    </details>
                  </>
                ) : (
                  <p>{m.text}</p>
                )}
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
                Claude está preparando la explicación…
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
        La IA explica esta selección. Puedes verificarla en Datos y método.
      </p>
    </div>
  );
}
function ExplanationText({ text }: { text: string }) {
  // React escapes all content; support emphasis without accepting generated HTML.
  return text
    .split(/\n{2,}/)
    .map((paragraph, index) => (
      <p key={index}>
        {paragraph
          .split(/(\*\*[^*\n]+\*\*)/g)
          .map((part, i) =>
            part.startsWith("**") && part.endsWith("**") ? (
              <strong key={i}>{part.slice(2, -2)}</strong>
            ) : (
              part
            ),
          )}
      </p>
    ));
}
function SourceLinks({
  variableId,
  includeEnso = true,
}: {
  variableId: VariableId;
  includeEnso?: boolean;
}) {
  const links = getSourceLinks(variableId).slice(0, includeEnso ? 2 : 1);
  if (!links.length) return null;
  return (
    <div className="result-source-links" aria-label="Fuentes del análisis">
      <span>Fuentes</span>
      {links.map((link) => (
        <a
          key={link.href}
          href={link.href}
          title={link.description}
          target="_blank"
          rel="noreferrer"
        >
          {link.label}
          <ExternalLink size={11} />
        </a>
      ))}
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
          Estos resultados provienen de datos NASA procesados para{" "}
          {analysis.region.name}. Son exploratorios y no permiten atribuir
          causas.
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
            {analysis.selection.start}–{analysis.selection.end} ·{" "}
            {r.sampleUnit === "meses"
              ? "modelo mensual; gráfica anual"
              : "modelo y gráfica anuales"}
            <small>
              {s?.sampleSize ?? 0} {r.sampleUnit} en el modelo ·{" "}
              {r.series.length} años en la tabla ·{" "}
              {r.series.filter((d) => d.value === null).length} faltantes
              anuales
            </small>
            <small>{r.annualLabel}</small>
          </dd>
        </div>
        <div>
          <dt>Fuente utilizada</dt>
          <dd>
            {r.source}
            <SourceLinks variableId={variableId} />
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
            <span>Intervalo individual del 95 % · bootstrap-t AR</span>
            <strong>
              {signed(s.confidenceInterval[0], 4)} a{" "}
              {signed(s.confidenceInterval[1], 4)} {v.unit}/década
            </strong>
          </div>
          <p>
            {evidenceLabel(s)} bajo este modelo. Un intervalo que cruza cero no
            confirma la dirección y tampoco demuestra ausencia de cambio.
          </p>
          <p>
            <strong>{getSignificance(r.evidence).label}.</strong>{" "}
            {getSignificance(r.evidence).description}
          </p>
          {s.evidence && (
            <>
              <div>
                <span>p bootstrap-t / p de Holm</span>
                <strong>
                  {formatNumber(s.evidence.pValue!, 4)} /{" "}
                  {formatNumber(s.evidence.pAdjusted!, 4)}
                </strong>
              </div>
              <p>
                Familia de {s.evidence.familySize} pruebas, independiente de las
                variables visibles. El IC individual puede excluir cero aunque
                la evidencia tras Holm sea inconclusa.
              </p>
              {s.evidence.baseline && (
                <div>
                  <span>Pendiente sin ENSO / con ENSO</span>
                  <strong>
                    {signed(s.evidence.baseline.slopePerDecade, 4)} /{" "}
                    {signed(s.slopePerDecade, 4)} {r.unit}/década
                  </strong>
                </div>
              )}
              {s.evidence.diagnostics && (
                <p>
                  Autocorrelación residual (un rezago):{" "}
                  {formatNumber(s.evidence.diagnostics.residualAcf1, 3)}. AR(
                  {s.evidence.arOrder});{" "}
                  {analysis.provenance.audit?.replicates.toLocaleString(
                    "es-MX",
                  )}{" "}
                  réplicas.{" "}
                  {s.evidence.diagnostics.steps.length > 0
                    ? `Escalones exploratorios compatibles: ${s.evidence.diagnostics.steps.map((d) => d.date).join(", ")}; requieren contraste, no prueban causas.`
                    : "Sin escalón compatible en las fechas exploratorias evaluadas; no descarta otros cambios de nivel."}
                </p>
              )}
              {s.evidence.diagnostics && (
                <p>
                  IC diagnóstico por bloques:{" "}
                  {signed(s.evidence.diagnostics.blockInterval[0], 4)} a{" "}
                  {signed(s.evidence.diagnostics.blockInterval[1], 4)} {r.unit}
                  /década. Sensibilidad HAC:{" "}
                  {s.evidence.diagnostics.hacSensitivity
                    .map(
                      (h) =>
                        `${h.lags} rezagos [${signed(h.interval[0], 3)}, ${signed(h.interval[1], 3)}]`,
                    )
                    .join("; ")}
                  .
                </p>
              )}
            </>
          )}
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
