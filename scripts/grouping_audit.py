"""Aggregation study with real daily POWER data, ETCCDI extremes, and calendar/ENSO variance decomposition.

Usage: python scripts/grouping_audit.py [--reps 5000]. Design: docs/ANALISIS_TENDENCIAS_PLAN_V2.md, sections 2-4.
"""

import argparse
import json
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

import trend_audit as ta
import trend_lib as tl

DAILY_T = ta.DATA / "external/power_daily_t2m/raw/power_daily_temperature_region_1992_2024.csv"
DAILY_P = ta.DATA / "raw/power_daily_prectotcorr"
DAYS = pd.date_range("1992-01-01", "2024-12-31", freq="D")
BLOCKS = (1, 3, 7, 14)
HAC_LAGS = {"1d": 365, "3d": 122, "7d": 52, "14d": 26, "month": 12, "season": 4, "year": 1}
GROUPINGS = {
    "1d": "día UTC", "3d": "bloques no solapados de 3 días anclados al 1 de enero de cada año",
    "7d": "bloques no solapados de 7 días anclados al 1 de enero", "14d": "bloques no solapados de 14 días anclados al 1 de enero",
    "month": "mes calendario", "season": "DJF (año de enero), MAM, JJA, SON", "year": "año calendario"}


def load_daily():
    t = pd.read_csv(DAILY_T, parse_dates=["date"]).set_index("date")
    if not t.index.equals(DAYS) or (t[["t2m_c_cells", "t2m_max_c_cells"]] != 15).any().any():
        raise ValueError("Daily temperature is incomplete")
    cells, regional = {}, []
    for year in range(1992, 2025):
        data = json.loads((DAILY_P / f"{year}.json").read_text())
        days = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
        keys = days.strftime("%Y%m%d")
        num, den = np.zeros(len(days)), 0.0
        for feature in data["features"]:
            lon, lat = feature["geometry"]["coordinates"][:2]
            values = np.array([feature["properties"]["parameter"]["PRECTOTCORR"][k] for k in keys], float)
            if (values == -999).any() or not np.isfinite(values).all():
                raise ValueError(f"Missing daily rainfall in {year}")
            w = math.cos(math.radians(lat))
            cells.setdefault((lat, lon), []).append(values)
            num += w * values
            den += w
        regional.append(pd.Series(num / den, index=days))
    frame = t[["t2m_c", "t2m_max_c"]].assign(prectotcorr=pd.concat(regional))
    cells = {k: np.concatenate(v) for k, v in cells.items()}
    return frame, cells


def year_length(years):
    return np.where((years % 4 == 0) & ((years % 100 != 0) | (years % 400 == 0)), 366, 365)


def blocks(series, grouping):
    """Block means with valid-day counts, mid-block time in real years and calendar phase."""
    idx = series.index
    year, doy = idx.year.to_numpy(), idx.day_of_year.to_numpy()
    if grouping.endswith("d"):
        key = year * 1000 + (doy - 1) // int(grouping[:-1])
    elif grouping == "month":
        key = year * 100 + idx.month.to_numpy()
    elif grouping == "season":
        season = np.array([0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 0])[idx.month.to_numpy() - 1]
        key = (year + (idx.month.to_numpy() == 12)) * 10 + season
    else:
        key = year
    frame = pd.DataFrame({"key": key, "v": series.to_numpy(), "year": year, "month": idx.month.to_numpy(),
                          "tf": year + (doy - 0.5) / year_length(year)})
    g = frame.groupby("key")
    out = pd.DataFrame({"mean": g["v"].mean(), "n": g["v"].count(), "year": g["year"].min(), "months": g["month"].nunique(), "t": g["tf"].mean()})
    if grouping == "season":
        out["year"] = out.index // 10
        out = out[out["months"] == 3]  # drops DJF 1992 (no Dec 1991) and the lone Dec 2024
    out["phase"] = out["t"] % 1
    return out


