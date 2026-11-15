"""Nested time-series forecast comparison: climatology, persistence, OLS, and Prophet tuned with Optuna (TPE).

Usage: python scripts/forecast_experiment.py [--trials 25] [--workers 8]. Design: docs/ANALISIS_TENDENCIAS_PLAN_V2.md, section 5.
"""

import argparse
import json
import logging
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
import statsmodels.api as sm

import trend_audit as ta

OUTER = (2016, 2017, 2018, 2019, 2020)
HOLDOUT = (2021, 2022, 2023, 2024)
INNER_YEARS = 3
PROPHETS = ("PROPHET", "PROPHET_ENSO_OPER", "PROPHET_ENSO_RECON")
MLP = "MLP_ENSO_OPER"
TUNED = PROPHETS + (MLP,)
MLP_SPACE = {"hidden_units": (2, 4, 8), "alpha": (1e-3, 10.0)}
SIMPLE = ("CLIM", "PERSIST", "OLS_TREND", "OLS_ENSO_OPER", "OLS_ENSO_RECON")
SPACE = {"changepoint_prior_scale": (0.001, 0.5), "seasonality_prior_scale": (0.01, 10.0), "yearly_fourier_order": (2, 6)}
FIXED = {"changepoint_range": 0.8, "n_changepoints": 25, "interval_width": 0.8, "enso_prior_scale": 10.0}


def dataset():
    frame, enso = ta.load_series(), ta.load_enso()
    dec = pd.Series(enso.loc[[pd.Timestamp(f"{y - 1}-12-01") for y in ta.DATES.year]].to_numpy(), index=ta.DATES)
    return frame.assign(n34_recon=ta.lagged(enso, ta.DATES, 0), n34_oper=dec.to_numpy())


def regressor(model):
    return "n34_oper" if model.endswith("OPER") else "n34_recon" if model.endswith("RECON") else None


def forecast_simple(model, train, test):
    """Point forecast and 80% interval for the non-Prophet models (intervals only for OLS)."""
    y = train["y"].to_numpy()
    if model == "CLIM":
        clim = train.groupby(train.index.month)["y"].mean()
        return clim.reindex(test.index.month).to_numpy(), None, None
    if model == "PERSIST":
        last = train["y"].iloc[-12:]
        return last.to_numpy(), None, None
    def design(df):
        t = (df.index.year - 1992) + (df.index.month - 1) / 12
        cols = [np.ones(len(df)), t] + [(df.index.month == m).astype(float) for m in range(2, 13)]
        if regressor(model):
            cols.append(df[regressor(model)].to_numpy())
        return np.column_stack(cols)
    fit = sm.OLS(y, design(train)).fit()
    frame = fit.get_prediction(design(test)).summary_frame(alpha=0.2)
    return frame["mean"].to_numpy(), frame["obs_ci_lower"].to_numpy(), frame["obs_ci_upper"].to_numpy()


def forecast_prophet(model, params, train, test, intervals):
    from prophet import Prophet
    m = Prophet(growth="linear", yearly_seasonality=False, weekly_seasonality=False, daily_seasonality=False,
                changepoint_prior_scale=params["changepoint_prior_scale"], seasonality_prior_scale=params["seasonality_prior_scale"],
                changepoint_range=FIXED["changepoint_range"], n_changepoints=FIXED["n_changepoints"],
                interval_width=FIXED["interval_width"], uncertainty_samples=500 if intervals else 0)
    m.add_seasonality(name="yearly", period=365.25, fourier_order=params["yearly_fourier_order"])
    reg = regressor(model)
    cols = ["ds", "y"] + ([reg] if reg else [])
    if reg:
        m.add_regressor(reg, prior_scale=FIXED["enso_prior_scale"], standardize=True)
    df = train.reset_index(names="ds")[cols]
    m.fit(df, seed=ta.SEED)
    future = test.reset_index(names="ds")[["ds"] + ([reg] if reg else [])]
    np.random.seed(ta.SEED)
    out = m.predict(future)
    if intervals:
        return out["yhat"].to_numpy(), out["yhat_lower"].to_numpy(), out["yhat_upper"].to_numpy()
    return out["yhat"].to_numpy(), None, None


