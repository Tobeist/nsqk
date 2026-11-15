"""Deep forecast experiment for northeast monthly T2M: Conv1D residual blocks + BiGRU + attention, tuned on validation only.

Usage: python scripts/deep_forecast.py [--trials 30] [--workers 5]. Protocol: docs/DEEP_FORECAST_PROTOCOL.md.
The test years 2021-2024 are scored once, after the configuration is frozen.
"""

import argparse
import hashlib
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from t2m_heatmaps import DATES, load_monthly

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis" / "deep"
SEED = 20261114
VALIDATION_YEARS = (2016, 2017, 2018, 2019, 2020)
TEST_YEARS = (2021, 2022, 2023, 2024)
BASELINE = {"deployed_neural_test_mae": 1.348, "deployed_neural_validation_mae": 0.958,
            "climatology_test_mae": 1.450, "trend_test_mae": 1.349}  # analysis/forecast/app-forecast.json
ENSO_LAG = 2  # Nino 3.4 known two months before the issue date, as in the app
FEATURE_SETS = {"all": ["T2M", "T2M_MIN", "T2M_MAX", "PRECTOTCORR", "GPCP", "RX5DAY"], "temp_enso": ["T2M", "T2M_MIN", "T2M_MAX"]}
MAX_EPOCHS, PATIENCE, BATCH = 400, 60, 32
ROUND1 = {"window": [24, 36, 48], "features": ["all"]}
ROUND2 = {"window": [12, 24, 36, 48, 60], "features": ["all", "temp_enso"]}


# ---------------------------------------------------------------- data, fitted inside each origin only

def origin_index(year):
    """Index of December of year-1: the last observation available when forecasting `year`."""
    return (year - 1992) * 12 - 1


def seasonal_design(index):
    index = np.asarray(index)
    return np.column_stack([np.ones(len(index)), index / 12] + [(index % 12 == m).astype(float) for m in range(1, 12)])


def prepare(frame, enso_full, origin, window, feature_set):
    """Windows, targets and the transformations, all estimated with months <= origin."""
    names = FEATURE_SETS[feature_set]
    train = frame.iloc[:origin + 1]
    clim = train.groupby(train.index.month).mean()
    anom = frame[names] - clim[names].reindex(frame.index.month).to_numpy()
    mu, sd = anom.iloc[:origin + 1].mean(), anom.iloc[:origin + 1].std()
    z = ((anom - mu) / sd).to_numpy()
    X = seasonal_design(np.arange(origin + 1))
    beta = np.linalg.lstsq(X, frame["T2M"].to_numpy()[:origin + 1], rcond=None)[0]
    base = seasonal_design(np.arange(len(frame))) @ beta
    resid = frame["T2M"].to_numpy() - base
    rsd = resid[:origin + 1].std()
    t_anom = anom["T2M"]
    roll = np.column_stack([t_anom.rolling(3).mean(), t_anom.rolling(3).std(), t_anom.rolling(12).mean(), t_anom.rolling(12).std()])
    roll = (roll - np.nanmean(roll[:origin + 1], axis=0)) / np.nanstd(roll[:origin + 1], axis=0)
    month = frame.index.month.to_numpy()
    cyc = np.column_stack([np.sin(2 * np.pi * month / 12), np.cos(2 * np.pi * month / 12)])
    enso_dates = frame.index
    known_at_issue = enso_dates[origin] - pd.DateOffset(months=ENSO_LAG)  # scaling must not see Nov-Dec of the origin year
    e_mu, e_sd = enso_full.loc[:known_at_issue].mean(), enso_full.loc[:known_at_issue].std()

    def sample(end):
        rows = np.arange(end - window + 1, end + 1)
        known = enso_dates[end] - pd.DateOffset(months=ENSO_LAG)
        enso = np.array([enso_full.loc[min(enso_dates[r], known)] for r in rows])  # persistence after the known month
        feats = np.column_stack([z[rows], (resid[rows] / rsd)[:, None], roll[rows], cyc[rows], ((enso - e_mu) / e_sd)[:, None]])
        target_months = month[end] % 12 + 1 + np.arange(12)
        head = np.concatenate([np.sin(2 * np.pi * target_months / 12), np.cos(2 * np.pi * target_months / 12)])
        return feats, head

    first = window - 1 + 11  # rolling 12-month statistics need 11 earlier months
    ends = [e for e in range(first, origin - 11)]  # training targets e+1..e+12 must be <= origin
    feats, heads, targets = [], [], []
    for e in ends:
        f, h = sample(e)
        feats.append(f)
        heads.append(h)
        targets.append(resid[e + 1:e + 13] / rsd)
    # Early stopping uses windows whose 12 targets all lie in the last 24 training months; training windows' targets
    # end before that block. Windows in between are purged, so no target month is shared between the two sets.
    early = np.array([e + 1 > origin - 24 for e in ends])
    fit = np.array([e + 12 <= origin - 24 for e in ends])
    f_last, h_last = sample(origin)
    if np.isnan(np.array(feats)).any() or np.isnan(f_last).any():
        raise ValueError("NaN in features; refusing to fill")
    return {"x": np.array(feats, np.float32), "h": np.array(heads, np.float32), "y": np.array(targets, np.float32), "early": early, "fit": fit,
            "x_new": f_last[None].astype(np.float32), "h_new": h_last[None].astype(np.float32),
            "base_future": base[origin + 1:origin + 13], "rsd": rsd,
            "clim_future": clim["T2M"].reindex(frame.index.month[origin + 1:origin + 13]).to_numpy()}


