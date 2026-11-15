"""Download daily POWER PRECTOTCORR in LST (the monthly API's time standard) for the study box, unmodified."""

import argparse
import json
from pathlib import Path

import requests

URL = "https://power.larc.nasa.gov/api/temporal/daily/regional"
BBOX = (-101, 25, -99, 27)


def run(start, end, output):
    output.mkdir(parents=True, exist_ok=True)
    for year in range(start, end + 1):
        path = output / f"{year}.json"
        if path.exists():
            continue
        params = {"latitude-min": BBOX[1], "latitude-max": BBOX[3], "longitude-min": BBOX[0], "longitude-max": BBOX[2],
                  "parameters": "PRECTOTCORR", "community": "SB", "format": "JSON",
                  "start": f"{year}0101", "end": f"{year}1231", "time-standard": "LST"}
        response = requests.get(URL, params=params, timeout=180)
        response.raise_for_status()
        data = response.json()
        if (data.get("messages") or data["header"].get("time_standard") != "LST"
                or data["parameters"]["PRECTOTCORR"]["units"] != "mm/day"):
            raise ValueError(f"Unexpected POWER response for {year}: {data.get('messages')}")
        path.write_bytes(response.content)
        print(year, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=1992)
    parser.add_argument("--end", type=int, default=2024)
    parser.add_argument("--output", type=Path, default=Path("data/external/power_daily_prectotcorr_lst"))
    args = parser.parse_args()
    run(args.start, args.end, args.output)
