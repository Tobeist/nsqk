"""Aggregation identity and absence of temporal leakage. Run: python -m unittest tests/test_v2_procedures.py"""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import forecast_experiment as fx  # noqa: E402
import grouping_audit as ga  # noqa: E402


class AggregationTest(unittest.TestCase):
    def setUp(self):
        days = pd.date_range("1999-01-01", "2001-12-31", freq="D")  # includes the 2000 leap year
        self.series = pd.Series(np.random.default_rng(3).gamma(0.5, 4, len(days)), index=days)

    def test_weighted_block_means_reproduce_daily_annual_mean(self):
        for row in ga.identity_check(self.series):
            self.assertLess(row["max_abs_diff_weighted_vs_daily"], 1e-10)

    def test_unweighted_block_means_do_not(self):
        rows = {r["grouping"]: r for r in ga.identity_check(self.series)}
        self.assertGreater(rows["7d"]["max_abs_diff_unweighted_vs_daily"], 1e-6)

    def test_blocks_restart_each_year_and_keep_leap_day(self):
        b = ga.blocks(self.series, "7d")
        self.assertEqual(b.groupby("year")["n"].sum().loc[2000], 366)
        self.assertEqual(b.groupby("year")["n"].last().loc[2000], 2)

    def test_incomplete_seasons_are_dropped(self):
        b = ga.blocks(self.series, "season")
        self.assertTrue((b["months"] == 3).all())
        self.assertNotIn(1999 * 10 + 0, b.index)  # DJF 1999 lacks December 1998


class LeakageTest(unittest.TestCase):
    def test_simple_forecasts_ignore_test_period_values(self):
        data = fx.dataset()
        train, test = fx.split(data, "t2m", 2017, 2018)
        self.assertLess(train.index.max(), test.index.min())
        changed = test.assign(y=test["y"] + 100)
        for model in ("CLIM", "PERSIST", "OLS_TREND", "OLS_ENSO_OPER"):
            np.testing.assert_allclose(fx.forecast_simple(model, train, test)[0], fx.forecast_simple(model, train, changed)[0])

    def test_operational_enso_is_known_at_issue_time(self):
        data = fx.dataset()
        enso = fx.ta.load_enso()
        jan_2018 = data.loc["2018-01-01":"2018-12-01", "n34_oper"]
        self.assertTrue((jan_2018 == enso.loc["2017-12-01"]).all())


if __name__ == "__main__":
    unittest.main()
