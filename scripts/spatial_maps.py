"""Giovanni-style lat x lon maps of NASA POWER T2M and PRECTOTCORR over northern/eastern Mexico (1992-2024).

Usage: python scripts/spatial_maps.py [--refresh]. Downloads missing tiles to data/external/power_map/
(unmodified responses + metadata.json) and writes PNGs and spatial_summary.json to analysis/maps/.
Per-cell trend tests are individual and descriptive: no multiple-comparison or spatial-dependence correction.
"""

import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patheffects
from matplotlib.colors import TwoSlopeNorm

import trend_lib as tl

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "external" / "power_map"
OUT = ROOT / "analysis" / "maps"
URL = "https://power.larc.nasa.gov/api/temporal/monthly/regional"
FILL = -999.0
START, END = 1992, 2024
BASE = (1992, 2021)  # fixed climatology already used across the project
N_MONTHS = (END - START + 1) * 12
# Four tiles (each axis 2-10 degrees) mosaic the rectangle [-108, 14, -88, 30] so no cell is empty by construction.
TILES = {"nw": (-108, 20, -98, 30), "sw": (-108, 14, -98, 20), "se": (-98, 14, -88, 22), "ne": (-98, 22, -88, 30)}
VARIABLES = {"T2M": "C", "PRECTOTCORR": "mm/day"}
DLAT, DLON = 0.5, 0.625  # MERRA-2 cell size
SOURCE = "Fuente: NASA POWER (MERRA-2), 0.5°×0.625°. Centros de celda; sin máscara de tierra."
BOXES = json.loads((ROOT / "config" / "study-boxes.json").read_text(encoding="utf-8"))["boxes"]
DPI = 200


def raw_path(variable, tile):
    return RAW / f"power_{variable.lower()}_{tile}_{START}_{END}.json"


def fetch(refresh=False):
    """One request at a time; keeps POWER's bytes untouched and records URL, date, SHA-256 and cell count."""
    RAW.mkdir(parents=True, exist_ok=True)
    meta_path = RAW / "metadata.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {"source": "NASA POWER monthly regional API", "files": {}}
    for variable, unit in VARIABLES.items():
        for tile, (w, s, e, n) in TILES.items():
            path = raw_path(variable, tile)
            if path.exists() and not refresh:
                continue
            params = {"latitude-min": s, "latitude-max": n, "longitude-min": w, "longitude-max": e, "parameters": variable,
                      "community": "SB", "start": START, "end": END, "format": "JSON"}
            url = f"{URL}?{urllib.parse.urlencode(params)}"
            with urllib.request.urlopen(url, timeout=300) as response:  # raises on HTTP errors
                content = response.read()
            data = json.loads(content)
            if data.get("messages") or not data.get("features"):
                raise ValueError(f"POWER returned no usable data for {variable}/{tile}: {data.get('messages')}")
            if data["parameters"][variable]["units"] != unit:
                raise ValueError(f"Unexpected {variable} unit; conversion needs review")
            if "MERRA2" not in data["header"].get("sources", []):
                raise ValueError("Unexpected source; review before comparing with MERRA-2")
            path.write_bytes(content)
            meta["files"][path.name] = {
                "request_url": url, "downloaded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "sha256": hashlib.sha256(content).hexdigest(), "parameter": variable, "units": unit,
                "bbox_wsen": [w, s, e, n], "grid_cells": len(data["features"]), "api_header": data["header"],
            }
            print(f"Downloaded {path.name}: {len(data['features'])} cells")
    meta["notes"] = "Responses saved unmodified. YYYY13 keys are POWER annual means and are ignored; -999 is missing, never zero or interpolated."
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_grid(variable):
    """(lats, lons, cube[lat, lon, month]) from every tile; NaN where a value is -999 or a cell is absent."""
    cells = {}
    for tile in TILES:
        for feature in json.loads(raw_path(variable, tile).read_text())["features"]:
            lon, lat = feature["geometry"]["coordinates"][:2]
            series = np.full(N_MONTHS, np.nan)
            for key, value in feature["properties"]["parameter"][variable].items():
                year, month = int(key[:4]), int(key[4:])
                if month == 13:  # POWER's annual summary
                    continue
                if not (START <= year <= END and 1 <= month <= 12):
                    raise ValueError(f"Unexpected time key: {key}")
                if value is not None and value != FILL:
                    series[(year - START) * 12 + month - 1] = value
            key = (round(lat, 4), round(lon, 4))
            if key in cells and not np.allclose(cells[key], series, equal_nan=True):
                raise ValueError(f"Tiles disagree on shared cell {key}")
            cells[key] = series
    lats = np.array(sorted({k[0] for k in cells}))
    lons = np.array(sorted({k[1] for k in cells}))
    cube = np.full((len(lats), len(lons), N_MONTHS), np.nan)
    for (lat, lon), series in cells.items():
        cube[np.searchsorted(lats, lat), np.searchsorted(lons, lon)] = series
    return lats, lons, cube


