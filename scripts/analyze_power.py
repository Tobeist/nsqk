"""Exploratory seasonal HAC trends for POWER regional monthly series."""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import statsmodels.api as sm


def run(source: Path, output: Path, product_source: str = "POWER") -> None:
    with source.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = [c for c in reader.fieldnames if c not in ("date", "valid_grid_cells")]
        if len(columns) != 1:
            raise ValueError("Expected one measurement column")
        column = columns[0]
        rows = list(reader)
    dates = [r["date"] for r in rows]
    if not dates or dates != sorted(set(dates)):
        raise ValueError("Missing, duplicate, or unordered dates")
    years = np.array([int(d[:4]) for d in dates])
    months = np.array([int(d[5:7]) for d in dates])
    expected = [f"{y}-{m:02d}-01" for y in range(years[0], years[-1] + 1) for m in range(1, 13)]
    if dates != expected or len(rows) < 120:
        raise ValueError("At least ten complete calendar years required")
    if any(not r[column] for r in rows):
        raise ValueError("Missing values; review before analysis")
    values = np.array([float(r[column]) for r in rows])
    if not np.isfinite(values).all():
        raise ValueError("Nonfinite values")
    baseline = (years >= 1992) & (years <= 2021)
    if baseline.sum() != 360:
        raise ValueError("Fixed 1992-2021 baseline requires 360 months")
    normal = {m: float(values[baseline & (months == m)].mean()) for m in range(1, 13)}
    anomaly = [float(v - normal[m]) for v, m in zip(values, months)]
    design = np.column_stack([np.ones(len(values)), np.arange(len(values)) / 12,
                              *[(months == m).astype(float) for m in range(2, 13)]])
    fit = sm.OLS(values, design).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
    annual = defaultdict(list)
    for y, v in zip(years, values):
        annual[int(y)].append(float(v))
    result = {
        "source": "NASA POWER monthly regional API" if product_source == "POWER" else "NASA Giovanni area-averaged monthly CSV",
        "measurement": column,
        "bbox_wsen": [-101, 25, -99, 27],
        "period": [int(years[0]), int(years[-1])],
        "baseline": "1992-2021 monthly climatology",
        "method": "OLS with linear time and 11 month indicators; HAC covariance with 12 monthly lags",
        "trend_per_decade": float(fit.params[1] * 10),
        "trend_ci95_per_decade": (fit.conf_int()[1] * 10).tolist(),
        "p_value_unadjusted": float(fit.pvalues[1]),
        "n_months": len(rows),
        "monthly": [{"date": d, "value": float(v), "anomaly": a} for d, v, a in zip(dates, values, anomaly)],
        "annual": [{"year": y, "mean_monthly_value": float(np.mean(v))} for y, v in sorted(annual.items())],
        "limitations": ["Exploratory single-variable result", "No multiple-testing correction or ENSO/PDO adjustment", "Spatial and product definitions must be checked before cross-source comparisons"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{column}: {result['trend_per_decade']:.4f}/decade, CI {result['trend_ci95_per_decade']}, p={result['p_value_unadjusted']:.4g}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--product-source", choices=("POWER", "Giovanni"), default="POWER")
    args = parser.parse_args()
    run(args.source, args.output, args.product_source)