# ---------------------------------------------------------------- model

def build(F, ch, blocks, gru, dropout):
    import torch
    from torch import nn

    class ResBlock(nn.Module):
        def __init__(self):
            super().__init__()
            self.norm = nn.LayerNorm(ch)
            self.conv = nn.Conv1d(ch, ch, kernel_size=3)
            self.drop = nn.Dropout(dropout)

        def forward(self, x):  # x: (B, T, C); left padding keeps the convolution causal
            y = self.norm(x).transpose(1, 2)
            y = self.conv(nn.functional.pad(y, (2, 0))).transpose(1, 2)
            return x + self.drop(nn.functional.gelu(y))

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.inp = nn.Linear(F, ch)
            self.blocks = nn.ModuleList([ResBlock() for _ in range(blocks)])
            self.gru = nn.GRU(ch, gru, batch_first=True, bidirectional=True)
            self.att = nn.Sequential(nn.Linear(2 * gru, gru), nn.Tanh(), nn.Linear(gru, 1))
            self.head = nn.Sequential(nn.LayerNorm(2 * gru + 24), nn.Linear(2 * gru + 24, 64), nn.GELU(), nn.Dropout(dropout), nn.Linear(64, 12))
            self.skip = nn.Linear(2 * gru + 24, 12)

        def forward(self, x, h):
            x = self.inp(x)
            for block in self.blocks:
                x = block(x)
            seq, _ = self.gru(x)
            weights = torch.softmax(self.att(seq), dim=1)
            z = torch.cat([(weights * seq).sum(dim=1), h], dim=1)
            return self.head(z) + self.skip(z)

    return Net()


