"""Audited app inference for all three boxes; see docs/APP_TREND_PROTOCOL.md."""
import argparse
import hashlib
import json
import sys
import os
import tempfile
from pathlib import Path

import numpy as np
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.diagnostic import acorr_ljungbox

import trend_lib as tl
from study_regions import BOXES, data_dir

ROOT = Path(__file__).resolve().parents[1]
VERSION = "app-seasonal-enso-sieve-v1"
SEED, REPS = 20261114, 4999
# Preserve the first three original series' bootstrap keys for numerical comparison.
FILES = {
    "temperature": "power_t2m_region_1992_2024.json",
    "precipitation": "giovanni_gpcp_1992_2024.json",
    "rain5": "giovanni_rx5day_1992_2024.json",
    "temperature-min": "power_t2m_min_region_1992_2024.json",
    "temperature-max": "power_t2m_max_region_1992_2024.json",
    "precipitation-power": "power_prectotcorr_region_1992_2024.json",
}
ANNUAL = "rain5-power-annual"
ANNUAL_FILE = "power_rx5day_annual_region_1992_2024.json"
ENSO_FILE = ROOT / "data/external/enso/ersst5.nino.mth.91-20.ascii"


def input_files():
    return [ROOT / "docs/APP_TREND_PROTOCOL.md", Path(__file__), ROOT / "scripts/trend_lib.py",
            ROOT / "scripts/study_regions.py", ROOT / "requirements-analysis.txt",
            ROOT / "config/study-boxes.json", ENSO_FILE] + [
        data_dir(ROOT / "data", "results", rid) / name
        for rid in BOXES for name in list(FILES.values()) + [ANNUAL_FILE]]


def fingerprints():
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in input_files()}
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(), hashes


def validate_period(start, end):
    if type(start) is not int or type(end) is not int or start < 1992 or end > 2024 or end - start + 1 < 10:
        raise ValueError("Elige al menos diez años completos entre 1992 y 2024.")


def fast_simulate_t(y, X, X_null, season, period, hac, max_order, variant, reps, key):
    """Same AR draws and HAC sandwich as tl.simulate_t; batch the OLS projections."""
    fitted = X_null @ np.linalg.lstsq(X_null, y, rcond=None)[0]
    phi, innov = tl.ar_fit(y - fitted, max_order, variant["order"])
    p = len(phi)
    # Stationary AR requires roots outside the unit circle (equivalently companion eigenvalues <1).
    if p and np.max(np.abs(np.roots(np.r_[1., -phi]))) >= 1:
        raise ValueError("El modelo de dependencia AR no es estable para este periodo.")
    phase_innov = season[p:]
    sd = (np.array([innov[phase_innov == k].std(ddof=1) for k in range(period)])
          if variant["monthly_scale"] else np.full(period, innov.std()))
    if not np.isfinite(sd).all() or np.min(sd) <= 0:
        raise ValueError("No se puede estimar la variabilidad residual de este periodo.")
    z = innov / sd[phase_innov]
    total = len(y) + tl.SIEVE_WARMUP
    phase = ((season[0] + np.arange(total) - tl.SIEVE_WARMUP) % period
             if period > 1 else np.zeros(total, int))
    rng = np.random.default_rng(list(key))
    draws = rng.standard_normal((reps, total)) if variant["innov"] == "gaussian" else rng.choice(z, (reps, total))
    shocks = draws * sd[phase]
    e = np.zeros_like(shocks)
    for i in range(total):
        e[:, i] = shocks[:, i]
        for j in range(min(p, i)):
            e[:, i] += phi[j] * e[:, i - j - 1]
    pinv = np.linalg.pinv(X)
    out = np.empty(reps)
    for first in range(0, reps, 256):
        values = fitted + e[first:first + 256, tl.SIEVE_WARMUP:]
        beta = values @ pinv.T
        residual = values - beta @ X.T
        score = residual * pinv[1]
        variance = (score * score).sum(axis=1)
        for lag in range(1, hac + 1):
            variance += 2 * (1 - lag / (hac + 1)) * (score[:, lag:] * score[:, :-lag]).sum(axis=1)
        out[first:first + len(values)] = beta[:, 1] / np.sqrt(np.maximum(variance, 0))
    return out, p


