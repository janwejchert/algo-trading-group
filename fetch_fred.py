import pandas as pd
import pandas_datareader.data as web
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

series_ids = ["DGS10", "DGS3MO", "BAMLH0A0HYM2", "T10YIE", "DTWEXBGS", "DFII10"]

for sid in series_ids:
    print(f"Fetching {sid}...")
    try:
        df = web.DataReader(sid, 'fred', "2000-01-01")
        df.index.name = "date"
        df.to_csv(DATA_DIR / f"{sid}.csv")
        print(f"Saved {sid}.csv with {len(df)} rows.")
    except Exception as e:
        print(f"Failed {sid}: {e}")
