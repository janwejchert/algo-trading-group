"""
Builds the three CSV files that Cesar's notebook needs:
  data/etfs_daily.csv     - ETF daily prices via yfinance
  data/naaim_weekly.csv   - NAAIM Exposure Index from naaim.org
  data/aaii_weekly.csv    - AAII Sentiment from Wayback Machine archive (2023-12-28)
                            Extended to today via forward-fill. AAII blocks automated
                            downloads; Cesar should replace with a fresh download from
                            aaii.com/sentimentsurvey/sent_results when possible.
Run once from the repo root with Anaconda Python.
"""
import io
import re
import requests
import pandas as pd
import yfinance as yf
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0"}


# ── 1. ETF daily prices ───────────────────────────────────────────────────────
print("1/3  etfs_daily.csv via yfinance...")
tickers = ["ACWI", "AGG", "GLD", "BSV"]
raw = yf.download(tickers, start="2007-01-01", auto_adjust=True, progress=False)
prices = raw["Close"][tickers].dropna(how="all")
prices.index.name = "Date"
prices.columns.name = None
out = DATA_DIR / "etfs_daily.csv"
prices.to_csv(out)
print(f"   {out.name}: {prices.shape[0]} rows, "
      f"{prices.index.min().date()} to {prices.index.max().date()}")


# ── 2. NAAIM Exposure Index ───────────────────────────────────────────────────
print("2/3  naaim_weekly.csv from naaim.org...")
page = requests.get(
    "https://www.naaim.org/programs/naaim-exposure-index/",
    timeout=20,
    headers=HEADERS,
)
# The download link host and path vary (naaim.org vs www.naaim.org, a year in
# the path, etc.), so match any .xlsx URL on the page and prefer a naaim.org one.
candidates = re.findall(r"https?://[^\s'\"<>]+?\.xlsx", page.text)
naaim_url = next(
    (u for u in candidates if "naaim.org" in u.lower()),
    candidates[0] if candidates else None,
)
if not naaim_url:
    raise RuntimeError(
        "Could not find a NAAIM .xlsx link on the exposure-index page "
        "(layout may have changed or the page is JS-rendered)."
    )
print(f"   URL: {naaim_url}")

r = requests.get(naaim_url, timeout=30, headers=HEADERS)
r.raise_for_status()
naaim_raw = pd.read_excel(io.BytesIO(r.content))

naaim_raw = naaim_raw.dropna(subset=["Date"])
naaim_raw["Date"] = pd.to_datetime(naaim_raw["Date"])
naaim_raw = naaim_raw.sort_values("Date").drop_duplicates("Date")

naaim = pd.DataFrame(
    {
        "naaim_mean": naaim_raw["Mean/Average"].values,
        "naaim_q1":   naaim_raw["Quart 1 (25% at/below)"].values,
        "naaim_q3":   naaim_raw["Quart 3 (25% at/above)"].values,
    },
    index=pd.DatetimeIndex(naaim_raw["Date"].values, name="Date"),
)
naaim = naaim.dropna(how="all")
out = DATA_DIR / "naaim_weekly.csv"
naaim.to_csv(out)
print(f"   {out.name}: {naaim.shape[0]} rows, "
      f"{naaim.index.min().date()} to {naaim.index.max().date()}")


# ── 3. AAII Sentiment Survey ──────────────────────────────────────────────────
print("3/3  aaii_weekly.csv from Wayback Machine (Dec 2023) + forward-fill...")

# AAII blocks automated downloads with Incapsula JS challenge.
# The most recent public archive is Dec 29 2023. We parse it and forward-fill
# 2024-today so the notebook runs. Cesar should replace with a fresh manual
# download from aaii.com/sentimentsurvey/sent_results when convenient.
archive_url = (
    "http://web.archive.org/web/20231229210519/"
    "https://www.aaii.com/files/surveys/sentiment.xls"
)
print(f"   Downloading archive from Wayback Machine...")
r = requests.get(archive_url, timeout=90, headers=HEADERS)
r.raise_for_status()

# The file is a real binary .xls (magic bytes D0 CF 11 E0).
aaii_raw = pd.read_excel(io.BytesIO(r.content), engine="xlrd", header=3)

# Drop metadata/summary rows (the file contains strings like "Count '18").
# Filter to rows where Date is a real Python datetime before converting.
import datetime as _dt
aaii_raw = aaii_raw[
    aaii_raw["Date"].apply(
        lambda x: isinstance(x, (_dt.datetime, pd.Timestamp))
    )
].copy()
aaii_raw["Date"] = pd.to_datetime(aaii_raw["Date"])
aaii_raw = aaii_raw.dropna(subset=["Bullish", "Bearish", "Neutral"])
aaii_raw = aaii_raw.sort_values("Date").drop_duplicates("Date")

aaii_raw = aaii_raw.set_index("Date")
aaii_hist = pd.DataFrame(
    {
        "bullish": pd.to_numeric(aaii_raw["Bullish"], errors="coerce"),
        "bearish": pd.to_numeric(aaii_raw["Bearish"], errors="coerce"),
        "neutral": pd.to_numeric(aaii_raw["Neutral"], errors="coerce"),
    }
)
aaii_hist = aaii_hist.dropna(how="all")

# Values should be fractions [0, 1]; convert from pct if needed
if aaii_hist["bullish"].median() > 1.5:
    aaii_hist = aaii_hist / 100.0

print(f"   Archive: {aaii_hist.shape[0]} rows, "
      f"{aaii_hist.index.min().date()} to {aaii_hist.index.max().date()}")

# Forward-fill to today so features exist for 2024-2026
today = pd.Timestamp.today().normalize()
full_fridays = pd.date_range(
    start=aaii_hist.index.min(), end=today, freq="W-FRI"
)
aaii = aaii_hist.reindex(aaii_hist.index.union(full_fridays)).ffill().reindex(full_fridays)
aaii.index.name = "Date"

out = DATA_DIR / "aaii_weekly.csv"
aaii.to_csv(out)
print(f"   {out.name}: {aaii.shape[0]} rows, "
      f"{aaii.index.min().date()} to {aaii.index.max().date()}")
print(f"   (rows after 2023-12-28 are forward-filled from last known value)")
print(f"   Sample (last 3):\n{aaii.tail(3)}")

print()
print("All three data files ready.")
