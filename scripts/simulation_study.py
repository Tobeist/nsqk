"""Simulation study on synthetic series (not NASA data): size, power, bias and coverage of the trend procedures.

Usage: python scripts/simulation_study.py [--sims 1000]. Design: docs/ANALISIS_TENDENCIAS_PLAN_V2.md, section 6.
"""

import argparse
import json

import numpy as np
import pandas as pd

import trend_audit as ta
import trend_lib as tl

N = 396
MONTHS = np.tile(np.arange(1, 13), 33)
YEARS = np.repeat(np.arange(1992, 2025), 12)
SCENARIOS = {"S0_sin_tendencia": 0, "S1_tendencia_0.27": 1, "S2_oscilacion_20a": 2, "S3_escalon_2008": 3}
TRUE_SLOPE = {0: 0.0, 1: 0.27, 2: None, 3: None}


def simulate(kind, rng):
    t = np.arange(N) / 12
    enso = np.zeros(N + 120)
    for i in range(1, len(enso)):
        enso[i] = 0.93 * enso[i - 1] + 0.33 * rng.standard_normal()
    enso = enso[120:]
    e = np.zeros(N + 50)
    for i in range(1, len(e)):
        e[i] = 0.37 * e[i - 1] + rng.standard_normal()
    y = 8 * np.sin(2 * np.pi * (MONTHS - 4) / 12) - 0.2 * enso + e[50:]
    if kind == 1:
        y = y + 0.027 * t
    elif kind == 2:
        y = y + 0.4 * np.sin(2 * np.pi * t / 20 + rng.uniform(0, 2 * np.pi))
    elif kind == 3:
        y = y + 0.5 * (np.arange(N) >= 192)
    return y, enso


def one(kind, s, reps):
    rng = np.random.default_rng([ta.SEED, 300, kind, s])
    y, enso = simulate(kind, rng)
    X0, _ = tl.design(N, MONTHS)
    X1, _ = tl.design(N, MONTHS, {"enso": enso})
    out = {}
    for name, X in (("M0", X0), ("M1", X1)):
        for L in (12, 24):
            c = tl.coefficient(tl.fit_hac(y, X, L), 1, 10)
            out[f"{name}_HAC{L}"] = c
        b = tl.block_bootstrap(y, X, 1, MONTHS, 12, reps, (ta.SEED, 301, kind, s, name == "M1"))
        out[f"{name}_BOOT12"] = {"est": 10 * b["est"], "lo": 10 * b["lo"], "hi": 10 * b["hi"], "p": b["p"]}
    out["THEIL_SEN"] = {"est": 10 * tl.seasonal_theil_sen(y.reshape(-1, 12)), "lo": np.nan, "hi": np.nan, "p": np.nan}
    pmin = min(tl.coefficient(tl.fit_hac(y[ta.window_slice(a, b)], tl.design((b - a + 1) * 12, MONTHS[ta.window_slice(a, b)])[0], 12), 1)["p"]
               for a, b in ta.WINDOWS.values())
    out["MIN_P_OF_4_WINDOWS"] = {"est": np.nan, "lo": np.nan, "hi": np.nan, "p": pmin}
    # predictive selection: CLIM vs OLS_TREND on the same outer folds as the real experiment
    mae = {"CLIM": [], "OLS_TREND": []}
    for year in range(2016, 2021):
        tr, te = YEARS < year, YEARS == year
        clim = np.array([y[tr & (MONTHS == m)].mean() for m in range(1, 13)])
        mae["CLIM"].append(np.abs(clim - y[te]).mean())
        Xtr, _ = tl.design(int(tr.sum()), MONTHS[tr])
        Xall, _ = tl.design(N, MONTHS)
        beta = np.linalg.lstsq(Xtr, y[tr], rcond=None)[0]
        mae["OLS_TREND"].append(np.abs(Xall[te] @ beta - y[te]).mean())
    out["PRED_PICKS_TREND"] = float(np.mean(mae["OLS_TREND"]) < np.mean(mae["CLIM"]))
    return out


def main(sims, reps):
    rows = []
    for scenario, kind in SCENARIOS.items():
        results = [one(kind, s, reps) for s in range(sims)]
        for proc in results[0]:
            if proc == "PRED_PICKS_TREND":
                rows.append({"scenario": scenario, "procedure": "prediccion_elige_OLS_TREND_sobre_CLIM", "simulations": sims,
                             "rate": float(np.mean([r[proc] for r in results]))})
                continue
            est = np.array([r[proc]["est"] for r in results])
            p = np.array([r[proc]["p"] for r in results])
            lo, hi = np.array([r[proc]["lo"] for r in results]), np.array([r[proc]["hi"] for r in results])
            truth = TRUE_SLOPE[kind]
            row = {"scenario": scenario, "procedure": proc, "simulations": sims,
                   "rejection_rate_5pct": float(np.mean(p < 0.05)) if np.isfinite(p).all() else None,
                   "mean_slope_per_decade": float(np.nanmean(est)) if np.isfinite(est).any() else None}
            if truth is not None and np.isfinite(est).all():
                row["bias_per_decade"] = float(est.mean() - truth)
            if truth is not None and np.isfinite(lo).all():
                row["coverage95"] = float(np.mean((lo <= truth) & (truth <= hi)))
            rows.append(row)
        print(scenario, "done", flush=True)
    ta.write_table(ta.OUT / "simulation_study.csv", rows)
    (ta.OUT / "simulation_config.json").write_text(json.dumps({
        "n_months": N, "simulations": sims, "bootstrap_reps": reps, "seed": ta.SEED,
        "noise": "AR(1) phi=0.37, sd 1; seasonal cycle amplitude 8; ENSO-like AR(1) phi=0.93, innovation sd 0.33, effect -0.2",
        "scenarios": {"S0": "no trend", "S1": "0.27 per decade", "S2": "20-year sinusoid, amplitude 0.4, random phase", "S3": "+0.5 step at month 192 (2008-01)"},
        "note": "Prophet with Optuna is not re-run inside the simulations (cost); predictive selection is simulated for CLIM vs OLS_TREND only."},
        indent=1) + "\n", encoding="utf-8")
    print(pd.DataFrame(rows).round(3).to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sims", type=int, default=1000)
    parser.add_argument("--reps", type=int, default=199)
    args = parser.parse_args()
    main(args.sims, args.reps)
