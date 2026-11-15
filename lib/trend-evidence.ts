import type { VariableId } from "./catalog";

export type EvidenceStatus = "consistent" | "inconclusive" | "sensitive" | "pending" | "not-evaluable";
export interface TrendModel {
  slopePerDecade: number;
  confidenceInterval: [number, number];
  pValue: number;
  pAdjusted: number;
  family: string;
  familySize: number;
  sampleSize: number;
  arOrder: number;
  nominalHacCoverage: number;
}
export interface TrendEvidence extends Partial<TrendModel> {
  status: EvidenceStatus;
  reasons: string[];
  baseline?: TrendModel | null;
  ensoCoefficient?: number;
  diagnostics?: {
    residualAcf1: number;
    ljungBoxP: number;
    hacSensitivity: { lags: number; interval: number[] }[];
    subperiodSlopes: number[];
    steps: { date: string; change: number; deltaAic: number; pHac: number }[];
    blockInterval: number[];
  };
}
export interface TrendBundle {
  version: string;
  start: number;
  end: number;
  replicates: number;
  seed: number;
  fingerprint: string;
  inputHashes: Record<string, string>;
  results: Record<string, Partial<Record<VariableId, TrendEvidence>>>;
}