def train_one(args):
    """Train one network for one origin; return the forecast and the loss curves."""
    import torch
    torch.set_num_threads(1)
    year, params, seed, frame, enso = args
    data = prepare(frame, enso, origin_index(year), params["window"], params["features"])
    torch.manual_seed(seed)
    np.random.seed(seed)
    net = build(data["x"].shape[2], params["channels"], params["blocks"], params["gru"], params["dropout"])
    opt = torch.optim.AdamW(net.parameters(), lr=params["lr"], weight_decay=params["weight_decay"])
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=MAX_EPOCHS)
    loss_fn = torch.nn.HuberLoss(delta=1.0)
    tr, va = data["fit"], data["early"]
    xt, ht, yt = (torch.from_numpy(data[k][tr]) for k in ("x", "h", "y"))
    xv, hv, yv = (torch.from_numpy(data[k][va]) for k in ("x", "h", "y"))
    rng = np.random.default_rng(seed)
    best, best_state, waited, curve = np.inf, None, 0, []
    for epoch in range(MAX_EPOCHS):
        net.train()
        order = rng.permutation(len(xt))  # shuffling windows inside training is fine; the split itself is chronological
        total = 0.0
        for i in range(0, len(order), BATCH):
            b = torch.from_numpy(order[i:i + BATCH])
            opt.zero_grad()
            loss = loss_fn(net(xt[b], ht[b]), yt[b])
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
            total += float(loss.detach()) * len(b)
        sched.step()
        net.eval()
        with torch.no_grad():
            val = float(loss_fn(net(xv, hv), yv))
        curve.append((total / len(xt), val))
        if val < best - 1e-6:
            best, waited = val, 0
            best_state = {k: v.clone() for k, v in net.state_dict().items()}
        else:
            waited += 1
            if waited >= PATIENCE:
                break
    net.load_state_dict(best_state)
    net.eval()
    with torch.no_grad():
        resid = net(torch.from_numpy(data["x_new"]), torch.from_numpy(data["h_new"])).numpy()[0] * data["rsd"]
    return {"year": year, "seed": seed, "prediction": (data["base_future"] + resid).tolist(), "clim": data["clim_future"].tolist(),
            "base": data["base_future"].tolist(), "curve": curve, "best_epoch": int(np.argmin([c[1] for c in curve]))}


def run(years, params, seeds, frame, enso, pool):
    jobs = [(y, params, SEED + 97 * s + y, frame, enso) for y in years for s in seeds]
    out = list(pool.map(train_one, jobs))
    preds = {}
    for r in out:
        preds.setdefault(r["year"], []).append(np.array(r["prediction"]))
    return {y: np.mean(v, axis=0) for y, v in preds.items()}, out


def actual(frame, year):
    return frame["T2M"].to_numpy()[(year - 1992) * 12:(year - 1991) * 12]


# ---------------------------------------------------------------- search, evaluation, outputs

def search(frame, enso, pool, trials, space, round_name, log):
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    truth = np.concatenate([actual(frame, y) for y in VALIDATION_YEARS])

    def objective(trial):
        params = {"window": trial.suggest_categorical("window", space["window"]),
                  "features": trial.suggest_categorical("features", space["features"]),
                  "channels": trial.suggest_categorical("channels", [16, 32, 64]),
                  "blocks": trial.suggest_int("blocks", 1, 3), "gru": trial.suggest_categorical("gru", [16, 32, 64]),
                  "dropout": trial.suggest_float("dropout", 0.0, 0.4), "lr": trial.suggest_float("lr", 1e-4, 3e-3, log=True),
                  "weight_decay": trial.suggest_float("weight_decay", 1e-5, 1e-1, log=True)}
        start = time.time()
        preds, raw = run(VALIDATION_YEARS, params, [0], frame, enso, pool)
        mae = float(np.mean(np.abs(np.concatenate([preds[y] for y in VALIDATION_YEARS]) - truth)))
        log.append({"round": round_name, "trial": trial.number, **params, "validation_mae": mae,
                    "mean_best_epoch": float(np.mean([r["best_epoch"] for r in raw])), "seconds": round(time.time() - start, 1)})
        print(f"{round_name} trial {trial.number}: val MAE {mae:.4f} {params}", flush=True)
        return mae

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=SEED + (0 if round_name == "round1" else 1)))
    study.optimize(objective, n_trials=trials)
    return study.best_params, study.best_value