def forecast_mlp(params, train, test):
    """One-hidden-layer network on month indicators, time and December Nino 3.4; scaling fitted on training only."""
    from sklearn.neural_network import MLPRegressor

    def features(df):
        t = ((df.index.year - 1992) + (df.index.month - 1) / 12).to_numpy()
        return np.column_stack([t, df["n34_oper"].to_numpy()] + [(df.index.month == m).astype(float) for m in range(1, 13)])

    xtr, xte = features(train), features(test)
    mu, sd = xtr[:, :2].mean(axis=0), xtr[:, :2].std(axis=0)
    xtr[:, :2], xte[:, :2] = (xtr[:, :2] - mu) / sd, (xte[:, :2] - mu) / sd
    ymu, ysd = train["y"].mean(), train["y"].std()
    net = MLPRegressor(hidden_layer_sizes=(params["hidden_units"],), alpha=params["alpha"], activation="tanh",
                       solver="lbfgs", max_iter=5000, random_state=ta.SEED)
    net.fit(xtr, (train["y"].to_numpy() - ymu) / ysd)
    return net.predict(xte) * ysd + ymu, None, None


def split(data, key, last_train_year, test_year):
    df = data[[key, "n34_oper", "n34_recon"]].rename(columns={key: "y"})
    return df[df.index.year <= last_train_year], df[df.index.year == test_year]


def tune(job):
    """Optuna TPE on inner folds inside one outer training set; returns best params and every trial."""
    key, model, last_train_year = job
    logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
    logging.getLogger("prophet").setLevel(logging.ERROR)
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    data = dataset()
    inner = range(last_train_year - INNER_YEARS + 1, last_train_year + 1)
    trials = []

    def objective(trial):
        if model == MLP:
            params = {"hidden_units": trial.suggest_categorical("hidden_units", MLP_SPACE["hidden_units"]),
                      "alpha": trial.suggest_float("alpha", *MLP_SPACE["alpha"], log=True)}
        else:
            params = {"changepoint_prior_scale": trial.suggest_float("changepoint_prior_scale", *SPACE["changepoint_prior_scale"], log=True),
                      "seasonality_prior_scale": trial.suggest_float("seasonality_prior_scale", *SPACE["seasonality_prior_scale"], log=True),
                      "yearly_fourier_order": trial.suggest_int("yearly_fourier_order", *SPACE["yearly_fourier_order"])}
        maes = []
        for year in inner:
            train, test = split(data, key, year - 1, year)
            yhat, _, _ = forecast_mlp(params, train, test) if model == MLP else forecast_prophet(model, params, train, test, intervals=False)
            maes.append(float(np.mean(np.abs(yhat - test["y"].to_numpy()))))
        trials.append({"variable": key, "model": model, "outer_last_train_year": last_train_year, "trial": trial.number,
                       **params, "inner_years": f"{inner.start}-{inner.stop - 1}", "inner_mae_mean": float(np.mean(maes)),
                       "inner_maes": json.dumps([round(x, 6) for x in maes])})
        return float(np.mean(maes))

    seed = ta.SEED + 1000 * list(ta.VARS).index(key) + 100 * TUNED.index(model) + last_train_year
    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(objective, n_trials=JOB_TRIALS)
    return key, model, last_train_year, study.best_params, trials


JOB_TRIALS = 25


def metrics(key, model, fold, test, yhat, lo, hi, params=None):
    y = test["y"].to_numpy()
    row = {"variable": key, "model": model, "fold": fold, "n_months": len(y), "mae": float(np.mean(np.abs(yhat - y))),
           "rmse": float(np.sqrt(np.mean((yhat - y) ** 2))), "bias": float(np.mean(yhat - y)), "operational": not model.endswith("RECON")}
    if lo is not None:
        row["coverage80"] = float(np.mean((y >= lo) & (y <= hi)))
        row["interval80_mean_width"] = float(np.mean(hi - lo))
    if params:
        row["params"] = json.dumps(params)
    return row


