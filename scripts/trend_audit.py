"""Reproducible trend audit: data checks, seasonal models with and without ENSO, robustness, reports.

Usage: python scripts/trend_audit.py [--reps 5000]. Design and decision rules: docs/ANALISIS_TENDENCIAS_PLAN.md.
"""

import argparse
import csv
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import statsmodels
import statsmodels.api as sm
from scipy import stats
from statsmodels.graphics.tsaplots import acf
from statsmodels.stats.multitest import multipletests

import trend_lib as tl

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "analysis" / "results"
FIG = ROOT / "analysis" / "figures"
PLAN = ROOT / "docs" / "ANALISIS_TENDENCIAS_PLAN.md"
SEED = 20261114
DATES = pd.date_range("1992-01-01", "2024-12-01", freq="MS")
BASE = (1992, 2021)
BREAKS = {"2001-01": 2001, "2008-01": 2008, "2011-01": 2011}
WINDOWS = {"W0": (1992, 2024), "W1": (1992, 2010), "W2": (2006, 2024), "W3": (2000, 2024)}
LAGS = (0, 3, 6)
N34_LABEL = "Nino3.4 monthly anomaly (NOAA CPC ERSSTv5, base 1991-2020)"
VARS = {
    "t2m": {"file": "processed/power_t2m_region_1992_2024.csv", "col": "t2m_c", "unit": "°C",
            "name": "Temperatura media a 2 m (NASA POWER, MERRA-2)",
            "existing": ("results/power_t2m_region_1992_2024.json", "trend_c_per_decade", "trend_ci95_c_per_decade")},
    "gpcp": {"file": "processed/giovanni_gpcp_1992_2024.csv", "col": "gpcp_mm_day", "unit": "mm/día",
             "name": "Precipitación media (GPCP satélite + pluviómetros, Giovanni)",
             "existing": ("results/giovanni_gpcp_1992_2024.json", "trend_per_decade", "trend_ci95_per_decade")},
    "rx5d": {"file": "processed/giovanni_rx5day_1992_2024.csv", "col": "rx5day_mm_per_5days", "unit": "mm/5 días",
             "name": "RX5Day mensual (MERRA-2, Giovanni)",
             "existing": ("results/giovanni_rx5day_1992_2024.json", "trend_per_decade", "trend_ci95_per_decade")},
}
SUPPLEMENTARY = {"prectotcorr": ("processed/power_prectotcorr_region_1992_2024.csv", "prectotcorr_mm_day")}
Q_SIMULTANEOUS = stats.norm.ppf(1 - 0.05 / 6)  # Bonferroni, three tests, two-sided


def load_series():
    frame = pd.DataFrame(index=DATES)
    for key, spec in {**VARS, **{k: {"file": v[0], "col": v[1]} for k, v in SUPPLEMENTARY.items()}}.items():
        raw = pd.read_csv(DATA / spec["file"], parse_dates=["date"]).set_index("date")
        if not raw.index.equals(DATES):
            raise ValueError(f"{key}: dates are not the complete 1992-01..2024-12 monthly sequence")
        frame[key] = raw[spec["col"]].astype(float)
    return frame


def load_enso():
    path = DATA / "external/enso/ersst5.nino.mth.91-20.ascii"
    rows = [line.split() for line in path.read_text().splitlines()[1:] if line.strip()]
    index = pd.to_datetime([f"{r[0]}-{int(r[1]):02d}-01" for r in rows])
    series = pd.Series([float(r[9]) for r in rows], index=index)
    expected = pd.date_range(series.index[0], series.index[-1], freq="MS")
    if not series.index.equals(expected) or series.loc["1991-01-01":"2024-12-01"].isna().any():
        raise ValueError("Nino 3.4 series has gaps in 1991-2024")
    return series


def lagged(enso, dates, lag):
    return enso.shift(lag).reindex(dates).to_numpy()


def climatology(frame):
    base = frame[(frame.index.year >= BASE[0]) & (frame.index.year <= BASE[1])]
    return base.groupby(base.index.month).mean()


# ---------------------------------------------------------------- data and spatial audit

def longest_run(values):
    best = run = 1
    for a, b in zip(values[:-1], values[1:]):
        run = run + 1 if a == b else 1
        best = max(best, run)
    return best


def read_giovanni(path):
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("time"))
    rows = [line.split(",") for line in lines[start + 1:] if line.strip()]
    return pd.Series([float(r[1]) for r in rows], index=pd.to_datetime([r[0][:10] for r in rows]))


def weighted_region_mean(path, parameter):
    """Cos-latitude weighted and plain regional means recomputed from the untouched POWER JSON."""
    records = []
    for feature in json.loads(path.read_text())["features"]:
        lon, lat = feature["geometry"]["coordinates"][:2]
        for key, value in feature["properties"]["parameter"][parameter].items():
            if key[4:] != "13":
                records.append((pd.Timestamp(f"{key[:4]}-{key[4:]}-01"), lat, lon, value))
    grid = pd.DataFrame(records, columns=["date", "latitude", "longitude", "value"])
    grid = grid[grid["value"] != -999]
    w = np.cos(np.radians(grid["latitude"]))
    grid = grid.assign(w=w, wv=grid["value"] * w)
    g = grid.groupby("date")
    return g["wv"].sum() / g["w"].sum(), g["value"].mean(), g["value"].count()