def box_mean(lats, lons, cube, bbox):
    """cos(lat)-weighted monthly mean of cell centres inside bbox (edges inclusive), as in scripts/power_t2m.py."""
    w, s, e, n = bbox
    li, lj = (lats >= s) & (lats <= n), (lons >= w) & (lons <= e)
    sub = cube[np.ix_(li, lj)]
    weights = np.broadcast_to(np.cos(np.radians(lats[li]))[:, None, None], sub.shape)
    valid = np.isfinite(sub)
    return (np.where(valid, sub, 0) * weights).sum(axis=(0, 1)) / (weights * valid).sum(axis=(0, 1)), int(li.sum() * lj.sum())


def anomalies(cube):
    """Monthly anomalies against the 1992-2021 calendar-month climatology."""
    by_month = cube.reshape(*cube.shape[:2], -1, 12)
    clim = np.nanmean(by_month[:, :, : BASE[1] - START + 1], axis=2)
    return (by_month - clim[:, :, None, :]).reshape(cube.shape)


def trends(cube):
    """Per-cell OLS slope (units/decade) with 11 month indicators and its individual HAC(12) 95% CI."""
    X, _ = tl.design(N_MONTHS, np.tile(np.arange(1, 13), END - START + 1))
    slope = np.full(cube.shape[:2], np.nan)
    lo, hi = slope.copy(), slope.copy()
    for i, j in np.ndindex(slope.shape):
        y = cube[i, j]
        if not np.isfinite(y).all():  # never fit through gaps
            continue
        res = tl.fit_hac(y, X, 12)
        slope[i, j] = 10 * res.params[1]
        lo[i, j], hi[i, j] = 10 * res.conf_int(0.05)[1]
    return slope, lo, hi


def boundaries():
    """Country and state polygons as lists of (lon, lat) rings, clipped loosely to the map area."""
    rings = []
    for name in ("countries.geojson", "region-states.json"):
        for feature in json.loads((ROOT / "public" / "assets" / name).read_text())["features"]:
            geom = feature["geometry"]
            polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
            for poly in polys:
                for ring in poly:
                    ring = np.asarray(ring)[:, :2]
                    if ring[:, 0].max() > -112 and ring[:, 0].min() < -84 and ring[:, 1].max() > 10 and ring[:, 1].min() < 34:
                        rings.append((ring, name == "countries.geojson"))
    return rings


RINGS = None


