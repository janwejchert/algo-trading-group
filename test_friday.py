import pandas as pd
import requests, io
archive_url = (
    "http://web.archive.org/web/20231229210519/"
    "https://www.aaii.com/files/surveys/sentiment.xls"
)
r = requests.get(archive_url, timeout=90, headers={"User-Agent": "Mozilla/5.0"})
aaii_raw = pd.read_excel(io.BytesIO(r.content), engine="xlrd", header=3)
aaii_raw = aaii_raw.dropna(subset=['Bullish']).copy()
aaii_raw['Date'] = pd.to_datetime(aaii_raw['Date'], errors='coerce')
aaii_raw = aaii_raw.dropna(subset=['Date']).set_index('Date')
print("Last Friday in AAII raw:")
fridays = aaii_raw[aaii_raw.index.weekday == 4]
print(fridays.tail())
