"""Sieve (autoregressive) bootstrap-t: valid p-values, bootstrap-t intervals and true coverage of the HAC intervals.

Usage: python scripts/uncertainty_validation.py [--reps 4999]. Design: docs/ANALISIS_TENDENCIAS_PLAN_V3.md, section 1.
"""

import argparse

import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests

import trend_audit as ta
import trend_lib as tl

VARIANTS = {"principal": {"order": "aic", "innov": "resample", "monthly_scale": True},
            "ar1": {"order": 1, "innov": "resample", "monthly_scale": True},
            "gaussiana": {"order": "aic", "innov": "gaussian", "monthly_scale": True},
            "sin_escala_mensual": {"order": "aic", "innov": "resample", "monthly_scale": False}}


def summarize(label, model, est, se, t_obs, tstats, p_order, scale):
    p_boot, q = tl.sieve_pvalue(tstats, t_obs)
    return {"series": label, "model": model, "ar_order": p_order, "slope_per_decade": est * scale, "se_hac_per_decade": se * scale,
            "t_hac": t_obs, "p_normal": float(2 * tl.stats.norm.sf(abs(t_obs))),
            "p_bootstrap": p_boot,
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
                tstats, p = tl.simulate_t(y, X, X_null, months - 1, 12, 12, 12, variant, reps, (ta.SEED, 600, vi, mi, wi))
                rows.append({**summarize(key, model, res.params[1], res.bse[1], res.params[1] / res.bse[1], tstats, p, 10), "variant": variant_name})
            print(key, model, "done", flush=True)
    extremes = pd.read_csv(ta.OUT / "extremes_annual.csv").set_index("year")
    for ei, name in enumerate(extremes.columns):
        y = extremes[name].to_numpy()
        X = np.column_stack([np.ones(len(y)), np.arange(len(y))])
        res = tl.fit_hac(y, X, 2)
        for wi, variant_name in enumerate(("principal", "ar1", "gaussiana")):
            variant = {**VARIANTS[variant_name], "monthly_scale": False}  # annual series: no calendar months
            tstats, p = tl.simulate_t(y, X, X[:, :1], np.zeros(len(y), int), 1, 2, 3, variant, reps, (ta.SEED, 601, ei, wi))
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
