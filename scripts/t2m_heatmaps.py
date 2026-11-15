"""Statistics and heatmaps for northeast T2M (1992-2024): year x month, daily anomalies, and lagged correlations.

Usage: python scripts/t2m_heatmaps.py. Outputs: analysis/deep/. See docs/DEEP_FORECAST_PROTOCOL.md.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis" / "deep"
RESULTS = ROOT / "data" / "results"
DATES = pd.date_range("1992-01-01", "2024-12-01", freq="MS")
BASE = (1992, 2021)  # fixed climatology already used across the project
SERIES = {"T2M": ("power_t2m_region_1992_2024.json", "°C"), "T2M_MIN": ("power_t2m_min_region_1992_2024.json", "°C"),
          "T2M_MAX": ("power_t2m_max_region_1992_2024.json", "°C"), "PRECTOTCORR": ("power_prectotcorr_region_1992_2024.json", "mm/día"),
          "GPCP": ("giovanni_gpcp_1992_2024.json", "mm/día"), "RX5DAY": ("giovanni_rx5day_1992_2024.json", "mm/5 días")}
MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def load_monthly():
    """All northeast monthly series plus Nino 3.4; fails instead of filling any gap."""
    frame = pd.DataFrame(index=DATES)
    for name, (file, _) in SERIES.items():
        rows = json.loads((RESULTS / file).read_text())["monthly"]
        values = pd.Series([r.get("value", r.get("t2m_c")) for r in rows], index=pd.to_datetime([r["date"] for r in rows]), dtype=float)
        if not values.index.equals(DATES) or not np.isfinite(values).all():
            raise ValueError(f"{name}: incomplete or non-finite monthly series; refusing to interpolate")
        frame[name] = values
    lines = [line.split() for line in (ROOT / "data/external/enso/ersst5.nino.mth.91-20.ascii").read_text().splitlines()[1:] if line.strip()]
    enso = pd.Series({pd.Timestamp(f"{r[0]}-{int(r[1]):02d}-01"): float(r[9]) for r in lines})
    frame["NINO34"] = enso.reindex(DATES)
    if frame["NINO34"].isna().any():
        raise ValueError("Nino 3.4 has gaps in 1992-2024")
    return frame, enso


def anomalies(frame):
    base = frame[(frame.index.year >= BASE[0]) & (frame.index.year <= BASE[1])]
    clim = base.groupby(base.index.month).mean()
    sd = base.groupby(base.index.month).std()
    anom = frame - clim.reindex(frame.index.month).to_numpy()
    z = anom / sd.reindex(frame.index.month).to_numpy()
    return anom, z, clim


def statistics(frame, anom, z):
    t = frame["T2M"]
    app = json.loads((ROOT / "analysis/app/1992-2024.json").read_text())["results"]["mx-northeast"]["temperature"]
    extremes = z["T2M"][z["T2M"].abs() >= 2].sort_values()
    return {
        "series": "NASA POWER T2M, cos(lat)-weighted mean of 15 cells, box [-101,25,-99,27]", "period": "1992-01..2024-12", "months": int(t.size),
        "mean_c": float(t.mean()), "sd_c": float(t.std()), "percentiles_c": {f"p{q}": float(t.quantile(q / 100)) for q in (5, 25, 50, 75, 95)},
        "climatology_1992_2021_by_month_c": {MONTHS[m - 1]: float(v) for m, v in anomalies(frame)[2]["T2M"].items()},
        "anomaly_sd_c": float(anom["T2M"].std()),
        "annual_means_c": {int(y): float(v) for y, v in t.groupby(t.index.year).mean().items()},
        "warmest_year": int(t.groupby(t.index.year).mean().idxmax()), "coolest_year": int(t.groupby(t.index.year).mean().idxmin()),
        "secular_trend_from_app": {"slope_per_decade_c": app["slopePerDecade"], "ci95_bootstrap_t": app["confidenceInterval"],
                                   "p_holm": app["pAdjusted"], "family": app["family"], "status": app["status"],
                                   "model": "monthly OLS + month effects + Nino 3.4, sieve bootstrap-t (docs/APP_TREND_PROTOCOL.md)"},
        "anomalies_abs_z_ge_2": {d.strftime("%Y-%m"): round(float(v), 2) for d, v in extremes.items()},
        "anomalies_abs_z_ge_2_count": int(extremes.size),
        "note": "z = anomaly / sd of that calendar month in 1992-2021. Under normality about 4.6% of months (~18) would exceed |z| >= 2 by chance.",
    }


def heatmap_year_month(frame, anom, z, stats):
    years = sorted(set(frame.index.year))
    values = frame["T2M"].to_numpy().reshape(len(years), 12)
    an = anom["T2M"].to_numpy().reshape(len(years), 12)
    zz = z["T2M"].to_numpy().reshape(len(years), 12)
    fig, axes = plt.subplots(1, 2, figsize=(16, 11), gridspec_kw={"width_ratios": [1, 1.15]})
    im = axes[0].imshow(values, aspect="auto", cmap="inferno")
    fig.colorbar(im, ax=axes[0], orientation="horizontal", fraction=0.035, pad=0.05, label="T2M mensual (°C)")
    lim = np.ceil(np.abs(an).max())
    im2 = axes[1].imshow(an, aspect="auto", cmap="RdBu_r", vmin=-lim, vmax=lim)
    fig.colorbar(im2, ax=axes[1], orientation="horizontal", fraction=0.035, pad=0.05, label="Anomalía respecto a 1992–2021 del mismo mes (°C)")
    for i in range(len(years)):
        for j in range(12):
            axes[1].text(j, i, f"{an[i, j]:+.1f}", ha="center", va="center", fontsize=6.5,
                         color="white" if abs(an[i, j]) > lim * 0.55 else "black")
            if abs(zz[i, j]) >= 2:
                axes[1].add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec="black", lw=1.6))
    annual = an.mean(axis=1)
    for ax in axes:
        ax.set_xticks(range(12))
        ax.set_xticklabels(MONTHS)
        ax.set_yticks(range(len(years)))
        ax.set_yticklabels(years, fontsize=7)
    ax2 = axes[1].twinx()
    ax2.set_ylim(axes[1].get_ylim())
    ax2.set_yticks(range(len(years)))
    ax2.set_yticklabels([f"{a:+.2f}" for a in annual], fontsize=6.5)
    ax2.set_ylabel("Anomalía media anual (°C)")
    tr = stats["secular_trend_from_app"]
    axes[0].set_title(f"T2M noreste (POWER/MERRA-2), 1992–2024\nmedia {stats['mean_c']:.2f} °C · DE {stats['sd_c']:.2f} · p5–p95 "
                      f"{stats['percentiles_c']['p5']:.1f}–{stats['percentiles_c']['p95']:.1f} °C", fontsize=10)
    axes[1].set_title(f"Anomalías por mes calendario; recuadro = |z| ≥ 2 ({stats['anomalies_abs_z_ge_2_count']} meses; ~18 esperables al azar)\n"
                      f"Tendencia: {tr['slope_per_decade_c']:+.3f} °C/década, IC95 [{tr['ci95_bootstrap_t'][0]:+.3f}, {tr['ci95_bootstrap_t'][1]:+.3f}], "
                      f"p Holm {tr['p_holm']:.2f} → {tr['status']}", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "heatmap_t2m_anio_mes.png", dpi=200)
    plt.close(fig)


def heatmap_daily():
    daily = pd.read_csv(ROOT / "data/external/power_daily_t2m/raw/power_daily_temperature_region_1992_2024.csv", parse_dates=["date"]).set_index("date")["t2m_c"]
    if daily.isna().any() or len(daily) != 12054:
        raise ValueError("Daily T2M incomplete; refusing to interpolate")
    doy = daily.index.day_of_year.to_numpy()
    length = np.where(daily.index.is_leap_year, 366, 365)
    phase = (doy - 0.5) / length
    base = np.asarray(daily.index.year <= BASE[1])
    # Smooth daily climatology: 3 harmonics fitted on 1992-2021 (leap days handled through the year fraction).
    H = np.column_stack([np.ones(len(daily))] + [f(2 * np.pi * k * phase) for k in (1, 2, 3) for f in (np.sin, np.cos)])
    beta = np.linalg.lstsq(H[base], daily.to_numpy()[base], rcond=None)[0]
    anom = daily.to_numpy() - H @ beta
    years = np.arange(1992, 2025)
    grid = np.full((len(years), 366), np.nan)
    grid[daily.index.year.to_numpy() - 1992, doy - 1] = anom
    lim = np.nanpercentile(np.abs(anom), 99)
    fig, ax = plt.subplots(figsize=(16, 7))
    im = ax.imshow(grid, aspect="auto", cmap="RdBu_r", vmin=-lim, vmax=lim, interpolation="nearest")
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.01, label="Anomalía diaria (°C) · escala saturada en el percentil 99")
    starts = pd.date_range("2001-01-01", "2001-12-01", freq="MS").day_of_year - 1
    ax.set_xticks(starts)
    ax.set_xticklabels(MONTHS)
    ax.set_yticks(range(0, len(years), 2))
    ax.set_yticklabels(years[::2], fontsize=8)
    ax.set_title("T2M diaria noreste (POWER, días UTC): anomalía respecto a un ciclo anual suave de 1992–2021 (3 armónicos)\n"
                 "Cada fila es un año y cada columna un día del año; el 29 de febrero ocupa la columna 60 en años bisiestos", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "heatmap_t2m_diaria.png", dpi=200)
    plt.close(fig)


def heatmap_correlations(anom):
    names = list(anom.columns)
    corr = anom.corr().to_numpy()
    lags = list(range(0, 13))
    target = anom["T2M"]
    lagged = np.array([[target.corr(anom[n].shift(L)) for L in lags] for n in names])
    fig, axes = plt.subplots(1, 2, figsize=(17, 6.5), gridspec_kw={"width_ratios": [1, 1.6]})
    im = axes[0].imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    for i in range(len(names)):
        for j in range(len(names)):
            axes[0].text(j, i, f"{corr[i, j]:.2f}", ha="center", va="center", fontsize=8, color="white" if abs(corr[i, j]) > 0.6 else "black")
    axes[0].set_xticks(range(len(names)))
    axes[0].set_xticklabels(names, rotation=45, ha="right")
    axes[0].set_yticks(range(len(names)))
    axes[0].set_yticklabels(names)
    axes[0].set_title("Correlación entre anomalías mensuales (1992–2024)", fontsize=10)
    im2 = axes[1].imshow(lagged, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    for i in range(len(names)):
        for j, _ in enumerate(lags):
            axes[1].text(j, i, f"{lagged[i, j]:.2f}", ha="center", va="center", fontsize=7, color="white" if abs(lagged[i, j]) > 0.6 else "black")
    axes[1].set_xticks(range(len(lags)))
    axes[1].set_xticklabels(lags)
    axes[1].set_xlabel("Rezago L (meses): variable en t−L frente a anomalía de T2M en t")
    axes[1].set_yticks(range(len(names)))
    axes[1].set_yticklabels(names)
    axes[1].set_title("Correlación con rezago respecto a la anomalía de T2M (L = 0 es contemporánea; T2M con L ≥ 1 es su autocorrelación)", fontsize=10)
    fig.colorbar(im2, ax=axes, fraction=0.025, pad=0.01, label="r de Pearson")
    fig.savefig(OUT / "heatmap_correlaciones_rezagos.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    return {"contemporaneous": {a: {b: float(corr[i, j]) for j, b in enumerate(names)} for i, a in enumerate(names)},
            "lagged_vs_t2m_anomaly": {n: {str(L): float(lagged[i, k]) for k, L in enumerate(lags)} for i, n in enumerate(names)},
            "note": "Pearson r on anomalies vs 1992-2021 monthly climatology. Descriptive; no significance test, autocorrelated series."}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frame, _ = load_monthly()
    anom, z, _ = anomalies(frame)
    stats = statistics(frame, anom, z)
    heatmap_year_month(frame, anom, z, stats)
    heatmap_daily()
    stats["correlations"] = heatmap_correlations(anom)
    (OUT / "t2m_statistics.json").write_text(json.dumps(stats, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in stats.items() if k not in ("annual_means_c", "correlations", "climatology_1992_2021_by_month_c")}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
