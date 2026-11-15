"""Extend the fixed-window northeast audit to all three study boxes.

Run from the repository root: python scripts/audit_regions.py
Protocol: docs/PLAN_AUDITORIA_REGIONAL.md. Writes only analysis/regions/.
"""

import argparse
import hashlib
import json
import platform
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests

import form_of_change as fc
import study_regions as sr
import trend_audit as ta
import trend_lib as tl


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "analysis" / "regions"
PLAN = ROOT / "docs" / "PLAN_AUDITORIA_REGIONAL.md"
REGIONS = sr.region_ids()
DATES = pd.date_range("1992-01-01", "2024-12-01", freq="MS")
YEARS = pd.Index(range(1992, 2025), name="year")
WINDOWS = {"W1": (1992, 2010), "W2": (2006, 2024), "W3": (2000, 2024)}
MONTHLY = {
    "t2m": ("power_t2m_region_1992_2024.csv", "t2m_c", "°C"),
    "gpcp": ("giovanni_gpcp_1992_2024.csv", "gpcp_mm_day", "mm/día"),
    "rx5d": ("giovanni_rx5day_1992_2024.csv", "rx5day_mm_per_5days", "mm/5 días"),
}
ANNUAL = ("power_rx5day_annual_region_1992_2024.csv", "rx5day_mm", "mm")
VARIANTS = {
    "principal": {"order": "aic", "innov": "resample", "monthly_scale": True},
    "ar1": {"order": 1, "innov": "resample", "monthly_scale": True},
    "gaussiana": {"order": "aic", "innov": "gaussian", "monthly_scale": True},
}
PAIRS = (("mx-chihuahua-interior", "mx-northeast"),
         ("mx-south-humid", "mx-northeast"),
         ("mx-south-humid", "mx-chihuahua-interior"))
HASH_POLICY = "sha256-text-lf-v1"


def sha256(path):
    """Fingerprint text identically after Git's LF/CRLF checkout conversion.

    Only normalize CRLF to LF. Whitespace, numeric precision, encoding and all
    other content remain significant; this is not a hash of parsed values.
    """
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_inputs():
    """Reject missing dates, non-finite values and region/bbox metadata mismatches."""
    data, hashes = {}, {}
    for region in REGIONS:
        base = sr.data_dir(DATA, "processed", region)
        data[region] = {}
        for key, (filename, column, unit) in {**MONTHLY, "Rx5day": ANNUAL}.items():
            path = base / filename
            meta_path = path.with_suffix(".metadata.json")
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            bbox = meta.get("bbox_wsen")
            if bbox is None and "User Bounding Box" in meta.get("original_metadata", {}):
                bbox = [float(x) for x in meta["original_metadata"]["User Bounding Box"].split(",")]
            if bbox != list(sr.study_box(region)):
                raise ValueError(f"Incorrect study box: {meta_path}")
            if region != sr.DEFAULT_REGION and meta.get("region_id") != region:
                raise ValueError(f"Incorrect region ID: {meta_path}")
            if meta.get("period") and meta["period"] != [1992, 2024]:
                raise ValueError(f"Incorrect period: {meta_path}")
            if key != "Rx5day" and meta.get("months") != 396:
                raise ValueError(f"Incomplete monthly metadata: {meta_path}")
            expected_units = {"t2m": {"C", "degC"}, "gpcp": {"mm/day"},
                              "rx5d": {"mm per 5 days"}, "Rx5day": {"mm"}}
            reported_units = meta.get("units_index") if key == "Rx5day" else meta.get("units")
            if reported_units not in expected_units[key]:
                raise ValueError(f"Incorrect units: {meta_path}")
            if meta.get("missing_months", 0) != 0 or meta.get("missing_grid_values", 0) != 0:
                raise ValueError(f"Missing source values: {meta_path}")
            if key == "Rx5day" and ("UTC" not in meta.get("source", "") or
                len(meta.get("requests", [])) != 33 or
                any(req.get("api_header", {}).get("time_standard") != "UTC"
                    for req in meta["requests"])):
                raise ValueError(f"Annual time standard is not UTC: {meta_path}")
            if key == "Rx5day":
                frame = pd.read_csv(path).set_index("year")
                if not frame.index.equals(YEARS) or len(frame) != 33:
                    raise ValueError(f"Incomplete annual dates: {path}")
            else:
                frame = pd.read_csv(path, parse_dates=["date"]).set_index("date")
                if not frame.index.equals(DATES):
                    raise ValueError(f"Incomplete monthly dates: {path}")
            if column not in frame or not np.isfinite(frame[column].to_numpy(dtype=float)).all():
                raise ValueError(f"Invalid values for {key}: {path}")
            if "valid_grid_cells" in frame:
                expected_cells = meta.get("grid_cells")
                if expected_cells is None or not (frame.valid_grid_cells == expected_cells).all():
                    raise ValueError(f"Invalid grid-cell counts: {path}")
            data[region][key] = frame[column].to_numpy(dtype=float)
            hashes[str(path.relative_to(ROOT)).replace("\\", "/")] = sha256(path)
            hashes[str(meta_path.relative_to(ROOT)).replace("\\", "/")] = sha256(meta_path)
    return data, hashes


