"""Estimate an exploratory linear trend in a complete annual index."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import statsmodels.api as sm


def run(source: Path, output: Path) -> None:
    rows = list(csv.DictReader(source.open(encoding="utf-8", newline="")))
    years = np.array([int(r["year"]) for r in rows])
    if len(years) < 20 or not np.array_equal(years, np.arange(years[0], years[-1] + 1)):
        raise ValueError("At least 20 consecutive years required")
    values = np.array([float(r["rx5day_mm"]) for r in rows])
    if not np.isfinite(values).all():
        raise ValueError("Missing or nonfinite index")
    fit = sm.OLS(values, sm.add_constant(years - years[0])).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    result = {
        "source": "Derived from NASA POWER daily regional PRECTOTCORR",
        "index": "cellwise annual maximum of five consecutive daily rainfall amounts, then latitude-weighted regional mean",
        "period": [int(years[0]), int(years[-1])], "units": "mm",
        "method": "OLS on annual values with intercept and time; HAC covariance with 3 annual lags",
        "trend_mm_per_decade": float(fit.params[1] * 10),
        "ci95_mm_per_decade": (fit.conf_int()[1] * 10).tolist(),
        "p_value_unadjusted": float(fit.pvalues[1]),
        "annual": [{"year": int(y), "rx5day_mm": float(v)} for y, v in zip(years, values)],
        "limitations": ["Not Giovanni RX5Day", "Index uses POWER corrected precipitation", "No multiplicity correction or climate-mode adjustment", "3-lag HAC choice needs sensitivity analysis"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{result['trend_mm_per_decade']:.3f} mm/decade, 95% CI {result['ci95_mm_per_decade']}, p={result['p_value_unadjusted']:.4g}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.source, args.output)
