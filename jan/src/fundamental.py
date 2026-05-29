"""Fundamental-vertical signal: target weights for ACWI/AGG/GLD/BSV.

Pure rates-driven GLD tilt: smoothed monthly change in the 10Y real yield
(FRED DFII10), z-scored over a 24-month window, mapped to a GLD overweight
via tanh and capped at +/- MAX_TILT. The other three legs split (1 - GLD)
equally. No macro-regime overlay; that domain belongs to Rayane's vertical.
"""
import numpy as np
import pandas as pd

from src.data import load_fred_as_of

UNIVERSE = ["ACWI", "AGG", "GLD", "BSV"]

SMOOTH_WINDOW = 3
LOOKBACK = 24
BASELINE_WEIGHT = 0.25
MAX_TILT = 0.15


def _gld_tilt(as_of_date: pd.Timestamp) -> float:
    """GLD tilt from negated z-score of smoothed Delta DFII10."""
    as_of_ts = pd.Timestamp(as_of_date)
    series = load_fred_as_of("DFII10", as_of_ts, start="2000-01-01")
    monthly = series.resample("ME").last()
    # Keep only completed month-end buckets to match a monthly signal cadence.
    monthly = monthly.loc[monthly.index <= as_of_ts]
    if monthly.empty:
        raise ValueError(f"No completed DFII10 month available on or before {as_of_ts.date()}")
    delta_smoothed = monthly.diff().rolling(SMOOTH_WINDOW).mean()
    z = (delta_smoothed - delta_smoothed.rolling(LOOKBACK).mean()) / delta_smoothed.rolling(LOOKBACK).std()
    tilt = MAX_TILT * np.tanh(-z)
    valid_tilt = tilt.dropna()
    if valid_tilt.empty:
        raise ValueError(
            f"Insufficient DFII10 history on {as_of_ts.date()} for a {LOOKBACK}-month z-score"
        )
    return float(valid_tilt.iloc[-1])


def get_weights(as_of_date: pd.Timestamp | str) -> pd.Series:
    """Target weights for ACWI/AGG/GLD/BSV as known on as_of_date."""
    gld_tilt = _gld_tilt(pd.Timestamp(as_of_date))
    gld = float(np.clip(BASELINE_WEIGHT + gld_tilt, 0, 1))
    other = (1 - gld) / 3
    return pd.Series(
        {"ACWI": other, "AGG": other, "GLD": gld, "BSV": other}
    ).reindex(UNIVERSE)