def model(y, key, nino=None, dates=None, lag=None):
    if key == "Rx5day":
        X = np.column_stack([np.ones(len(y)), np.arange(len(y), dtype=float)])
        return X, np.zeros(len(y), dtype=int), 1, lag or 2, 3
    months = dates.month.to_numpy()
    X, _ = tl.design(len(y), months, {"nino34": nino} if nino is not None else {})
    return X, months - 1, 12, lag or 12, 12


def fit_row(y, X, lag):
    fit = tl.fit_hac(y, X, lag)
    c = tl.coefficient(fit, 1, 10)
    return {"slope_per_decade": c["est"], "se_hac_per_decade": c["se"],
            "ci_hac_low": c["lo"], "ci_hac_high": c["hi"], "p_normal": c["p"]}, fit


def bootstrap(y, X, season, period, lag, max_ar, variant, reps, key):
    null = np.delete(X, 1, axis=1)
    stats, order = tl.simulate_t(y, X, null, season, period, lag, max_ar,
                                 variant, reps, (ta.SEED, *key))
    point, fit = fit_row(y, X, lag)
    p, q = tl.sieve_pvalue(stats, fit.params[1] / fit.bse[1])
    return {"ar_order": order, "p_bootstrap": p,
            "ci_boot_t_low": point["slope_per_decade"] - q * point["se_hac_per_decade"],
            "ci_boot_t_high": point["slope_per_decade"] + q * point["se_hac_per_decade"],
            "hac95_coverage_under_null": float(np.mean(np.abs(stats) <= tl.Z975))}


def existing_northeast():
    uv = pd.read_csv(ROOT / "analysis" / "results" / "uncertainty_validation.csv")
    old = {}
    for key in (*MONTHLY, "Rx5day"):
        model_name = "OLS_anual" if key == "Rx5day" else "M1_L0"
        for variant in VARIANTS:
            row = uv[(uv.series == key) & (uv.model == model_name) &
                     (uv.variant == variant)]
            if len(row) != 1:
                raise ValueError(f"Missing published northeast audit: {key}/{variant}")
            old[key, variant] = row.iloc[0]
    return old


def add_holm(frame, family, mask):
    frame.loc[mask, "family"] = family
    frame.loc[mask, "p_holm"] = multipletests(frame.loc[mask, "p_bootstrap"], method="holm")[1]


