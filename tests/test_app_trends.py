"""Runtime engine parity, fixed families, and source freshness."""
import json
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

import numpy as np
from statsmodels.stats.multitest import multipletests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import app_trends as app
import trend_lib as tl


class AppTrendsTest(unittest.TestCase):
    def test_vectorized_studentization_matches_statsmodels_draw_for_draw(self):
        for annual, with_enso in ((False, False), (False, True), (True, False)):
            y = app.source_series("mx-northeast", app.ANNUAL_FILE if annual else app.FILES["temperature"], 1992, 2024, annual)
            phase = np.zeros(len(y), int) if annual else np.tile(np.arange(12), 33)
            X = (np.column_stack([np.ones(len(y)), np.arange(len(y))]) if annual else
                 tl.design(len(y), phase + 1, {"enso": app.enso_values(1992, 2024)} if with_enso else None)[0])
            args = (y, X, np.delete(X, 1, axis=1), phase, 1 if annual else 12, 2 if annual else 12,
                    3 if annual else 12, {"order": "aic", "innov": "resample", "monthly_scale": not annual}, 257, (12, 53))
            reference, p = tl.simulate_t(*args)
            fast, q = app.fast_simulate_t(*args)
            self.assertEqual(p, q)
            np.testing.assert_allclose(fast, reference, atol=1e-10, rtol=1e-10)
            observed = tl.fit_hac(y, X, 2 if annual else 12)
            self.assertEqual(tl.sieve_pvalue(fast, observed.tvalues[1])[0], tl.sieve_pvalue(reference, observed.tvalues[1])[0])

    def test_committed_bundle_matches_every_current_input_and_family(self):
        bundle = json.loads((ROOT / "analysis/app/1992-2024.json").read_text())
        fingerprint, hashes = app.fingerprints()
        self.assertEqual(bundle["fingerprint"], fingerprint, "Regenerate the app bundle after changing data, code or protocol")
        self.assertEqual(bundle["inputHashes"], hashes)
        for ids in (list(app.FILES), [app.ANNUAL]):
            entries = [bundle["results"][rid][vid] for rid in app.BOXES for vid in ids]
            expected = multipletests([e.get("pValue", 1) for e in entries], method="holm")[1]
            for entry, p in zip(entries, expected):
                self.assertEqual(entry["familySize"], len(entries))
                self.assertAlmostEqual(entry["pAdjusted"], p)
                if p >= .05:
                    self.assertIn(entry["status"], ("inconclusive", "not-evaluable"))
        # Every exported coefficient must use that box's observations and its real frequency.
        for rid in app.BOXES:
            for vid, row in bundle["results"][rid].items():
                annual = vid == app.ANNUAL
                y = app.source_series(rid, app.ANNUAL_FILE if annual else app.FILES[vid], 1992, 2024, annual)
                X = (np.column_stack([np.ones(len(y)), np.arange(len(y))]) if annual else
                     tl.design(len(y), np.tile(np.arange(1, 13), 33), {"enso": app.enso_values(1992, 2024)})[0])
                self.assertAlmostEqual(row["slopePerDecade"], tl.fit_hac(y, X, 2 if annual else 12).params[1] * 10)

    def test_unstable_ar_cannot_produce_a_certainty_label(self):
        y = np.arange(33, dtype=float)
        X = np.column_stack([np.ones(33), y])
        with patch.object(tl, "ar_fit", return_value=(np.array([1.01]), np.ones(32))):
            with self.assertRaisesRegex(ValueError, "estable"):
                app.fast_simulate_t(y, X, X[:, :1], np.zeros(33, int), 1, 2, 3,
                                    {"order": "aic", "innov": "resample", "monthly_scale": False}, 10, (1,))

    def test_period_validation_and_complete_sources(self):
        for start, end in ((1991, 2024), (1992, 2025), (2016, 2024), (True, 2024), (2000.0, 2024)):
            with self.assertRaises(ValueError):
                app.validate_period(start, end)
        app.validate_period(2015, 2024)
        for rid in app.BOXES:
            for name in app.FILES.values():
                self.assertEqual(len(app.source_series(rid, name, 2000, 2014)), 180)

    def test_ten_year_monthly_window_does_not_require_an_annual_family(self):
        bundle = app.compute(2015, 2024)
        self.assertEqual(bundle["start"], 2015)
        for rid, rows in bundle["results"].items():
            self.assertNotIn(app.ANNUAL, rows)
            self.assertEqual(set(rows), set(app.FILES))
            for row in rows.values():
                self.assertEqual(row["familySize"], 18)


if __name__ == "__main__":
    unittest.main()
