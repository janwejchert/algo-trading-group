import io
from pathlib import Path

import pandas as pd
import requests

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# Public fredgraph CSV endpoint. No API key required, and it avoids
# pandas_datareader, which is unmaintained and fails to import on pandas 3.x.
series_ids = ["DGS10", "DGS3MO", "BAMLH0A0HYM2", "T10YIE", "DTWEXBGS", "DFII10"]
headers = {"User-Agent": "Mozilla/5.0"}

for sid in series_ids:
    print(f"Fetching {sid}...")
    try:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd=2000-01-01"
        resp = requests.get(url, timeout=30, headers=headers)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        # fredgraph returns two columns: observation date, then the series id.
        df.columns = ["date", sid]
        df["date"] = pd.to_datetime(df["date"])
        # FRED encodes missing observations as ".".
        df[sid] = pd.to_numeric(df[sid], errors="coerce")
        df = df.set_index("date")
        df.to_csv(DATA_DIR / f"{sid}.csv")
        print(f"Saved {sid}.csv with {len(df)} rows.")
    except Exception as e:
        print(f"Failed {sid}: {e}")