def run(primary_reps=4999, sensitivity_reps=999):
    data, hashes = load_inputs()
    enso = ta.load_enso()
    hashes[str((DATA / "external/enso/ersst5.nino.mth.91-20.ascii").relative_to(ROOT)).replace("\\", "/")] = sha256(DATA / "external/enso/ersst5.nino.mth.91-20.ascii")
    hashes["analysis/results/uncertainty_validation.csv"] = sha256(ROOT / "analysis/results/uncertainty_validation.csv")
    nino = ta.lagged(enso, DATES, 0)
    old = existing_northeast()
    rows, sensitivity, windows, lag_rows, step_rows = [], [], [], [], []
    for ri, region in enumerate(REGIONS):
        for ki, key in enumerate((*MONTHLY, "Rx5day")):
            y = data[region][key]
            annual = key == "Rx5day"
            X, season, period, lag, max_ar = model(y, key, None if annual else nino, None if annual else DATES)
            point, _ = fit_row(y, X, lag)
            if annual:
                base_slope = point["slope_per_decade"]
            else:
                X0, _, _, _, _ = model(y, key, None, DATES)
                base_slope = fit_row(y, X0, 12)[0]["slope_per_decade"]
            main = old[key, "principal"] if region == sr.DEFAULT_REGION else bootstrap(
                y, X, season, period, lag, max_ar,
                {**VARIANTS["principal"], "monthly_scale": not annual},
                primary_reps, (700, ri, ki, 0))
            if region == sr.DEFAULT_REGION:
                # The app's annual CSV is rounded to four decimals; the earlier
                # daily audit retained more precision in extremes_annual.csv.
                if abs(float(main.slope_per_decade) - point["slope_per_decade"]) > 1e-6:
                    raise ValueError(f"Published northeast estimate no longer matches: {key}")
                boot = {name: float(main[name]) for name in
                        ("p_bootstrap", "ci_boot_t_low", "ci_boot_t_high")}
                boot.update({"ar_order": int(main.ar_order),
                             "hac95_coverage_under_null": float(main.coverage_of_nominal_hac95)})
            else:
                boot = main
            rows.append({"region_id": region, "variable": key, "unit": ANNUAL[2] if annual else MONTHLY[key][2],
                         "model": "OLS_anual" if annual else "M1_L0", "n": len(y),
                         "base_M0_slope_per_decade": base_slope, **point, **boot})
            for vi, (variant_name, variant) in enumerate(VARIANTS.items()):
                if region == sr.DEFAULT_REGION:
                    prev = old[key, variant_name]
                    sb = {"p_bootstrap": float(prev.p_bootstrap), "ar_order": int(prev.ar_order)}
                elif variant_name == "principal":
                    sb = boot
                else:
                    spec = {**variant, "monthly_scale": not annual}
                    sb = bootstrap(y, X, season, period, lag, max_ar, spec,
                                   sensitivity_reps, (701, ri, ki, vi))
                sensitivity.append({"region_id": region, "variable": key,
                                    "variant": variant_name, "reps": 4999 if region == sr.DEFAULT_REGION else
                                    primary_reps if variant_name == "principal" else sensitivity_reps,
                                    "p_bootstrap": sb["p_bootstrap"], "ar_order": sb["ar_order"]})
            for window, (start, end) in WINDOWS.items():
                if annual:
                    yw = y[start - 1992:end - 1992 + 1]
                    Xw, _, _, _, _ = model(yw, key)
                else:
                    keep = (DATES.year >= start) & (DATES.year <= end)
                    yw = y[keep]
                    Xw, _, _, _, _ = model(yw, key, nino[keep], DATES[keep])
                slope = fit_row(yw, Xw, lag)[0]["slope_per_decade"]
                windows.append({"region_id": region, "variable": key, "window": window,
                                "start": start, "end": end, "slope_per_decade": slope})
            for use_lag in ((1, 2, 3) if annual else (6, 12, 24)):
                c = fit_row(y, X, use_lag)[0]
                lag_rows.append({"region_id": region, "variable": key, "hac_lag": use_lag, **c})
            if annual:
                base = np.ones((len(y), 1))
                steps = {"2001-01": 9, "2011-01": 19}
            else:
                base = np.delete(X, 1, axis=1)
                steps = {"2001-01": 9 * 12, "2011-01": 19 * 12}
            step_rows += [{"region_id": region, "variable": key, **x} for x in
                          fc.compare(key, y, base, X[:, 1], steps, lag, 10)]
            print(region, key, "done", flush=True)

    results = pd.DataFrame(rows)
    results["family"], results["p_holm"] = "", np.nan
    add_holm(results, "F2-regional", results.variable != "Rx5day")
    add_holm(results, "B-regional", results.variable == "Rx5day")
    sens = pd.DataFrame(sensitivity)
    sens["family"], sens["p_holm"] = "", np.nan
    for variant in VARIANTS:
        add_holm(sens, "F2-regional", (sens.variant == variant) & (sens.variable != "Rx5day"))
        add_holm(sens, "B-regional", (sens.variant == variant) & (sens.variable == "Rx5day"))
    steps = pd.DataFrame(step_rows)
    stability = pd.DataFrame(windows)
    for i, row in results.iterrows():
        key, region = row.variable, row.region_id
        relevant_steps = steps[(steps.region_id == region) & (steps.variable == key) &
                               (steps.model.str.startswith("HS(")) &
                               (steps.delta_aic_vs_HL <= 0) & (steps.step_p < 0.05)]
        slopes = stability[(stability.region_id == region) & (stability.variable == key)].slope_per_decade
        variants = sens[(sens.region_id == region) & (sens.variable == key) & (sens.variant != "principal")]
        unstable = any(np.sign(slopes) != np.sign(row.slope_per_decade)) or (variants.p_holm >= 0.05).any()
        state = ("inconcluso" if row.p_holm >= 0.05 else
                 "pendiente" if len(relevant_steps) else
                 "sensible" if unstable else "sustentado dentro del protocolo")
        results.at[i, "status"] = state
        results.at[i, "step_flags"] = ", ".join(relevant_steps.model.tolist())
        results.at[i, "window_sign_stable"] = not any(np.sign(slopes) != np.sign(row.slope_per_decade))

    differences = []
    for ki, key in enumerate((*MONTHLY, "Rx5day")):
        annual = key == "Rx5day"
        for pi, (a, b) in enumerate(PAIRS):
            y = data[a][key] - data[b][key]
            X, season, period, lag, max_ar = model(y, key, None if annual else nino, None if annual else DATES)
            point, _ = fit_row(y, X, lag)
            boot = bootstrap(y, X, season, period, lag, max_ar,
                             {**VARIANTS["principal"], "monthly_scale": not annual},
                             primary_reps, (702, ki, pi))
            differences.append({"variable": key, "region_a": a, "region_b": b,
                                "difference": f"{a} minus {b}", "unit": ANNUAL[2] if annual else MONTHLY[key][2],
                                **point, **boot})
            print(key, a, "minus", b, "done", flush=True)
    differences = pd.DataFrame(differences)
    differences["family"] = "D-regional"
    differences["p_holm"] = multipletests(differences.p_bootstrap, method="holm")[1]
    differences["status"] = np.where(differences.p_holm < 0.05, "diferencia detectada", "inconcluso")

    OUT.mkdir(parents=True, exist_ok=True)
    for name, frame in (("trends", results), ("sensitivities", sens), ("windows", stability),
                        ("hac_lags", pd.DataFrame(lag_rows)), ("step_models", steps),
                        ("pairwise_differences", differences)):
        frame.to_csv(OUT / f"{name}.csv", index=False)
    info = {"command": "python scripts/audit_regions.py", "seed": ta.SEED,
            "primary_reps": primary_reps, "sensitivity_reps": sensitivity_reps,
            "python": platform.python_version(),
            "packages": {p: version(p) for p in ("numpy", "pandas", "scipy", "statsmodels")},
            "hash_policy": HASH_POLICY,
            "plan_sha256": sha256(PLAN), "script_sha256": sha256(Path(__file__)),
            "input_sha256": hashes,
            "scope": "exploratory extension after the northeast audit; no causal attribution"}
    (OUT / "run_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_summary(results, differences)
    return results, differences


def write_summary(results, differences):
    def val(x, digits=3):
        return f"{x:+.{digits}f}"
    lines = ["# Extensión de la auditoría a tres cajas", "",
             "Plan fijado antes de calcular Chihuahua y sur: [protocolo](../../docs/PLAN_AUDITORIA_REGIONAL.md). "
             "El noreste ya se conocía: esta ampliación es exploratoria. Datos y métodos no implican causalidad ni cobertura de estados completos.", "",
             "Las pendientes mensuales primarias usan calendario + Niño 3.4 (M1), HAC(12), p e IC bootstrap-t de criba AR. "
             "Rx5day anual usa HAC(2). Holm se aplica a las nueve pruebas mensuales y a las tres anuales por separado. "
             "La app integra seis variables mensuales por caja (18 pruebas) y el índice anual (tres pruebas), "
             "con HAC(12) mensual y HAC(2) anual. Esta auditoría regional tiene un alcance mensual menor (nueve pruebas); "
             "sus p de Holm no son intercambiables con los de la app ni con la auditoría original de tres pruebas mensuales.", "",
             "| Caja | Serie | Pendiente [IC bootstrap-t 95 %] por década | p Holm | Estado |", "| --- | --- | --- | ---: | --- |"]
    for x in results.itertuples():
        lines.append(f"| {x.region_id} | {x.variable} | {val(x.slope_per_decade)} "
                     f"[{val(x.ci_boot_t_low)}, {val(x.ci_boot_t_high)}] {x.unit} | "
                     f"{x.p_holm:.3f} | {x.status} |")
    lines += ["", "## Diferencias directas de pendientes", "",
              "Se ajustó la serie emparejada de diferencias con el mismo modelo. Los doce p se corrigieron juntos con Holm; "
              "no se compararon valores p de cajas aisladas.", "",
              "| Serie | Diferencia | Pendiente [IC bootstrap-t 95 %] por década | p Holm | Estado |",
              "| --- | --- | --- | ---: | --- |"]
    for x in differences.itertuples():
        lines.append(f"| {x.variable} | {x.region_a} − {x.region_b} | {val(x.slope_per_decade)} "
                     f"[{val(x.ci_boot_t_low)}, {val(x.ci_boot_t_high)}] {x.unit} | "
                     f"{x.p_holm:.3f} | {x.status} |")
    lines += ["", "## Lectura de las comprobaciones", ""]
    for x in results.itertuples():
        if x.p_holm < 0.05:
            details = []
            if x.step_flags:
                details.append(f"escalón candidato {x.step_flags} que ajusta igual o mejor")
            if not x.window_sign_stable:
                details.append("la pendiente cambia de signo entre ventanas predefinidas")
            lines.append(f"- **{x.region_id}, {x.variable}: {x.status}.** "
                         f"p Holm {x.p_holm:.3f}; " +
                         ("; ".join(details) if details else "sin las señales de sensibilidad predefinidas") + ".")
    detected = int((differences.p_holm < 0.05).sum())
    lines.append(f"- Diferencias directas entre cajas que superan Holm: **{detected} de {len(differences)}**. "
                 "Esto no demuestra que todas las pendientes sean iguales.")
    lines += ["", "## Límites", "",
              "Los IC de la tabla son individuales; el p Holm evalúa la familia completa. "
              "Un IC individual que excluye cero puede coexistir con p Holm ≥ 0.05. "
              "Las pruebas de escalón en 2001 y 2011 son exploratorias y su p no se corrigió. "
              "Las cajas, celdas y máscaras efectivas de POWER y Giovanni difieren. "
              "El índice anual derivado de POWER no es el RX5Day mensual de Giovanni.", "",
              "Archivos detallados: `trends.csv`, `pairwise_differences.csv`, `sensitivities.csv`, "
              "`windows.csv`, `hac_lags.csv`, `step_models.csv` y `run_info.json`."]
    (OUT / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reps", type=int, default=4999)
    parser.add_argument("--sensitivity-reps", type=int, default=999)
    args = parser.parse_args()
    if args.reps < 99 or args.sensitivity_reps < 99:
        parser.error("At least 99 bootstrap replicates are required")
    run(args.reps, args.sensitivity_reps)
