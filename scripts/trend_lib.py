"""Estimators and diagnostics for the seasonal trend audit (no file I/O)."""

import numpy as np
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox, breaks_cusumolsresid, het_breuschpagan
from statsmodels.stats.stattools import jarque_bera
from statsmodels.tsa.ar_model import AutoReg, ar_select_order

Z975 = 1.959963984540054
SIEVE_WARMUP = 200
SEASONS = {"DJF": (12, 1, 2), "MAM": (3, 4, 5), "JJA": (6, 7, 8), "SON": (9, 10, 11)}


def design(n, months, extras=None):
    """Intercept, time in years from the first month, months 2-12, then extra columns."""
    t = np.arange(n) / 12
    cols = [np.ones(n), t] + [(months == m).astype(float) for m in range(2, 13)]
    names = ["const", "t"] + [f"m{m}" for m in range(2, 13)]
    for name, values in (extras or {}).items():
        cols.append(np.asarray(values, float))
        names.append(name)
    return np.column_stack(cols), names


def fit_hac(y, X, maxlags):
    return sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags})


def coefficient(res, index, scale=1.0, critical="z"):
    """Estimate, standard error, 95% interval and two-sided p for one coefficient (scaled)."""
    beta, se = res.params[index], res.bse[index]
    if critical == "t":
        q = stats.t.ppf(0.975, res.df_resid)
        p = 2 * stats.t.sf(abs(beta / se), res.df_resid)
    else:
        q, p = Z975, 2 * stats.norm.sf(abs(beta / se))
    return {"est": beta * scale, "se": se * scale, "lo": (beta - q * se) * scale,
            "hi": (beta + q * se) * scale, "p": p}


def wald(res, rows):
    """HAC Wald chi-square test that the listed linear contrasts are zero."""
    r = np.zeros((len(rows), len(res.params)))
    for i, row in enumerate(rows):
        for j, value in row.items():
            r[i, j] = value
    w = res.wald_test(r, use_f=False, scalar=True)
    return float(w.statistic), float(w.pvalue)


def block_bootstrap(y, X, index, months, block_len, reps, key):
    """Circular residual block bootstrap of one coefficient; blocks start in January
    and last a multiple of 12 months, so every residual keeps its calendar-month phase."""
    n, k = X.shape
    if n % 12 or block_len % 12:
        raise ValueError("Series and blocks must contain whole years")
    pinv = np.linalg.pinv(X)
    beta = pinv @ y
    resid = (y - X @ beta) * np.sqrt(n / (n - k))
    jan = np.flatnonzero(months == 1)
    nblocks = int(np.ceil(n / block_len))
    rng = np.random.default_rng(list(key))
    starts = rng.choice(jan, size=(reps, nblocks))
    idx = ((starts[:, :, None] + np.arange(block_len)) % n).reshape(reps, -1)[:, :n]
    dev = resid[idx] @ pinv[index]
    est = beta[index]
    lo, hi = np.percentile(est + dev, [2.5, 97.5])
    p = (1 + np.sum(np.abs(dev) >= abs(est))) / (reps + 1)
    return {"est": est, "se": dev.std(ddof=1), "lo": lo, "hi": hi, "p": p}


def annual_bootstrap(y, block_years, reps, key):
    """OLS slope per year of an annual series with a circular residual block bootstrap."""
    n = len(y)
    X = np.column_stack([np.ones(n), np.arange(n)])
    pinv = np.linalg.pinv(X)
    beta = pinv @ y
    resid = (y - X @ beta) * np.sqrt(n / (n - 2))
    rng = np.random.default_rng(list(key))
    nblocks = int(np.ceil(n / block_years))
    starts = rng.integers(0, n, size=(reps, nblocks))
    idx = ((starts[:, :, None] + np.arange(block_years)) % n).reshape(reps, -1)[:, :n]
    dev = resid[idx] @ pinv[1]
    lo, hi = np.percentile(beta[1] + dev, [2.5, 97.5])
    p = (1 + np.sum(np.abs(dev) >= abs(beta[1]))) / (reps + 1)
    return {"est": beta[1], "se": dev.std(ddof=1), "lo": lo, "hi": hi, "p": p}


def seasonal_theil_sen(grid):
    """Median of all within-month slopes between years; grid has shape (years, 12)."""
    i, j = np.triu_indices(grid.shape[0], 1)
    return float(np.median((grid[j] - grid[i]) / (j - i)[:, None]))


