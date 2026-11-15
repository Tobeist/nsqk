"""Linear trend vs level shifts at the documented MERRA-2 stream starts (2001-01, 2011-01), with calendar and Nino 3.4.

Usage: python scripts/form_of_change.py. Design: docs/ANALISIS_TENDENCIAS_PLAN_V3.md, section 3.
"""

import numpy as np
import pandas as pd

import trend_audit as ta
import trend_lib as tl

DATES_STEP = {"2001-01": 2001, "2011-01": 2011}


def compare(label, y, base, t, step_index, hac, scale_t):
    """Fit H0, HL, HS(d), HL+S(d); HAC Wald for each term given the other; AIC is descriptive (assumes iid errors)."""
    rows = []
    n = len(y)
    fits = {"H0": base, "HL": np.column_stack([base, t])}
    for d, pos in step_index.items():
        step = (np.arange(n) >= pos).astype(float)
        fits[f"HS({d})"] = np.column_stack([base, step])
        fits[f"HL+S({d})"] = np.column_stack([base, t, step])
    import statsmodels.api as sm
    aic = {k: sm.OLS(y, X).fit().aic for k, X in fits.items()}
    for name, X in fits.items():
        res = tl.fit_hac(y, X, hac)
        row = {"series": label, "model": name, "aic": aic[name], "delta_aic_vs_HL": aic[name] - aic["HL"]}
        k = base.shape[1]
        if name.startswith("HL"):
            c = tl.coefficient(res, k, scale_t)
            row.update({"trend_per_decade": c["est"], "trend_lo": c["lo"], "trend_hi": c["hi"], "trend_p": c["p"]})
        if "S(" in name:
            c = tl.coefficient(res, X.shape[1] - 1)
            row.update({"step": c["est"], "step_lo": c["lo"], "step_hi": c["hi"], "step_p": c["p"]})
        rows.append(row)
    return rows


def main():
    frame, enso = ta.load_series(), ta.load_enso()
    months = ta.DATES.month.to_numpy()
    n34 = ta.lagged(enso, ta.DATES, 0)
    rows = []
    for key in ta.VARS:
        X, _ = tl.design(396, months, {"nino34": n34})
        base = np.delete(X, 1, axis=1)
        rows += compare(key, frame[key].to_numpy(), base, X[:, 1], {d: (y - 1992) * 12 for d, y in DATES_STEP.items()}, 12, 10)
    ext = pd.read_csv(ta.OUT / "extremes_annual.csv").set_index("year")
    for name in ext.columns:
        y = ext[name].to_numpy()
        rows += compare(name, y, np.ones((len(y), 1)), np.arange(len(y), dtype=float), {d: v - 1992 for d, v in DATES_STEP.items()}, 2, 10)
    out = pd.DataFrame(rows)
    out.to_csv(ta.OUT / "form_of_change.csv", index=False)
    print(out.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
