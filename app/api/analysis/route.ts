import { AnalysisBusyError, analyzeOnServer } from "../../../lib/analysis-server";
import { validateSelection } from "../../../lib/real-data";
import type { Selection } from "../../../lib/contracts";

export const runtime = "nodejs";
export const maxDuration = 120;

export async function POST(request: Request) {
  let selection: Selection;
  try {
    if (Number(request.headers.get("content-length")) > 4096) throw new Error("Selección demasiado grande.");
    const text = await request.text();
    if (text.length > 4096) throw new Error("Selección demasiado grande.");
    selection = JSON.parse(text);
    if (!selection || typeof selection.regionId !== "string" || !Array.isArray(selection.variables)) {
      throw new Error("Selección inválida.");
    }
    validateSelection(selection);
  } catch {
    return Response.json({ error: "Elige una caja, de una a tres variables y años completos entre 1992 y 2024: mínimo diez años, o veinte para RX5day anual." }, { status: 400 });
  }
  try {
    return Response.json(await analyzeOnServer(selection), { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "No se pudo realizar el análisis." }, {
      status: 503, headers: error instanceof AnalysisBusyError ? { "Retry-After": "10" } : {},
    });
  }
}
