"""Shared study-box definitions and region-safe data paths."""

import json
from pathlib import Path


DEFAULT_REGION = "mx-northeast"
CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "study-boxes.json"
BOXES = {box["id"]: box for box in json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["boxes"]}


def region_ids() -> tuple[str, ...]:
    return tuple(BOXES)


def study_box(region_id: str) -> tuple[float, float, float, float]:
    if region_id not in BOXES:
        raise ValueError(f"Unknown study region: {region_id}")
    return tuple(BOXES[region_id]["bbox"])


def data_dir(root: Path, bucket: str, region_id: str) -> Path:
    """Keep the original northeast paths; scope every new region by its ID."""
    study_box(region_id)
    if bucket not in ("raw", "processed", "results"):
        raise ValueError(f"Unknown data bucket: {bucket}")
    base = root / bucket
    return base if region_id == DEFAULT_REGION else base / region_id


def check_region_path(path: Path, root: Path, bucket: str, region_id: str) -> None:
    """Prevent a new region from reading or writing a legacy northeast path."""
    expected = data_dir(root, bucket, region_id).resolve()
    if region_id != DEFAULT_REGION and expected not in path.resolve().parents:
        raise ValueError(f"{region_id} {bucket} path must be inside {expected}: {path}")


def check_source_metadata(source: Path, region_id: str) -> None:
    """Check that a processed regional input carries its own provenance."""
    if region_id == DEFAULT_REGION:
        return  # Historical files predate the region_id metadata field.
    metadata_path = source.with_suffix(".metadata.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("region_id") != region_id or metadata.get("bbox_wsen") != list(study_box(region_id)):
        raise ValueError(f"Region metadata mismatch: {metadata_path}")