def draw(ax, lats, lons, field, cmap, norm, dots=None, boxes=True, labels=True):
    global RINGS
    RINGS = RINGS if RINGS is not None else boundaries()
    lon_edges = np.append(lons - DLON / 2, lons[-1] + DLON / 2)
    lat_edges = np.append(lats - DLAT / 2, lats[-1] + DLAT / 2)
    ax.set_facecolor("#d9d9d9")  # any missing cell shows as grey, never as a value
    mesh = ax.pcolormesh(lon_edges, lat_edges, np.ma.masked_invalid(field), cmap=cmap, norm=norm, shading="flat")
    for ring, country in RINGS:
        ax.plot(ring[:, 0], ring[:, 1], color="k", lw=0.8 if country else 0.35, alpha=0.9 if country else 0.6)
    if dots is not None:
        jj, ii = np.meshgrid(lons, lats)
        ax.scatter(jj[dots], ii[dots], s=1.5 if not labels else 3, c="k", marker=".", linewidths=0,
                   label="IC95 HAC(12) individual excluye 0\n(sin corrección múltiple ni espacial)")
        ax.legend(loc="lower left", fontsize=6, markerscale=4, framealpha=0.85)
    if boxes:
        for box in BOXES:
            w, s, e, n = box["bbox"]
            ax.plot([w, e, e, w, w], [s, s, n, n, s], color="#e7298a", lw=1.4 if labels else 0.8)
            if labels:
                ax.text(w + 0.1, s + 0.1, box["id"], color="#e7298a", fontsize=6, fontweight="bold",
                        path_effects=[patheffects.withStroke(linewidth=2, foreground="white")])
    ax.set_xlim(lon_edges[0], lon_edges[-1])
    ax.set_ylim(lat_edges[0], lat_edges[-1])
    ax.set_aspect(1 / np.cos(np.radians(lats.mean())))
    if labels:
        ax.set_xticks(np.arange(-105, lon_edges[-1], 5))
        ax.set_xlabel("Longitud (°)")
        ax.set_ylabel("Latitud (°)")
    else:
        ax.set_xticks([])
        ax.set_yticks([])
    return mesh


def single_map(path, title, lats, lons, field, cmap, norm, cbar_label, dots=None, note=None):
    fig, ax = plt.subplots(figsize=(8, 6.6))
    mesh = draw(ax, lats, lons, field, cmap, norm, dots)
    fig.colorbar(mesh, ax=ax, shrink=0.8, label=cbar_label, extend="neither" if norm is None else "both")
    ax.set_title(title, fontsize=10)
    fig.text(0.01, 0.01, SOURCE + (f"\n{note}" if note else ""), fontsize=6.5, va="bottom")
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def symmetric(field, q=99):
    vmax = np.nanpercentile(np.abs(field), q)
    return TwoSlopeNorm(0, -vmax, vmax)


DOTS_NOTE = ("Puntos: celdas cuyo IC95 HAC(12) individual excluye 0. Pruebas individuales por celda, SIN corrección por "
             "comparaciones múltiples ni por dependencia espacial; solo descriptivo.")


