import pandas as pd
import requests, io
import datetime as _dt

HEADERS = {"User-Agent": "Mozilla/5.0"}
archive_url = (
    "http://web.archive.org/web/20231229210519/"
    "https://www.aaii.com/files/surveys/sentiment.xls"
)
r = requests.get(archive_url, timeout=90, headers=HEADERS)
aaii_raw = pd.read_excel(io.BytesIO(r.content), engine="xlrd", header=3)
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

print("aaii_hist length:", len(aaii_hist))
print("aaii_hist gaps > 30 days:")
gaps = aaii_hist.index.to_series().diff()
print(gaps[gaps > pd.Timedelta(days=30)])
