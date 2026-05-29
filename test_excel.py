import pandas as pd
import requests, io

archive_url = (
    "http://web.archive.org/web/20231229210519/"
    "https://www.aaii.com/files/surveys/sentiment.xls"
)
r = requests.get(archive_url, timeout=90, headers={"User-Agent": "Mozilla/5.0"})
aaii_raw = pd.read_excel(io.BytesIO(r.content), engine="xlrd", header=3)

print(aaii_raw[['Date', 'Bullish', 'Bearish', 'Neutral']].head(20))
print("...")
print(aaii_raw[['Date', 'Bullish', 'Bearish', 'Neutral']].iloc[1000:1020])
