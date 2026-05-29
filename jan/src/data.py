"""Data loaders (FRED macro series, yfinance ETF prices) with on-disk CSV cache."""
import os
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
FRED_BASE = "https://api.stlouisfed.org/fred"


def _load_env() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def _fred_api_key() -> str:
    _load_env()
    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise RuntimeError("FRED_API_KEY not set. Copy .env.example to .env and add your key.")
    return key


def load_fred_series(
    series_id: str,
    start: str = "1990-01-01",
    end: str | None = None,
    refresh: bool = False,
) -> pd.Series:
    """Load a FRED series, cached at data/<series_id>.csv (full history, filtered on read)."""
    DATA_DIR.mkdir(exist_ok=True)
    cache = DATA_DIR / f"{series_id}.csv"

    if cache.exists() and not refresh:
        cached = pd.read_csv(cache, index_col="date", parse_dates=["date"])[series_id]
        return cached.loc[start:end]

    params = {
        "series_id": series_id,
        "api_key": _fred_api_key(),
        "file_type": "json",
    }
    response = requests.get(f"{FRED_BASE}/series/observations", params=params, timeout=30)
    response.raise_for_status()

    observations = response.json()["observations"]
    df = pd.DataFrame(observations)
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.set_index("date")[["value"]].rename(columns={"value": series_id})
    df.to_csv(cache)
    return df[series_id].loc[start:end]


def load_fred_vintages(
    series_id: str,
    start: str = "1990-01-01",
    refresh: bool = False,
) -> pd.DataFrame:
    """Full ALFRED vintage history, cached at data/<series_id>_vintages.csv (one row per revision)."""
    DATA_DIR.mkdir(exist_ok=True)
    cache = DATA_DIR / f"{series_id}_vintages.csv"

    if cache.exists() and not refresh:
        df = pd.read_csv(cache, parse_dates=["date", "realtime_start", "realtime_end"])
        return df[df["date"] >= pd.Timestamp(start)].reset_index(drop=True)

    params = {
        "series_id": series_id,
        "api_key": _fred_api_key(),
        "file_type": "json",
        "realtime_start": "1776-07-04",
        "realtime_end": "9999-12-31",
    }
    response = requests.get(f"{FRED_BASE}/series/observations", params=params, timeout=60)
    response.raise_for_status()

    df = pd.DataFrame(response.json()["observations"])
    df["date"] = pd.to_datetime(df["date"])
    df["realtime_start"] = pd.to_datetime(df["realtime_start"])
    df["realtime_end"] = pd.to_datetime(df["realtime_end"], format="%Y-%m-%d", errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df[["date", "realtime_start", "realtime_end", "value"]]
    df.to_csv(cache, index=False)
    return df[df["date"] >= pd.Timestamp(start)].reset_index(drop=True)


def load_fred_as_of(
    series_id: str,
    as_of_date: str | pd.Timestamp,
    start: str = "1990-01-01",
    refresh: bool = False,
) -> pd.Series:
    """Series as it was known on as_of_date; falls back to obs-date filter when vintages exceed FRED's 2000-row API limit."""
    DATA_DIR.mkdir(exist_ok=True)
    as_of_ts = pd.Timestamp(as_of_date)
    no_vintages_marker = DATA_DIR / f"{series_id}.no_vintages"

    # Skip the FRED vintage call for series we already know exceed the API limit (daily yields).
    if no_vintages_marker.exists() and not refresh:
        series = load_fred_series(series_id, start=start, refresh=refresh)
        return series[series.index <= as_of_ts]

    try:
        vintages = load_fred_vintages(series_id, start=start, refresh=refresh)
    except requests.HTTPError as e:
        # FRED rejects vintage queries returning > 2000 vintage dates. Daily series
        # (e.g., DFII10, DGS10) hit this and have no meaningful revisions anyway, so
        # filtering by observation date is approximately correct (<= 1 business day error).
        if e.response is not None and "vintage dates" in e.response.text:
            no_vintages_marker.touch()
            series = load_fred_series(series_id, start=start, refresh=refresh)
            return series[series.index <= as_of_ts]
        raise
    visible = vintages[vintages["realtime_start"] <= as_of_ts]
    latest = visible.sort_values("realtime_start").groupby("date").tail(1)
    return latest.set_index("date")["value"].sort_index().rename(series_id)


def load_etf_prices(
    tickers: list[str] | str,
    start: str = "2003-01-01",
    refresh: bool = False,
) -> pd.DataFrame:
    """Adjusted close prices from yfinance, cached at data/<ticker>_prices.csv (full history, filtered on read)."""
    if isinstance(tickers, str):
        tickers = [tickers]

    DATA_DIR.mkdir(exist_ok=True)
    prices = {}
    for ticker in tickers:
        cache = DATA_DIR / f"{ticker}_prices.csv"
        if cache.exists() and not refresh:
            prices[ticker] = pd.read_csv(cache, index_col=0, parse_dates=True).iloc[:, 0]
            continue

        raw = yf.download(ticker, period="max", auto_adjust=True, progress=False)
        if raw.empty:
            raise RuntimeError(f"No data returned from yfinance for {ticker}")
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        close = raw["Close"].rename(ticker)
        close.to_csv(cache, header=True)
        prices[ticker] = close

    return pd.DataFrame(prices).loc[start:]