def theil_sen_bootstrap(grid, block_years, reps, key, chunk=250):
    """Residual block bootstrap (blocks of whole years) around the Theil-Sen line."""
    years = grid.shape[0]
    slope = seasonal_theil_sen(grid)
    time = np.arange(years)[:, None]
    detrended = grid - slope * time
    fit = np.median(detrended, axis=0)[None, :] + slope * time
    resid = grid - fit
    i, j = np.triu_indices(years, 1)
    nblocks = int(np.ceil(years / block_years))
    rng = np.random.default_rng(list(key))
    starts = rng.integers(0, years, size=(reps, nblocks))
    idx = ((starts[:, :, None] + np.arange(block_years)) % years).reshape(reps, -1)[:, :years]
    boot = np.empty(reps)
    for a in range(0, reps, chunk):
        sample = fit[None] + resid[idx[a:a + chunk]]
        d = (sample[:, j, :] - sample[:, i, :]) / (j - i)[None, :, None]
        boot[a:a + chunk] = np.median(d.reshape(len(sample), -1), axis=1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return {"est": slope, "se": boot.std(ddof=1), "lo": lo, "hi": hi}


def residual_diagnostics(res_ols, months):
    """Residual checks on an ordinary least-squares fit (non-robust results object)."""
    e, n, k = res_ols.resid, len(res_ols.resid), res_ols.model.exog.shape[1]
    lb = acorr_ljungbox(e, lags=[12, 24], return_df=True)
    jb, jb_p, skew, kurt = jarque_bera(e)
    cook = res_ols.get_influence().cooks_distance[0]
    cusum = breaks_cusumolsresid(e, ddof=k)
    return {
        "resid_sd": float(e.std(ddof=k)),
        "resid_acf1": float(np.corrcoef(e[1:], e[:-1])[0, 1]),
        "ljungbox_p12": float(lb["lb_pvalue"].iloc[0]),
        "ljungbox_p24": float(lb["lb_pvalue"].iloc[1]),
        "breusch_pagan_p": float(het_breuschpagan(e, res_ols.model.exog)[1]),
        "levene_month_p": float(stats.levene(*[e[months == m] for m in range(1, 13)]).pvalue),
        "jarque_bera_p": float(jb_p),
        "resid_skew": float(skew),
        "resid_kurtosis": float(kurt),
        "cook_max": float(cook.max()),
        "cook_max_index": int(cook.argmax()),
        "cook_count_gt_4_over_n": int((cook > 4 / n).sum()),
        "cusum_p": float(cusum[1]),
    }


def leave_one_year_out(y, X, months, index=1):
    """Slope per decade after dropping each whole calendar year (diagnostic, not a filter)."""
    years = np.arange(len(y)) // 12
    out = []
    for yr in np.unique(years):
        keep = years != yr
        out.append(10 * np.linalg.lstsq(X[keep], y[keep], rcond=None)[0][index])
    return np.array(out)


def collinearity(t, others):
    """Correlation of t with the first extra column and VIF of t given all other regressors."""
    z = sm.add_constant(others)
    r2 = sm.OLS(t, z).fit().rsquared
    return float(np.corrcoef(t, others[:, 0])[0, 1]), float(1 / (1 - r2))


def ar_fit(resid, max_order, order):
    if order == "aic":
        lags = ar_select_order(resid, maxlag=max_order, trend="n", ic="aic").ar_lags
        p = max(lags) if lags else 0
    else:
        p = order
    if p == 0:
        return np.array([]), resid.copy()
    res = AutoReg(resid, lags=p, trend="n").fit()
    return np.asarray(res.params), np.asarray(res.resid)  # innovations for observations p..n-1


def simulate_t(y, X_full, X_null, season, period, hac, max_order, variant, reps, key):
    """Bootstrap distribution of t = beta_t / SE_HAC under the no-trend null with AR(p) errors."""
    null_fit = np.linalg.lstsq(X_null, y, rcond=None)[0]
    fitted = X_null @ null_fit
    resid = y - fitted
    phi, innov = ar_fit(resid, max_order, variant["order"])
    p = len(phi)
    season_innov = season[p:]
    if variant["monthly_scale"]:
        sd = np.array([innov[season_innov == k].std(ddof=1) for k in range(period)])
        z = innov / sd[season_innov]
    else:
        sd = np.full(period, innov.std())
        z = innov / innov.std()
    rng = np.random.default_rng(list(key))
    n = len(y)
    total = n + SIEVE_WARMUP
    phase = (season[0] + np.arange(total) - SIEVE_WARMUP) % period if period > 1 else np.zeros(total, int)
    draws = rng.standard_normal((reps, total)) if variant["innov"] == "gaussian" else rng.choice(z, size=(reps, total))
    shocks = draws * sd[phase]
    e = np.zeros((reps, total))
    for i in range(total):
        acc = shocks[:, i].copy()
        for j in range(p):
            if i - j - 1 >= 0:
                acc += phi[j] * e[:, i - j - 1]
        e[:, i] = acc
    e = e[:, SIEVE_WARMUP:]
    tstats = np.empty(reps)
    for b in range(reps):
        res = fit_hac(fitted + e[b], X_full, hac)
        tstats[b] = res.params[1] / res.bse[1]
    return tstats, p


def sieve_pvalue(tstats, t_obs):
    """Two-sided bootstrap p-value and the 95% critical value of |t*|."""
    return float((1 + np.sum(np.abs(tstats) >= abs(t_obs))) / (len(tstats) + 1)), float(np.percentile(np.abs(tstats), 95))