def variable_maps(variable, lats, lons, cube, summary):
    name = variable.lower()
    unit = "°C" if variable == "T2M" else "mm/día"
    seq = "YlOrRd" if variable == "T2M" else "YlGnBu"
    div = "RdBu_r" if variable == "T2M" else "BrBG"
    mean = cube.mean(axis=2)
    single_map(OUT / f"{name}_mean_1992_2024.png", f"{variable} media {START}–{END} ({unit})", lats, lons, mean,
               seq, None, f"{variable} medio ({unit})")

    slope, lo, hi = trends(cube)
    sig = (lo > 0) | (hi < 0)
    title = (f"Tendencia de {variable} {START}–{END} ({unit}/década), MCO mensual + 11 indicadores de mes\n"
             "Puntos = IC95 HAC(12) individual excluye 0 (sin corrección múltiple ni espacial; descriptivo)")
    single_map(OUT / f"{name}_trend_1992_2024.png", title, lats, lons, slope, div, symmetric(slope),
               f"Pendiente ({unit}/década)", sig, DOTS_NOTE)
    if variable == "PRECTOTCORR":
        pct = 100 * slope / mean
        single_map(OUT / f"{name}_trend_pct_1992_2024.png", title.replace(f"({unit}/década)", "(% de la media por década)"),
                   lats, lons, pct, div, symmetric(pct), "Pendiente (% de la media / década)", sig, DOTS_NOTE)

    anom = anomalies(cube)
    annual = anom.reshape(*anom.shape[:2], -1, 12).mean(axis=3)
    last = annual[:, :, -2:]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6))
    norm = symmetric(last)
    for ax, k, year in zip(axes, (0, 1), (2023, 2024)):
        mesh = draw(ax, lats, lons, last[:, :, k], div, norm)
        ax.set_title(f"{year}", fontsize=10)
    fig.colorbar(mesh, ax=axes, shrink=0.8, label=f"Anomalía anual ({unit})", extend="both")
    fig.suptitle(f"Anomalía de {variable} en 2023 y 2024 respecto a la climatología mensual {BASE[0]}–{BASE[1]}", fontsize=11)
    fig.text(0.01, 0.01, SOURCE, fontsize=6.5)
    fig.savefig(OUT / f"{name}_anomaly_2023_2024.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

    summary[variable] = {
        "units": unit, "cells": int(np.isfinite(mean).sum()), "grid_shape": list(mean.shape), "missing_values": int(np.isnan(cube).sum()),
        "mean_range": [float(np.nanmin(mean)), float(np.nanmax(mean))],
        "trend_per_decade": {"min": float(np.nanmin(slope)), "median": float(np.nanmedian(slope)), "max": float(np.nanmax(slope)),
                             "share_positive": float(np.nanmean(slope > 0)), "share_ci_excludes_zero": float(sig.mean())},
        "anomaly_2023": {"min": float(np.nanmin(last[:, :, 0])), "median": float(np.nanmedian(last[:, :, 0])), "max": float(np.nanmax(last[:, :, 0]))},
        "anomaly_2024": {"min": float(np.nanmin(last[:, :, 1])), "median": float(np.nanmedian(last[:, :, 1])), "max": float(np.nanmax(last[:, :, 1]))},
        "boxes": {},
    }
    if variable == "PRECTOTCORR":
        summary[variable]["trend_pct_per_decade"] = {"min": float(np.nanmin(pct)), "median": float(np.nanmedian(pct)), "max": float(np.nanmax(pct))}
    for box in BOXES:
        w, s, e, n = box["bbox"]
        inside = np.ix_((lats >= s) & (lats <= n), (lons >= w) & (lons <= e))
        summary[variable]["boxes"][box["id"]] = {"cells": int(slope[inside].size), "trend_median": float(np.nanmedian(slope[inside])),
                                                 "anomaly_2024_median": float(np.nanmedian(last[:, :, 1][inside]))}
    return annual


def small_multiples(lats, lons, annual):
    years = list(range(START, END + 1))
    fig, axes = plt.subplots(6, 6, figsize=(14, 11))
    norm = symmetric(annual)
    for ax, k in zip(axes.flat, range(len(years))):
        mesh = draw(ax, lats, lons, annual[:, :, k], "RdBu_r", norm, labels=False)
        ax.set_title(str(years[k]), fontsize=9)
    for ax in axes.flat[len(years):]:
        ax.axis("off")
    fig.colorbar(mesh, ax=axes.flat[len(years):], orientation="horizontal", fraction=0.5, label="Anomalía anual de T2M (°C)",
                 extend="both")
    fig.suptitle(f"Anomalía anual de T2M {START}–{END} respecto a la climatología mensual {BASE[0]}–{BASE[1]}", fontsize=13)
    fig.text(0.01, 0.005, SOURCE + " Cajas del proyecto en magenta.", fontsize=8)
    fig.savefig(OUT / "t2m_annual_anomaly_small_multiples.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def main(refresh=False):
    fetch(refresh)
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {"source": "NASA POWER monthly regional (MERRA-2), 0.5°×0.625°", "period": [START, END], "baseline": list(BASE),
               "tiles_wsen": TILES, "trend_method": "OLS on monthly values + 11 month indicators; slope*10; HAC/Newey-West 12 lags",
               "significance_warning": DOTS_NOTE}
    for variable in VARIABLES:
        lats, lons, cube = load_grid(variable)
        annual = variable_maps(variable, lats, lons, cube, summary)
        if variable == "T2M":
            small_multiples(lats, lons, annual)
    (OUT / "spatial_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote maps to {OUT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="re-download tiles that already exist")
    main(parser.parse_args().refresh)