def summarize(perf):
    summary = []
    for (key, model), g in perf.groupby(["variable", "model"], sort=False):
        outer, hold = g[~g.fold.str.startswith("holdout")], g[g.fold.str.startswith("holdout")]
        ref = {name: perf[(perf.variable == key) & (perf.model == name)].set_index("fold")["mae"]
               for name in ("CLIM", "OLS_TREND", "OLS_ENSO_OPER", "OLS_ENSO_RECON")}
        m = g.set_index("fold")["mae"]
        o, h = list(outer.fold), list(hold.fold)

        def consistent(r):
            return bool(m[o].mean() < r[o].mean() and (m[o] < r[o]).sum() >= 4 and m[h].mean() < r[h].mean())
        summary.append({"variable": key, "model": model, "operational": bool(g.operational.iloc[0]),
                        "mae_outer_mean": outer.mae.mean(), "mae_holdout_mean": hold.mae.mean(),
                        "rmse_outer_mean": outer.rmse.mean(), "rmse_holdout_mean": hold.rmse.mean(),
                        "bias_outer_mean": outer.bias.mean(), "bias_holdout_mean": hold.bias.mean(),
                        "skill_vs_clim_outer": 1 - outer.mae.mean() / ref["CLIM"][o].mean(),
                        "skill_vs_clim_holdout": 1 - hold.mae.mean() / ref["CLIM"][h].mean(),
                        "outer_folds_better_than_clim": int((m[o] < ref["CLIM"][o]).sum()),
                        "consistent_vs_clim": consistent(ref["CLIM"]), "consistent_vs_ols_trend": consistent(ref["OLS_TREND"]),
                        "consistent_vs_ols_enso_oper": consistent(ref["OLS_ENSO_OPER"]) if model.endswith("OPER") else None,
                        "consistent_vs_ols_enso_recon": consistent(ref["OLS_ENSO_RECON"]) if model.endswith("RECON") else None,
                        "coverage80_outer": outer["coverage80"].mean() if "coverage80" in g else None,
                        "coverage80_holdout": hold["coverage80"].mean() if "coverage80" in g else None})
    return pd.DataFrame(summary)


def run_tuning(models, keys, workers, trials):
    jobs = [(k, m, y - 1) for k in keys for m in models for y in OUTER] + [(k, m, HOLDOUT[0] - 1) for k in keys for m in models]
    with ProcessPoolExecutor(max_workers=workers, initializer=_init, initargs=(trials,)) as pool:
        tuned = list(pool.map(tune, jobs))
    return {(k, m, y): p for k, m, y, p, _ in tuned}, [t for *_, ts in tuned for t in ts]


def evaluate(data, keys, models, best):
    rows = []
    for key in keys:
        for year in OUTER + HOLDOUT:
            fold = str(year) if year in OUTER else f"holdout_{year}"
            train, test = split(data, key, year - 1, year)
            for model in models:
                if model in SIMPLE:
                    rows.append(metrics(key, model, fold, test, *forecast_simple(model, train, test)))
                    continue
                params = best[(key, model, year - 1 if year in OUTER else HOLDOUT[0] - 1)]
                out = forecast_mlp(params, train, test) if model == MLP else forecast_prophet(model, params, train, test, intervals=True)
                rows.append(metrics(key, model, fold, test, *out, params=params))
    return rows