def enso_values(start, end):
    lines = [line.split() for line in ENSO_FILE.read_text().splitlines()[1:] if line.strip()]
    lookup = {(int(r[0]), int(r[1])): float(r[9]) for r in lines}
    values = np.array([lookup[(year, month)] for year in range(start, end + 1) for month in range(1, 13)])
    if not np.isfinite(values).all() or np.any(np.abs(values) > 20):
        raise ValueError("Índice Niño 3.4 incompleto o inválido.")
    return values


def source_series(rid, name, start, end, annual=False):
    d = json.loads((data_dir(ROOT / "data", "results", rid) / name).read_text())
    if d.get("region_id", "mx-northeast") != rid:
        raise ValueError(f"La fuente de {rid} no coincide con su región.")
    if annual:
        rows = [r for r in d["annual"] if start <= r["year"] <= end]
        if [r["year"] for r in rows] != list(range(start, end + 1)):
            raise ValueError("Serie anual incompleta.")
        y = np.array([r["rx5day_mm"] for r in rows], float)
    else:
        rows = [r for r in d["monthly"] if start <= int(r["date"][:4]) <= end]
        dates = [f"{year}-{month:02d}-01" for year in range(start, end + 1) for month in range(1, 13)]
        if [r["date"] for r in rows] != dates:
            raise ValueError("Serie mensual incompleta.")
        y = np.array([r.get("value", r.get("t2m_c")) for r in rows], float)
    if not np.isfinite(y).all():
        raise ValueError("La serie contiene valores no finitos.")
    return y


def model(y, X, phase, annual, key):
    hac = 2 if annual else 12
    res = tl.fit_hac(y, X, hac)
    draws, order = fast_simulate_t(y, X, np.delete(X, 1, axis=1), phase, 1 if annual else 12,
                                   hac, 3 if annual else 12,
                                   {"order": "aic", "innov": "resample", "monthly_scale": not annual}, REPS, key)
    p, q = tl.sieve_pvalue(draws, res.params[1] / res.bse[1])
    return {"slopePerDecade": float(10 * res.params[1]),
            "confidenceInterval": [float(10 * (res.params[1] - q * res.bse[1])), float(10 * (res.params[1] + q * res.bse[1]))],
            "pValue": p, "sampleSize": len(y), "arOrder": int(order),
            "nominalHacCoverage": float(np.mean(np.abs(draws) <= tl.Z975))}, res


