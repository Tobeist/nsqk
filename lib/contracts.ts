import type { VariableId, Region } from "./catalog";
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
  rSquared: number;
  sampleSize: number;
}
export interface VariableResult {
  variableId: VariableId;
  unit: string;
  series: Observation[];
  trend: Observation[];
  statistics: Statistics | null;
  status: "ready" | "no-data";
}
export interface Analysis {
  id: string;
  selection: Selection;
  region: Region;
  results: VariableResult[];
  mode: "demo" | "real";
  method: { id: string; name: string; description: string };
  provenance: {
    source: string;
    updatedAt: string;
    resolution: string;
    limitations: string[];
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
  method: Analysis["method"];
  sources: Analysis["provenance"];
  mode: "demo" | "real";
}
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  evidence?: "slope" | "interval" | "method";
}
export interface ChatAdapter {
  connected: boolean;
  mode: "demo" | "real";
  reply(
    question: string,
    context: ChatContext,
    signal?: AbortSignal,
  ): Promise<Omit<ChatMessage, "id" | "role">>;
}
export function selectionKey(s: Selection) {
  return `${s.regionId}:${[...s.variables].sort().join(",")}:${s.start}-${s.end}`;
}
export function conversationKey(analysisId: string, variableId: VariableId) {
  return `${analysisId}:${variableId}`;
}
