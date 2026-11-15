"""Reproducible monthly forecast experiment; protocol: docs/FORECAST_PROTOCOL.md."""
import argparse
import csv
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
VERSION = "monthly-forecast-v2-enso"
VALIDATION_YEARS = tuple(range(2016, 2021))
TEST_YEARS = tuple(range(2021, 2025))
MODEL_ORDER = ("climatology", "seasonal-naive", "trend", "neural", "neural-enso")
MODEL_LABELS = {"climatology": "Promedio estacional", "seasonal-naive": "Repetir último año",
                "trend": "Regresión estacional", "neural": "Red neuronal", "neural-enso": "Red neuronal + ENSO"}
NEURAL_CONFIGS = {
    "small": {"hidden": 4, "alpha": 10., "lags": (1, 2, 3, 6, 12)},
    "wide": {"hidden": 8, "alpha": 10., "lags": (1, 2, 3, 6, 12, 24)},
}
ENSO_CONFIGS = {f"{shape}-a{alpha}": {**spec, "alpha": float(alpha)}
                for alpha in (10, 50) for shape, spec in NEURAL_CONFIGS.items()}
ENSO_LAGS = (3, 6, 12)
ENSO_AVAILABILITY_LAG = 2
ENSO_PATH = ROOT / "data/external/enso/ersst5.nino.mth.91-20.ascii"
ENSO_METADATA = ENSO_PATH.with_suffix(".metadata.json")
ENSO_POLICY = {"source": "NOAA CPC ERSSTv5 Niño 3.4 monthly anomaly, 1991–2020 base",
               "availabilityLagMonths": ENSO_AVAILABILITY_LAG, "lagMonths": ENSO_LAGS,
               "futureStrategy": "persistence", "sourceUrl": "https://www.cpc.ncep.noaa.gov/data/indices/ersst5.nino.mth.91-20.ascii"}
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
             ROOT / "requirements-forecast.txt", ROOT / "requirements-analysis.txt", ROOT / "config/study-boxes.json",
             ENSO_PATH, ENSO_METADATA]
    files += [data_dir(ROOT / "data", "results", rid) / spec[0] for rid in BOXES for spec in FILES.values()]
    hashes = {p.relative_to(ROOT).as_posix(): text_sha256(p) for p in files}
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(), hashes


def dates(start=1992, end=2024):
    return [f"{year}-{month:02d}-01" for year in range(start, end + 1) for month in range(1, 13)]


def load_enso(path=ENSO_PATH):
    """Validate the cached NOAA source and return exactly Jan1992–Dec2024 anomalies."""
    lines = Path(path).read_text(encoding="ascii").splitlines()
    if not lines or lines[0].split() != "YR MON NINO1+2 ANOM NINO3 ANOM NINO4 ANOM NINO3.4 ANOM".split():
        raise ValueError("Unexpected NOAA Niño 3.4 header")
    rows = [line.split() for line in lines[1:] if line.strip()]
    if not rows or any(len(row) != 10 for row in rows):
        raise ValueError("Unexpected NOAA row width")
    keys = [(int(row[0]), int(row[1])) for row in rows]
    if keys != sorted(set(keys)) or any(month not in range(1, 13) for _, month in keys):
        raise ValueError("Unordered, duplicate or invalid NOAA month")
    expected = [(year, month) for year in range(keys[0][0], keys[-1][0] + 1) for month in range(1, 13)
                if keys[0] <= (year, month) <= keys[-1]]
    if keys != expected:
        raise ValueError("Missing NOAA month")
    all_values = np.array([float(row[-1]) for row in rows])
    if not np.isfinite(all_values).all() or np.any(np.abs(all_values) > 20):
        raise ValueError("Invalid NOAA anomaly or missing-value sentinel")
    lookup = dict(zip(keys, all_values))
    try:
        values = np.array([lookup[(year, month)] for year in range(1992, 2025) for month in range(1, 13)])
    except KeyError as exc:
        raise ValueError("NOAA source lacks a required 1992–2024 month") from exc
    return values


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


def mlp_features(residuals, index, lags, enso_training=None):
    angle = 2 * np.pi * (index % 12) / 12
    features = [residuals[index - lag] for lag in lags] + [np.sin(angle), np.cos(angle)]
    if enso_training is not None:
        # Unknown ENSO after the available October persists; never consult an observed future value.
        enso = [enso_training[min(index - lag, len(enso_training) - 1)] for lag in ENSO_LAGS]
        features += enso + [enso[0] * np.sin(angle), enso[0] * np.cos(angle)]
    return features


