"""Weekly KPIs for the fundamental strategy vs equal-weight benchmark."""
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import TRAIN_END, VAL_END
from src.data import load_etf_prices
from src.fundamental import UNIVERSE, get_weights
from src.metrics import compute_kpis, portfolio_returns

PERIODS_PER_YEAR = 52
MIN_PERIODS_FOR_RATIO = 52


def build_weights(rebalance_dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Build target weights directly from production get_weights()."""
    return pd.DataFrame([get_weights(date) for date in rebalance_dates], index=rebalance_dates)


def main() -> None:
    prices = load_etf_prices(UNIVERSE, start="2008-01-01")
    weekly_prices = prices.resample("W-FRI").last()
    weekly_returns = weekly_prices.pct_change()
    full_dates = pd.date_range("2008-01-04", VAL_END, freq="W-FRI")
    weekly_returns = weekly_returns.reindex(full_dates)

    weights = build_weights(full_dates)
    strat = portfolio_returns(weights, weekly_returns)

    eq_weights = pd.DataFrame(0.25, index=full_dates, columns=UNIVERSE)
    bench = portfolio_returns(eq_weights, weekly_returns)

    windows = {
        "train (through 2024-12-31)": (None, TRAIN_END),
        "validation (2025)": (TRAIN_END, VAL_END),
        "full sample": (None, VAL_END),
    }

    records = []
    for label, (lo, hi) in windows.items():
        mask = pd.Series(True, index=strat.index)
        if lo is not None:
            mask &= strat.index > lo
        if hi is not None:
            mask &= strat.index <= hi
        s = strat[mask]
        b = bench.reindex(s.index)
        for name, ret, bm in [("Fundamental", s, b), ("Equal-weight", b, None)]:
            row = {
                "window": label,
                "strategy": name,
                **compute_kpis(
                    ret,
                    bm,
                    periods_per_year=PERIODS_PER_YEAR,
                    min_periods_for_ratio=MIN_PERIODS_FOR_RATIO,
                ),
            }
            records.append(row)

    df = pd.DataFrame(records).set_index(["window", "strategy"])
    df = df.rename(
        columns={
            "n_periods": "n_weeks",
            "ann_return": "arith_ann_return",
            "best_period": "best_week",
            "worst_period": "worst_week",
        }
    )
    pct_cols = [
        "total_return",
        "CAGR",
        "arith_ann_return",
        "ann_vol",
        "max_drawdown",
        "hit_rate",
        "best_week",
        "worst_week",
        "excess_ann_return",
    ]
    for c in pct_cols:
        if c in df.columns:
            df[c] = df[c].map(lambda x: f"{x:.2%}" if pd.notna(x) else "")
    ratio_cols = ["Sharpe", "Sortino", "calmar", "active_sharpe_vs_bench"]
    for c in ratio_cols:
        if c in df.columns:
            df[c] = df[c].map(lambda x: f"{x:.3f}" if pd.notna(x) else "")
    if "n_weeks" in df.columns:
        df["n_weeks"] = df["n_weeks"].astype(int)

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    print(df.to_string())


if __name__ == "__main__":
    main()
