"""Build the audited bundles for every valid full-year period used by the app.

Run after source or method changes, then commit the generated analysis/periods files.
The deployed Next.js server reads these bundles without a Python runtime.
"""
import argparse
import json
import os
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import app_trends

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/periods"


def periods():
    return [(start, end) for start in range(1992, 2016) for end in range(start + 9, 2025)]


def build(period):
    start, end = period
    output = OUTPUT / f"{start}-{end}.json"
    bundle = app_trends.compute(start, end)
    if bundle["fingerprint"] != app_trends.fingerprints()[0]:
        raise RuntimeError(f"Inputs changed while calculating {start}–{end}")
    with tempfile.NamedTemporaryFile(mode="w", dir=OUTPUT, delete=False) as temp:
        json.dump(bundle, temp, allow_nan=False, ensure_ascii=False, separators=(",", ":"))
        temp.write("\n")
    os.replace(temp.name, output)
    return output.name


def verify():
    fingerprint, _ = app_trends.fingerprints()
    expected = periods()
    for start, end in expected:
        path = OUTPUT / f"{start}-{end}.json"
        bundle = json.loads(path.read_text())
        if (bundle["start"], bundle["end"], bundle["fingerprint"], bundle["replicates"]) != (start, end, fingerprint, app_trends.REPS):
            raise RuntimeError(f"Outdated or invalid bundle: {path}")
        if set(bundle["results"]) != set(app_trends.BOXES):
            raise RuntimeError(f"Incomplete regions: {path}")
        variables = set(app_trends.FILES)
        if end - start + 1 >= 20:
            variables.add(app_trends.ANNUAL)
        if any(set(bundle["results"][region]) != variables for region in app_trends.BOXES):
            raise RuntimeError(f"Incomplete variables: {path}")
    print(f"Verified {len(expected)} audited periods with fingerprint {fingerprint}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=3)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if not args.verify_only:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            for i, name in enumerate(pool.map(build, periods()), 1):
                if i % 25 == 0 or i == 300:
                    print(f"{i}/300: {name}", flush=True)
    verify()