def dm_test(e_model, e_base, lags=11):
    """Diebold-Mariano on absolute-error differences with a Bartlett HAC variance (normal reference)."""
    d = np.abs(e_model) - np.abs(e_base)
    n, mean = len(d), d.mean()
    c = d - mean
    var = c @ c / n
    for lag in range(1, lags + 1):
        var += 2 * (1 - lag / (lags + 1)) * (c[lag:] @ c[:-lag]) / n
    from scipy import stats
    stat = mean / np.sqrt(var / n)
    return float(stat), float(2 * stats.norm.sf(abs(stat)))


def metrics(y, p, clim):
    err = p - y
    return {"mae": float(np.mean(np.abs(err))), "rmse": float(np.sqrt(np.mean(err ** 2))), "mse": float(np.mean(err ** 2)),
            "r2_monthly_values": float(1 - np.sum(err ** 2) / np.sum((y - y.mean()) ** 2)),
            "r2_anomalies_vs_training_climatology": float(1 - np.sum(err ** 2) / np.sum((y - clim) ** 2)), "bias": float(err.mean())}


def figures(frame, val_preds, test_preds, raw_test, deployed):
    fig, ax = plt.subplots(figsize=(13, 4.5))
    years = VALIDATION_YEARS + TEST_YEARS
    idx = pd.date_range(f"{years[0]}-01-01", f"{years[-1]}-12-01", freq="MS")
    ax.plot(idx, np.concatenate([actual(frame, y) for y in years]), color="black", lw=1.5, label="Observado (POWER T2M)")
    ax.plot(idx[:60], np.concatenate([val_preds[y] for y in VALIDATION_YEARS]), color="#0072B2", lw=1.2, ls="--", label="Red, validación 2016–2020 (eligió hiperparámetros)")
    ax.plot(idx[60:], np.concatenate([test_preds[y] for y in TEST_YEARS]), color="#D55E00", lw=1.5, label="Red, prueba 2021–2024 (evaluada una vez)")
    ax.plot(idx[60:], deployed, color="#009E73", lw=1.2, ls=":", label="Modelo desplegado (app), prueba")
    ax.axvspan(idx[60], idx[-1], color="grey", alpha=0.1)
    ax.set_ylabel("T2M (°C)")
    ax.legend(fontsize=8, ncol=2)
    ax.set_title("T2M noreste: pronóstico a 12 meses emitido cada diciembre (ensamble de 5 semillas)", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "deep_real_vs_predicho.png", dpi=200)
    plt.close(fig)
    fig, axes = plt.subplots(1, len(TEST_YEARS), figsize=(16, 3.8), sharey=True)
    for ax, year in zip(axes, TEST_YEARS):
        for r in [r for r in raw_test if r["year"] == year]:
            c = np.array(r["curve"])
            ax.plot(c[:, 0], color="#0072B2", alpha=0.5, lw=0.8)
            ax.plot(c[:, 1], color="#D55E00", alpha=0.7, lw=0.8)
            ax.axvline(r["best_epoch"], color="grey", lw=0.5, ls=":")
        ax.set_title(f"Origen dic-{year - 1}", fontsize=9)
        ax.set_xlabel("Época")
    axes[0].set_ylabel("Huber (residuo estandarizado)")
    axes[0].plot([], [], color="#0072B2", label="train_loss")
    axes[0].plot([], [], color="#D55E00", label="val_loss (últimos 24 meses del entrenamiento)")
    axes[0].legend(fontsize=7)
    fig.suptitle("Curvas de entrenamiento de los modelos de prueba (5 semillas; punteado = mejor época conservada)", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "deep_curvas_perdida.png", dpi=200)
    plt.close(fig)


