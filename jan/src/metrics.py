"""Shared performance metrics for strategy and benchmark return series."""

import numpy as np
import pandas as pd


def portfolio_returns(weights: pd.DataFrame, period_returns: pd.DataFrame) -> pd.Series:
    """Lagged portfolio returns for close-to-close execution."""
    aligned_weights = weights.reindex(period_returns.index, method="ffill")
    return (aligned_weights.shift() * period_returns).sum(axis=1, skipna=False).dropna()


def compute_kpis(
    returns: pd.Series,
    benchmark: pd.Series | None = None,
    *,
    periods_per_year: int,
    mar: float = 0.0,
    risk_free_rate: float = 0.0,
    min_periods_for_ratio_metrics: int = 24,
) -> dict:
    """Compute core KPIs with standard downside-deviation Sortino."""
    ret = returns.dropna()
    if ret.empty:
        return {}

    rf_per_period = risk_free_rate / periods_per_year
    mar_per_period = mar / periods_per_year
    ann_scale = np.sqrt(periods_per_year)

    mean = ret.mean()
    vol = ret.std()
    excess = ret - rf_per_period
    excess_mean = excess.mean()
    excess_vol = excess.std()

    downside = np.minimum(excess - mar_per_period, 0.0)
    downside_dev = float(np.sqrt(np.mean(np.square(downside))))

    equity = (1 + ret).cumprod()
    drawdown = equity / equity.cummax() - 1
    n_years = len(ret) / periods_per_year
    total_return = equity.iloc[-1] - 1
    cagr = equity.iloc[-1] ** (1 / n_years) - 1

    enough_ratio_obs = len(ret) >= min_periods_for_ratio_metrics
    sharpe = np.nan
    sortino = np.nan
    if enough_ratio_obs and excess_vol > 0:
        sharpe = (excess_mean / excess_vol) * ann_scale
    if enough_ratio_obs and downside_dev > 0:
        sortino = (excess_mean / downside_dev) * ann_scale

    out = {
        "n_periods": len(ret),
        "total_return": total_return,
        "CAGR": cagr,
        "arithmetic_ann_return": mean * periods_per_year,
        "ann_vol": vol * ann_scale,
        "Sharpe_rf0": sharpe,
        "Sortino_rf0": sortino,
        "max_drawdown": drawdown.min(),
        "calmar": cagr / abs(drawdown.min()) if drawdown.min() < 0 else np.nan,
        "hit_rate": (ret > 0).mean(),
        "best_period": ret.max(),
        "worst_period": ret.min(),
    }

    if benchmark is not None:
        aligned_benchmark = benchmark.reindex(ret.index)
        active = (ret - aligned_benchmark).dropna()
        active_sharpe = np.nan
        if len(active) >= min_periods_for_ratio_metrics and active.std() > 0:
            active_sharpe = (active.mean() / active.std()) * ann_scale
        out["active_sharpe_vs_bench"] = active_sharpe
        out["excess_ann_return"] = active.mean() * periods_per_year if not active.empty else np.nan

    return out
