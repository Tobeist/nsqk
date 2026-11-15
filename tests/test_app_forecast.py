"""Temporal isolation and source/metric checks for the app forecast artifact."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import app_forecast as f


class AppForecastTest(unittest.TestCase):
    def test_future_values_cannot_change_selection_or_first_test_forecast(self):
        values, unit, nonnegative, source = f.load_series("mx-northeast", "temperature")
        original = f.evaluate_series(values, unit, nonnegative, source)
        changed = values.copy()
        changed[(2021 - 1992) * 12:] += 10
        altered = f.evaluate_series(changed, unit, nonnegative, source)
        self.assertEqual(original["selectedModel"], altered["selectedModel"])
        self.assertEqual(original["selectedNeuralConfig"], altered["selectedNeuralConfig"])
        self.assertEqual(original["neuralConfigurations"], altered["neuralConfigurations"])
        for model, other in zip(original["models"], altered["models"]):
            self.assertEqual(model["validationMae"], other["validationMae"])
            self.assertEqual(model["intervalRadius80"], other["intervalRadius80"])
        for a, b in zip(original["holdout"][:12], altered["holdout"][:12]):
            for key in ("value", "neuralValue", "climatologyValue", "lower", "upper"):
                self.assertEqual(a[key], b[key])
        # Later observed years legitimately affect subsequent refits and the final 2025 projection.
        self.assertNotEqual(original["projection"], altered["projection"])

    def test_cycle_is_learned_only_from_training_and_rain_is_nonnegative(self):
        cycle = np.tile(np.arange(12, dtype=float), 15)
        for model in f.MODEL_ORDER:
            predicted, _ = f.forecast(model, cycle, nonnegative=True)
            np.testing.assert_allclose(predicted, np.arange(12), atol=1e-8)
        with self.assertRaises(ValueError):
            f.forecast("neural", cycle[:-1])
        with self.assertRaises(ValueError):
            f.forecast("neural", cycle, horizon=24)

    def test_committed_forecasts_have_current_sources_and_honest_dates(self):
        bundle = json.loads((ROOT / "analysis/forecast/app-forecast.json").read_text())
        fingerprint, hashes = f.fingerprints()
        self.assertEqual(bundle["fingerprint"], fingerprint)
        self.assertEqual(bundle["inputHashes"], hashes)
        self.assertEqual(bundle["sourceEnd"], "2024-12-01")
        self.assertEqual(bundle["projectionStart"], "2025-01-01")
        self.assertEqual(bundle["projectionEnd"], "2025-12-01")
        self.assertEqual(set(bundle["results"]), set(f.BOXES))
        for rid, results in bundle["results"].items():
            self.assertEqual(set(results), set(f.FILES))
            for vid, entry in results.items():
                values, unit, nonnegative, _ = f.load_series(rid, vid)
                self.assertEqual(entry["unit"], unit)
                self.assertEqual([row["date"] for row in entry["projection"]], f.dates(2025, 2025))
                self.assertEqual([row["date"] for row in entry["holdout"]], f.dates(2021, 2024))
                self.assertEqual([row["date"] for row in entry["history"]], f.dates(2022, 2024))
                np.testing.assert_array_equal([row["actual"] for row in entry["holdout"]], values[-48:])
                winner = min(entry["models"], key=lambda m: (m["validationMae"], f.MODEL_ORDER.index(m["id"])))
                self.assertEqual(winner["id"], entry["selectedModel"])
                for model in entry["models"]:
                    self.assertEqual(len(model["testByYear"]), 4)
                    self.assertGreaterEqual(model["coverage80"], 0)
                    self.assertLessEqual(model["coverage80"], 1)
                    if model["id"] == "climatology":
                        self.assertAlmostEqual(model["skillVsClimatology"], 0)
                # Independently check published errors and training cutoffs against the stored observations.
                by_id = {m["id"]: m for m in entry["models"]}
                for model_id, point_key in ((entry["selectedModel"], "value"), ("neural", "neuralValue"), ("climatology", "climatologyValue")):
                    error = np.array([r[point_key] - r["actual"] for r in entry["holdout"]])
                    self.assertAlmostEqual(by_id[model_id]["testMae"], np.abs(error).mean())
                    self.assertAlmostEqual(by_id[model_id]["testRmse"], np.sqrt((error ** 2).mean()))
                for row in entry["holdout"]:
                    self.assertLess(row["trainedThrough"], row["date"])
                for row in entry["projection"] + entry["holdout"]:
                    self.assertLessEqual(row["lower"], row["value"])
                    self.assertGreaterEqual(row["upper"], row["value"])
                    if nonnegative:
                        for key in ("value", "lower", "neuralValue", "neuralLower", "climatologyValue", "climatologyLower"):
                            self.assertGreaterEqual(row[key], 0)

    def test_hashes_are_portable_but_not_blind_to_value_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "source.csv"
            p.write_bytes(b"date,value\n1992-01-01,1.5\n")
            original = f.text_sha256(p)
            p.write_bytes(b"date,value\r\n1992-01-01,1.5\r\n")
            self.assertEqual(original, f.text_sha256(p))
            p.write_bytes(b"date,value\r\n1992-01-01,1.6\r\n")
            self.assertNotEqual(original, f.text_sha256(p))


if __name__ == "__main__":
    unittest.main()
