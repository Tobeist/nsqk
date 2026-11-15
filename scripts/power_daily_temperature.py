"""Download daily POWER T2M and T2M_MAX (UTC) for the study box and build a regional daily series."""

import argparse
import csv
import datetime as dt
import json
import math
from pathlib import Path

import requests

URL = "https://power.larc.nasa.gov/api/temporal/daily/regional"
BBOX = (-101, 25, -99, 27)
VARIABLES = {"T2M": "t2m_c", "T2M_MAX": "t2m_max_c"}


def fetch(variable, year, raw_dir):
    """Return the POWER JSON for one variable-year, reusing the untouched saved copy if present."""
    params = {"latitude-min": BBOX[1], "latitude-max": BBOX[3], "longitude-min": BBOX[0], "longitude-max": BBOX[2],
              "parameters": variable, "community": "SB", "format": "JSON",
              "start": f"{year}0101", "end": f"{year}1231", "time-standard": "UTC"}
    path = raw_dir / variable / f"{year}.json"
    if path.exists():
        content = path.read_bytes()
    else:
        response = requests.get(URL, params=params, timeout=180)
        response.raise_for_status()
        content = response.content
    data = json.loads(content)
    header = data.get("header", {})
    if (data.get("messages") or not data.get("features") or data["parameters"][variable]["units"] != "C"
            or header.get("time_standard") != "UTC" or "MERRA2" not in header.get("sources", [])):
        raise ValueError(f"Unexpected POWER response for {variable} {year}: {data.get('messages')}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(content)
    return data, requests.Request("GET", URL, params=params).prepare().url, header


def run(start, end, output):
    raw_dir = output / "raw"
    region = {}
    requests_used, reference = [], None
    for year in range(start, end + 1):
        days = [dt.date(year, 1, 1) + dt.timedelta(days=i) for i in range((dt.date(year + 1, 1, 1) - dt.date(year, 1, 1)).days)]
        keys = [d.strftime("%Y%m%d") for d in days]
        for variable, column in VARIABLES.items():
            data, url, header = fetch(variable, year, raw_dir)
            cells, sums = set(), [[0.0, 0.0, 0] for _ in days]
            for feature in data["features"]:
                lon, lat = feature["geometry"]["coordinates"][:2]
                if not (BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]):
                    raise ValueError(f"Cell outside bbox in {variable} {year}")
                cells.add((lat, lon))
                values = feature["properties"]["parameter"][variable]
                if set(values) != set(keys):
                    raise ValueError(f"Incomplete daily coverage in {variable} {year} at {lat},{lon}")
                w = math.cos(math.radians(lat))
                for acc, key in zip(sums, keys):
                    v = values[key]
                    if v is not None and math.isfinite(v) and v != -999:  # fill values stay excluded, never zero
                        acc[0] += w * v
                        acc[1] += w
                        acc[2] += 1
            if reference is None:
                reference = cells
            elif cells != reference:
                raise ValueError(f"Grid changed in {variable} {year}")
            for day, (wv, w, n) in zip(days, sums):
                row = region.setdefault(day.isoformat(), {})
                row[column] = round(wv / w, 4) if n else ""
                row[f"{column}_cells"] = n
            requests_used.append({"variable": variable, "year": year, "request_url": url, "api_header": header})
        print(f"{year}: {len(reference)} cells, {len(days)} days", flush=True)
    path = raw_dir / f"power_daily_temperature_region_{start}_{end}.csv"
    columns = ["date"] + [c for col in VARIABLES.values() for c in (col, f"{col}_cells")]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        for date in sorted(region):
            writer.writerow([date] + [region[date][c] for c in columns[1:]])
    (raw_dir / f"power_daily_temperature_region_{start}_{end}.metadata.json").write_text(json.dumps({
        "source": "NASA POWER daily regional API, community SB, time-standard UTC (same convention as data/raw/power_daily_prectotcorr)",
        "variables": {"T2M": "daily mean 2 m air temperature, C", "T2M_MAX": "daily maximum 2 m air temperature, C"},
        "bbox_wsen": BBOX, "period": [start, end], "grid_cells": len(reference),
        "aggregation": "cos(latitude)-weighted mean of returned grid-cell centres; fill value -999 excluded",
        "downloaded_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "requests": requests_used,
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=1992)
    parser.add_argument("--end", type=int, default=2024)
    parser.add_argument("--output", type=Path, default=Path("data/external/power_daily_t2m"))
    args = parser.parse_args()
    run(args.start, args.end, args.output)