def main(trials, workers):
    OUT.mkdir(parents=True, exist_ok=True)
    frame, enso = load_monthly()
    log = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        best, best_val = search(frame, enso, pool, trials, ROUND1, "round1", log)
        rounds = 1
        if best_val >= BASELINE["deployed_neural_validation_mae"]:  # pre-registered second round, still validation only
            best2, best_val2 = search(frame, enso, pool, 20, ROUND2, "round2", log)
            rounds = 2
            if best_val2 < best_val:
                best, best_val = best2, best_val2
        pd.DataFrame(log).to_csv(OUT / "deep_optuna_trials.csv", index=False)
        frozen = dict(best)
        (OUT / "deep_frozen_config.json").write_text(json.dumps({"params": frozen, "single_seed_validation_mae": best_val, "rounds": rounds,
                                                                "frozen_before_test": True}, indent=1) + "\n")
        val_preds, _ = run(VALIDATION_YEARS, frozen, range(5), frame, enso, pool)
        test_preds, raw_test = run(TEST_YEARS, frozen, range(5), frame, enso, pool)  # the only time the test years are scored
    app = json.loads((ROOT / "analysis/forecast/app-forecast.json").read_text())["results"]["mx-northeast"]["temperature"]
    holdout = pd.DataFrame(app["holdout"])
    deployed = holdout["value"].to_numpy()
    y_test = np.concatenate([actual(frame, y) for y in TEST_YEARS])
    p_test = np.concatenate([test_preds[y] for y in TEST_YEARS])
    clim_test = np.concatenate([np.array(r["clim"]) for y in TEST_YEARS for r in raw_test if r["year"] == y and r["seed"] == SEED + y])
    if not np.allclose(holdout["actual"].to_numpy(), y_test, atol=1e-4):
        raise ValueError("App holdout and local observations disagree")
    y_val = np.concatenate([actual(frame, y) for y in VALIDATION_YEARS])
    stat, p = dm_test(p_test - y_test, deployed - y_test)
    net = metrics(y_test, p_test, clim_test)
    base = metrics(y_test, deployed, clim_test)
    result = {
        "target": "NASA POWER T2M monthly, northeast box [-101,25,-99,27], °C", "task": "12-month forecast issued each December",
        "frozen_config": frozen, "rounds": rounds, "trials_logged": len(log),
        "validation_mae_ensemble": float(np.mean(np.abs(np.concatenate([val_preds[y] for y in VALIDATION_YEARS]) - y_val))),
        "test_network": net, "test_deployed_model": base,
        "baseline_reference": BASELINE,
        "improvement_vs_deployed_mae_pct": 100 * (1 - net["mae"] / BASELINE["deployed_neural_test_mae"]),
        "improvement_vs_climatology_mae_pct": 100 * (1 - net["mae"] / BASELINE["climatology_test_mae"]),
        "improvement_vs_trend_mae_pct": 100 * (1 - net["mae"] / BASELINE["trend_test_mae"]),
        "diebold_mariano_vs_deployed": {"statistic": stat, "p_value": p, "loss": "absolute error", "hac_lags": 11,
                                         "note": "negative statistic = network has smaller absolute errors"},
        "meets_publication_rule": bool(net["mae"] < BASELINE["deployed_neural_test_mae"] and p < 0.05),
        "per_year_mae": {str(y): float(np.mean(np.abs(test_preds[y] - actual(frame, y)))) for y in TEST_YEARS},
        "hardware": "CPU (Apple M2), no CUDA; mixed precision not applicable", "seed": SEED, "ensemble_seeds": 5,
        "protocol_sha256": hashlib.sha256((ROOT / "docs/DEEP_FORECAST_PROTOCOL.md").read_bytes()).hexdigest(),
    }
    (OUT / "deep_results.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    pd.DataFrame({"date": pd.date_range("2021-01-01", "2024-12-01", freq="MS").strftime("%Y-%m"), "actual": y_test,
                  "network": p_test, "deployed": deployed, "training_climatology": clim_test}).to_csv(OUT / "deep_test_predictions.csv", index=False)
    figures(frame, val_preds, test_preds, raw_test, deployed)
    print(json.dumps(result, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=30)
    parser.add_argument("--workers", type=int, default=5)
    args = parser.parse_args()
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    main(args.trials, args.workers)