def identity_check(series):
    rows = []
    daily_annual = series.groupby(series.index.year).mean()
    for grouping in ("1d", "3d", "7d", "14d", "month"):
        b = blocks(series, grouping)
        weighted = b.groupby("year").apply(lambda d: (d["n"] * d["mean"]).sum() / d["n"].sum())
        unweighted = b.groupby("year")["mean"].mean()
        rows.append({"grouping": grouping, "max_abs_diff_weighted_vs_daily": float((weighted - daily_annual).abs().max()),
                     "max_abs_diff_unweighted_vs_daily": float((unweighted - daily_annual).abs().max()),
                     "blocks_per_year_min": int(b.groupby("year").size().min()), "shortest_block_days": int(b["n"].min())})
        if rows[-1]["max_abs_diff_weighted_vs_daily"] > 1e-10:
            raise AssertionError(f"Aggregation identity fails for {grouping}")
    return rows


def grouping_trend(series, grouping):
    b = blocks(series, grouping)
    y, t = b["mean"].to_numpy(), b["t"].to_numpy()
    cols = [np.ones(len(y)), t - 1992]
    if grouping.endswith("d"):
        cols += [f(2 * np.pi * k * b["phase"].to_numpy()) for k in (1, 2, 3) for f in (np.sin, np.cos)]
    elif grouping == "month":
        m = (b.index % 100).to_numpy()
        cols += [(m == k).astype(float) for k in range(2, 13)]
    elif grouping == "season":
        s = (b.index % 10).to_numpy()
        cols += [(s == k).astype(float) for k in range(1, 4)]
    X = np.column_stack(cols)
    c = tl.coefficient(tl.fit_hac(y, X, HAC_LAGS[grouping]), 1, 10)
    row = {"grouping": grouping, "n_blocks": len(y), "hac_lags": HAC_LAGS[grouping], "slope_per_decade": c["est"],
           "se_per_decade": c["se"], "ci_low": c["lo"], "ci_high": c["hi"], "p_value": c["p"]}
    # The same lag duration (6, 12, 24 months) expressed in each grouping's own observations.
    block_days = {"month": 365.25 / 12, "season": 365.25 / 4, "year": 365.25}.get(grouping) or int(grouping[:-1])
    for months in (6, 12, 24):
        lags = int(round(months * 365.25 / 12 / block_days))
        row[f"hac_lags_{months}m"] = lags
        row[f"se_per_decade_{months}m"] = tl.coefficient(tl.fit_hac(y, X, lags), 1, 10)["se"]
    if grouping.endswith("d"):  # weighting blocks by their valid days removes the short year-end blocks' extra weight
        wls = sm.WLS(y, X, weights=b["n"].to_numpy()).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS[grouping]})
        row["wls_days_slope_per_decade"] = 10 * wls.params[1]
        row["wls_days_se_per_decade"] = 10 * wls.bse[1]
    return row


def calendar_index(idx):
    """Day index on a 365-day calendar; 29 February shares 28 February's index."""
    doy = idx.day_of_year.to_numpy()
    leap = idx.is_leap_year
    return np.where(leap & (doy > 59), doy - 1, doy) - 1


def tx90p(tmax):
    cal = calendar_index(tmax.index)
    years = tmax.index.year.to_numpy()
    values = tmax.to_numpy()
    base = (years >= 1992) & (years <= 2021)
    near = {c: np.isin(cal, [(c + k) % 365 for k in range(-2, 3)]) for c in range(365)}

    def thresholds(mask):
        return np.array([np.percentile(values[mask & near[c]], 90, method="median_unbiased") for c in range(365)])

    full = thresholds(base)
    out = {}
    for y in range(1992, 2025):
        thr = thresholds(base & (years != y)) if y <= 2021 else full
        sel = years == y
        out[y] = 100 * float(np.mean(values[sel] > thr[cal[sel]]))
    return pd.Series(out), full


