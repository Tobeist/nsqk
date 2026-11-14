import type { Statistics } from "./contracts";

export function evidenceLabel(s: Statistics) {
  const [lo, hi] = s.confidenceInterval;
  return lo > 0 ? "Evidencia de aumento" : hi < 0 ? "Evidencia de disminución" : "Evidencia inconclusa";
}
export const formatNumber = (value: number, digits = 2) =>
  value.toLocaleString("es-MX", { minimumFractionDigits: digits, maximumFractionDigits: digits });
export const signed = (value: number, digits = 2) =>
  `${value > 0 ? "+" : ""}${formatNumber(value, digits)}`;
