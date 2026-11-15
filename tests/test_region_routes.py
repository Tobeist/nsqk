"""Guard against mixing climate inputs or outputs between study boxes."""

import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from study_regions import check_region_path, check_source_metadata, data_dir, study_box  # noqa: E402


class RegionRoutesTest(unittest.TestCase):
    def test_legacy_paths_stay_usable(self):
        root = Path("data")
        self.assertEqual(data_dir(root, "processed", "mx-northeast"), root / "processed")
        self.assertEqual(study_box("mx-northeast"), (-101, 25, -99, 27))

    def test_new_region_cannot_use_legacy_or_other_region_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            region = "mx-chihuahua-interior"
            valid = data_dir(root, "processed", region) / "series.csv"
            valid.parent.mkdir(parents=True)
            check_region_path(valid, root, "processed", region)
            for invalid in (root / "processed" / "series.csv",
                            root / "processed" / "mx-south-humid" / "series.csv"):
                with self.subTest(path=invalid), self.assertRaises(ValueError):
                    check_region_path(invalid, root, "processed", region)

    def test_analysis_requires_matching_source_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "series.csv"
            metadata = source.with_suffix(".metadata.json")
            metadata.write_text(json.dumps({
                "region_id": "mx-chihuahua-interior",
                "bbox_wsen": [-107, 28, -105, 30],
            }), encoding="utf-8")
            check_source_metadata(source, "mx-chihuahua-interior")
            with self.assertRaises(ValueError):
                check_source_metadata(source, "mx-south-humid")


if __name__ == "__main__":
    unittest.main()