def cdd(precip):
    out = {}
    for y, s in precip.groupby(precip.index.year):
        run = best = 0
        for dry in (s.to_numpy() < 1.0):
            run = run + 1 if dry else 0
            best = max(best, run)
        out[y] = best
    return pd.Series(out, dtype=float)


def rx5day(cells):
    years = DAYS.year.to_numpy()
    out = {}
    for y in range(1992, 2025):
        sel = years == y
        num = den = 0.0
        for (lat, _), values in cells.items():
            v = values[sel]
            w = math.cos(math.radians(lat))
            num += w * max(v[i:i + 5].sum() for i in range(len(v) - 4))
            den += w
        out[y] = num / den
    return pd.Series(out)


def variance_decomposition(frame_monthly, enso):
    rows = []
    months = ta.DATES.month.to_numpy()
    n34 = ta.lagged(enso, ta.DATES, 0)
    for key in ta.VARS:
        y = frame_monthly[key].to_numpy()
        X, _ = tl.design(len(y), months)
        seasons = np.column_stack([n34 * np.isin(months, ms) for ms in tl.SEASONS.values()])
        specs = {"calendario": X[:, [0] + list(range(2, 13))], "calendario+tendencia": X,
                 "calendario+tendencia+Niño3.4": np.column_stack([X, n34]),
                 "calendario+tendencia+Niño3.4 por estación": np.column_stack([X, seasons])}
        total = sm.OLS(y, np.ones((len(y), 1))).fit().ssr
        prev = 0.0
        for name, Z in specs.items():
            r2 = 1 - sm.OLS(y, Z).fit().ssr / total
            anom_r2 = 1 - sm.OLS(y, Z).fit().ssr / sm.OLS(y, specs["calendario"]).fit().ssr
            rows.append({"variable": key, "model": name, "r2_total": r2, "r2_of_anomaly_variance": anom_r2, "increment_r2_total": r2 - prev})
            prev = r2
    return rows


