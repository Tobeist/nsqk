"""Reconcile daily and monthly POWER PRECTOTCORR: same product, cells, weights, dates and units; UTC vs LST.

Usage: python scripts/rain_reconciliation.py. Design: docs/ANALISIS_TENDENCIAS_PLAN_V3.md, section 2.
"""

import json
import math

import numpy as np
import pandas as pd

import trend_audit as ta

UTC = ta.DATA / "raw/power_daily_prectotcorr"
LST = ta.DATA / "external/power_daily_prectotcorr_lst"
MONTHLY = ta.DATA / "raw/power_prectotcorr_1992_2024.json"


def daily_cells(folder):
    out = {}
    for year in range(1992, 2025):
        for f in json.loads((folder / f"{year}.json").read_text())["features"]:
            lon, lat = f["geometry"]["coordinates"][:2]
            values = f["properties"]["parameter"]["PRECTOTCORR"]
            out.setdefault((lat, lon), {}).update(values)
    return {k: pd.Series(list(v.values()), index=pd.to_datetime(list(v), format="%Y%m%d")).sort_index().astype(float) for k, v in out.items()}


def monthly_cells():
    out = {}
    for f in json.loads(MONTHLY.read_text())["features"]:
        lon, lat = f["geometry"]["coordinates"][:2]
        values = {k: v for k, v in f["properties"]["parameter"]["PRECTOTCORR"].items() if k[4:] != "13"}
        out[(lat, lon)] = pd.Series(list(values.values()), index=pd.to_datetime(list(values), format="%Y%m")).sort_index().astype(float)
    return out


def regional(cells):
    w = {k: math.cos(math.radians(k[0])) for k in cells}
    return sum(cells[k] * w[k] for k in cells) / sum(w.values())


def describe(diff):
    a = diff.abs()
    return {"max_abs": float(a.max()), "mean_abs": float(a.mean()), "p99_abs": float(a.quantile(0.99)),
            "share_months_abs_gt_0.1": float((a > 0.1).mean()), "top5": {d.strftime("%Y-%m"): round(float(diff[d]), 4) for d in a.nlargest(5).index}}


def rx5day(cells):
    out = {}
    w = {k: math.cos(math.radians(k[0])) for k in cells}
    for year in range(1992, 2025):
        num = 0.0
        for k, s in cells.items():
            v = s[str(year)].to_numpy()
            num += w[k] * max(v[i:i + 5].sum() for i in range(len(v) - 4))
        out[year] = num / sum(w.values())
    return pd.Series(out)


def main():
    utc, lst, mon = daily_cells(UTC), daily_cells(LST), monthly_cells()
    if not (set(utc) == set(lst) == set(mon)) or len(mon) != 15:
        raise ValueError("Grid cells differ between products")
    for cells in (utc, lst):
        for s in cells.values():
            if len(s) != 12054 or (s == -999).any() or s.isna().any():
                raise ValueError("Daily series incomplete or with fill values")
    m_utc = {k: s.resample("MS").mean() for k, s in utc.items()}
    m_lst = {k: s.resample("MS").mean() for k, s in lst.items()}
    reg_mon, reg_utc, reg_lst = regional(mon), regional(m_utc), regional(m_lst)
    processed = pd.read_csv(ta.DATA / "processed/power_prectotcorr_region_1992_2024.csv", parse_dates=["date"]).set_index("date")["prectotcorr_mm_day"]
    result = {
        "cells": len(mon), "weights": "cos(latitude) of cell centres", "units": "mm/day, monthly mean of daily rates (each day weight 1)",
        "a_monthly_api_vs_daily_lst": describe(reg_mon - reg_lst),
        "a_cellwise_monthly_api_vs_daily_lst_max_abs": float(max((mon[k] - m_lst[k]).abs().max() for k in mon)),
        "b_daily_utc_vs_daily_lst_monthly": describe(reg_utc - reg_lst),
        "b_cellwise_daily_utc_vs_lst_monthly_max_abs": float(max((m_utc[k] - m_lst[k]).abs().max() for k in mon)),
        "c_monthly_api_vs_daily_utc": describe(reg_mon - reg_utc),
        "processed_region_csv_vs_recomputed_monthly_max_abs": float((processed - reg_mon).abs().max()),
        "daily_utc_vs_lst_same_day_regional_max_abs_mm": float((regional(utc) - regional(lst)).abs().max()),
        "annual_total_mm_utc_vs_lst_max_abs": float((regional(utc).resample("YS").sum() - regional(lst).resample("YS").sum()).abs().max()),
    }
    rx = pd.DataFrame({"Rx5day_UTC": rx5day(utc), "Rx5day_LST": rx5day(lst)})
    for col in rx:
        fit = np.polyfit(rx.index, rx[col], 1)
        result[f"{col}_ols_slope_per_decade"] = float(10 * fit[0])
    result["Rx5day_UTC_vs_LST_max_abs_mm"] = float((rx["Rx5day_UTC"] - rx["Rx5day_LST"]).abs().max())
    rx.rename_axis("year").to_csv(ta.OUT / "rx5day_utc_vs_lst.csv")
    (ta.OUT / "rain_reconciliation.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