def forecast(model, training, horizon=12, neural_config=None, nonnegative=False, enso_training=None):
    """Only past observations are accepted; future actuals cannot enter the predictor."""
    training = np.asarray(training, dtype=float)
    n = len(training)
    if n < 60 or n % 12 or horizon < 1 or horizon > 12 or not np.isfinite(training).all():
        raise ValueError("Training must contain at least five complete finite years; horizon 1–12")
    if model == "neural-enso":
        enso_training = np.asarray(enso_training, dtype=float)
        if enso_training.shape != (n - ENSO_AVAILABILITY_LAG,) or not np.isfinite(enso_training).all():
            raise ValueError("ENSO must stop exactly two months before December training cutoff")
    else:
        enso_training = None
    future = np.arange(n, n + horizon)
    count = 0
    if model == "climatology":
        means = training.reshape(-1, 12).mean(axis=0)
        prediction = means[future % 12]
    elif model == "seasonal-naive":
        prediction = training[-12:][:horizon].copy()
    elif model in ("trend", "neural", "neural-enso"):
        X = seasonal_design(np.arange(n))
        beta = np.linalg.lstsq(X, training, rcond=None)[0]
        baseline = seasonal_design(future) @ beta
        prediction = baseline.copy()
        if model in ("neural", "neural-enso"):
            configs = ENSO_CONFIGS if model == "neural-enso" else NEURAL_CONFIGS
            neural_config = neural_config or ("small-a10" if model == "neural-enso" else "small")
            if neural_config not in configs:
                raise ValueError("Unknown neural configuration")
            config = configs[neural_config]
            lags = config["lags"]
            residuals = training - X @ beta
            first = max(max(lags), max(ENSO_LAGS) if enso_training is not None else 0)
            features = np.array([mlp_features(residuals, i, lags, enso_training) for i in range(first, n)])
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
                feature = np.array(mlp_features(path, int(index), lags, enso_training)).reshape(1, -1)
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
    enso_config = min(ENSO_CONFIGS, key=lambda c: maes[f"neural-enso-{c}"])
    mapped = {"neural": f"neural-{neural_config}", "neural-enso": f"neural-enso-{enso_config}"}
    compact = {model: maes[mapped.get(model, model)] for model in MODEL_ORDER}
    validation_winner = min(MODEL_ORDER, key=lambda m: compact[m])
    # Deployment gate is global: preserve the v1 champion until new independent observations exist.
    selected = min(MODEL_ORDER[:-1], key=lambda m: compact[m])
    return selected, validation_winner, neural_config, enso_config, compact, maes


