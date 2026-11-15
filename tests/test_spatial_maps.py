"""Map grid reproduces the northeast regional T2M series. Run: python -m unittest tests/test_spatial_maps.py"""

import json
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import spatial_maps as sm  # noqa: E402


class SpatialMapsTest(unittest.TestCase):
    def test_northeast_box_matches_regional_series(self):
        lats, lons, cube = sm.load_grid("T2M")
        bbox = next(b["bbox"] for b in sm.BOXES if b["id"] == "mx-northeast")
        series, cells = sm.box_mean(lats, lons, cube, bbox)
        reference = json.loads((ROOT / "data/results/power_t2m_region_1992_2024.json").read_text())
        expected = np.array([row["t2m_c"] for row in reference["monthly"]])
        self.assertEqual(cells, 15)
        self.assertEqual(len(series), len(expected))
        self.assertLessEqual(np.abs(series - expected).max(), 1e-3)

    def test_grid_is_complete(self):
        for variable in sm.VARIABLES:
            _, _, cube = sm.load_grid(variable)
            self.assertFalse(np.isnan(cube).any(), variable)


if __name__ == "__main__":
    unittest.main()
