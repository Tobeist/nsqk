"""Download and normalize NASA POWER monthly regional T2M data."""

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import requests


URL = "https://power.larc.nasa.gov/api/temporal/monthly/regional"
BBOX = (-101, 25, -99, 27)  # west, south, east, north
FILL = -999.0


def run(start: int, end: int, output: Path) -> None:
    params = {
        "latitude-min": BBOX[1], "latitude-max": BBOX[3],
        "longitude-min": BBOX[0], "longitude-max": BBOX[2],
        "parameters": "T2M", "community": "SB",
        "start": start, "end": end, "format": "JSON",
    }
    response = requests.get(URL, params=params, timeout=120)
    response.raise_for_status()
    data = response.json()
    if data.get("messages") or not data.get("features"):
        raise ValueError(f"POWER returned no usable data: {data.get('messages')}")
    if data.get("parameters", {}).get("T2M", {}).get("units") != "C":
        raise ValueError("Unexpected T2M unit; conversion needs review")
    if data.get("header", {}).get("sources") != ["MERRA2"]:
        raise ValueError("Unexpected source; review before comparing with MERRA-2")

    raw = output / "raw" / f"power_t2m_{start}_{end}.json"
    grid = output / "processed" / f"power_t2m_grid_{start}_{end}.csv"
    region = output / "processed" / f"power_t2m_region_{start}_{end}.csv"
    metadata = output / "processed" / f"power_t2m_region_{start}_{end}.metadata.json"
    for path in (raw, grid, region, metadata):
        path.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(response.content)

    rows = []
    by_month = defaultdict(list)
    missing = 0
    for feature in data["features"]:
        lon, lat = feature["geometry"]["coordinates"][:2]
        if not (BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]):
            raise ValueError("Grid point outside requested box")
        weight = math.cos(math.radians(lat))
        for key, value in feature["properties"]["parameter"]["T2M"].items():
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
        writer.writerow(("date", "latitude", "longitude", "t2m_c"))
        writer.writerows(sorted(rows))
    with region.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("date", "t2m_c", "valid_grid_cells"))
        for date in sorted(expected):
            values = by_month[date]
            mean = sum(v * w for v, w in values) / sum(w for _, w in values) if values else ""
            writer.writerow((date, f"{mean:.4f}" if values else "", len(values)))

    metadata.write_text(json.dumps({
        "request_url": response.url,
        "source": "NASA POWER monthly regional API; source reported by API: MERRA2",
        "parameter": "T2M", "units": "degC", "bbox_wsen": BBOX,
        "period": [start, end], "grid_cells": len(data["features"]),
        "months": len(expected), "missing_grid_values": missing,
        "aggregation": "cos(latitude)-weighted mean of returned grid-cell centers inside bbox; no land mask or polygon clipping",
        "time": "calendar month; POWER annual keys YYYY13 excluded",
        "api_header": data["header"],
        "comparison_warning": "POWER T2M is not the Giovanni M2TMNXSLV_5_12_4_T2M extraction; compare processing before treating them as interchangeable",
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved {len(data['features'])} grid cells, {len(expected)} months, {missing} missing grid values")
    print(raw, grid, region, metadata, sep="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=2010)
    parser.add_argument("--end", type=int, default=2012)
    parser.add_argument("--output", type=Path, default=Path("data"))
    args = parser.parse_args()
    if args.start > args.end:
        parser.error("--start must not exceed --end")
    run(args.start, args.end, args.output)
