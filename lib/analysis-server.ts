import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import type { Selection } from "./contracts";
import type { TrendBundle } from "./trend-evidence";
import { createRealAnalysis, defaultTrendBundle, validateSelection } from "./real-data";

// Deduplicate requests for the same period; the Python cache also checks source hashes.
const pending = new Map<string, Promise<TrendBundle>>();
// PYTHON_BIN wins; otherwise the .venv documented in docs/APP_TREND_PROTOCOL.md, then python3 on PATH.
export function pythonExecutable() {
  if (process.env.PYTHON_BIN) return process.env.PYTHON_BIN;
  const venv = path.join(/*turbopackIgnore: true*/ process.cwd(), ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
  return existsSync(/*turbopackIgnore: true*/ venv) ? venv : "python3";
}
export class AnalysisBusyError extends Error {}
async function precomputed(start: number, end: number): Promise<TrendBundle | null> {
  const filename = path.join(process.cwd(), "analysis", "periods", `${start}-${end}.json`);
  let raw: string;
  try {
    raw = await readFile(filename, "utf8");
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw error;
  }
  const bundle = JSON.parse(raw) as TrendBundle;
  if (bundle.start !== start || bundle.end !== end || bundle.fingerprint !== defaultTrendBundle.fingerprint) {
    throw new Error("El cálculo guardado no coincide con los datos auditados. Regenera los periodos antes de desplegar.");
  }
  return bundle;
}
function calculate(start: number, end: number): Promise<TrendBundle> {
  const key = `${start}-${end}`;
  const existing = pending.get(key);
  if (existing) return existing;
  if (pending.size >= 2) throw new AnalysisBusyError("Hay cálculos en curso. Espera unos segundos y vuelve a analizar.");
  // Keep the executable external to Next's module/file tracing. Activate the venv or set PYTHON_BIN.
  const python = pythonExecutable();
  const task = new Promise<TrendBundle>((resolve, reject) => {
    const child = execFile(/*turbopackIgnore: true*/ python, [path.join(process.cwd(), "scripts/app_trends.py"), "--stdin"], {
      cwd: process.cwd(), timeout: 120_000, maxBuffer: 2 * 1024 * 1024,
      env: { ...process.env, OPENBLAS_NUM_THREADS: "1", OMP_NUM_THREADS: "1" },
    }, (error, stdout, stderr) => {
      if (error) {
        // Server-side log only: the client gets a generic message, operators get the cause.
        console.error("[api/analysis] Python engine failed", { python, period: key, code: error.code, signal: error.signal,
          stderr: String(stderr ?? "").slice(-2000) });
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
  // The canonical full-period bundle ships with the app and needs no Python runtime.
  // Other full-year windows have the same audited Python result precomputed at build time.
  if (selection.start === 1992 && selection.end === 2024) return createRealAnalysis(selection);
  const bundle = await precomputed(selection.start, selection.end);
  if (bundle) return createRealAnalysis(selection, bundle);
  if (process.env.VERCEL) {
    throw new Error("No hay un cálculo auditado para este periodo en el despliegue. Vuelve a intentarlo más tarde.");
  }
  return createRealAnalysis(selection, await calculate(selection.start, selection.end));
}