def audit_data(frame):
    out = {}
    clim = climatology(frame)
    for key in frame.columns:
        v = frame[key]
        years = v.index.year
        anomaly = v - clim[key].reindex(v.index.month).to_numpy()
        periods = {"1992-2000": (1992, 2000), "2001-2010": (2001, 2010), "2011-2024": (2011, 2024)}
        out[key] = {
            "months": int(v.size), "missing": int(v.isna().sum()),
            "duplicate_dates": int(v.index.duplicated().sum()),
            "fill_like_values(<=-900)": int((v <= -900).sum()),
            "min": float(v.min()), "max": float(v.max()), "mean": float(v.mean()), "sd": float(v.std()),
            "zeros": int((v == 0).sum()), "negatives": int((v < 0).sum()),
            "longest_identical_run": longest_run(v.to_numpy()),
            "anomaly_by_period(mean,sd)": {
                name: [float(anomaly[(years >= a) & (years <= b)].mean()), float(anomaly[(years >= a) & (years <= b)].std())]
                for name, (a, b) in periods.items()},
        }
    # raw files against the processed series
    wt, plain, count = weighted_region_mean(DATA / "raw/power_t2m_1992_2024.json", "T2M")
    out["t2m"]["raw_json_cells"] = len(json.loads((DATA / "raw/power_t2m_1992_2024.json").read_text())["features"])
    out["t2m"]["region_csv_vs_recomputed_weighted_max_abs_diff"] = float((wt - frame["t2m"]).abs().max())
    out["t2m"]["unweighted_vs_cos_weighted_max_abs_diff"] = float((plain - wt).abs().max())
    out["t2m"]["valid_cells_per_month(min,max)"] = [int(count.min()), int(count.max())]
    wt, plain, count = weighted_region_mean(DATA / "raw/power_prectotcorr_1992_2024.json", "PRECTOTCORR")
    out["prectotcorr"]["region_csv_vs_recomputed_weighted_max_abs_diff"] = float((wt - frame["prectotcorr"]).abs().max())
    out["prectotcorr"]["unweighted_vs_cos_weighted_max_abs_diff"] = float((plain - wt).abs().max())
    for key, name in (("gpcp", "gpcp_1992_2024.csv"), ("rx5d", "rx5day_1992_2024.csv")):
        raw = read_giovanni(DATA / "raw/giovanni" / name)
        out[key]["raw_csv_vs_processed_max_abs_diff"] = float((raw.reindex(DATES) - frame[key]).abs().max())
    # definition cross-checks: a monthly maximum five-day total cannot be below 5 x the mean daily rate
    # of the same precipitation field; MERRA-2 corrected precipitation is a close but not identical field
    out["rx5d"]["share_months_below_5x_prectotcorr"] = float((frame["rx5d"] < 5 * frame["prectotcorr"]).mean())
    out["rx5d"]["share_months_below_5x_gpcp"] = float((frame["rx5d"] < 5 * frame["gpcp"]).mean())
    anomalies = frame.sub(clim.reindex(frame.index.month).to_numpy())
    out["gpcp"]["anomaly_corr_with_prectotcorr"] = float(anomalies["gpcp"].corr(anomalies["prectotcorr"]))
    out["rx5d"]["anomaly_corr_with_prectotcorr"] = float(anomalies["rx5d"].corr(anomalies["prectotcorr"]))
    out["rx5d"]["anomaly_corr_with_gpcp"] = float(anomalies["rx5d"].corr(anomalies["gpcp"]))
    return out


def audit_spatial():
    try:
        from shapely.geometry import box, shape
        from shapely.ops import unary_union
    except ImportError:
        return {"skipped": "shapely is not installed"}
    states = json.loads((ROOT / "public/assets/region-states.json").read_text())
    shapes = {f["properties"]["name"]: shape(f["geometry"]) for f in states["features"] if f["properties"]["intersects"]}
    study = box(-101, 25, -99, 27)
    meta = json.loads((DATA / "processed/giovanni_gpcp_1992_2024.metadata.json").read_text())
    w, s, e, n = (float(x) for x in meta["original_metadata"]["Data Bounding Box"].split(","))
    grid = pd.read_csv(DATA / "processed/power_t2m_grid_1992_2024.csv", nrows=40)
    cells = sorted({(a, b) for a, b in zip(grid["latitude"], grid["longitude"])})
    merra = unary_union([box(lo - 0.3125, la - 0.25, lo + 0.3125, la + 0.25) for la, lo in cells])
    gpcp = unary_union([box(lo - 0.25, la - 0.25, lo + 0.25, la + 0.25)
                        for la in np.arange(s, n + 0.01, 0.5) for lo in np.arange(w, e + 0.01, 0.5)])
    result = {"boundaries": states["source"],
              "note": "Geometric overlap of footprints with state polygons (unweighted); the 0.5-degree products are not clipped at borders."}
    for label, footprint in (("requested_box", study), ("merra2_cells_footprint", merra), ("gpcp_cells_footprint", gpcp)):
        result[label] = {"bounds_wsen": [round(x, 4) for x in footprint.bounds],
                         "area_deg2": round(footprint.area, 4),
                         "share_by_state": {k: round(footprint.intersection(g).area / footprint.area, 4) for k, g in shapes.items()},
                         "share_outside_listed_states": round(1 - sum(footprint.intersection(g).area for g in shapes.values()) / footprint.area, 4)}
    result["merra2_cells"] = len(cells)
    return result


# ---------------------------------------------------------------- models

def window_slice(start, end):
    return slice((start - 1992) * 12, (end - 1992 + 1) * 12)


def window_data(frame, enso, key, window, transform=None):
    start, end = WINDOWS[window]
    sl = window_slice(start, end)
    dates = DATES[sl]
    y = frame[key].to_numpy()[sl]
    if transform == "pct":
        clim = climatology(frame)[key].reindex(dates.month).to_numpy()
        y = 100 * y / clim - 100
    return dates, y, dates.month.to_numpy()


