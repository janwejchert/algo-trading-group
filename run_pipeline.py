import os
import subprocess
import datetime
import pandas as pd
from pathlib import Path
from src.combiner import get_tier2b_weights, get_last_submission, UNIVERSE, RESULTS_DIRS

REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR = REPO_ROOT / "data"
SUBMISSIONS_DIR = REPO_ROOT / "submissions"
DATA_DIR.mkdir(exist_ok=True)
SUBMISSIONS_DIR.mkdir(exist_ok=True)

def step(msg: str):
    print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

def run_cmd(cmd: list, cwd: Path = REPO_ROOT):
    subprocess.run(cmd, cwd=cwd, check=True)

def update_fred_data() -> None:
    """Fetch FRED macro data via the public fredgraph CSV endpoint.

    Uses requests directly instead of pandas_datareader, which is unmaintained
    and fails to import on pandas 3.x (its deprecate_kwarg call broke). No API
    key is required for this endpoint. Each series is written to data/{sid}.csv
    with columns date,{sid}, matching what the vertical notebooks read from cache.
    """
    step("Fetching FRED macro data...")
    import io
    import requests

    series_ids = ["DGS10", "DGS3MO", "BAMLH0A0HYM2", "T10YIE", "DTWEXBGS", "DFII10"]
    headers = {"User-Agent": "Mozilla/5.0"}
    for sid in series_ids:
        print(f"  -> Fetching {sid}...")
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
        except Exception as e:
            print(f"  -> Error fetching {sid}: {e}")

def run_pipeline():
    step("--- STARTING END-TO-END PIPELINE ---")
    
    # 1. Update Market & Sentiment Data
    update_fred_data()
    
    step("Fetching AAII/NAAIM Sentiment Data...")
    run_cmd(["python", "_build_cesar_data.py"])

    # 2. Execute all vertical models to generate their latest views
    notebooks = {
        "Fundamental (Jan)": "jan-fundamental/notebooks/00_fundamental_self_contained_jan.ipynb",
        "Technical (Sacha)": "sacha-technical/technical_analysis_dynamic_asset_allocation.ipynb",
        "Macro (Rayane)": "rayane-macro/macro_regime_strategy.ipynb",
        "Sentiment (Cesar)": "cesar-sentiment/notebooks/cesar_sentiment_simple.ipynb"
    }

    for name, path in notebooks.items():
        step(f"Executing {name}...")
        run_cmd([
            "jupyter", "nbconvert", 
            "--to", "notebook", 
            "--execute", 
            "--inplace", 
            path
        ])

    # 3. Combine Views using Black-Litterman
    step("Extracting current portfolio targets...")
    views = {}
    for vert, path in RESULTS_DIRS.items():
        hist_file = path / "weekly_weights_history.csv"
        if not hist_file.exists():
            raise FileNotFoundError(f"Missing history for {vert}. Did the notebook fail?")
        
        df = pd.read_csv(hist_file, index_col=0, parse_dates=True)
        views[vert] = df.iloc[-1][UNIVERSE]
    
    current_views = pd.DataFrame(views).T
    print("\nRaw Portfolio Views for the Week:")
    print(current_views.round(4).to_string())

    step("Applying Black-Litterman Optimisation (Tier 2B)...")
    w_prev = get_last_submission()
    w_target = get_tier2b_weights(current_views, w_prev=w_prev)

    print("\nFinal Recommended Weights:")
    for asset in UNIVERSE:
        print(f"  {asset}: {w_target[asset]:.2%}")

    # 4. Generate the final submission CSV
    today = datetime.date.today()
    friday = today + datetime.timedelta((4 - today.weekday()) % 7)
    date_str = friday.strftime("%Y-%m-%d")
    out_file = SUBMISSIONS_DIR / f"Team03_{date_str}.csv"
    
    # Format: week,team_id,acwi,agg,gld,bsv
    row = {
        "week": date_str,
        "team_id": "Team03",
        "acwi": round(w_target["ACWI"] * 100, 2),
        "agg": round(w_target["AGG"] * 100, 2),
        "gld": round(w_target["GLD"] * 100, 2),
        "bsv": round(w_target["BSV"] * 100, 2)
    }
    
    df_out = pd.DataFrame([row])
    df_out.to_csv(out_file, index=False)
    
    step(f"Pipeline complete! Submission saved to {out_file}")

if __name__ == "__main__":
    run_pipeline()
