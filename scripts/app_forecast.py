"""Reproducible monthly forecast experiment; protocol: docs/FORECAST_PROTOCOL.md."""
import argparse
import hashlib
import json
import platform
import warnings
from importlib.metadata import version
from pathlib import Path

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

from study_regions import BOXES, data_dir

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261114
VERSION = "monthly-forecast-v1"
VALIDATION_YEARS = tuple(range(2016, 2021))
TEST_YEARS = tuple(range(2021, 2025))
MODEL_ORDER = ("climatology", "seasonal-naive", "trend", "neural")
MODEL_LABELS = {"climatology": "Promedio estacional", "seasonal-naive": "Repetir último año",
                "trend": "Regresión estacional", "neural": "Red neuronal"}
NEURAL_CONFIGS = {
    "small": {"hidden": 4, "alpha": 10., "lags": (1, 2, 3, 6, 12)},
    "wide": {"hidden": 8, "alpha": 10., "lags": (1, 2, 3, 6, 12, 24)},
}
FILES = {
    "temperature": ("power_t2m_region_1992_2024.json", "°C", False),
    "temperature-min": ("power_t2m_min_region_1992_2024.json", "°C", False),
    "temperature-max": ("power_t2m_max_region_1992_2024.json", "°C", False),
    "precipitation": ("giovanni_gpcp_1992_2024.json", "mm/día", True),
    "precipitation-power": ("power_prectotcorr_region_1992_2024.json", "mm/día", True),
    "rain5": ("giovanni_rx5day_1992_2024.json", "mm", True),
}
MEASUREMENTS = {"temperature-min": "t2m_min_c", "temperature-max": "t2m_max_c",
                "precipitation": "gpcp_mm_day", "precipitation-power": "prectotcorr_mm_day",
                "rain5": "rx5day_mm_per_5days"}


def text_sha256(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def fingerprints():
    files = [Path(__file__), ROOT / "scripts/study_regions.py", ROOT / "docs/FORECAST_PROTOCOL.md",
             ROOT / "requirements-forecast.txt", ROOT / "requirements-analysis.txt", ROOT / "config/study-boxes.json"]
    files += [data_dir(ROOT / "data", "results", rid) / spec[0] for rid in BOXES for spec in FILES.values()]
    hashes = {p.relative_to(ROOT).as_posix(): text_sha256(p) for p in files}
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(), hashes


def dates(start=1992, end=2024):
    return [f"{year}-{month:02d}-01" for year in range(start, end + 1) for month in range(1, 13)]


def load_series(region_id, variable_id):
    name, unit, nonnegative = FILES[variable_id]
    payload = json.loads((data_dir(ROOT / "data", "results", region_id) / name).read_text())
    if payload.get("region_id", "mx-northeast") != region_id:
        raise ValueError("Region/source mismatch")
    if payload.get("region_bbox_wsen", payload.get("bbox_wsen")) != BOXES[region_id]["bbox"] or payload.get("period") != [1992, 2024]:
        raise ValueError("Forecast source bounding box or period mismatch")
    if ((variable_id == "temperature" and payload.get("units") not in ("degC", "C")) or
        (variable_id != "temperature" and payload.get("measurement") != MEASUREMENTS[variable_id])):
        raise ValueError("Forecast source measurement/unit mismatch")
    monthly = payload["monthly"]
    if [r["date"] for r in monthly] != dates() or payload.get("n_months") != 396:
        raise ValueError("Forecast source requires all 396 consecutive months, 1992–2024")
    values = np.array([r.get("value", r.get("t2m_c")) for r in monthly], dtype=float)
    if not np.isfinite(values).all() or (nonnegative and np.min(values) < 0):
        raise ValueError("Invalid monthly source values")
    return values, unit, nonnegative, payload["source"]


def seasonal_design(indices):
    indices = np.asarray(indices)
    return np.column_stack([np.ones(len(indices)), indices / 12] + [(indices % 12 == month).astype(float) for month in range(1, 12)])


def mlp_features(residuals, index, lags):
    angle = 2 * np.pi * (index % 12) / 12
    return [residuals[index - lag] for lag in lags] + [np.sin(angle), np.cos(angle)]


def forecast(model, training, horizon=12, neural_config="small", nonnegative=False):
    """Only past observations are accepted; future actuals cannot enter the predictor."""
    training = np.asarray(training, dtype=float)
    n = len(training)
    if n < 60 or n % 12 or horizon < 1 or horizon > 12 or not np.isfinite(training).all():
        raise ValueError("Training must contain at least five complete finite years; horizon 1–12")
    future = np.arange(n, n + horizon)
    count = 0
    if model == "climatology":
        means = training.reshape(-1, 12).mean(axis=0)
        prediction = means[future % 12]
    elif model == "seasonal-naive":
        prediction = training[-12:][:horizon].copy()
    elif model in ("trend", "neural"):
        X = seasonal_design(np.arange(n))
        beta = np.linalg.lstsq(X, training, rcond=None)[0]
        baseline = seasonal_design(future) @ beta
        prediction = baseline.copy()
        if model == "neural":
            config = NEURAL_CONFIGS[neural_config]
            lags = config["lags"]
            residuals = training - X @ beta
            first = max(lags)
            features = np.array([mlp_features(residuals, i, lags) for i in range(first, n)])
            target = residuals[first:]
            scaler = StandardScaler().fit(features)
            ymean, yscale = float(target.mean()), float(target.std())
            if yscale < 1e-10:
                return np.maximum(prediction, 0) if nonnegative else prediction, count
            network = MLPRegressor(hidden_layer_sizes=(config["hidden"],), activation="tanh", solver="lbfgs",
                                   alpha=config["alpha"], max_iter=700, max_fun=3000, random_state=SEED,
                                   early_stopping=False, tol=1e-5)
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ConvergenceWarning)
                network.fit(scaler.transform(features), (target - ymean) / yscale)
            count = sum(issubclass(w.category, ConvergenceWarning) for w in caught)
            path = list(residuals)
            for h, index in enumerate(future):
                feature = np.array(mlp_features(path, int(index), lags)).reshape(1, -1)
                predicted_residual = float(network.predict(scaler.transform(feature))[0] * yscale + ymean)
                value = float(baseline[h] + predicted_residual)
                if nonnegative:
                    value = max(0., value)
                prediction[h] = value
                # A future lag is a previous forecast, never the hidden future observation.
                path.append(value - float(baseline[h]))
    else:
        raise ValueError(f"Unknown model: {model}")
    if nonnegative:
        prediction = np.maximum(prediction, 0)
    if not np.isfinite(prediction).all():
        raise ValueError("Forecast is non-finite")
    return np.asarray(prediction, dtype=float), count


