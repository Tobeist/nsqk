"""Download and normalize selected NASA POWER monthly regional variables."""

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import requests

from study_regions import DEFAULT_REGION, data_dir, region_ids, study_box

URL = "https://power.larc.nasa.gov/api/temporal/monthly/regional"
FILL = -999.0
UNITS = {"T2M": "C", "T2M_MIN": "C", "T2M_MAX": "C", "PRECTOTCORR": "mm/day"}


def run(start: int, end: int, output: Path, variable: str = "T2M", region_id: str = DEFAULT_REGION) -> None:
    bbox = study_box(region_id)
    params = {
        "latitude-min": bbox[1], "latitude-max": bbox[3],
        "longitude-min": bbox[0], "longitude-max": bbox[2],
        "parameters": variable, "community": "SB",
        "start": start, "end": end, "format": "JSON",
    }
    response = requests.get(URL, params=params, timeout=120)
    response.raise_for_status()
    data = response.json()
    if data.get("messages") or not data.get("features"):
        raise ValueError(f"POWER returned no usable data: {data.get('messages')}")
    if data.get("parameters", {}).get(variable, {}).get("units") != UNITS[variable]:
        raise ValueError(f"Unexpected {variable} unit; conversion needs review")
    if "MERRA2" not in data.get("header", {}).get("sources", []):
        raise ValueError("Unexpected source; review before comparing with MERRA-2")

    name = variable.lower()
    column = f"{name}_{'c' if UNITS[variable] == 'C' else 'mm_day'}"
    raw = data_dir(output, "raw", region_id) / f"power_{name}_{start}_{end}.json"
    grid = data_dir(output, "processed", region_id) / f"power_{name}_grid_{start}_{end}.csv"
    region = data_dir(output, "processed", region_id) / f"power_{name}_region_{start}_{end}.csv"
    metadata = data_dir(output, "processed", region_id) / f"power_{name}_region_{start}_{end}.metadata.json"
    for path in (raw, grid, region, metadata):
        path.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(response.content)

    rows = []
    by_month = defaultdict(list)
    missing = 0
    for feature in data["features"]:
        lon, lat = feature["geometry"]["coordinates"][:2]
        if not (bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]):
            raise ValueError("Grid point outside requested box")
        weight = math.cos(math.radians(lat))
        for key, value in feature["properties"]["parameter"][variable].items():
            if len(key) != 6 or key[4:] == "13":  # POWER's annual summary
                continue
            month = int(key[4:])
            if not 1 <= month <= 12 or not start <= int(key[:4]) <= end:
                raise ValueError(f"Unexpected time key: {key}")
            date = f"{key[:4]}-{key[4:]}-01"
            valid = value is not None and math.isfinite(value) and value != FILL
            if not valid:
                missing += 1
            rows.append((date, lat, lon, value if valid else ""))
            if valid:
                by_month[date].append((float(value), weight))

    expected = {f"{year}-{month:02d}-01" for year in range(start, end + 1) for month in range(1, 13)}
    actual = {row[0] for row in rows}
    if actual != expected:
        raise ValueError(f"Monthly coverage mismatch; missing={sorted(expected - actual)}, extra={sorted(actual - expected)}")
    with grid.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("date", "latitude", "longitude", column))
        writer.writerows(sorted(rows))
    with region.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("date", column, "valid_grid_cells"))
        for date in sorted(expected):
            values = by_month[date]
            mean = sum(v * w for v, w in values) / sum(w for _, w in values) if values else ""
            writer.writerow((date, f"{mean:.4f}" if values else "", len(values)))

    metadata.write_text(json.dumps({
        "request_url": response.url,
        "source": "NASA POWER monthly regional API",
        "region_id": region_id, "parameter": variable, "units": UNITS[variable], "bbox_wsen": bbox,
        "period": [start, end], "grid_cells": len(data["features"]),
        "months": len(expected), "missing_grid_values": missing,
        "aggregation": "cos(latitude)-weighted mean of returned grid-cell centers inside bbox; no land mask or polygon clipping",
        "time": "calendar month; POWER annual keys YYYY13 excluded",
        "api_header": data["header"],
        "comparison_warning": "POWER processing and grid values are not interchangeable with corresponding Giovanni or GPCP products without validation",
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved {len(data['features'])} grid cells, {len(expected)} months, {missing} missing grid values")
    print(raw, grid, region, metadata, sep="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=2010)
    parser.add_argument("--end", type=int, default=2012)
    parser.add_argument("--output", type=Path, default=Path("data"))
    parser.add_argument("--variable", choices=UNITS, default="T2M")
    parser.add_argument("--region", choices=region_ids(), default=DEFAULT_REGION)
    args = parser.parse_args()
    if args.start > args.end:
        parser.error("--start must not exceed --end")
    run(args.start, args.end, args.output, args.variable, args.region)