def evaluate_series(values, unit, nonnegative, source, enso_values=None):
    values = np.asarray(values, dtype=float)
    if len(values) != 396 or not np.isfinite(values).all():
        raise ValueError("Experiment requires 396 finite monthly values")
    enso_values = load_enso() if enso_values is None else np.asarray(enso_values, dtype=float)
    if enso_values.shape != values.shape or not np.isfinite(enso_values).all():
        raise ValueError("ENSO experiment requires exactly 396 finite monthly values")
    candidates = ("climatology", "seasonal-naive", "trend", "neural-small", "neural-wide") + tuple(f"neural-enso-{key}" for key in ENSO_CONFIGS)
    validation = {candidate: [] for candidate in candidates}
    convergence = []
    cache = {}

    def run_one(candidate, year):
        if (candidate, year) in cache:
            return cache[(candidate, year)]
        training, _ = split(values, year)
        if candidate.startswith("neural-enso-"):
            config, model = candidate.removeprefix("neural-enso-"), "neural-enso"
        elif candidate.startswith("neural-"):
            config, model = candidate.removeprefix("neural-"), "neural"
        else:
            config, model = "small", candidate
        enso_training = enso_values[:len(training) - ENSO_AVAILABILITY_LAG] if model == "neural-enso" else None
        point, count = forecast(model, training, neural_config=config, nonnegative=nonnegative, enso_training=enso_training)
        if count:
            convergence.append({"model": candidate, "forecastYear": year, "trainedThrough": f"{year - 1}-12-01", "warnings": count})
        cache[(candidate, year)] = point
        return point

    for year in VALIDATION_YEARS:
        for candidate in candidates:
            validation[candidate].append(run_one(candidate, year))
    validation_actual = np.concatenate([split(values, year)[1] for year in VALIDATION_YEARS])
    selected, validation_winner, neural_config, enso_config, validation_maes, candidate_maes = choose_models(validation, validation_actual)
    mapped = {model: model for model in MODEL_ORDER}
    mapped.update({"neural": f"neural-{neural_config}", "neural-enso": f"neural-enso-{enso_config}"})
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
    projection_points = {model: run_one(mapped[model], 2025) for model in MODEL_ORDER if model in (selected, "neural", "neural-enso", "climatology")}
    projection = []
    for i, date in enumerate(dates(2025, 2025)):
        point, neural = float(projection_points[selected][i]), float(projection_points["neural"][i])
        enso = float(projection_points["neural-enso"][i])
        clim = float(projection_points["climatology"][i])
        projection.append({"date": date, "value": point, "lower": max(0., point - radii[selected]) if nonnegative else point - radii[selected],
                           "upper": point + radii[selected], "neuralValue": neural,
                           "neuralLower": max(0., neural - radii["neural"]) if nonnegative else neural - radii["neural"],
                           "neuralUpper": neural + radii["neural"], "climatologyValue": clim,
                           "climatologyLower": max(0., clim - radii["climatology"]) if nonnegative else clim - radii["climatology"],
                           "climatologyUpper": clim + radii["climatology"],
                           "ensoValue": enso, "ensoLower": max(0., enso - radii["neural-enso"]) if nonnegative else enso - radii["neural-enso"],
                           "ensoUpper": enso + radii["neural-enso"], "ensoKnownThrough": "2024-10-01"})
    holdout = []
    for yi, year in enumerate(TEST_YEARS):
        for month in range(12):
            point = float(hold_predictions[selected][yi][month])
            neural = float(hold_predictions["neural"][yi][month])
            enso = float(hold_predictions["neural-enso"][yi][month])
            holdout.append({"date": f"{year}-{month + 1:02d}-01", "actual": float(test_actual[yi * 12 + month]),
                            "value": point, "lower": max(0., point - radii[selected]) if nonnegative else point - radii[selected],
                            "upper": point + radii[selected], "neuralValue": neural,
                            "neuralLower": max(0., neural - radii["neural"]) if nonnegative else neural - radii["neural"],
                            "neuralUpper": neural + radii["neural"],
                            "climatologyValue": float(hold_predictions["climatology"][yi][month]),
                            "climatologyLower": max(0., float(hold_predictions["climatology"][yi][month]) - radii["climatology"]) if nonnegative else float(hold_predictions["climatology"][yi][month]) - radii["climatology"],
                            "climatologyUpper": float(hold_predictions["climatology"][yi][month]) + radii["climatology"],
                            "trainedThrough": f"{year - 1}-12-01",
                            "ensoValue": enso, "ensoLower": max(0., enso - radii["neural-enso"]) if nonnegative else enso - radii["neural-enso"],
                            "ensoUpper": enso + radii["neural-enso"], "ensoKnownThrough": f"{year - 1}-10-01"})
    by_model = {row["id"]: row for row in metrics}
    # Paired ablations are audited after validation has frozen both configurations and the winner.
    def config_rows(configs, prefix):
        rows = []
        for key, spec in configs.items():
            candidate = f"{prefix}-{key}"
            predicted = np.concatenate([run_one(candidate, year) for year in TEST_YEARS])
            rows.append({"id": key, **spec, "validationMae": candidate_maes[candidate],
                         "testMae": float(np.mean(np.abs(predicted - test_actual)))})
        return rows
    return {"unit": unit, "source": source, "selectedModel": selected, "selectedNeuralConfig": neural_config,
            "validationWinner": validation_winner, "deploymentPolicy": "retain-v1-until-independent-validation",
            "selectedEnsoConfig": enso_config, "ensoPolicy": ENSO_POLICY,
            "models": metrics, "projection": projection,
            "history": [{"date": date, "value": float(value)} for date, value in zip(dates(2022, 2024), values[-36:])],
            "holdout": holdout, "neuralBeatsSelectedOnTest": bool(by_model["neural"]["testMae"] < by_model[selected]["testMae"]),
            "neuralConfigurations": config_rows(NEURAL_CONFIGS, "neural"),
            "ensoConfigurations": config_rows(ENSO_CONFIGS, "neural-enso"),
            "warnings": convergence}


