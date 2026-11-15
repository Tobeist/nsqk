"""Download the NOAA CPC monthly Nino 3.4 (ERSSTv5) file unmodified and record its provenance."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

URL = "https://www.cpc.ncep.noaa.gov/data/indices/ersst5.nino.mth.91-20.ascii"
HEADER = "YR   MON  NINO1+2  ANOM   NINO3    ANOM   NINO4    ANOM   NINO3.4  ANOM"


def run(output_dir: Path) -> None:
    response = requests.get(URL, timeout=60)
    response.raise_for_status()
    body = response.content
    lines = body.decode("ascii").splitlines()
    if " ".join(lines[0].split()) != " ".join(HEADER.split()):
        raise ValueError("Unexpected header; the CPC file format changed")
    rows = [line.split() for line in lines[1:] if line.strip()]
    if any(len(r) != 10 for r in rows):
        raise ValueError("Unexpected row width")
    keys = [(int(r[0]), int(r[1])) for r in rows]
    if keys != sorted(set(keys)):
        raise ValueError("Duplicate or unordered months")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "ersst5.nino.mth.91-20.ascii").write_bytes(body)
    metadata = {
        "source": "NOAA Climate Prediction Center, Nino regions SST indices from ERSSTv5",
        "url": URL,
        "downloaded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "http_last_modified": response.headers.get("Last-Modified"),
        "sha256": hashlib.sha256(body).hexdigest(),
        "definition": "Nino 3.4 = SST area average over 5N-5S, 170W-120W; ANOM column = anomaly relative to the fixed 1991-2020 base period",
        "column_used": "NINO3.4 ANOM (monthly, degC, not the 3-month running mean ONI)",
        "first_month": f"{keys[0][0]}-{keys[0][1]:02d}",
        "last_month": f"{keys[-1][0]}-{keys[-1][1]:02d}",
        "rows": len(rows),
        "note": "The latest months can be revised by CPC; the analysis uses only 1991-01 to 2024-12.",
    }
    (output_dir / "ersst5.nino.mth.91-20.metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(rows)} months {metadata['first_month']}..{metadata['last_month']} sha256={metadata['sha256'][:12]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("data/external/enso"))
    run(parser.parse_args().output_dir)
