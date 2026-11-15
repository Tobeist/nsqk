import finalStatus from "../analysis/results/final_status.json";
import type { VariableId } from "./catalog";
import type { Selection } from "./contracts";

export const auditReportUrl =
  "https://github.com/Tobeist/nsqk/blob/main/docs/INFORME_TENDENCIAS.md";

export type AuditStatus = {
  status: string;
  estimate: number;
  ciLow: number;
  ciHigh: number;
  pHolm: number;
  note: string;
  unit: string;
  model: string;
};

// The published audit covers only this box and the complete 1992–2024 window.
// Its conclusions cannot be transferred to another region or selected window.
export function getAuditStatus(
  selection: Selection,
  variableId: VariableId,
): AuditStatus | null {
  if (selection.regionId !== "mx-northeast" ||
      selection.start !== 1992 || selection.end !== 2024) return null;
  const row = finalStatus.find((item) => item.variable_id === variableId);
  if (!row || row.estimate === null || row.ci_low === null ||
      row.ci_high === null || row.p_holm === null) return null;
  return {
    status: row.status,
    estimate: row.estimate,
    ciLow: row.ci_low,
    ciHigh: row.ci_high,
    pHolm: row.p_holm,
    note: row.note ?? "",
    unit: row.unit,
    model: variableId === "rain5-power-annual"
      ? "Índice anual · bootstrap-t con criba AR y ajuste de Holm"
      : "Calendario + ENSO · bootstrap-t con criba AR y ajuste de Holm",
  };
}

export function auditStatusLabel(status: string) {
  return status === "inconcluso" ? "Inconcluso" :
    status === "pendiente" ? "Pendiente de comprobación" :
    status === "sustentado" ? "Sustentado" :
    status === "sensible" ? "Sensible a decisiones" : "No evaluable";
}

export function auditStatusExplanation(status: string) {
  return status === "inconcluso"
    ? "No supera los criterios finales de la auditoría."
    : status === "pendiente"
      ? "Requiere una comprobación independiente antes de presentarse como hallazgo."
      : status === "sustentado"
        ? "Supera los criterios definidos para esta auditoría."
        : status === "sensible"
          ? "La conclusión depende de decisiones del análisis."
          : "No hay una conclusión evaluable con estos criterios.";
}
