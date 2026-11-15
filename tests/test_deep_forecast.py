"""Leakage and shape checks for the deep forecast experiment. Run: python -m unittest tests/test_deep_forecast.py"""

import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
MISSING = next((m for m in ("torch", "optuna", "matplotlib") if importlib.util.find_spec(m) is None), None)
if not MISSING:
    import deep_forecast as d  # noqa: E402


@unittest.skipIf(MISSING, f"requiere requirements-deep.txt (falta {MISSING})")
class DeepForecastTest(unittest.TestCase):
    def setUp(self):
        self.frame, self.enso = d.load_monthly()

    def test_inputs_ignore_everything_after_the_origin(self):
        origin = d.origin_index(2018)
        a = d.prepare(self.frame, self.enso, origin, 36, "all")
        future = self.frame.copy()
        future.iloc[origin + 1:] += 50
        enso = self.enso.copy()
        enso.loc[self.frame.index[origin - 1]:] += 9  # Nino 3.4 after October of the origin year is unknown
        b = d.prepare(future, enso, origin, 36, "all")
        for key in ("x", "h", "y", "x_new", "h_new", "base_future", "clim_future"):
            np.testing.assert_allclose(a[key], b[key], err_msg=key)

    def test_training_targets_end_by_the_origin_and_early_stop_uses_the_latest(self):
        origin = d.origin_index(2016)
        data = d.prepare(self.frame, self.enso, origin, 24, "temp_enso")
        self.assertEqual(data["x"].shape[1:], (24, 3 + 1 + 4 + 2 + 1))
        self.assertEqual(int(data["early"].sum()), 24)
        self.assertTrue(data["early"][-24:].all() and not data["early"][:-24].any())


if __name__ == "__main__":
    unittest.main()
