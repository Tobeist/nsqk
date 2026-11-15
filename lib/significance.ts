import type { TrendEvidence } from "./trend-evidence";

// Significance is a family-adjusted hypothesis test, separate from robustness or causality.
export function getSignificance(evidence?: TrendEvidence | null) {
  const p = evidence?.pAdjusted;
  if (!evidence || evidence.status === "not-evaluable" || p === undefined || !Number.isFinite(p) || p < 0 || p > 1) {
    return { significant: null, label: "Significancia no evaluable", description: "Falta una prueba ajustada válida para esta caja y periodo." };
  }
  const significant = p < .05;
  return {
    significant,
    label: significant ? "Estadísticamente significativo" : "No estadísticamente significativo",
    description: significant
      ? "p de Holm < 0.05. La significancia no establece causas ni garantiza una tendencia estable; revisa las comprobaciones."
      : "p de Holm ≥ 0.05. La evidencia no alcanza el umbral; esto no demuestra ausencia de cambio.",
  };
}
