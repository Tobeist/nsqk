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
        self.assertEqual(original["validationWinner"], altered["validationWinner"])
        self.assertEqual(original["selectedNeuralConfig"], altered["selectedNeuralConfig"])
        self.assertEqual(original["selectedEnsoConfig"], altered["selectedEnsoConfig"])
        for config_key in ("neuralConfigurations", "ensoConfigurations"):
            for a, b in zip(original[config_key], altered[config_key]):
                self.assertEqual(a["id"], b["id"])
                self.assertEqual(a["validationMae"], b["validationMae"])
        for model, other in zip(original["models"], altered["models"]):
            self.assertEqual(model["validationMae"], other["validationMae"])
            self.assertEqual(model["intervalRadius80"], other["intervalRadius80"])
        for a, b in zip(original["holdout"][:12], altered["holdout"][:12]):
            for key in ("value", "neuralValue", "ensoValue", "climatologyValue", "lower", "upper"):
                self.assertEqual(a[key], b[key])
        # Later observed years legitimately affect subsequent refits and the final 2025 projection.
        self.assertNotEqual(original["projection"], altered["projection"])

    def test_cycle_is_learned_only_from_training_and_rain_is_nonnegative(self):
        cycle = np.tile(np.arange(12, dtype=float), 15)
        for model in f.MODEL_ORDER:
            predicted, _ = f.forecast(model, cycle, nonnegative=True, enso_training=np.zeros(len(cycle) - 2))
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
                self.assertEqual(winner["id"], entry["validationWinner"])
                original_winner = min((m for m in entry["models"] if m["id"] != "neural-enso"), key=lambda m: (m["validationMae"], f.MODEL_ORDER.index(m["id"])))
                self.assertEqual(original_winner["id"], entry["selectedModel"])
                self.assertEqual(entry["deploymentPolicy"], "retain-v1-until-independent-validation")
                for model in entry["models"]:
                    self.assertEqual(len(model["testByYear"]), 4)
                    self.assertGreaterEqual(model["coverage80"], 0)
                    self.assertLessEqual(model["coverage80"], 1)
                    if model["id"] == "climatology":
                        self.assertAlmostEqual(model["skillVsClimatology"], 0)
                    # Recompute every model's out-of-year metrics, including trajectories not plotted.
                    predictions, observations = [], []
                    for year in f.TEST_YEARS:
                        training, actual = f.split(values, year)
                        config = entry["selectedEnsoConfig"] if model["id"] == "neural-enso" else entry["selectedNeuralConfig"]
                        enso = f.load_enso()[:len(training) - 2] if model["id"] == "neural-enso" else None
                        prediction, _ = f.forecast(model["id"], training, neural_config=config, nonnegative=nonnegative, enso_training=enso)
                        predictions.extend(prediction)
                        observations.extend(actual)
                    errors = np.asarray(predictions) - observations
                    self.assertAlmostEqual(model["testMae"], np.abs(errors).mean())
                    self.assertAlmostEqual(model["testRmse"], np.sqrt((errors ** 2).mean()))
                    self.assertAlmostEqual(model["testBias"], errors.mean())
                # Independently check published errors and training cutoffs against the stored observations.
                by_id = {m["id"]: m for m in entry["models"]}
                for model_id, point_key in ((entry["selectedModel"], "value"), ("neural", "neuralValue"), ("neural-enso", "ensoValue"), ("climatology", "climatologyValue")):
                    error = np.array([r[point_key] - r["actual"] for r in entry["holdout"]])
                    self.assertAlmostEqual(by_id[model_id]["testMae"], np.abs(error).mean())
                    self.assertAlmostEqual(by_id[model_id]["testRmse"], np.sqrt((error ** 2).mean()))
                    if model_id == "neural-enso":
                        lower, upper = "ensoLower", "ensoUpper"
                    elif model_id == "neural":
                        lower, upper = "neuralLower", "neuralUpper"
                    elif model_id == "climatology":
                        lower, upper = "climatologyLower", "climatologyUpper"
                    else:
                        lower, upper = "lower", "upper"
                    covered = np.mean([r[lower] <= r["actual"] <= r[upper] for r in entry["holdout"]])
                    self.assertAlmostEqual(by_id[model_id]["coverage80"], covered)
                for row in entry["holdout"]:
                    self.assertLess(row["trainedThrough"], row["date"])
                    self.assertEqual(row["ensoKnownThrough"], f"{int(row['date'][:4]) - 1}-10-01")
                for row in entry["projection"]:
                    self.assertEqual(row["ensoKnownThrough"], "2024-10-01")
                for row in entry["projection"] + entry["holdout"]:
                    self.assertLessEqual(row["lower"], row["value"])
                    self.assertGreaterEqual(row["upper"], row["value"])
                    if nonnegative:
                        for key in ("value", "lower", "neuralValue", "neuralLower", "ensoValue", "ensoLower", "climatologyValue", "climatologyLower"):
                            self.assertGreaterEqual(row[key], 0)

    def test_future_enso_cannot_change_validation_or_first_year_predictions(self):
        values, unit, nonnegative, source = f.load_series("mx-northeast", "temperature")
        enso = f.load_enso()
        original = f.evaluate_series(values, unit, nonnegative, source, enso)
        changed = enso.copy()
        changed[(2021 - 1992) * 12:] += 5
        altered = f.evaluate_series(values, unit, nonnegative, source, changed)
        self.assertEqual(original["selectedModel"], altered["selectedModel"])
        self.assertEqual(original["validationWinner"], altered["validationWinner"])
        self.assertEqual(original["selectedEnsoConfig"], altered["selectedEnsoConfig"])
        for a, b in zip(original["ensoConfigurations"], altered["ensoConfigurations"]):
            self.assertEqual(a["validationMae"], b["validationMae"])
        for a, b in zip(original["holdout"][:12], altered["holdout"][:12]):
            self.assertEqual(a["ensoValue"], b["ensoValue"])
        self.assertNotEqual([p["ensoValue"] for p in original["projection"]], [p["ensoValue"] for p in altered["projection"]])

    def test_enso_cutoff_persistence_and_input_are_enforced_for_every_configuration(self):
        values, _, _, _ = f.load_series("mx-northeast", "temperature")
        enso = f.load_enso()
        n = (2021 - 1992) * 12
        training = values[:n]
        changed = enso.copy()
        changed[n - 2:] += 50  # Nov2020 and all later values must be unavailable at this origin.
        for config in f.ENSO_CONFIGS:
            original, _ = f.forecast("neural-enso", training, neural_config=config, enso_training=enso[:n - 2])
            altered, _ = f.forecast("neural-enso", training, neural_config=config, enso_training=changed[:n - 2])
            np.testing.assert_array_equal(original, altered)
            known = enso[:n - 2].copy()
            known[-1] += 4
            affected, _ = f.forecast("neural-enso", training, neural_config=config, enso_training=known)
            self.assertGreater(np.max(np.abs(original - affected)), 1e-6)
        for invalid in (None, enso[:n], enso, enso[:n - 3], np.full(n - 2, np.nan)):
            with self.assertRaises(ValueError):
                f.forecast("neural-enso", training, enso_training=invalid)

    def test_enso_signal_is_used_and_source_validation_rejects_bad_dates_and_values(self):
        rng = np.random.default_rng(42)
        enso = np.repeat(rng.normal(size=30), 12)
        residuals = np.zeros(360)
        feature = f.mlp_features(residuals, 60, (1, 2, 3, 6, 12), enso)
        self.assertEqual(feature[-5], enso[57])
        self.assertEqual(feature[-4], enso[54])
        self.assertEqual(feature[-3], enso[48])
        values = 10 + np.sin(np.arange(360) * 2 * np.pi / 12) + 2 * np.roll(enso, 3)
        before, _ = f.forecast("neural-enso", values, enso_training=enso[:-2])
        changed = enso[:-2].copy()
        changed[-1] += 3
        after, _ = f.forecast("neural-enso", values, enso_training=changed)
        self.assertGreater(np.max(np.abs(after - before)), .1)
        lines = f.ENSO_PATH.read_text().splitlines()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "enso.txt"
            for invalid in (["invalid header"] + lines[1:], lines[:3] + lines[4:], lines[:3] + [lines[2]] + lines[3:],
                            lines[:3] + [lines[3].rsplit(maxsplit=1)[0] + " nan"] + lines[4:]):
                path.write_text("\n".join(invalid) + "\n")
                with self.assertRaises(ValueError):
                    f.load_enso(path)

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