def quantile_radius(errors):
    """Empirical absolute-error radius; no conformal/independence coverage guarantee."""
    absolute = np.sort(np.abs(np.asarray(errors, dtype=float)))
    rank = min(len(absolute), int(np.ceil((len(absolute) + 1) * .8)))
    return float(absolute[rank - 1])


def split(training_values, target_year):
    stop = (target_year - 1992) * 12
    return training_values[:stop], training_values[stop:stop + 12]


def choose_models(validation_predictions, actual):
    maes = {key: float(np.mean(np.abs(np.concatenate(values) - actual))) for key, values in validation_predictions.items()}
    neural_config = min(NEURAL_CONFIGS, key=lambda c: maes[f"neural-{c}"])
    compact = {model: maes[f"neural-{neural_config}" if model == "neural" else model] for model in MODEL_ORDER}
    selected = min(MODEL_ORDER, key=lambda m: compact[m])
    return selected, neural_config, compact, maes


def evaluate_series(values, unit, nonnegative, source):
    values = np.asarray(values, dtype=float)
    if len(values) != 396 or not np.isfinite(values).all():
        raise ValueError("Experiment requires 396 finite monthly values")
    candidates = ("climatology", "seasonal-naive", "trend", "neural-small", "neural-wide")
    validation = {candidate: [] for candidate in candidates}
    convergence = []

    def run_one(candidate, year):
        training, _ = split(values, year)
        config = candidate.removeprefix("neural-") if candidate.startswith("neural-") else "small"
        model = "neural" if candidate.startswith("neural-") else candidate
        point, count = forecast(model, training, neural_config=config, nonnegative=nonnegative)
        if count:
            convergence.append({"model": candidate, "forecastYear": year, "trainedThrough": f"{year - 1}-12-01", "warnings": count})
        return point

    for year in VALIDATION_YEARS:
        for candidate in candidates:
            validation[candidate].append(run_one(candidate, year))
    validation_actual = np.concatenate([split(values, year)[1] for year in VALIDATION_YEARS])
    selected, neural_config, validation_maes, candidate_maes = choose_models(validation, validation_actual)
    mapped = {model: f"neural-{neural_config}" if model == "neural" else model for model in MODEL_ORDER}
    radii = {model: quantile_radius(np.concatenate(validation[candidate]) - validation_actual) for model, candidate in mapped.items()}
    hold_predictions = {model: [] for model in MODEL_ORDER}
    for year in TEST_YEARS:
        for model in MODEL_ORDER:
            hold_predictions[model].append(run_one(mapped[model], year))
    test_actual = np.concatenate([split(values, year)[1] for year in TEST_YEARS])
    metrics = []
    clim_mae = float(np.mean(np.abs(np.concatenate(hold_predictions["climatology"]) - test_actual)))
    for model in MODEL_ORDER:
        point = np.concatenate(hold_predictions[model])
        lower = point - radii[model]
        if nonnegative:
            lower = np.maximum(lower, 0)
        upper = point + radii[model]
        metrics.append({"id": model, "label": MODEL_LABELS[model], "validationMae": validation_maes[model],
                        "testMae": float(np.mean(np.abs(point - test_actual))),
                        "testRmse": float(np.sqrt(np.mean((point - test_actual) ** 2))),
                        "testBias": float(np.mean(point - test_actual)),
                        "coverage80": float(np.mean((test_actual >= lower) & (test_actual <= upper))),
                        "skillVsClimatology": float(1 - np.mean(np.abs(point - test_actual)) / clim_mae) if clim_mae > 0 else None,
                        "intervalRadius80": radii[model],
                        "testByYear": [{"year": year, "mae": float(np.mean(np.abs(hold_predictions[model][i] - split(values, year)[1])))} for i, year in enumerate(TEST_YEARS)]})
    projection_points = {model: run_one(mapped[model], 2025) for model in MODEL_ORDER if model in (selected, "neural", "climatology")}
    projection = []
    for i, date in enumerate(dates(2025, 2025)):
        point, neural = float(projection_points[selected][i]), float(projection_points["neural"][i])
        clim = float(projection_points["climatology"][i])
        projection.append({"date": date, "value": point, "lower": max(0., point - radii[selected]) if nonnegative else point - radii[selected],
                           "upper": point + radii[selected], "neuralValue": neural,
                           "neuralLower": max(0., neural - radii["neural"]) if nonnegative else neural - radii["neural"],
                           "neuralUpper": neural + radii["neural"], "climatologyValue": clim,
                           "climatologyLower": max(0., clim - radii["climatology"]) if nonnegative else clim - radii["climatology"],
                           "climatologyUpper": clim + radii["climatology"]})
    holdout = []
    for yi, year in enumerate(TEST_YEARS):
        for month in range(12):
            point = float(hold_predictions[selected][yi][month])
            neural = float(hold_predictions["neural"][yi][month])
            holdout.append({"date": f"{year}-{month + 1:02d}-01", "actual": float(test_actual[yi * 12 + month]),
                            "value": point, "lower": max(0., point - radii[selected]) if nonnegative else point - radii[selected],
                            "upper": point + radii[selected], "neuralValue": neural,
                            "neuralLower": max(0., neural - radii["neural"]) if nonnegative else neural - radii["neural"],
                            "neuralUpper": neural + radii["neural"],
                            "climatologyValue": float(hold_predictions["climatology"][yi][month]),
                            "climatologyLower": max(0., float(hold_predictions["climatology"][yi][month]) - radii["climatology"]) if nonnegative else float(hold_predictions["climatology"][yi][month]) - radii["climatology"],
                            "climatologyUpper": float(hold_predictions["climatology"][yi][month]) + radii["climatology"],
                            "trainedThrough": f"{year - 1}-12-01"})
    by_model = {row["id"]: row for row in metrics}
    return {"unit": unit, "source": source, "selectedModel": selected, "selectedNeuralConfig": neural_config,
            "models": metrics, "projection": projection,
            "history": [{"date": date, "value": float(value)} for date, value in zip(dates(2022, 2024), values[-36:])],
            "holdout": holdout, "neuralBeatsSelectedOnTest": bool(by_model["neural"]["testMae"] < by_model[selected]["testMae"]),
            "neuralConfigurations": [{"id": key, **spec, "validationMae": candidate_maes[f"neural-{key}"]} for key, spec in NEURAL_CONFIGS.items()],
            "warnings": convergence}


def compute():
    fingerprint, hashes = fingerprints()
    results = {rid: {} for rid in BOXES}
    for rid in BOXES:
        for vid in FILES:
            values, unit, nonnegative, source = load_series(rid, vid)
            results[rid][vid] = evaluate_series(values, unit, nonnegative, source)
            entry = results[rid][vid]
            print(rid, vid, entry["selectedModel"], "done", flush=True)
    return {"version": VERSION, "sourceStart": "1992-01-01", "sourceEnd": "2024-12-01",
            "projectionStart": "2025-01-01", "projectionEnd": "2025-12-01",
            "validationYears": VALIDATION_YEARS, "testYears": TEST_YEARS,
            "seed": SEED, "fingerprint": fingerprint, "inputHashes": hashes, "hashPolicy": "sha256-text-lf-v1",
            "intervalLevel": .8, "intervalMethod": "pooled-validation-absolute-errors-experimental",
            "versions": {"python": platform.python_version(), "numpy": version("numpy"), "scikit-learn": version("scikit-learn")},
            "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "analysis/forecast/app-forecast.json")
    args = parser.parse_args()
    bundle = compute()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(bundle, ensure_ascii=False, allow_nan=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
