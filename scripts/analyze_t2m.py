"""Analyze a complete monthly regional POWER T2M series."""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import statsmodels.api as sm


def run(source: Path, output: Path) -> None:
    rows = list(csv.DictReader(source.open(encoding="utf-8", newline="")))
    dates = [r["date"] for r in rows]
    if len(set(dates)) != len(dates) or dates != sorted(dates):
        raise ValueError("Dates must be unique and ordered")
    if not rows or any(not r["t2m_c"] for r in rows):
        raise ValueError("Missing monthly values; review before analysis")
    years = np.array([int(date[:4]) for date in dates])
    months = np.array([int(date[5:7]) for date in dates])
    expected = [f"{year}-{month:02d}-01" for year in range(years[0], years[-1] + 1) for month in range(1, 13)]
    if dates != expected or len(dates) < 120:
        raise ValueError("Analysis requires at least ten complete calendar years")
    values = np.array([float(r["t2m_c"]) for r in rows])
    if not np.isfinite(values).all():
        raise ValueError("Nonfinite temperature")

    # Reference climatology fixed before looking at the result: 1992-2021.
    baseline = (years >= 1992) & (years <= 2021)
    if baseline.sum() != 360:
        raise ValueError("The fixed 1992-2021 climatology needs 360 months")
    normal = {m: float(values[baseline & (months == m)].mean()) for m in range(1, 13)}
    anomaly = np.array([v - normal[m] for v, m in zip(values, months)])

    t_years = np.arange(len(values)) / 12
    seasonal = np.column_stack([(months == m).astype(float) for m in range(2, 13)])
    design = np.column_stack([np.ones(len(values)), t_years, seasonal])
    fit = sm.OLS(values, design).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
    slope = float(fit.params[1] * 10)
    ci = (fit.conf_int(alpha=0.05)[1] * 10).tolist()
    annual = defaultdict(list)
    for year, value in zip(years, values):
        annual[int(year)].append(float(value))
    result = {
        "source": "NASA POWER monthly regional T2M; API reports MERRA2",
        "region_bbox_wsen": [-101, 25, -99, 27],
        "period": [int(years[0]), int(years[-1])],
        "units": "degC",
        "baseline": "1992-2021 calendar-month means",
        "method": "OLS with linear time and 11 month indicators; HAC/Newey-West covariance, 12 monthly lags",
        "trend_c_per_decade": slope,
        "trend_ci95_c_per_decade": ci,
        "p_value_unadjusted": float(fit.pvalues[1]),
        "n_months": len(values),
        "monthly": [{"date": date, "t2m_c": float(v), "anomaly_c": float(a)} for date, v, a in zip(dates, values, anomaly)],
        "annual": [{"year": year, "mean_t2m_c": float(np.mean(vals))} for year, vals in sorted(annual.items())],
        "limitations": ["POWER processing has not been cross-checked against Giovanni T2M", "bbox grid-center mean, not a Mexico state polygon", "no ENSO/PDO adjustment or multiple-testing correction"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{slope:.3f} °C/decade; 95% CI [{ci[0]:.3f}, {ci[1]:.3f}]; p={fit.pvalues[1]:.4g}")
    print(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.source, args.output)