def compute():
    fingerprint, hashes = fingerprints()
    results = {rid: {} for rid in BOXES}
    enso_values = load_enso()
    for rid in BOXES:
        for vid in FILES:
            values, unit, nonnegative, source = load_series(rid, vid)
            results[rid][vid] = evaluate_series(values, unit, nonnegative, source, enso_values)
            entry = results[rid][vid]
            print(rid, vid, entry["selectedModel"], "done", flush=True)
    return {"version": VERSION, "sourceStart": "1992-01-01", "sourceEnd": "2024-12-01",
            "projectionStart": "2025-01-01", "projectionEnd": "2025-12-01",
            "validationYears": VALIDATION_YEARS, "testYears": TEST_YEARS,
            "evaluationStatus": "reused-retrospective-audit-not-fresh-confirmation",
            "deploymentPolicy": "retain-v1-until-independent-validation",
            "ensoPolicy": ENSO_POLICY,
            "seed": SEED, "fingerprint": fingerprint, "inputHashes": hashes, "hashPolicy": "sha256-text-lf-v1",
            "intervalLevel": .8, "intervalMethod": "pooled-validation-absolute-errors-experimental",
            "versions": {"python": platform.python_version(), "numpy": version("numpy"), "scikit-learn": version("scikit-learn")},
            "results": results}


def write_comparison(bundle, baseline_path):
    """Audit vs frozen v1; it never feeds back into model/configuration selection."""
    previous = json.loads(Path(baseline_path).read_text())
    if previous.get("version") != "monthly-forecast-v1":
        raise ValueError("Comparison requires the frozen v1 artifact")
    rows = []
    for rid, variables in bundle["results"].items():
        for vid, entry in variables.items():
            old = previous["results"][rid][vid]
            old_scores = {m["id"]: m for m in old["models"]}
            scores = {m["id"]: m for m in entry["models"]}
            old_selected = old_scores[old["selectedModel"]]
            candidate, deployed = scores[entry["validationWinner"]], scores[entry["selectedModel"]]
            row = {"region_id": rid, "variable_id": vid, "unit": entry["unit"],
                   "old_selected_model": old["selectedModel"], "validation_winner": entry["validationWinner"],
                   "deployed_model": entry["selectedModel"], "candidate_not_promoted": entry["validationWinner"] != entry["selectedModel"],
                   "old_validation_mae": old_selected["validationMae"], "candidate_validation_mae": candidate["validationMae"],
                   "old_test_mae": old_selected["testMae"], "candidate_test_mae": candidate["testMae"],
                   "deployed_test_mae": deployed["testMae"],
                   "test_improvement_candidate_vs_v1": 1 - candidate["testMae"] / old_selected["testMae"],
                   "neural_test_mae": scores["neural"]["testMae"], "enso_test_mae": scores["neural-enso"]["testMae"],
                   "enso_selected_config": entry["selectedEnsoConfig"],
                   "neural_test_mae_unchanged": bool(np.isclose(scores["neural"]["testMae"], old_scores["neural"]["testMae"], atol=1e-12, rtol=0)),
                   "baseline_fingerprint": previous["fingerprint"], "current_fingerprint": bundle["fingerprint"]}
            plain = {c["id"]: c for c in entry["neuralConfigurations"]}
            enso = {c["id"]: c for c in entry["ensoConfigurations"]}
            for shape in NEURAL_CONFIGS:
                for stage in ("validationMae", "testMae"):
                    row[f"paired_{shape}_{stage}_without_enso"] = plain[shape][stage]
                    row[f"paired_{shape}_{stage}_with_enso_alpha10"] = enso[f"{shape}-a10"][stage]
            rows.append(row)
    output = ROOT / "analysis/forecast/retraining-comparison.csv"
    with output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "analysis/forecast/app-forecast.json")
    parser.add_argument("--comparison-baseline", type=Path, help="Optional frozen v1 JSON for an audit-only CSV")
    args = parser.parse_args()
    bundle = compute()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(bundle, ensure_ascii=False, allow_nan=False, indent=2) + "\n")
    if args.comparison_baseline:
        rows = write_comparison(bundle, args.comparison_baseline)
        print("ENSO validation winners", sum(r["validation_winner"] == "neural-enso" for r in rows), "of", len(rows), "; no promotion without independent validation", flush=True)


if __name__ == "__main__":
    main()
