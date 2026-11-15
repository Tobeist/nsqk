"""Self-checks for scripts/trend_lib.py. Run: python -m unittest tests/test_trend_lib.py"""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import trend_lib as tl  # noqa: E402

MONTHS = np.tile(np.arange(1, 13), 30)
SEASONAL = np.tile(np.sin(np.arange(12) * 2 * np.pi / 12) * 5, 30)


class TrendLibTest(unittest.TestCase):
    def test_noise_free_slope_is_recovered(self):
        n = len(MONTHS)
        y = 3 + 0.25 * np.arange(n) / 12 + SEASONAL
        X, _ = tl.design(n, MONTHS)
        self.assertAlmostEqual(tl.fit_hac(y, X, 12).params[1], 0.25, places=10)
        self.assertAlmostEqual(tl.seasonal_theil_sen(y.reshape(-1, 12)), 0.25, places=10)

    def test_monthly_slope_equals_annual_means_slope(self):
        rng = np.random.default_rng(1)
        y = SEASONAL + rng.standard_normal(len(MONTHS))
        X, _ = tl.design(len(y), MONTHS)
        annual = np.polyfit(np.arange(30), y.reshape(-1, 12).mean(axis=1), 1)[0]
        self.assertAlmostEqual(tl.fit_hac(y, X, 12).params[1], annual, places=10)

    def test_block_bootstrap_matches_hac_scale_on_white_noise(self):
        rng = np.random.default_rng(2)
        y = SEASONAL + rng.standard_normal(len(MONTHS))
        X, _ = tl.design(len(y), MONTHS)
        boot = tl.block_bootstrap(y, X, 1, MONTHS, 12, 2000, (1, 2, 3))
        self.assertLess(abs(boot["se"] / tl.fit_hac(y, X, 12).bse[1] - 1), 0.25)

    def test_block_bootstrap_rejects_partial_years(self):
        X, _ = tl.design(len(MONTHS), MONTHS)
        with self.assertRaises(ValueError):
            tl.block_bootstrap(np.zeros(len(MONTHS)), X, 1, MONTHS, 10, 10, (1,))


if __name__ == "__main__":
    unittest.main()
