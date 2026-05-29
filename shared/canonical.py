"""Canonical setup, KPI bank, turnover projection, and submission writer.

Source of truth for code that is inlined verbatim into each vertical's
notebook. Each canonical block is delimited with markers so the parity
checker can verify that the four notebooks (Jan, Sacha, Rayane, Cesar)
have not drifted.

No notebook imports from this module at runtime. The canonical blocks
between the BEGIN/END markers must appear unchanged inside each notebook.

If you edit a block here, sync every notebook's matching block in the
same change. Run shared/parity_check.py to confirm.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# === BEGIN canonical:constants ===
UNIVERSE = ["ACWI", "AGG", "GLD", "BSV"]
TEAM_ID = "TeamXX"
TRAIN_END = pd.Timestamp("2024-12-31")
VAL_END = pd.Timestamp("2025-12-31")
TURNOVER_CAP = 0.25
PERIODS_PER_YEAR = 52
RISK_FREE_RATE = 0.0
MAR = 0.0
MIN_PERIODS_FOR_RATIO = 24
RNG_SEED = 42

np.random.seed(RNG_SEED)
pd.set_option("display.float_format", "{:.4f}".format)
# === END canonical:constants ===


# === BEGIN canonical:kpis ===
def compute_kpis(
    returns: pd.Series,
    benchmark: pd.Series | None = None,
    *,
    periods_per_year: int = PERIODS_PER_YEAR,
    risk_free_rate: float = RISK_FREE_RATE,
    mar: float = MAR,
    min_periods_for_ratio: int = MIN_PERIODS_FOR_RATIO,
) -> dict:
    """Weekly KPI bank shared by every vertical.

    Sharpe uses mean excess return over sample-std (ddof=1), annualised by
    sqrt(periods_per_year). Sortino uses the textbook downside deviation:
    sqrt(mean(min(excess - mar_per_period, 0)^2)). Returns NaN for the
    ratio metrics when the sample is shorter than min_periods_for_ratio.
    """
    r = returns.dropna()
    if r.empty:
        return {}
    rf_per = risk_free_rate / periods_per_year
    mar_per = mar / periods_per_year
    ann = float(np.sqrt(periods_per_year))

    excess = r - rf_per
    mean_excess = float(excess.mean())
    vol = float(excess.std(ddof=1))

    downside = np.minimum(excess - mar_per, 0.0)
    downside_dev = float(np.sqrt(np.mean(np.square(downside))))

    equity = (1.0 + r).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    n = len(r)
    n_years = n / periods_per_year
    total_return = float(equity.iloc[-1] - 1.0)
    cagr = float(equity.iloc[-1] ** (1.0 / n_years) - 1.0) if n_years > 0 else float("nan")
    max_dd = float(drawdown.min())

    enough = n >= min_periods_for_ratio
    sharpe = (mean_excess / vol) * ann if enough and vol > 0 else float("nan")
    sortino = (mean_excess / downside_dev) * ann if enough and downside_dev > 0 else float("nan")
    calmar = cagr / abs(max_dd) if max_dd < 0 and not np.isnan(cagr) else float("nan")

    out = {
        "n_periods": int(n),
        "total_return": total_return,
        "CAGR": cagr,
        "ann_return": float(r.mean() * periods_per_year),
        "ann_vol": float(r.std(ddof=1) * ann),
        "Sharpe": float(sharpe),
        "Sortino": float(sortino),
        "max_drawdown": max_dd,
        "calmar": float(calmar),
        "hit_rate": float((r > 0).mean()),
        "best_period": float(r.max()),
        "worst_period": float(r.min()),
    }
    if benchmark is not None:
        bench = benchmark.reindex(r.index).dropna()
        active = (r - bench).dropna()
        if len(active) >= min_periods_for_ratio and active.std(ddof=1) > 0:
            out["active_sharpe_vs_bench"] = float(
                (active.mean() / active.std(ddof=1)) * ann
            )
        else:
            out["active_sharpe_vs_bench"] = float("nan")
        out["excess_ann_return"] = (
            float(active.mean() * periods_per_year) if not active.empty else float("nan")
        )
    return out
# === END canonical:kpis ===


# === BEGIN canonical:turnover ===
def project_to_turnover_ball(
    target: pd.Series,
    previous: pd.Series,
    *,
    cap: float = TURNOVER_CAP,
) -> pd.Series:
    """L1-ball projection of target toward previous so sum(|target-previous|) <= cap.

    Returns a Series indexed by UNIVERSE, clipped to [0,1] and renormalised to
    sum to 1. Matches the math each vertical already used independently.
    """
    target = target.reindex(UNIVERSE).astype(float)
    previous = previous.reindex(UNIVERSE).astype(float)
    delta = target - previous
    total = float(np.abs(delta).sum())
    if total <= cap + 1e-12:
        out = target.copy()
    else:
        out = previous + delta * (cap / total)
    out = out.clip(lower=0.0, upper=1.0)
    s = float(out.sum())
    return out / s if s > 0 else target
# === END canonical:turnover ===


# === BEGIN canonical:submission ===
def write_submission_csv(
    weights_fraction: pd.Series,
    week: "pd.Timestamp | str",
    team_id: str,
    out_dir: Path,
    *,
    vertical_tag: str | None = None,
    previous_path: Path | None = None,
    enforce_turnover: bool = True,
) -> Path:
    """Write the weekly submission CSV in the format mandated by CLAUDE.md.

    Input weights are fractions in [0,1] summing to 1. They are scaled to
    percentages, rounded to two decimals, and the residual is added to the
    largest weight so the row sums to exactly 100.00. Per-vertical draft files
    get a {team_id}_{vertical_tag}_{date}.csv name; the final team submission
    uses {team_id}_{date}.csv. Header is week,team_id,acwi,agg,gld,bsv.
    """
    week_ts = pd.Timestamp(week)
    week_str = week_ts.strftime("%Y-%m-%d")
    w = weights_fraction.reindex(UNIVERSE).astype(float) * 100.0
    w = w.round(2)
    residual = round(100.0 - float(w.sum()), 2)
    largest = w.idxmax()
    w.loc[largest] = round(float(w.loc[largest]) + residual, 2)
    if not ((w >= 0).all() and (w <= 100).all()):
        raise ValueError(f"weights out of [0,100]: {w.to_dict()}")
    if abs(float(w.sum()) - 100.0) > 1e-6:
        raise ValueError(f"weights do not sum to 100: {float(w.sum())}")
    if enforce_turnover and previous_path is not None and Path(previous_path).exists():
        prev_df = pd.read_csv(previous_path)
        prev_w = pd.Series(
            {k: float(prev_df.iloc[0][k.lower()]) for k in UNIVERSE},
        ).reindex(UNIVERSE)
        turnover_pp = float((w - prev_w).abs().sum())
        if turnover_pp - 25.0 > 1e-9:
            raise ValueError(
                f"turnover {turnover_pp:.2f}pp > 25.00pp vs {Path(previous_path).name}"
            )
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = (
        f"{team_id}_{vertical_tag}_{week_str}.csv"
        if vertical_tag
        else f"{team_id}_{week_str}.csv"
    )
    path = out_dir / name
    row = {
        "week": week_str,
        "team_id": team_id,
        "acwi": w["ACWI"],
        "agg": w["AGG"],
        "gld": w["GLD"],
        "bsv": w["BSV"],
    }
    pd.DataFrame([row], columns=["week", "team_id", "acwi", "agg", "gld", "bsv"]).to_csv(
        path, index=False, float_format="%.2f",
    )
    return path
# === END canonical:submission ===