def diagnostics(y, X, res, start, end, annual):
    hacs = (1, 2, 3) if annual else (6, 12, 24)
    hac = [{"lags": lag, "interval": [float(v * 10) for v in tl.fit_hac(y, X, lag).conf_int()[1]]} for lag in hacs]
    steps = []
    for year in (2001, 2011):
        if year - start < 5 or end - year + 1 < 5:
            continue
        pos = (year - start) * (1 if annual else 12)
        base = np.delete(X, 1, axis=1)
        shift = (np.arange(len(y)) >= pos).astype(float)
        fit = tl.fit_hac(y, np.column_stack([base, shift]), 2 if annual else 12)
        delta = float(fit.aic - res.aic)
        p = tl.coefficient(fit, -1)["p"]
        if delta <= 0 and p < .05:
            steps.append({"date": f"{year}-01", "change": float(fit.params[-1]), "deltaAic": delta, "pHac": float(p)})
    # Predefined halves, keeping real time and calendar columns; no p-based window selection.
    signs = []
    middle = (start + end + 1) // 2
    if min(middle - start, end - middle + 1) >= (20 if annual else 10):
        count = (middle - start) * (1 if annual else 12)
        for sl in (slice(0, count), slice(count, None)):
            signs.append(float(10 * np.linalg.lstsq(X[sl], y[sl], rcond=None)[0][1]))
    if annual:
        block = tl.annual_bootstrap(y, 3, REPS, (SEED, 990, start, end))
    else:
        block = tl.block_bootstrap(y, X, 1, np.tile(np.arange(1, 13), end - start + 1), 24, REPS, (SEED, 990, start, end))
    return {"residualAcf1": float(np.corrcoef(res.resid[1:], res.resid[:-1])[0, 1]),
            "ljungBoxP": float(acorr_ljungbox(res.resid, lags=[min(12, len(y) // 4)], return_df=True).lb_pvalue.iloc[0]),
            "hacSensitivity": hac, "subperiodSlopes": signs, "steps": steps,
            "blockInterval": [float(10 * block["lo"]), float(10 * block["hi"])]}


def compute(start, end):
    validate_period(start, end)
    fingerprint, hashes = fingerprints()
    enso = enso_values(start, end)
    phase = np.tile(np.arange(12), end - start + 1)
    results = {rid: {} for rid in BOXES}
    for ri, rid in enumerate(BOXES):
        for vi, (vid, name) in enumerate(FILES.items()):
            y = source_series(rid, name, start, end)
            X0, _ = tl.design(len(y), phase + 1)
            X1, _ = tl.design(len(y), phase + 1, {"nino34": enso})
            try:
                base, _ = model(y, X0, phase, False, (SEED, 600, ri * 6 + vi, 0, 0))
                adjusted, fit = model(y, X1, phase, False, (SEED, 600, ri * 6 + vi, 1, 0))
                diag = diagnostics(y, X1, fit, start, end, False)
                results[rid][vid] = {**adjusted, "baseline": base, "diagnostics": diag, "ensoCoefficient": float(fit.params[-1]), "status": "inconclusive"}
            except ValueError as error:
                results[rid][vid] = {"status": "not-evaluable", "reasons": [str(error)]}
        if end - start + 1 >= 20:
            y = source_series(rid, ANNUAL_FILE, start, end, annual=True)
            X = np.column_stack([np.ones(len(y)), np.arange(len(y))])
            try:
                annual, fit = model(y, X, np.zeros(len(y), int), True, (SEED, 601, 2 + ri, 0))
                results[rid][ANNUAL] = {**annual, "baseline": None, "diagnostics": diagnostics(y, X, fit, start, end, True), "status": "inconclusive"}
            except ValueError as error:
                results[rid][ANNUAL] = {"status": "not-evaluable", "reasons": [str(error)]}
    monthly = [results[rid][vid] for rid in BOXES for vid in FILES]
    annual = [results[rid][ANNUAL] for rid in BOXES if ANNUAL in results[rid]]
    for family, entries in (("monthly-18", monthly), ("annual-3", annual)):
        if not entries:
            continue
        # Non-evaluable hypotheses remain in the family with p=1; never shrink the correction after seeing data.
        adjusted = multipletests([r.get("pValue", 1.) for r in entries], method="holm")[1]
        for row, p in zip(entries, adjusted):
            row.update(family=family, familySize=len(entries), pAdjusted=float(p))
            if row["status"] == "not-evaluable":
                continue
            row["reasons"] = []
            if p >= .05:
                row["status"] = "inconclusive"
                row["reasons"].append("Evidencia insuficiente tras Holm; no demuestra ausencia de cambio.")
            elif row["diagnostics"]["steps"]:
                row["status"] = "pending"
                row["reasons"].append("Un escalón en una fecha exploratoria ajusta igual o mejor; requiere contraste independiente.")
            elif any(s * row["slopePerDecade"] <= 0 for s in row["diagnostics"]["subperiodSlopes"]):
                row["status"] = "sensitive"
                row["reasons"].append("El signo cambia entre subperiodos predefinidos.")
            else:
                row["status"] = "consistent"
                row["reasons"].append("Evidencia consistente dentro del modelo y las comprobaciones realizadas.")
        if family.startswith("monthly"):
            basep = multipletests([r.get("baseline", {}).get("pValue", 1.) for r in entries], method="holm")[1]
            for row, p in zip(entries, basep):
                if row.get("baseline"):
                    row["baseline"].update(pAdjusted=float(p), family="monthly-18-without-enso", familySize=len(entries))
    return {"version": VERSION, "start": start, "end": end, "replicates": REPS, "seed": SEED,
            "fingerprint": fingerprint, "inputHashes": hashes, "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=1992)
    parser.add_argument("--end", type=int, default=2024)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--stdin", action="store_true")
    args = parser.parse_args()
    if args.stdin:
        request = json.load(sys.stdin)
        args.start, args.end = request.get("start"), request.get("end")
    validate_period(args.start, args.end)
    fingerprint, _ = fingerprints()
    cache = ROOT / ".cache/trends" / f"{args.start}-{args.end}-{fingerprint}.json"
    if cache.exists():
        bundle = json.loads(cache.read_text())
    else:
        bundle = compute(args.start, args.end)
        cache.parent.mkdir(parents=True, exist_ok=True)
        # Concurrent workers must never read a partially written cache entry.
        with tempfile.NamedTemporaryFile(mode="w", dir=cache.parent, delete=False) as tmp:
            json.dump(bundle, tmp, allow_nan=False, ensure_ascii=False)
        os.replace(tmp.name, cache)
    payload = json.dumps(bundle, allow_nan=False, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n")
    else:
        print(payload)


if __name__ == "__main__":
    main()
