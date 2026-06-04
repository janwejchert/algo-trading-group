import os
import sys
import subprocess
import datetime
import pandas as pd
from pathlib import Path
from src.combiner import get_tier2a_weights, get_last_submission, UNIVERSE, RESULTS_DIRS
from shared.canonical import write_submission_csv

REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR = REPO_ROOT / "data"
SUBMISSIONS_DIR = REPO_ROOT / "submissions"
DATA_DIR.mkdir(exist_ok=True)
SUBMISSIONS_DIR.mkdir(exist_ok=True)

# Public, read-only FRED API key. The team is fine committing it; override it
# via the FRED_API_KEY environment variable or a .env file if you prefer.
DEFAULT_FRED_API_KEY = "2d33fd0e25f5535b2e41cbeae5bc2650"

# Each vertical's notebook, keyed to match RESULTS_DIRS from the combiner.
NOTEBOOKS = {
    "jan": "jan-fundamental/notebooks/00_fundamental_self_contained_jan.ipynb",
    "sacha": "sacha-technical/technical_analysis_dynamic_asset_allocation.ipynb",
    "rayane": "rayane-macro/macro_regime_strategy.ipynb",
    "cesar": "cesar-sentiment/notebooks/cesar_sentiment_simple.ipynb",
}

def step(msg: str):
    print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

def run_cmd(cmd: list, cwd: Path = REPO_ROOT):
    subprocess.run(cmd, cwd=cwd, check=True)

def _load_dotenv() -> None:
    """Load KEY=VALUE pairs from a gitignored .env at the repo root into os.environ.

    Variables already present in the real environment are not overwritten.
    """
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def update_fred_data() -> None:
    """Fetch FRED macro data and cache each series to data/{sid}.csv (date,{sid}).

    Uses the official FRED API with FRED_API_KEY (from the environment or .env,
    falling back to DEFAULT_FRED_API_KEY). Retries each series a few times to
    ride out transient timeouts. Avoids pandas_datareader, which is unmaintained
    and fails to import on pandas 3.x. The cache format matches what the vertical
    notebooks read.
    """
    step("Fetching FRED macro data...")
    import time
    import requests

    _load_dotenv()
    api_key = os.environ.get("FRED_API_KEY") or DEFAULT_FRED_API_KEY
    series_ids = ["DGS10", "DGS3MO", "BAMLH0A0HYM2", "T10YIE", "DTWEXBGS", "DFII10"]
    headers = {"User-Agent": "Mozilla/5.0"}

    for sid in series_ids:
        print(f"  -> Fetching {sid}...")
        for attempt in range(3):
            try:
                resp = requests.get(
                    "https://api.stlouisfed.org/fred/series/observations",
                    params={
                        "series_id": sid,
                        "api_key": api_key,
                        "file_type": "json",
                        "observation_start": "2000-01-01",
                    },
                    timeout=60,
                    headers=headers,
                )
                resp.raise_for_status()
                df = pd.DataFrame(resp.json().get("observations", []))
                df["date"] = pd.to_datetime(df["date"])
                # FRED encodes missing observations as ".".
                df[sid] = pd.to_numeric(df["value"], errors="coerce")
                df = df[["date", sid]].set_index("date")
                df.to_csv(DATA_DIR / f"{sid}.csv")
                break
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    print(f"  -> Error fetching {sid}: {e}")