def run_models(frame, enso, reps):
    rows, enso_cmp, enso_season, breaks, influence, diag_store = [], [], [], [], [], {}
    for vi, key in enumerate(VARS):
        for wi, window in enumerate(WINDOWS):
            dates, y, months = window_data(frame, enso, key, window)
            n = len(y)
            base_row = {"variable": key, "window": window, "start": WINDOWS[window][0], "end": WINDOWS[window][1],
                        "n_months": n, "n_years": n // 12, "unit_per_decade": VARS[key]["unit"] + "/década"}
            specs = [("M0", None, {})]
            for lag in LAGS:
                specs.append((f"M1_L{lag}", lag, {"nino34": lagged(enso, dates, lag)}))
            season_cols = {f"nino34_{s}": lagged(enso, dates, 0) * np.isin(months, ms) for s, ms in tl.SEASONS.items()}
            specs.append(("M1S_L0", 0, season_cols))
            for model, lag, extras in specs:
                X, names = tl.design(n, months, extras)
                fits = {L: tl.fit_hac(y, X, L) for L in (6, 12, 24)}
                ols = sm.OLS(y, X).fit()
                diag = tl.residual_diagnostics(ols, months)
                diag["cook_max_date"] = dates[diag.pop("cook_max_index")].strftime("%Y-%m")
                diag_store[(key, window, model)] = (ols, diag)
                row = {**base_row, "model": model, "enso_index": N34_LABEL if lag is not None else "",
                       "enso_lag_months": "" if lag is None else lag, **diag}
                if lag is not None and model != "M1S_L0":
                    g = tl.coefficient(fits[12], names.index("nino34"))
                    row.update({"enso_coef": g["est"], "enso_coef_lo": g["lo"], "enso_coef_hi": g["hi"], "enso_coef_p": g["p"],
                                "corr_t_nino34": tl.collinearity(X[:, 1], np.column_stack([extras["nino34"], X[:, 2:13]]))[0],
                                "vif_t": tl.collinearity(X[:, 1], np.column_stack([extras["nino34"], X[:, 2:13]]))[1]})
                methods = [("HAC6", fits[6], "z"), ("HAC12", fits[12], "z"), ("HAC24", fits[24], "z"), ("HAC12_t", fits[12], "t")]
                if model in ("M1_L3", "M1_L6", "M1S_L0"):
                    methods = [("HAC12", fits[12], "z")]
                for method, res, crit in methods:
                    c = tl.coefficient(res, 1, 10, crit)
                    rows.append({**row, "method": method, "hac_lags": int(method[3:].split("_")[0]), "slope_per_decade": c["est"],
                                 "se_per_decade": c["se"], "ci_low": c["lo"], "ci_high": c["hi"], "p_value": c["p"]})
                if model in ("M0", "M1_L0"):
                    for block in ((12, 24, 36) if window == "W0" else (12,)):
                        b = tl.block_bootstrap(y, X, 1, months, block, reps, (SEED, vi, wi, 0 if model == "M0" else 1, block))
                        rows.append({**row, "method": f"BOOT{block}", "hac_lags": "", "slope_per_decade": 10 * b["est"],
                                     "se_per_decade": 10 * b["se"], "ci_low": 10 * b["lo"], "ci_high": 10 * b["hi"], "p_value": b["p"]})
                if model == "M1S_L0":
                    cols = [names.index(f"nino34_{s}") for s in tl.SEASONS]
                    chi2, p = tl.wald(fits[12], [{cols[0]: 1, cols[i]: -1} for i in range(1, 4)])
                    for s, ci in zip(tl.SEASONS, cols):
                        g = tl.coefficient(fits[12], ci)
                        enso_season.append({"variable": key, "window": window, "season": s, "enso_coef": g["est"], "lo": g["lo"],
                                            "hi": g["hi"], "p": g["p"], "wald_equal_chi2": chi2, "wald_equal_p": p})
            # Theil-Sen (no ENSO)
            grid = y.reshape(-1, 12)
            ts = tl.theil_sen_bootstrap(grid, 2, reps, (SEED, vi, wi, 9))
            rows.append({**base_row, "model": "SEASONAL_THEIL_SEN", "enso_index": "", "enso_lag_months": "", "method": "THEILSEN_BOOT2y",
                         "hac_lags": "", "slope_per_decade": 10 * ts["est"], "se_per_decade": 10 * ts["se"],
                         "ci_low": 10 * ts["lo"], "ci_high": 10 * ts["hi"], "p_value": float("nan")})
            if window == "W0":
                if key in ("gpcp", "rx5d"):
                    _, yp, _ = window_data(frame, enso, key, window, "pct")
                    X, _ = tl.design(n, months)
                    c = tl.coefficient(tl.fit_hac(yp, X, 12), 1, 10)
                    rows.append({**base_row, "model": "M0_pct_of_monthly_mean", "unit_per_decade": "% de la media mensual/década",
                                 "enso_index": "", "enso_lag_months": "", "method": "HAC12", "hac_lags": 12, "slope_per_decade": c["est"],
                                 "se_per_decade": c["se"], "ci_low": c["lo"], "ci_high": c["hi"], "p_value": c["p"]})
            # ENSO comparison (same dates, same HAC)
            m0 = next(r for r in rows if (r["variable"], r["window"], r["model"], r["method"]) == (key, window, "M0", "HAC12"))
            for lag in LAGS:
                m1 = next(r for r in rows if (r["variable"], r["window"], r["model"], r["method"]) == (key, window, f"M1_L{lag}", "HAC12"))
                enso_cmp.append({"variable": key, "window": window, "enso_lag_months": lag, "n_months": n,
                                 "beta_M0": m0["slope_per_decade"], "beta_M0_lo": m0["ci_low"], "beta_M0_hi": m0["ci_high"],
                                 "beta_E": m1["slope_per_decade"], "beta_E_lo": m1["ci_low"], "beta_E_hi": m1["ci_high"],
                                 "beta_E_minus_beta": m1["slope_per_decade"] - m0["slope_per_decade"],
                                 "se_ratio_E_over_M0": m1["se_per_decade"] / m0["se_per_decade"],
                                 "enso_coef": m1["enso_coef"], "enso_coef_lo": m1["enso_coef_lo"], "enso_coef_hi": m1["enso_coef_hi"],
                                 "enso_coef_p": m1["enso_coef_p"], "corr_t_nino34": m1["corr_t_nino34"], "vif_t": m1["vif_t"],
                                 "resid_sd_M0": m0["resid_sd"], "resid_sd_E": m1["resid_sd"]})
        # linearity, breaks and influence (full window, M0)
        dates, y, months = window_data(frame, enso, key, "W0")
        n = len(y)
        X, names = tl.design(n, months)
        t = X[:, 1]
        tc = t - t.mean()
        quad = tl.fit_hac(y, np.column_stack([X, tc**2 / 100]), 12)
        c = tl.coefficient(quad, X.shape[1])
        breaks.append({"variable": key, "test": "quadratic_term", "date": "", "statistic": c["est"] / c["se"], "p": c["p"], "p_holm": float("nan")})
        pvals = []
        for label, year in BREAKS.items():
            pos = (year - 1992) * 12
            step = (np.arange(n) >= pos).astype(float)
            ramp = step * (t - pos / 12)
            res = tl.fit_hac(y, np.column_stack([X, step, ramp]), 12)
            stat, p = tl.wald(res, [{X.shape[1]: 1}, {X.shape[1] + 1: 1}])
            pvals.append(p)
            breaks.append({"variable": key, "test": "level_and_slope_change_wald_hac12", "date": label, "statistic": stat, "p": p, "p_holm": float("nan")})
        holm = multipletests(pvals, method="holm")[1]
        for r, ph in zip(breaks[-3:], holm):
            r["p_holm"] = ph
        cus = diag_store[(key, "W0", "M0")][1]["cusum_p"]
        breaks.append({"variable": key, "test": "cusum_ols_residuals", "date": "", "statistic": float("nan"), "p": cus, "p_holm": float("nan")})
        loyo = tl.leave_one_year_out(y, X, months)
        years = np.arange(1992, 2025)
        full = next(r for r in rows if (r["variable"], r["window"], r["model"], r["method"]) == (key, "W0", "M0", "HAC12"))["slope_per_decade"]
        influence.append({"variable": key, "full_slope_per_decade": full, "loyo_min": loyo.min(), "year_of_min": int(years[loyo.argmin()]),
                          "loyo_max": loyo.max(), "year_of_max": int(years[loyo.argmax()]),
                          "loyo_range_over_full_hac12_ci_width": (loyo.max() - loyo.min()) / (
                              next(r for r in rows if (r["variable"], r["window"], r["model"], r["method"]) == (key, "W0", "M0", "HAC12"))["ci_high"]
                              - next(r for r in rows if (r["variable"], r["window"], r["model"], r["method"]) == (key, "W0", "M0", "HAC12"))["ci_low"])})
        diag_store[(key, "loyo")] = (years, loyo)
    return rows, enso_cmp, enso_season, breaks, influence, diag_store


def add_families(rows):
    for family, model in (("F1", "M0"), ("F2", "M1_L0")):
        sel = [r for r in rows if r["window"] == "W0" and r["model"] == model and r["method"] == "HAC12"]
        adj = multipletests([r["p_value"] for r in sel], method="holm")[1]
        for r, p in zip(sel, adj):
            r["family"], r["p_holm"] = family, p
            if family == "F1":
                se = r["se_per_decade"]
                r["ci_simultaneous_low"] = r["slope_per_decade"] - Q_SIMULTANEOUS * se
                r["ci_simultaneous_high"] = r["slope_per_decade"] + Q_SIMULTANEOUS * se
    for r in rows:
        r.setdefault("family", "exploratory")
        r.setdefault("p_holm", float("nan"))


def coverage_simulation(sims=1000, reps=399):
    """Empirical size of the 95% trend tests on simulated no-trend AR(1) series (n = 396, month effects zero)."""
    rng = np.random.default_rng([SEED, 77])
    months = DATES.month.to_numpy()
    X, _ = tl.design(len(DATES), months)
    out = {}
    for phi in (0.0, 0.37):
        hits = {k: 0 for k in ("HAC6", "HAC12", "HAC24", "HAC12_t", "BOOT12")}
        for s in range(sims):
            shocks = rng.standard_normal(len(DATES) + 50)
            e = np.zeros_like(shocks)
            for i in range(1, len(e)):
                e[i] = phi * e[i - 1] + shocks[i]
            y = e[50:]
            for L in (6, 12, 24):
                c = tl.coefficient(tl.fit_hac(y, X, L), 1)
                hits[f"HAC{L}"] += c["lo"] > 0 or c["hi"] < 0
            c = tl.coefficient(tl.fit_hac(y, X, 12), 1, critical="t")
            hits["HAC12_t"] += c["lo"] > 0 or c["hi"] < 0
            b = tl.block_bootstrap(y, X, 1, months, 12, reps, (SEED, 78, s))
            hits["BOOT12"] += b["lo"] > 0 or b["hi"] < 0
        out[f"ar1_phi_{phi}"] = {"simulations": sims, "nominal_rejection_rate": 0.05,
                                 "empirical_rejection_rate": {k: v / sims for k, v in hits.items()}}
    return out


def rolling(frame, enso):
    out = []
    for key in VARS:
        y = frame[key].to_numpy()
        for length in (10, 15):
            for start in range(1992, 2025 - length + 1):
                sl = window_slice(start, start + length - 1)
                X, _ = tl.design(length * 12, DATES[sl].month.to_numpy())
                out.append({"variable": key, "length_years": length, "start_year": start, "end_year": start + length - 1,
                            "slope_per_decade": 10 * np.linalg.lstsq(X, y[sl], rcond=None)[0][1]})
    return out


def annual_consistency(frame, rows):
    out, reproduction = {}, []
    for key, spec in VARS.items():
        y = frame[key].to_numpy()
        annual = y.reshape(-1, 12).mean(axis=1)
        years = np.arange(1992, 2025)
        ols = sm.OLS(annual, sm.add_constant(years - 1992)).fit()
        hac = sm.OLS(annual, sm.add_constant(years - 1992)).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
        m0 = next(r for r in rows if (r["variable"], r["window"], r["model"], r["method"]) == (key, "W0", "M0", "HAC12"))
        out[key] = {"monthly_slope_per_decade": m0["slope_per_decade"], "annual_means_ols_slope_per_decade": 10 * ols.params[1],
                    "abs_difference": abs(m0["slope_per_decade"] - 10 * ols.params[1]),
                    "monthly_hac12_ci": [m0["ci_low"], m0["ci_high"]],
                    "annual_ols_classical_ci": [10 * x for x in ols.conf_int()[1]],
                    "annual_ols_hac3_ci": [10 * x for x in hac.conf_int()[1]],
                    "annual_ols_residual_acf1": float(np.corrcoef(ols.resid[1:], ols.resid[:-1])[0, 1])}
        path, slope_key, ci_key = spec["existing"]
        existing = json.loads((DATA / path).read_text())
        for label, mine, theirs in (("slope", m0["slope_per_decade"], existing[slope_key]),
                                    ("ci_low", m0["ci_low"], existing[ci_key][0]), ("ci_high", m0["ci_high"], existing[ci_key][1]),
                                    ("p_value", m0["p_value"], existing["p_value_unadjusted"])):
            reproduction.append({"variable": key, "quantity": label, "this_analysis": mine, "versioned_json": theirs, "abs_diff": abs(mine - theirs)})
        months = existing["monthly"]
        vk = "value" if "value" in months[0] else "t2m_c"
        reproduction.append({"variable": key, "quantity": "monthly_values_max_abs_diff", "this_analysis": float("nan"), "versioned_json": float("nan"),
                             "abs_diff": float(np.max(np.abs(np.array([m[vk] for m in months]) - y)))})
    return out, reproduction


def parity_fixture(frame):
    out = {}
    for label, (a, b) in (("W0", (1992, 2024)), ("W3", (2000, 2024))):
        out[label] = {"start": a, "end": b}
        for key in VARS:
            sl = window_slice(a, b)
            y = frame[key].to_numpy()[sl]
            X, _ = tl.design(len(y), DATES[sl].month.to_numpy())
            c = tl.coefficient(tl.fit_hac(y, X, 12), 1, 10)
            annual = y.reshape(-1, 12).mean(axis=1)
            yrs = np.arange(a, b + 1)
            line = sm.OLS(annual, sm.add_constant(yrs)).fit().params
            out[label][key] = {"slope_per_decade": c["est"], "ci95": [c["lo"], c["hi"]], "n_months": len(y),
                               "annual_means": annual.tolist(), "annual_ols_intercept": line[0], "annual_ols_slope_per_year": line[1]}
    return out


# ---------------------------------------------------------------- classification

def pick(rows, key, window, model, method):
    return next(r for r in rows if (r["variable"], r["window"], r["model"], r["method"]) == (key, window, model, method))


def classify(rows, breaks):
    result = {}
    for key in VARS:
        m0 = pick(rows, key, "W0", "M0", "HAC12")
        m1 = pick(rows, key, "W0", "M1_L0", "HAC12")
        boot = pick(rows, key, "W0", "M0", "BOOT12")
        ratio = boot["se_per_decade"] / m0["se_per_decade"]
        brk = [b for b in breaks if b["variable"] == key and b["date"]]
        break_flag = any(b["p_holm"] < 0.01 for b in brk)
        excl = lambda r: r["ci_low"] > 0 or r["ci_high"] < 0
        checks = {
            "F1_holm_lt_0.05": m0["p_holm"] < 0.05, "F2_holm_lt_0.05": m1["p_holm"] < 0.05,
            "M1_L0_ci_excludes_0": excl(m1), "boot12_ci_excludes_0": excl(boot),
            "hac6_hac12_hac24_exclude_0": all(excl(pick(rows, key, "W0", "M0", f"HAC{L}")) for L in (6, 12, 24)),
            "same_sign_W1_W2_W3": all(np.sign(pick(rows, key, w, "M0", "HAC12")["slope_per_decade"]) == np.sign(m0["slope_per_decade"]) for w in ("W1", "W2", "W3")),
        }
        d = break_flag or not (0.67 <= ratio <= 1.5)
        if d:
            label = "D"
        elif all(checks.values()):
            label = "A"
        elif checks["F1_holm_lt_0.05"] or checks["F2_holm_lt_0.05"]:
            label = "B"
        else:
            label = "C"
        result[key] = {"class": label, "checks": checks, "se_ratio_boot12_over_hac12": ratio,
                       "break_flag_holm_lt_0.01": break_flag, "se_ratio_in_range": 0.67 <= ratio <= 1.5}
    return result


BREAK_LABELS = {"quadratic_term": "término cuadrático", "level_and_slope_change_wald_hac12": "cambio de nivel y pendiente en"}
LABELS = {"A": "Evidencia consistente de tendencia dentro de los análisis realizados",
          "B": "Resultado sensible al periodo, al modelo o a los controles",
          "C": "Evidencia insuficiente",
          "D": "Datos o supuestos que impiden una conclusión confiable"}


# ---------------------------------------------------------------- figures

BLUE, ORANGE, GRAY, GREEN, PURPLE = "#0072B2", "#D55E00", "#6b7280", "#009E73", "#CC79A7"


def figure_series(frame, enso, rows, key):
    spec = VARS[key]
    y = frame[key]
    clim = climatology(frame)[key]
    anomaly = y - clim.reindex(y.index.month).to_numpy()
    m0, m1 = pick(rows, key, "W0", "M0", "HAC12"), pick(rows, key, "W0", "M1_L0", "HAC12")
    n34 = lagged(enso, DATES, 0)
    adjusted = anomaly - m1["enso_coef"] * n34
    years = np.arange(1992, 2025)
    annual = y.to_numpy().reshape(-1, 12).mean(axis=1)
    tmid = (y.index.year + (y.index.month - 0.5) / 12).to_numpy()
    fig, ax = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    ax[0].plot(tmid, y, color=GRAY, lw=0.7, label="Observación mensual")
    ax[0].plot(years + 0.5, annual, "o", color="black", ms=4, label="Promedio anual (observación)")
    centre = 2008.5
    line = annual.mean() + m0["slope_per_decade"] / 10 * (years + 0.5 - centre)
    ax[0].plot(years + 0.5, line, color=BLUE, lw=2, label=f"Ajuste M0: {m0['slope_per_decade']:+.3g} {spec['unit']}/década")
    half = (m0["ci_high"] - m0["ci_low"]) / 20 * np.abs(years + 0.5 - centre)
    ax[0].fill_between(years + 0.5, line - half, line + half, color=BLUE, alpha=0.2, label="Incertidumbre de la pendiente (HAC12, 95 % individual)")
    ax[0].set_ylabel(spec["unit"])
    ax[0].legend(fontsize=7, loc="upper left", ncol=2)
    ax[0].set_title(f"{spec['name']}\nObservaciones y ajuste; la banda no es el intervalo de la media anual", fontsize=10)
    ax[1].plot(tmid, anomaly, color=GRAY, lw=0.7, label="Anomalía observada (clim. 1992–2021)")
    ax[1].plot(tmid, adjusted, color=ORANGE, lw=0.7, ls="--", label="Anomalía − γ·Niño3.4 (construida, no observada)")
    ax[1].plot(tmid, anomaly.mean() + m0["slope_per_decade"] / 10 * (tmid - tmid.mean()), color=BLUE, lw=2, label=f"Tendencia M0 {m0['slope_per_decade']:+.3g}")
    ax[1].plot(tmid, adjusted.mean() + m1["slope_per_decade"] / 10 * (tmid - tmid.mean()), color=ORANGE, lw=2, label=f"Tendencia M1 (con ENSO) {m1['slope_per_decade']:+.3g}")
    ax[1].axhline(0, color="black", lw=0.5)
    ax[1].set_ylabel(f"Anomalía ({spec['unit']})")
    ax[1].legend(fontsize=7, loc="upper left", ncol=2)
    fig.tight_layout()
    fig.savefig(FIG / f"serie_{key}.png", dpi=130)
    plt.close(fig)


def figure_forest(rows):
    order = [("M0", "W0", "HAC12", "M0 HAC12 (principal)", BLUE), ("M0", "W0", "HAC6", "M0 HAC6", BLUE), ("M0", "W0", "HAC24", "M0 HAC24", BLUE),
             ("M0", "W0", "HAC12_t", "M0 HAC12, t", BLUE), ("M0", "W0", "BOOT12", "M0 bootstrap bloque 12", PURPLE),
             ("M0", "W0", "BOOT24", "M0 bootstrap bloque 24", PURPLE), ("M0", "W0", "BOOT36", "M0 bootstrap bloque 36", PURPLE),
             ("SEASONAL_THEIL_SEN", "W0", "THEILSEN_BOOT2y", "Theil–Sen estacional", GRAY),
             ("M1_L0", "W0", "HAC12", "M1 ENSO L0", ORANGE), ("M1_L3", "W0", "HAC12", "M1 ENSO L3", ORANGE), ("M1_L6", "W0", "HAC12", "M1 ENSO L6", ORANGE),
             ("M1S_L0", "W0", "HAC12", "M1S ENSO por estación", ORANGE),
             ("M1_L0", "W0", "BOOT12", "M1 L0 bootstrap 12", ORANGE)]
    order += [("M0", w, "HAC12", f"M0 {w} {WINDOWS[w][0]}–{WINDOWS[w][1]}", GREEN) for w in ("W1", "W2", "W3")]
    order += [("M1_L0", w, "HAC12", f"M1 L0 {w}", GREEN) for w in ("W1", "W2", "W3")]
    fig, axes = plt.subplots(1, 3, figsize=(15, 6.5), sharey=True)
    for ax, key in zip(axes, VARS):
        for i, (model, window, method, label, color) in enumerate(order):
            r = pick(rows, key, window, model, method)
            ax.plot([r["ci_low"], r["ci_high"]], [i, i], color=color, lw=2)
            ax.plot(r["slope_per_decade"], i, "o", color=color)
        ax.axvline(0, color="black", ls="--", lw=0.8)
        ax.set_title(f"{VARS[key]['name'].split(' (')[0]}\n(95 % individual, {VARS[key]['unit']}/década)", fontsize=9)
        ax.set_yticks(range(len(order)))
        ax.set_yticklabels([o[3] for o in order], fontsize=8)
        ax.invert_yaxis()
    fig.suptitle("Pendiente por década y su intervalo según modelo, incertidumbre y ventana (azul: base; morado/gris: bootstrap y no paramétrico; naranja: ENSO; verde: ventanas)", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "pendientes_por_modelo.png", dpi=130)
    plt.close(fig)


def figure_diagnostics(frame, diag_store, key):
    ols0, _ = diag_store[(key, "W0", "M0")]
    ols1, _ = diag_store[(key, "W0", "M1_L0")]
    fig, ax = plt.subplots(2, 3, figsize=(14, 7))
    ax[0, 0].plot(DATES, ols0.resid, color=GRAY, lw=0.7)
    ax[0, 0].axhline(0, color="black", lw=0.5)
    ax[0, 0].set_title("Residuos de M0 en el tiempo")
    for ols, color, label in ((ols0, BLUE, "M0"), (ols1, ORANGE, "M1 L0")):
        ax[0, 1].plot(range(1, 37), acf(ols.resid, nlags=36)[1:], "o-", ms=3, color=color, label=label)
    bound = 1.96 / math.sqrt(len(ols0.resid))
    ax[0, 1].axhline(bound, color="black", ls=":", lw=0.8)
    ax[0, 1].axhline(-bound, color="black", ls=":", lw=0.8)
    ax[0, 1].set_title("ACF de residuos (banda ±1.96/√n, solo referencia)")
    ax[0, 1].legend(fontsize=7)
    sm.qqplot(ols0.resid, line="s", ax=ax[0, 2], markersize=2)
    ax[0, 2].set_title("QQ normal de residuos de M0")
    months = DATES.month.to_numpy()
    ax[1, 0].boxplot([ols0.resid[months == m] for m in range(1, 13)], tick_labels=range(1, 13), showfliers=True)
    ax[1, 0].set_title("Residuos de M0 por mes")
    cook = ols0.get_influence().cooks_distance[0]
    ax[1, 1].vlines(DATES, 0, cook, color=GRAY, lw=0.8)
    ax[1, 1].axhline(4 / len(cook), color=ORANGE, ls="--", lw=0.8)
    ax[1, 1].set_title("Distancia de Cook (línea: 4/n)")
    years, loyo = diag_store[(key, "loyo")]
    ax[1, 2].bar(years, loyo, color=BLUE, alpha=0.7)
    ax[1, 2].axhline(pick_slope(diag_store, key), color="black", lw=1)
    ax[1, 2].set_title("Pendiente al omitir cada año (línea: completo)")
    fig.suptitle(f"Diagnósticos — {VARS[key]['name']}", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / f"diagnosticos_{key}.png", dpi=120)
    plt.close(fig)


def pick_slope(diag_store, key):
    ols, _ = diag_store[(key, "W0", "M0")]
    return 10 * ols.params[1]


def figure_rolling(rolling_rows, rows):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for ax, key in zip(axes, VARS):
        m0 = pick(rows, key, "W0", "M0", "HAC12")
        ax.axhspan(m0["ci_low"], m0["ci_high"], color=BLUE, alpha=0.2, label="IC 95 % periodo completo (HAC12)")
        ax.axhline(m0["slope_per_decade"], color=BLUE, lw=1.5)
        for length, color in ((10, GRAY), (15, ORANGE)):
            sel = [r for r in rolling_rows if r["variable"] == key and r["length_years"] == length]
            ax.plot([r["start_year"] + (length - 1) / 2 + 0.5 for r in sel], [r["slope_per_decade"] for r in sel], "o-", ms=3, color=color,
                    label=f"Pendiente en ventanas de {length} años (solo descriptivo)")
        ax.axhline(0, color="black", lw=0.5)
        ax.set_title(VARS[key]["name"].split(" (")[0], fontsize=9)
        ax.set_xlabel("Centro de la ventana")
        ax.set_ylabel(f"{VARS[key]['unit']}/década")
        ax.legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(FIG / "ventanas_moviles.png", dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------- reports

def fmt(r, digits=3):
    return f"{r['slope_per_decade']:+.{digits}g} [{r['ci_low']:+.{digits}g}, {r['ci_high']:+.{digits}g}]"


def write_report(key, rows, enso_cmp, breaks, influence, classification, enso_season):
    spec = VARS[key]
    unit = spec["unit"]
    m0, m1 = pick(rows, key, "W0", "M0", "HAC12"), pick(rows, key, "W0", "M1_L0", "HAC12")
    cls = classification[key]
    infl = next(i for i in influence if i["variable"] == key)
    cmp0 = next(c for c in enso_cmp if c["variable"] == key and c["window"] == "W0" and c["enso_lag_months"] == 0)
    seasons = [s for s in enso_season if s["variable"] == key and s["window"] == "W0"]
    brk = [b for b in breaks if b["variable"] == key]
    lines = [f"# Informe: {spec['name']}", "",
             f"**Clasificación según las reglas del plan:** {cls['class']} — {LABELS[cls['class']]}.", "",
             "## Qué se estimó", "",
             f"Cambio lineal por década en la caja `[-101, 25, -99, 27]`, enero de 1992 a diciembre de 2024 ({m0['n_months']} meses, {m0['n_years']} años), "
             f"con efectos fijos por mes y covarianza HAC (Bartlett). Unidad: {unit} por década. Los intervalos son del 95 % **individuales**.", "",
             "| Análisis | Pendiente [IC 95 %] | p original | p Holm |", "| --- | --- | ---: | ---: |",
             f"| M0 base, HAC12 (familia F1) | {fmt(m0)} | {m0['p_value']:.3g} | {m0['p_holm']:.3g} |",
             f"| M1 con Niño 3.4 (L = 0), HAC12 (familia F2) | {fmt(m1)} | {m1['p_value']:.3g} | {m1['p_holm']:.3g} |", "",
             f"Intervalo simultáneo de Bonferroni para M0 (F1): [{m0['ci_simultaneous_low']:+.3g}, {m0['ci_simultaneous_high']:+.3g}].", "",
             "## Sensibilidad (exploratoria, sin ajuste de p)", "",
             "| Variante | Pendiente [IC 95 %] |", "| --- | --- |"]
    for model, window, method, label in [("M0", "W0", "HAC6", "M0 HAC6"), ("M0", "W0", "HAC24", "M0 HAC24"), ("M0", "W0", "HAC12_t", "M0 HAC12 con t"),
                                         ("M0", "W0", "BOOT12", "M0 bootstrap bloque 12"), ("M0", "W0", "BOOT24", "M0 bootstrap bloque 24"),
                                         ("M0", "W0", "BOOT36", "M0 bootstrap bloque 36"), ("SEASONAL_THEIL_SEN", "W0", "THEILSEN_BOOT2y", "Theil–Sen estacional"),
                                         ("M1_L3", "W0", "HAC12", "M1 ENSO L = 3"), ("M1_L6", "W0", "HAC12", "M1 ENSO L = 6"),
                                         ("M1S_L0", "W0", "HAC12", "M1S ENSO por estación"),
                                         ("M0", "W1", "HAC12", "M0 1992–2010"), ("M0", "W2", "HAC12", "M0 2006–2024"), ("M0", "W3", "HAC12", "M0 2000–2024"),
                                         ("M1_L0", "W1", "HAC12", "M1 L0 1992–2010"), ("M1_L0", "W2", "HAC12", "M1 L0 2006–2024"), ("M1_L0", "W3", "HAC12", "M1 L0 2000–2024")]:
        lines.append(f"| {label} | {fmt(pick(rows, key, window, model, method))} |")
    if key in ("gpcp", "rx5d"):
        lines.append(f"| M0 en % de la media mensual (unidad: %/década) | {fmt(pick(rows, key, 'W0', 'M0_pct_of_monthly_mean', 'HAC12'))} |")
    lines += ["", "## Validez de p e intervalos", "",
              "Los p de esta tabla usan la aproximación normal del HAC, que en simulaciones cubre alrededor del 90 % en lugar del 95 %. "
              "Los valores p válidos (bootstrap-t con criba AR estimada de los residuos), sus correcciones de Holm y la cobertura real "
              "están en `uncertainty_validation.csv` (plan v3)."]
    lines += ["", "## ENSO", "",
              f"β cambia de {cmp0['beta_M0']:+.3g} a {cmp0['beta_E']:+.3g} {unit}/década al incluir Niño 3.4 (diferencia {cmp0['beta_E_minus_beta']:+.3g}); "
              f"el error estándar HAC se multiplica por {cmp0['se_ratio_E_over_M0']:.2f}. Coeficiente de Niño 3.4: {cmp0['enso_coef']:+.3g} [{cmp0['enso_coef_lo']:+.3g}, {cmp0['enso_coef_hi']:+.3g}] {unit}/°C (p = {cmp0['enso_coef_p']:.3g}). "
              f"Correlación del tiempo con Niño 3.4: {cmp0['corr_t_nino34']:+.2f}; VIF del tiempo: {cmp0['vif_t']:.2f}.", "",
              "Por estación (L = 0): " + "; ".join(f"{s['season']} {s['enso_coef']:+.3g} [{s['lo']:+.3g}, {s['hi']:+.3g}]" for s in seasons)
              + f". Prueba de igualdad entre estaciones: p = {seasons[0]['wald_equal_p']:.3g}.", "",
              "## Diagnósticos", "",
              f"Ljung–Box p (12/24 rezagos) en M0: {m0['ljungbox_p12']:.3g} / {m0['ljungbox_p24']:.3g}; Breusch–Pagan p = {m0['breusch_pagan_p']:.3g}; "
              f"varianza por mes (Levene) p = {m0['levene_month_p']:.3g}; Jarque–Bera p = {m0['jarque_bera_p']:.3g} (asimetría {m0['resid_skew']:.2f}); "
              f"Cook máximo {m0['cook_max']:.3g} en {m0['cook_max_date']} ({m0['cook_count_gt_4_over_n']} meses > 4/n); CUSUM p = {m0['cusum_p']:.3g}. "
              f"Al omitir un año completo la pendiente va de {infl['loyo_min']:+.3g} (sin {infl['year_of_min']}) a {infl['loyo_max']:+.3g} (sin {infl['year_of_max']}); "
              f"el resultado completo se conserva como principal.", "",
              "Rupturas y linealidad (Wald HAC12): " + "; ".join(
                  f"{BREAK_LABELS[b['test']]} {b['date']} p = {b['p']:.3g}" + (f" (Holm {b['p_holm']:.3g})" if b["date"] else "") for b in brk if b["test"] != "cusum_ols_residuals") + ".", "",
              f"Razón de errores estándar bootstrap(12)/HAC(12): {cls['se_ratio_boot12_over_hac12']:.2f}.", "",
              "## Qué se puede concluir", ""]
    c = cls["class"]
    sign = "aumento" if m0["slope_per_decade"] > 0 else "disminución"
    if c == "A":
        lines += [f"- La estimación central indica un {sign} de {abs(m0['slope_per_decade']):.3g} {unit} por década, con intervalo que excluye cero en todas las variantes preespecificadas y signo coincidente en las tres ventanas.",
                  "- Esto describe una asociación estadística dentro de este modelo, esta caja y estos productos."]
    elif c == "B":
        lines += [f"- La estimación central es un {sign} de {abs(m0['slope_per_decade']):.3g} {unit} por década, pero no se cumple: " + ", ".join(k for k, v in cls["checks"].items() if not v) + ".",
                  "- El resultado depende del periodo, del control por ENSO o del método de incertidumbre."]
    elif c == "C":
        lines += [f"- La estimación central es un {sign} de {abs(m0['slope_per_decade']):.3g} {unit} por década, pero el intervalo y los ajustes por Holm no establecen el signo con estos datos.",
                  "- Un intervalo que contiene cero indica evidencia insuficiente bajo este análisis; no prueba que no haya cambio."]
    else:
        lines += ["- Los criterios fijados de antemano señalan una ruptura o una discrepancia de incertidumbre que impide fiarse del error estándar HAC; la estimación no debe interpretarse como tendencia sin investigar el producto."]
    lines += ["", "Criterios del plan (verdadero = se cumple): " + "; ".join(f"{k}: {v}" for k, v in cls["checks"].items()) + f"; ruptura (Holm < 0.01): {cls['break_flag_holm_lt_0.01']}; razón SE en [0.67, 1.5]: {cls['se_ratio_in_range']}.", "",
              "## Qué no se puede concluir", "",
              "- No se puede atribuir el cambio a causas antropogénicas: no se hizo detección y atribución.",
              "- La pendiente con ENSO es una asociación condicionada a un índice y a un rezago; no elimina otras fuentes de variabilidad ni prueba causalidad.",
              "- La caja es un área de 2°×2°; no representa un estado completo ni la región Norte-Noreste (ver `spatial_audit.json`).",
              "- Treinta y tres años no separan por completo una tendencia de la variabilidad de varias décadas (ver `ventanas_moviles.png`).",
              "- Los valores p no son probabilidades de que la tendencia sea real; las ventanas, los rezagos y los HAC alternativos son exploratorios sin ajuste de multiplicidad.", ""]
    (OUT / f"informe_{key}.md").write_text("\n".join(lines), encoding="utf-8")


def write_summary(rows, classification, spatial, audit, consistency):
    lines = ["# Resumen del análisis de tendencias", "",
             "Generado por `scripts/trend_audit.py`. Reglas y definiciones: `docs/ANALISIS_TENDENCIAS_PLAN.md`. Cifras: pendiente por década [IC 95 % individual].", "",
             "| Variable | M0 base (F1) | p original / Holm | M1 con Niño 3.4 (F2) | p original / Holm | Bootstrap bloque 12 | Clase |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for key in VARS:
        m0, m1, b = pick(rows, key, "W0", "M0", "HAC12"), pick(rows, key, "W0", "M1_L0", "HAC12"), pick(rows, key, "W0", "M0", "BOOT12")
        lines.append(f"| {VARS[key]['name']} ({VARS[key]['unit']}) | {fmt(m0)} | {m0['p_value']:.3g} / {m0['p_holm']:.3g} | {fmt(m1)} | {m1['p_value']:.3g} / {m1['p_holm']:.3g} | {fmt(b)} | {classification[key]['class']} |")
    lines += ["", "Clases: " + "; ".join(f"**{k}** = {v}" for k, v in LABELS.items()) + ".", "",
              "La pendiente mensual coincide con la pendiente de MCO de los promedios anuales (diferencia máxima "
              f"{max(v['abs_difference'] for v in consistency.values()):.1e}); los intervalos difieren porque usan 396 meses con HAC frente a 33 promedios.", ""]
    if "share_by_state" in spatial.get("requested_box", {}):
        shares = spatial["requested_box"]["share_by_state"]
        lines += ["Cobertura espacial de la caja solicitada: " + ", ".join(f"{k} {v:.1%}" for k, v in shares.items())
                  + f". Huella de las celdas MERRA-2: Texas {spatial['merra2_cells_footprint']['share_by_state'].get('Texas', 0):.1%}; GPCP: Texas {spatial['gpcp_cells_footprint']['share_by_state'].get('Texas', 0):.1%}.", ""]
    lines += ["Los p de Holm de esta tabla usan la aproximación normal del HAC; los p válidos por bootstrap-t con criba AR, "
              "que reemplazan a la calibración retirada de la versión anterior, están en `uncertainty_validation.csv`.", ""]
    lines += ["Informes: " + ", ".join(f"[{k}](informe_{k}.md)" for k in VARS) + ".", ""]
    (OUT / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------- main

def write_table(path, records):
    keys = list(dict.fromkeys(k for r in records for k in r))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(records)


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (np.floating, float)):
        return None if not math.isfinite(value) else float(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def main(reps):
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    frame, enso = load_series(), load_enso()
    audit, spatial = audit_data(frame), audit_spatial()
    rows, enso_cmp, enso_season, breaks, influence, diag_store = run_models(frame, enso, reps)
    add_families(rows)
    rolling_rows = rolling(frame, enso)
    consistency, reproduction = annual_consistency(frame, rows)
    classification = classify(rows, breaks)
    coverage = coverage_simulation()
    for name, table in (("trend_results", rows), ("enso_comparison", enso_cmp), ("enso_by_season", enso_season),
                        ("breaks_linearity", breaks), ("influence_leave_one_year_out", influence),
                        ("rolling_slopes", rolling_rows), ("reproduction_check", reproduction)):
        write_table(OUT / f"{name}.csv", table)
    (OUT / "trend_results.json").write_text(json.dumps(clean(rows), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for name, payload in (("data_audit", audit), ("spatial_audit", spatial), ("consistency_checks", consistency),
                          ("classification", classification), ("parity_fixture", parity_fixture(frame)),
                          ("coverage_simulation", coverage)):
        (OUT / f"{name}.json").write_text(json.dumps(clean(payload), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    enso_meta = json.loads((DATA / "external/enso/ersst5.nino.mth.91-20.metadata.json").read_text())
    run_info = {"command": "python scripts/trend_audit.py", "seed": SEED, "bootstrap_reps": reps,
                "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "plan_sha256": hashlib.sha256(PLAN.read_bytes()).hexdigest(),
                "enso": {k: enso_meta[k] for k in ("url", "downloaded_utc", "sha256", "definition", "column_used")},
                "python": sys.version.split()[0],
                "packages": {"numpy": np.__version__, "scipy": scipy.__version__, "statsmodels": statsmodels.__version__, "pandas": pd.__version__, "matplotlib": matplotlib.__version__},
                "input_sha256": {k: hashlib.sha256((DATA / v["file"]).read_bytes()).hexdigest() for k, v in VARS.items()}}
    (OUT / "run_info.json").write_text(json.dumps(run_info, indent=1) + "\n", encoding="utf-8")
    for key in VARS:
        figure_series(frame, enso, rows, key)
        figure_diagnostics(frame, diag_store, key)
        write_report(key, rows, enso_cmp, breaks, influence, classification, enso_season)
    figure_forest(rows)
    figure_rolling(rolling_rows, rows)
    write_summary(rows, classification, spatial, audit, consistency)
    print((OUT / "SUMMARY.md").read_text())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reps", type=int, default=5000)
    main(parser.parse_args().reps)
