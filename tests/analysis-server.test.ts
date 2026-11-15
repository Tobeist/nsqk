import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import path from "node:path";
import { pythonExecutable } from "../lib/analysis-server";

test("Python engine: PYTHON_BIN, then the documented .venv, then python3", () => {
  const original = process.env.PYTHON_BIN;
  try {
    process.env.PYTHON_BIN = "/custom/python";
    assert.equal(pythonExecutable(), "/custom/python");
    delete process.env.PYTHON_BIN;
    const venv = path.join(process.cwd(), ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
    assert.equal(pythonExecutable(), existsSync(venv) ? venv : "python3");
  } finally {
    if (original === undefined) delete process.env.PYTHON_BIN; else process.env.PYTHON_BIN = original;
  }
});
