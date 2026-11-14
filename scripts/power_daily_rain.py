"""Download daily POWER rainfall and derive an annual five-day maximum."""

import argparse
import csv
import datetime as dt
import json
import math
from pathlib import Path

import requests


URL = "https://power.larc.nasa.gov/api/temporal/daily/regional"
BBOX = (-101, 25, -99, 27)
VARIABLE = "PRECTOTCORR"


def run(start: int, end: int, output: Path) -> None:
    raw_dir = output / "raw" / "power_daily_prectotcorr"
    raw_dir.mkdir(parents=True, exist_ok=True)
    grid_path = output / "processed" / f"power_prectotcorr_daily_grid_{start}_{end}.csv"
    index_path = output / "processed" / f"power_rx5day_annual_grid_{start}_{end}.csv"
    region_path = output / "processed" / f"power_rx5day_annual_region_{start}_{end}.csv"
    metadata_path = output / "processed" / f"power_rx5day_annual_region_{start}_{end}.metadata.json"
    grid_path.parent.mkdir(parents=True, exist_ok=True)
    cell_rows, annual_rows, region_rows, requests_used = [], [], [], []
    reference_cells = None

    for year in range(start, end + 1):
        params = {
            "latitude-min": BBOX[1], "latitude-max": BBOX[3],
            "longitude-min": BBOX[0], "longitude-max": BBOX[2],
            "parameters": VARIABLE, "community": "SB", "format": "JSON",
            "start": f"{year}0101", "end": f"{year}1231", "time-standard": "UTC",
        }
        raw_path = raw_dir / f"{year}.json"
        if raw_path.exists():
            content = raw_path.read_bytes()
            data = json.loads(content)
        else:
            response = requests.get(URL, params=params, timeout=120)
            response.raise_for_status()
            content = response.content
            data = response.json()
        header = data.get("header", {})
        if (data.get("messages") or not data.get("features") or
            data.get("parameters", {}).get(VARIABLE, {}).get("units") != "mm/day" or
            header.get("time_standard") != "UTC" or "MERRA2" not in header.get("sources", [])):
            raise ValueError(f"Unexpected POWER response for {year}: {data.get('messages')}")
        days = [(dt.date(year, 1, 1) + dt.timedelta(days=i)) for i in range((dt.date(year + 1, 1, 1) - dt.date(year, 1, 1)).days)]
        expected = {day.strftime("%Y%m%d") for day in days}
        cells = set()
        year_maxima = []
        year_rows = []
        for feature in data["features"]:
            lon, lat = feature["geometry"]["coordinates"][:2]
            if not (BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]):
                raise ValueError(f"Cell outside bbox in {year}")
            cells.add((lat, lon))
            values = feature["properties"]["parameter"][VARIABLE]
            if set(values) != expected:
                raise ValueError(f"Incomplete daily coverage in {year} at {lat},{lon}")
            series = [values[day.strftime("%Y%m%d")] for day in days]
            if any(v is None or not math.isfinite(v) or v == -999 or v < 0 for v in series):
                raise ValueError(f"Missing or invalid daily rainfall in {year} at {lat},{lon}")
            year_rows.extend((day.isoformat(), lat, lon, value) for day, value in zip(days, series))
            # mm/day is the daily mean rate; over one day it is numerically mm.
            maximum = max(sum(series[i:i + 5]) for i in range(len(series) - 4))
            annual_rows.append((year, lat, lon, round(maximum, 4)))
            year_maxima.append((maximum, math.cos(math.radians(lat))))
        if reference_cells is None:
            reference_cells = cells
        elif cells != reference_cells:
            raise ValueError(f"Grid changed in {year}")
        region_mean = sum(v * w for v, w in year_maxima) / sum(w for _, w in year_maxima)
        region_rows.append((year, round(region_mean, 4), len(year_maxima)))
        if not raw_path.exists():
            raw_path.write_bytes(content)
        requests_used.append({"year": year, "request_url": requests.Request("GET", URL, params=params).prepare().url, "api_header": header})
        cell_rows.extend(year_rows)
        print(f"{year}: {len(cells)} cells, {len(days)} days", flush=True)

    for path, header, rows in (
        (grid_path, ("date", "latitude", "longitude", "prectotcorr_mm_day"), cell_rows),
        (index_path, ("year", "latitude", "longitude", "rx5day_mm"), annual_rows),
        (region_path, ("year", "rx5day_mm", "valid_grid_cells"), region_rows),
    ):
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)
    metadata_path.write_text(json.dumps({
        "source": "NASA POWER daily regional API; PRECTOTCORR, UTC",
        "bbox_wsen": BBOX, "period": [start, end], "units_raw": "mm/day", "units_index": "mm",
        "grid_cells": len(reference_cells), "daily_rows": len(cell_rows),
        "index_definition": "For each grid cell and calendar year: maximum sum over five consecutive daily precipitation values; windows do not cross year boundaries. Regional index is cosine-latitude-weighted mean of cellwise annual maxima.",
        "warning": "Derived POWER index, not Giovanni M2SMNXEDI RX5Day; daily POWER processing and definitions may differ.",
        "requests": requests_used,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(grid_path, index_path, region_path, metadata_path, sep="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=1992)
    parser.add_argument("--end", type=int, default=2024)
    parser.add_argument("--output", type=Path, default=Path("data"))
    args = parser.parse_args()
    if args.start > args.end:
        parser.error("--start must not exceed --end")
    run(args.start, args.end, args.output)
