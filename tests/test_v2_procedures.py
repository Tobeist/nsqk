"""Aggregation identity and absence of temporal leakage. Run: python -m unittest tests/test_v2_procedures.py"""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
# The full historical audit needs requirements.txt (matplotlib, shapely, ...), not the API's requirements-analysis.txt.
try:
    import forecast_experiment as fx  # noqa: E402
    import grouping_audit as ga  # noqa: E402
    MISSING = None
except ModuleNotFoundError as error:
    MISSING = error.name



@unittest.skipIf(MISSING, f"requiere requirements.txt (falta {MISSING})")
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


@unittest.skipIf(MISSING, f"requiere requirements.txt (falta {MISSING})")
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


@unittest.skipIf(MISSING, f"requiere requirements.txt (falta {MISSING})")
class SingleOutputTest(unittest.TestCase):
    """After `python scripts/run_analysis.py`, every summary must use the same valid (bootstrap-t) Holm p-values."""

    def test_primary_holm_matches_uncertainty_validation_and_final_status(self):
        out = Path(__file__).resolve().parents[1] / "analysis" / "results"
        trends = pd.read_csv(out / "trend_results.csv")
        uv = pd.read_csv(out / "uncertainty_validation.csv")
        final = pd.read_csv(out / "final_status.csv")
        for family, model in (("F1", "M0"), ("F2", "M1_L0")):
            a = trends[(trends.family == family)].set_index("variable")["p_holm"]
            b = uv[(uv.family == family)].set_index("series")["p_holm_bootstrap"]
            np.testing.assert_allclose(a.sort_index(), b.sort_index())
        f2 = trends[trends.family == "F2"].set_index("variable")["p_holm"]
        for key, p in f2.items():
            row = final[final.result.str.startswith("Tendencia mensual") & final.result.str.contains(fx.ta.VARS[key]["name"], regex=False)]
            self.assertAlmostEqual(float(row.p_holm.iloc[0]), p)
        extremes = pd.read_csv(out / "extremes_trends.csv").set_index("index")["p_holm_family_B"]
        uvb = uv[uv.family == "B"].set_index("series")["p_holm_bootstrap"]
        np.testing.assert_allclose(extremes.sort_index(), uvb.sort_index())
