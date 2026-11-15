import { execFile } from "node:child_process";
import path from "node:path";
import type { Selection } from "./contracts";
import type { TrendBundle } from "./trend-evidence";
import { createRealAnalysis, validateSelection } from "./real-data";

// Deduplicate requests for the same period; the Python cache also checks source hashes.
const pending = new Map<string, Promise<TrendBundle>>();
export class AnalysisBusyError extends Error {}
function calculate(start: number, end: number): Promise<TrendBundle> {
  const key = `${start}-${end}`;
  const existing = pending.get(key);
  if (existing) return existing;
  if (pending.size >= 2) throw new AnalysisBusyError("Hay cálculos en curso. Espera unos segundos y vuelve a analizar.");
  // Keep the executable external to Next's module/file tracing. Activate the venv or set PYTHON_BIN.
  const python = process.env.PYTHON_BIN || "python3";
  const task = new Promise<TrendBundle>((resolve, reject) => {
    const child = execFile(/*turbopackIgnore: true*/ python, [path.join(process.cwd(), "scripts/app_trends.py"), "--stdin"], {
      cwd: process.cwd(), timeout: 120_000, maxBuffer: 2 * 1024 * 1024,
      env: { ...process.env, OPENBLAS_NUM_THREADS: "1", OMP_NUM_THREADS: "1" },
    }, (error, stdout) => {
      if (error) {
        reject(new Error("No se pudo calcular este periodo. Comprueba el entorno Python indicado en docs/APP_TREND_PROTOCOL.md y vuelve a analizar."));
        return;
      }
      try { resolve(JSON.parse(stdout) as TrendBundle); } catch { reject(new Error("El cálculo devolvió un resultado inválido.")); }
    });
    child.stdin?.end(JSON.stringify({ start, end }));
  });
  pending.set(key, task);
  void task.finally(() => pending.delete(key)).catch(() => {});
  return task;
}

export async function analyzeOnServer(selection: Selection) {
  validateSelection(selection);
  const bundle = await calculate(selection.start, selection.end);
  return createRealAnalysis(selection, bundle);
}