def main(trials, workers):
    global JOB_TRIALS
    JOB_TRIALS = trials
    data = dataset()
    best, trial_log = run_tuning(PROPHETS, list(ta.VARS), workers, trials)
    rows = evaluate(data, list(ta.VARS), SIMPLE + PROPHETS, best)
    summary = summarize(pd.DataFrame(rows))
    # Pre-registered gate: a small network is tried only where some Prophet passes the consistency rule against OLS_TREND.
    gated = sorted(set(summary[summary.model.isin(PROPHETS) & summary.consistent_vs_ols_trend].variable))
    if gated:
        mlp_best, mlp_trials = run_tuning((MLP,), gated, workers, trials)
        best.update(mlp_best)
        trial_log += mlp_trials
        rows += evaluate(data, gated, (MLP,), best)
        summary = summarize(pd.DataFrame(rows))
    ta.write_table(ta.OUT / "forecast_performance_by_fold.csv", rows)
    summary.to_csv(ta.OUT / "forecast_summary.csv", index=False)
    ta.write_table(ta.OUT / "optuna_trials.csv", trial_log)
    import optuna, prophet, sklearn
    (ta.OUT / "forecast_config.json").write_text(json.dumps({
        "outer_test_years": OUTER, "holdout_years": HOLDOUT, "inner_years_per_outer": INNER_YEARS, "trials_per_study": trials,
        "sampler": "optuna TPESampler, seed = 20261114 + 1000*variable + 100*model + last training year",
        "objective": "mean MAE over inner 12-month folds", "search_space": SPACE, "mlp_search_space": MLP_SPACE, "fixed": FIXED,
        "nn_gate_variables": gated,
        "versions": {"prophet": prophet.__version__, "optuna": optuna.__version__, "scikit-learn": sklearn.__version__},
        "plan_sha256": __import__("hashlib").sha256((ta.ROOT / "docs/ANALISIS_TENDENCIAS_PLAN_V2.md").read_bytes()).hexdigest(),
        "best_params": [{"variable": k, "model": m, "last_train_year": y, **p} for (k, m, y), p in best.items()]}, indent=1) + "\n", encoding="utf-8")
    figure_forecast()
    print(summary.round(3).to_string(index=False))


def figure_forecast():
    import matplotlib.pyplot as plt
    perf = pd.read_csv(ta.OUT / "forecast_performance_by_fold.csv")
    folds = list(dict.fromkeys(perf["fold"]))
    styles = {"CLIM": ("black", "-"), "PERSIST": (ta.GRAY, ":"), "OLS_TREND": (ta.BLUE, "-"), "OLS_ENSO_OPER": (ta.BLUE, "--"),
              "OLS_ENSO_RECON": (ta.BLUE, ":"), "PROPHET": (ta.ORANGE, "-"), "PROPHET_ENSO_OPER": (ta.ORANGE, "--"), "PROPHET_ENSO_RECON": (ta.ORANGE, ":"), MLP: (ta.PURPLE, "--")}
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    for ax, key in zip(axes, ta.VARS):
        for model, (color, ls) in styles.items():
            g = perf[(perf.variable == key) & (perf.model == model)].set_index("fold").reindex(folds)
            if g["mae"].isna().all():
                continue
            ax.plot(range(len(folds)), g["mae"], color=color, ls=ls, marker="o", ms=3, label=model)
        ax.axvspan(len(OUTER) - 0.5, len(folds) - 0.5, color=ta.GRAY, alpha=0.12)
        ax.set_xticks(range(len(folds)))
        ax.set_xticklabels([f.replace("holdout_", "R") for f in folds], fontsize=7)
        ax.set_title(f"{ta.VARS[key]['name'].split(' (')[0]}: MAE por año pronosticado ({ta.VARS[key]['unit']})\nsombreado = periodo reservado; RECON usa ENSO observado (no operativo)", fontsize=8)
    axes[0].legend(fontsize=6)
    if MLP in set(perf.model):
        axes[2].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(ta.FIG / "prediccion_mae.png", dpi=120)
    plt.close(fig)


def _init(trials):
    global JOB_TRIALS
    JOB_TRIALS = trials
    os.environ.setdefault("PYTHONWARNINGS", "ignore")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=25)
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = parser.parse_args()
    main(args.trials, args.workers)