def figures(frame_monthly, enso, daily, thr, grouping_rows, extremes):
    clim = ta.climatology(frame_monthly)
    fig, ax = plt.subplots(1, 4, figsize=(17, 4))
    base = frame_monthly[(frame_monthly.index.year >= 1992) & (frame_monthly.index.year <= 2021)]
    for a, key in zip(ax[:3], ta.VARS):
        q = base.groupby(base.index.month)[key].quantile([0.1, 0.9]).unstack()
        a.fill_between(range(1, 13), q[0.1], q[0.9], color=ta.BLUE, alpha=0.2, label="Percentiles 10–90 de cada mes")
        a.plot(range(1, 13), clim[key], "o-", color=ta.BLUE, label="Climatología 1992–2021")
        a.set_xticks(range(1, 13))
        a.set_title(ta.VARS[key]["name"].split(" (")[0], fontsize=9)
        a.set_ylabel(ta.VARS[key]["unit"])
        a.legend(fontsize=7)
    cal = calendar_index(daily.index)
    base_d = (daily.index.year <= 2021)
    mean_d = pd.Series(daily["t2m_max_c"].to_numpy()[base_d]).groupby(cal[base_d]).mean()
    ax[3].plot(mean_d.index + 1, mean_d, color=ta.GRAY, lw=0.8, label="Media diaria de T2M_MAX 1992–2021")
    ax[3].plot(np.arange(1, 366), thr, color=ta.ORANGE, lw=1, label="Percentil 90 por fecha (umbral TX90p)")
    ax[3].set_title("T2M_MAX diaria (POWER): ciclo y umbral calendárico", fontsize=9)
    ax[3].set_xlabel("Día del año")
    ax[3].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(ta.FIG / "ciclo_estacional.png", dpi=120)
    plt.close(fig)

    fig, ax = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    n34 = ta.lagged(enso, ta.DATES, 0)
    tmid = (ta.DATES.year + (ta.DATES.month - 0.5) / 12).to_numpy()
    for a, key in zip(ax, ta.VARS):
        anomaly = frame_monthly[key] - clim[key].reindex(frame_monthly.index.month).to_numpy()
        a.plot(tmid, anomaly, color=ta.GRAY, lw=0.7, label="Anomalía observada (clim. 1992–2021)")
        a.axhline(0, color="black", lw=0.5)
        a.set_ylabel(ta.VARS[key]["unit"])
        a.set_title(ta.VARS[key]["name"], fontsize=9)
        b = a.twinx()
        b.fill_between(tmid, 0, n34, where=n34 > 0, color=ta.ORANGE, alpha=0.25, label="Niño 3.4 > 0")
        b.fill_between(tmid, 0, n34, where=n34 < 0, color=ta.BLUE, alpha=0.25, label="Niño 3.4 < 0")
        b.set_ylabel("Niño 3.4 (°C)")
        if key == "t2m":
            a.legend(fontsize=7, loc="upper left")
            b.legend(fontsize=7, loc="upper right")
    fig.tight_layout()
    fig.savefig(ta.FIG / "anomalias_enso.png", dpi=120)
    plt.close(fig)

    order = list(HAC_LAGS)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for a, var in zip(ax, ("t2m_c", "prectotcorr")):
        sel = [r for r in grouping_rows if r["variable"] == var]
        for i, g in enumerate(order):
            r = next(r for r in sel if r["grouping"] == g)
            a.plot([r["ci_low"], r["ci_high"]], [i, i], color=ta.BLUE, lw=2)
            a.plot(r["slope_per_decade"], i, "o", color=ta.BLUE)
        a.axvline(0, color="black", ls="--", lw=0.8)
        a.set_yticks(range(len(order)))
        a.set_yticklabels(order)
        a.invert_yaxis()
        a.set_title(("T2M diaria POWER (°C/década)" if var == "t2m_c" else "PRECTOTCORR diaria POWER (mm/día/década)") + "\nmismo producto y días; IC 95 % HAC ≈ 1 año", fontsize=9)
    fig.tight_layout()
    fig.savefig(ta.FIG / "agrupaciones.png", dpi=120)
    plt.close(fig)

    fig, ax = plt.subplots(1, 3, figsize=(15, 3.8))
    years = np.arange(1992, 2025)
    for a, (name, unit) in zip(ax, (("TX90p", "% de días"), ("CDD", "días"), ("Rx5day", "mm"))):
        y = extremes[name].to_numpy()
        a.plot(years, y, "o-", color=ta.GRAY, ms=3, label="Índice anual (observado en reanálisis)")
        fit = np.polyfit(years, y, 1)
        a.plot(years, np.polyval(fit, years), color=ta.BLUE, label=f"Ajuste MCO {10 * fit[0]:+.3g} {unit}/década")
        a.set_title(f"{name} (POWER diario)", fontsize=9)
        a.set_ylabel(unit)
        a.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(ta.FIG / "extremos.png", dpi=120)
    plt.close(fig)


