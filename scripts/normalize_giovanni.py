"""Normalize an area-averaged monthly CSV exported by NASA Giovanni."""

import argparse
import csv
import json
import math
from pathlib import Path


VARIABLES = {
    "GPCPMON_3_3_sat_gauge_precip": ("gpcp_mm_day", "mm/day"),
    "M2SMNXEDI_2_RX5Day": ("rx5day_mm_per_5days", "mm per 5 days"),
}


def run(source: Path, output: Path, metadata_path: Path, variable: str) -> None:
    with source.open(encoding="utf-8-sig", newline="") as handle:
        raw_rows = list(csv.reader(handle))
    header_index = next((i for i, row in enumerate(raw_rows) if row and row[0].strip() == "time"), None)
    if header_index is None or len(raw_rows[header_index]) != 2:
        raise ValueError("Giovanni time-series header not found")
    expected_column = f"mean_{variable}"
    if raw_rows[header_index][1].strip() != expected_column:
        raise ValueError("Unexpected variable column")
    metadata = {row[0].rstrip(":").strip(): row[1].strip() for row in raw_rows[:header_index] if len(row) == 2 and row[0].strip()}
    if variable not in metadata.get("URL to Reproduce Results", ""):
        raise ValueError("Variable mismatch in reproduction URL")
    if metadata.get("User Bounding Box") != "-101,25,-99,27":
        raise ValueError("Unexpected user bounding box")
    fill_key = f"Fill Value ({expected_column})"
    fill = float(metadata[fill_key])
    rows = []
    missing = 0
    for row in raw_rows[header_index + 1:]:
        if not row or not any(x.strip() for x in row):
            continue
        if len(row) != 2:
            raise ValueError(f"Unexpected data row: {row}")
        date = row[0][:10]
        if row[0][10:] != " 00:00:00" or date[7:] != "-01":
            raise ValueError(f"Unexpected monthly timestamp: {row[0]}")
        value = float(row[1])
        valid = math.isfinite(value) and value != fill
        if not valid:
            missing += 1
        rows.append((date, value if valid else ""))
    dates = [row[0] for row in rows]
    if dates != sorted(set(dates)):
        raise ValueError("Dates must be ordered and unique")
    start = metadata["User Start Date"][:7]
    end = metadata["User End Date"][:7]
    expected = [f"{year}-{month:02d}-01" for year in range(int(start[:4]), int(end[:4]) + 1)
                for month in range(1, 13) if start <= f"{year}-{month:02d}" <= end]
    if dates != expected:
        raise ValueError(f"Incomplete series: expected {len(expected)} months, got {len(dates)}")
    column, units = VARIABLES[variable]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("date", column))
        writer.writerows(rows)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps({
        "source": "NASA Giovanni area-averaged time series CSV",
        "variable": variable, "units": units,
        "source_file": str(source), "original_metadata": metadata,
        "months": len(rows), "missing_months": missing,
        "note": "Unit from Giovanni plot description; original CSV contains no machine-readable units field. Spatial averaging performed by Giovanni, not our POWER pipeline.",
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{variable}: {len(rows)} months, {missing} missing; {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("metadata", type=Path)
    parser.add_argument("--variable", required=True, choices=VARIABLES)
    args = parser.parse_args()
    run(args.source, args.output, args.metadata, args.variable)
