"""Sieve (autoregressive) bootstrap-t: valid p-values, bootstrap-t intervals and true coverage of the HAC intervals.

Usage: python scripts/uncertainty_validation.py [--reps 4999]. Design: docs/ANALISIS_TENDENCIAS_PLAN_V3.md, section 1.
"""

import argparse

import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests
from statsmodels.tsa.ar_model import AutoReg, ar_select_order

import trend_audit as ta
import trend_lib as tl

WARMUP = 200
VARIANTS = {"principal": {"order": "aic", "innov": "resample", "monthly_scale": True},
            "ar1": {"order": 1, "innov": "resample", "monthly_scale": True},
            "gaussiana": {"order": "aic", "innov": "gaussian", "monthly_scale": True},
            "sin_escala_mensual": {"order": "aic", "innov": "resample", "monthly_scale": False}}


def ar_fit(resid, max_order, order):
    if order == "aic":
        lags = ar_select_order(resid, maxlag=max_order, trend="n", ic="aic").ar_lags
        p = max(lags) if lags else 0
    else:
        p = order
    if p == 0:
        return np.array([]), resid.copy()
    res = AutoReg(resid, lags=p, trend="n").fit()
    return np.asarray(res.params), np.asarray(res.resid)  # innovations for observations p..n-1


def simulate_t(y, X_full, X_null, season, period, hac, max_order, variant, reps, key):
    """Bootstrap distribution of t = beta_t / SE_HAC under the no-trend null with AR(p) errors."""
    null_fit = np.linalg.lstsq(X_null, y, rcond=None)[0]
    fitted = X_null @ null_fit
    resid = y - fitted
    phi, innov = ar_fit(resid, max_order, variant["order"])
    p = len(phi)
    season_innov = season[p:]
    if variant["monthly_scale"]:
        sd = pd.Series(innov).groupby(season_innov).std().reindex(range(period)).to_numpy()
        z = innov / sd[season_innov]
    else:
        sd = np.full(period, innov.std())
        z = innov / innov.std()
    rng = np.random.default_rng(list(key))
    n = len(y)
    total = n + WARMUP
    phase = (season[0] + np.arange(total) - WARMUP) % period if period > 1 else np.zeros(total, int)
    draws = rng.standard_normal((reps, total)) if variant["innov"] == "gaussian" else rng.choice(z, size=(reps, total))
    shocks = draws * sd[phase]
    e = np.zeros((reps, total))
    for i in range(total):
        acc = shocks[:, i].copy()
        for j in range(p):
            if i - j - 1 >= 0:
                acc += phi[j] * e[:, i - j - 1]
        e[:, i] = acc
    e = e[:, WARMUP:]
    tstats = np.empty(reps)
    for b in range(reps):
        res = tl.fit_hac(fitted + e[b], X_full, hac)
        tstats[b] = res.params[1] / res.bse[1]
    return tstats, p


def summarize(label, model, est, se, t_obs, tstats, p_order, scale):
    q = np.percentile(np.abs(tstats), 95)
    return {"series": label, "model": model, "ar_order": p_order, "slope_per_decade": est * scale, "se_hac_per_decade": se * scale,
            "t_hac": t_obs, "p_normal": float(2 * tl.stats.norm.sf(abs(t_obs))),
            "p_bootstrap": float((1 + np.sum(np.abs(tstats) >= abs(t_obs))) / (len(tstats) + 1)),
            "q_star_95": float(q), "ci_boot_t_low": (est - q * se) * scale, "ci_boot_t_high": (est + q * se) * scale,
            "coverage_of_nominal_hac95": float(np.mean(np.abs(tstats) <= tl.Z975))}


def main(reps):
    frame, enso = ta.load_series(), ta.load_enso()
    months = ta.DATES.month.to_numpy()
    n34 = ta.lagged(enso, ta.DATES, 0)
    rows = []
    for vi, key in enumerate(ta.VARS):
        y = frame[key].to_numpy()
        for mi, (model, extras) in enumerate((("M0", {}), ("M1_L0", {"nino34": n34}))):
            X, _ = tl.design(len(y), months, extras)
            X_null = np.delete(X, 1, axis=1)
            res = tl.fit_hac(y, X, 12)
            for wi, (variant_name, variant) in enumerate(VARIANTS.items()):
                tstats, p = simulate_t(y, X, X_null, months - 1, 12, 12, 12, variant, reps, (ta.SEED, 600, vi, mi, wi))
                rows.append({**summarize(key, model, res.params[1], res.bse[1], res.params[1] / res.bse[1], tstats, p, 10), "variant": variant_name})
            print(key, model, "done", flush=True)
    extremes = pd.read_csv(ta.OUT / "extremes_annual.csv").set_index("year")
    for ei, name in enumerate(extremes.columns):
        y = extremes[name].to_numpy()
        X = np.column_stack([np.ones(len(y)), np.arange(len(y))])
        res = tl.fit_hac(y, X, 2)
        for wi, variant_name in enumerate(("principal", "ar1", "gaussiana")):
            variant = {**VARIANTS[variant_name], "monthly_scale": False}  # annual series: no calendar months
            tstats, p = simulate_t(y, X, X[:, :1], np.zeros(len(y), int), 1, 2, 3, variant, reps, (ta.SEED, 601, ei, wi))
            rows.append({**summarize(name, "OLS_anual", res.params[1], res.bse[1], res.params[1] / res.bse[1], tstats, p, 10), "variant": variant_name})
    out = pd.DataFrame(rows)
    out["family"], out["p_holm_bootstrap"] = "exploratory", np.nan
    for family, sel in (("F1", (out.model == "M0") & (out.variant == "principal")),
                        ("F2", (out.model == "M1_L0") & (out.variant == "principal")),
                        ("B", (out.model == "OLS_anual") & (out.variant == "principal"))):
        out.loc[sel, "family"] = family
        out.loc[sel, "p_holm_bootstrap"] = multipletests(out.loc[sel, "p_bootstrap"], method="holm")[1]
    out.to_csv(ta.OUT / "uncertainty_validation.csv", index=False)
    print(out.round(4).to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reps", type=int, default=4999)
    main(parser.parse_args().reps)