def main(reps):
    ta.OUT.mkdir(parents=True, exist_ok=True)
    daily, cells = load_daily()
    frame_monthly, enso = ta.load_series(), ta.load_enso()
    identity = []
    for var in ("t2m_c", "prectotcorr"):
        identity += [{"variable": var, **r} for r in identity_check(daily[var])]
    grouping_rows = [{"variable": var, **grouping_trend(daily[var], g)} for var in ("t2m_c", "prectotcorr") for g in HAC_LAGS]
    definitions = []
    for g, text in GROUPINGS.items():
        b = blocks(daily["t2m_c"], g)
        definitions.append({"grouping": g, "definition": text, "blocks": len(b), "days_per_block_min": int(b["n"].min()),
                            "days_per_block_max": int(b["n"].max()), "coverage_rule": "100 % de días válidos; sin faltantes en 1992–2024",
                            "purpose": {"month": "pregunta A (principal), C y D", "year": "resumen visual y pregunta B (índices anuales)",
                                        "season": "descripción de ENSO por estación"}.get(g, "solo estudio de agregación de la pregunta A"),
                            "justification": {"month": "resolución común a los tres productos y a Niño 3.4",
                                              "year": "los índices ETCCDI son anuales; la media anual ponderada coincide con la diaria",
                                              "season": "la teleconexión ENSO depende de la estación",
                                              "1d": "resolución nativa del producto diario"}.get(g, "comparación predefinida; no se elige por p")})
    m = daily.resample("MS").mean()
    coherence = {"t2m_daily_utc_vs_monthly_power_max_abs_diff": float((m["t2m_c"].to_numpy() - frame_monthly["t2m"].to_numpy()).__abs__().max()),
                 "t2m_daily_utc_vs_monthly_power_mean_abs_diff": float(np.abs(m["t2m_c"].to_numpy() - frame_monthly["t2m"].to_numpy()).mean()),
                 "prectotcorr_daily_utc_vs_monthly_power_max_abs_diff": float(np.abs(m["prectotcorr"].to_numpy() - frame_monthly["prectotcorr"].to_numpy()).max()),
                 "prectotcorr_daily_utc_vs_monthly_power_mean_abs_diff": float(np.abs(m["prectotcorr"].to_numpy() - frame_monthly["prectotcorr"].to_numpy()).mean()),
                 "note": "Daily series use UTC days; the monthly POWER API header declares LST."}
    tx, thr = tx90p(daily["t2m_max_c"])
    extremes = pd.DataFrame({"TX90p": tx, "CDD": cdd(daily["prectotcorr"]), "Rx5day": rx5day(cells)})
    repo = pd.read_csv(ta.DATA / "processed/power_rx5day_annual_region_1992_2024.csv").set_index("year")["rx5day_mm"]
    coherence["rx5day_annual_vs_repository_max_abs_diff"] = float((extremes["Rx5day"] - repo).abs().max())
    trends = []
    for i, name in enumerate(extremes.columns):
        y = extremes[name].to_numpy()
        b = tl.annual_bootstrap(y, 3, reps, (ta.SEED, 50, i))
        ts = tl.theil_sen_bootstrap(y[:, None], 3, reps, (ta.SEED, 51, i))
        trends.append({"index": name, "years": len(y), "slope_per_decade": 10 * b["est"], "ci_low": 10 * b["lo"], "ci_high": 10 * b["hi"],
                       "p_bootstrap": b["p"], "theil_sen_per_decade": 10 * ts["est"], "theil_sen_ci_low": 10 * ts["lo"], "theil_sen_ci_high": 10 * ts["hi"]})
    for r, p in zip(trends, multipletests([r["p_bootstrap"] for r in trends], method="holm")[1]):
        r["p_holm_family_B"] = p
        excl = lambda lo, hi: lo > 0 or hi < 0
        consistent = p < 0.05 and excl(r["ci_low"], r["ci_high"]) and np.sign(r["theil_sen_per_decade"]) == np.sign(r["slope_per_decade"])
        r["class"] = "consistente" if consistent else ("sensible a decisiones" if p < 0.05 or excl(r["theil_sen_ci_low"], r["theil_sen_ci_high"]) else "inconcluso")
    decomposition = variance_decomposition(frame_monthly, enso)
    for name, table in (("aggregation_identity", identity), ("grouping_trends", grouping_rows), ("grouping_definitions", definitions),
                        ("extremes_trends", trends), ("variance_decomposition", decomposition)):
        ta.write_table(ta.OUT / f"{name}.csv", table)
    extremes.rename_axis("year").to_csv(ta.OUT / "extremes_annual.csv")
    (ta.OUT / "product_coherence.json").write_text(json.dumps(ta.clean(coherence), indent=1) + "\n", encoding="utf-8")
    figures(frame_monthly, enso, daily, thr, grouping_rows, extremes)
    print(pd.DataFrame(grouping_rows).round(4).to_string(index=False))
    print(pd.DataFrame(trends).round(4).to_string(index=False))
    print(json.dumps(ta.clean(coherence), indent=1))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reps", type=int, default=5000)
    main(parser.parse_args().reps)
