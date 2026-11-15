import type { Statistics } from "./contracts";

export function evidenceLabel(s: Statistics) {
  if (s.evidence) {
    switch (s.evidence.status) {
      case "inconclusive": return "Evidencia inconclusa";
      case "pending": return "Pendiente de contraste";
      case "sensitive": return "Sensible al periodo";
      case "not-evaluable": return "No evaluable";
    }
  }
  const [lo, hi] = s.confidenceInterval;
  return lo > 0 ? "Evidencia de aumento" : hi < 0 ? "Evidencia de disminución" : "Evidencia inconclusa";
}
export function uncertainEvidence(s: Statistics) {
  return s.evidence ? s.evidence.status !== "consistent" : s.confidenceInterval[0] <= 0 && s.confidenceInterval[1] >= 0;
}
export const formatNumber = (value: number, digits = 2) =>
  value.toLocaleString("es-MX", { minimumFractionDigits: digits, maximumFractionDigits: digits });
export const signed = (value: number, digits = 2) =>
  `${value > 0 ? "+" : ""}${formatNumber(value, digits)}`;