def make_submission(refreshed: "dict | None" = None) -> Path:
    """Read each vertical's latest view, blend with Tier 2A (inverse-volatility),
    enforce the 25pp turnover cap, and write the weekly submission CSV.

    refreshed maps vertical -> bool (refreshed this run). When None (combine-only
    mode) the views are simply read from the committed histories.
    """
    step("Extracting current portfolio targets...")
    if not (DATA_DIR / "etfs_daily.csv").exists():
        raise FileNotFoundError(
            "data/etfs_daily.csv missing; run the full pipeline once to build it."
        )

    views = {}
    print("\nVertical view dates:")
    for vert, hist_path in RESULTS_DIRS.items():
        hist_file = hist_path / "weekly_weights_history.csv"
        if not hist_file.exists():
            raise FileNotFoundError(f"Missing history for {vert}. Did the notebook fail?")
        df = pd.read_csv(hist_file, index_col=0, parse_dates=True)
        views[vert] = df.iloc[-1][UNIVERSE]
        if refreshed is None:
            tag = "from history"
        else:
            tag = "fresh" if refreshed.get(vert) else "STALE (last committed)"
        print(f"  {vert:8s} {df.index[-1].date()}  [{tag}]")

    current_views = pd.DataFrame(views).T
    print("\nRaw Portfolio Views for the Week:")
    print(current_views.round(4).to_string())

    step("Blending with Tier 2A (inverse-volatility) + 25pp turnover cap...")
    w_prev = get_last_submission()
    w_target = get_tier2a_weights(current_views, w_prev=w_prev)

    turnover_pp = float((w_target - w_prev).abs().sum() * 100)
    print("\nFinal Recommended Weights:")
    for asset in UNIVERSE:
        print(f"  {asset}: {w_target[asset]:.2%}")
    print(f"  sum: {w_target.sum():.2%} | turnover vs last submission: {turnover_pp:.2f}pp (cap 25.00pp)")

    today = datetime.date.today()
    friday = today + datetime.timedelta((4 - today.weekday()) % 7)
    # Canonical writer scales to %, fixes the rounding residual so the row sums
    # to exactly 100, validates bounds, and names the file Team03_<date>.csv.
    out_file = write_submission_csv(
        w_target, week=friday, team_id="Team03", out_dir=SUBMISSIONS_DIR
    )
    step(f"Pipeline complete! Submission saved to {out_file}")
    return out_file


def run_pipeline():
    step("--- STARTING END-TO-END PIPELINE ---")

    # 1. Market and FRED data. update_fred_data() caches FRED; _build_cesar_data.py
    # builds etfs_daily.csv (needed by the combiner) plus the NAAIM/AAII sentiment
    # files. NAAIM moved its data behind a JavaScript members-widget with no
    # downloadable file, so the sentiment build can fail. Tolerate a non-zero exit
    # and continue with whatever was produced (etfs_daily.csv is written first).
    update_fred_data()

    step("Building market and sentiment data...")
    try:
        run_cmd(["python", "_build_cesar_data.py"])
    except subprocess.CalledProcessError:
        print("  -> WARNING: data builder exited non-zero (NAAIM/AAII unavailable); continuing")

    if not (DATA_DIR / "etfs_daily.csv").exists():
        raise FileNotFoundError(
            "data/etfs_daily.csv was not built; cannot run the combiner. "
            "Check the yfinance step in _build_cesar_data.py."
        )

    # 2. Refresh each vertical's view. A vertical that cannot refresh (failed
    # notebook, or Cesar with no sentiment data) falls back to its last committed
    # view, which the combiner reads from weekly_weights_history.csv. This is a
    # transparent degradation, not a discretionary override: every weight still
    # comes from a model output, and the freshness of each is reported below.
    sentiment_ready = (DATA_DIR / "naaim_weekly.csv").exists() and (
        DATA_DIR / "aaii_weekly.csv"
    ).exists()

    refreshed = {}
    for name, path in NOTEBOOKS.items():
        if name == "cesar" and not sentiment_ready:
            print("  -> SKIP cesar: sentiment data unavailable (NAAIM); using last committed view")
            refreshed[name] = False
            continue
        step(f"Executing {name} notebook...")
        try:
            run_cmd(["jupyter", "nbconvert", "--to", "notebook", "--execute", "--inplace", path])
            refreshed[name] = True
        except subprocess.CalledProcessError:
            print(f"  -> WARNING: {name} notebook failed; using its last committed view")
            refreshed[name] = False

    # 3. Blend the views (Tier 2A) and write the submission.
    make_submission(refreshed)


if __name__ == "__main__":
    # --combine-only re-blends the existing committed views and rewrites the
    # submission CSV without re-fetching data or re-running the notebooks.
    if "--combine-only" in sys.argv:
        make_submission()
    else:
        run_pipeline()
