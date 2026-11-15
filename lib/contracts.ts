import type { VariableId, Region } from "./catalog";
import type { TrendEvidence } from "./trend-evidence";
export interface Selection {
  regionId: string;
  variables: VariableId[];
  start: number;
  end: number;
}
export interface Observation {
  year: number;
  value: number | null;
}
export interface Statistics {
  slopePerDecade: number;
  confidenceInterval: [number, number];
  confidenceLevel: 0.95;
  intercept: number;
  rSquared?: number;
  sampleSize: number;
  evidence?: TrendEvidence;
}
export interface VariableResult {
  variableId: VariableId;
  unit: string;
  source: string;
  annualLabel: string;
  sampleUnit: "meses" | "años";
  method: { id: string; name: string; description: string };
  limitations: string[];
  series: Observation[];
  trend: Observation[];
  statistics: Statistics | null;
  evidence?: TrendEvidence;
  status: "ready" | "no-data" | "not-evaluable";
}
export interface Analysis {
  id: string;
  selection: Selection;
  region: Region;
  results: VariableResult[];
  mode: "real";
  provenance: {
    source: string;
    updatedAt: string;
    resolution: string;
    limitations: string[];
    audit?: { version: string; fingerprint: string; replicates: number; seed: number };
  };
}
export interface AnalysisAdapter {
  analyze(selection: Selection, signal?: AbortSignal): Promise<Analysis>;
}
export interface ChatContext {
  analysisId: string;
  selection: Selection;
  region: Region;
  variableId: VariableId;
  unit: string;
  series: Observation[];
  statistics: Statistics | null;
  method: VariableResult["method"];
  sampleUnit: VariableResult["sampleUnit"];
  annualLabel: string;
  sources: Analysis["provenance"];
  mode: "real";
}
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  evidence?: "slope" | "interval" | "method";
  provider?: "claude" | "local";
  model?: string;
  analysisId?: string;
  verifiedSummary?: string;
  explanation?: string;
}
export interface ChatAdapter {
  connected: boolean;
  mode: "real";
  reply(
    question: string,
    context: ChatContext,
    signal?: AbortSignal,
    history?: Pick<ChatMessage, "role" | "text">[],
  ): Promise<Omit<ChatMessage, "id" | "role">>;
}
export function selectionKey(s: Selection) {
  return `${s.regionId}:${[...s.variables].sort().join(",")}:${s.start}-${s.end}`;
}
export function conversationKey(analysisId: string, variableId: VariableId) {
  return `${analysisId}:${variableId}`;
}
