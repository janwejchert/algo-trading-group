import pandas as pd
import numpy as np
import scipy.optimize as sco
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
SUBMISSIONS_DIR = REPO_ROOT / "submissions"
RESULTS_DIRS = {
    "jan": REPO_ROOT / "jan-fundamental" / "results",
    "sacha": REPO_ROOT / "sacha-technical" / "results",
    "rayane": REPO_ROOT / "rayane-macro" / "results",
    "cesar": REPO_ROOT / "cesar-sentiment" / "results",
}

UNIVERSE = ["ACWI", "AGG", "GLD", "BSV"]
TURNOVER_LIMIT = 0.25

def enforce_turnover(w_target: pd.Series, w_prev: pd.Series) -> pd.Series:
    """Enforce the 25pp max turnover limit constraint linearly."""
    delta = w_target - w_prev
    turnover = np.abs(delta).sum()
    if turnover <= TURNOVER_LIMIT:
        return w_target
    scale = TURNOVER_LIMIT / turnover
    return w_prev + delta * scale

def get_last_submission() -> pd.Series:
    """Read the last submission from the submissions/ folder."""
    csvs = list(SUBMISSIONS_DIR.glob("*.csv"))
    if not csvs:
        # Default starting point if no submission exists
        return pd.Series([0.25, 0.25, 0.25, 0.25], index=UNIVERSE)
    
    latest_csv = sorted(csvs)[-1]
    df = pd.read_csv(latest_csv)
    # The header is: week,team_id,acwi,agg,gld,bsv (percentages)
    w_prev = pd.Series({
        "ACWI": df["acwi"].iloc[0] / 100.0,
        "AGG": df["agg"].iloc[0] / 100.0,
        "GLD": df["gld"].iloc[0] / 100.0,
        "BSV": df["bsv"].iloc[0] / 100.0,
    })
    return w_prev[UNIVERSE]

def get_tier1_weights(current_views: pd.DataFrame, w_prev: pd.Series = None) -> pd.Series:
    """
    Tier 1 - Equal weight blend of all models.
    current_views: DataFrame of shape (4, 4) with index=models, columns=assets.
    """
    w_target = current_views.mean(axis=0)
    w_target = w_target / w_target.sum() # Normalize just in case
    
    if w_prev is not None:
        w_target = enforce_turnover(w_target, w_prev)
        
    return w_target

def _load_etf_weekly_returns() -> pd.DataFrame:
    """Load weekly ETF returns from 2008 to 2024."""
    etfs = pd.read_csv(DATA_DIR / "etfs_daily.csv", index_col="Date", parse_dates=True)
    # Resample to weekly fridays
    etfs_w = etfs.resample("W-FRI").last()
    rets = etfs_w.pct_change().dropna()
    return rets

def get_tier2a_weights(current_views: pd.DataFrame, w_prev: pd.Series = None) -> pd.Series:
    """
    Tier 2A - Inverse-volatility blend based on training-period realized volatility.
    Calibration window: 2010-2024 only (no 2025 validation data).
    """
    rets = _load_etf_weekly_returns()
    # Calibrate on training period only to avoid using held-out 2025 data.
    rets_calib = rets.loc["2010":"2024"]

    volatilities = {}
    for vertical, path in RESULTS_DIRS.items():
        hist_file = path / "weekly_weights_history.csv"
        if not hist_file.exists():
            raise FileNotFoundError(f"Missing history for {vertical}: {hist_file}")

        hist = pd.read_csv(hist_file, index_col=0, parse_dates=True)
        hist = hist[UNIVERSE]

        # The return for week t uses the weights assigned at week t-1.
        # Shift weights forward by 1 so the index matches the return it earned.
        weights_shifted = hist.shift(1).loc["2010":"2024"]
        common = rets_calib.index.intersection(weights_shifted.dropna().index)

        if len(common) < 20:
            print(f"Warning: Only {len(common)} weeks of overlap for {vertical} in calibration window")

        port_rets = (weights_shifted.loc[common] * rets_calib.loc[common]).sum(axis=1)
        vol = port_rets.std() * np.sqrt(52)
        volatilities[vertical] = vol
        
    # Inverse vol weighting
    inv_vols = {k: 1.0 / v for k, v in volatilities.items()}
    total_inv_vol = sum(inv_vols.values())
    weights = {k: v / total_inv_vol for k, v in inv_vols.items()}
    
    # Compute combined weights
    w_target = pd.Series(0.0, index=UNIVERSE)
    for vertical in current_views.index:
        w_target += current_views.loc[vertical] * weights[vertical]
        
    w_target = w_target / w_target.sum()
    
    if w_prev is not None:
        w_target = enforce_turnover(w_target, w_prev)
        
    return w_target

def get_tier2b_weights(current_views: pd.DataFrame, w_prev: pd.Series = None) -> pd.Series:
    """
    Tier 2B - Black-Litterman blend.
    """
    rets = _load_etf_weekly_returns()
    
    # Input 1: Covariance Matrix (Sigma) from 2008-2024
    rets_train = rets.loc["2008":"2024"]
    Sigma = rets_train.cov() * 52  # Annualized covariance
    
    # Equilibrium inputs
    w_eq = pd.Series([0.25, 0.25, 0.25, 0.25], index=UNIVERSE)
    risk_aversion = 2.5
    Pi = risk_aversion * Sigma.dot(w_eq)
    
    # Input 2: View Uncertainty Matrix (Omega) from training-period tracking error.
    # Use 2008-2024 only - same window as Sigma - to avoid using held-out 2025 data.
    rets_calib = rets.loc["2008":"2024"]
    eq_rets_calib = (rets_calib * w_eq).sum(axis=1)

    omega_diag = []

    # current_views.index is assumed to be ["jan", "sacha", "rayane", "cesar"]
    for vertical in current_views.index:
        path = RESULTS_DIRS[vertical]
        hist_file = path / "weekly_weights_history.csv"
        if not hist_file.exists():
            raise FileNotFoundError(f"Missing history for {vertical}: {hist_file}")

        hist = pd.read_csv(hist_file, index_col=0, parse_dates=True)
        hist = hist[UNIVERSE]
        weights_shifted = hist.shift(1).loc["2008":"2024"]
        common = rets_calib.index.intersection(weights_shifted.dropna().index)

        port_rets = (weights_shifted.loc[common] * rets_calib.loc[common]).sum(axis=1)
        te_rets = port_rets - eq_rets_calib.loc[common]
        
        tracking_error_var = te_rets.var() * 52
        omega_diag.append(tracking_error_var)
        
    Omega = pd.DataFrame(np.diag(omega_diag), index=current_views.index, columns=current_views.index)
    
    # Input 3: Current Views (P and Q)
    # P is simply the current weight vectors of the 4 models
    P = current_views.copy()
    
    # Q is the implied returns of those portfolios
    # Q_k = w_k^T * Pi_k = w_k^T * (lambda * Sigma * w_k)
    Q = pd.Series(index=current_views.index, dtype=float)
    for vertical in current_views.index:
        w_k = current_views.loc[vertical]
        Q[vertical] = w_k.dot(risk_aversion * Sigma.dot(w_k))
        
    # Black-Litterman Posterior
    tau = 0.05
    tau_Sigma_inv = pd.DataFrame(np.linalg.inv(tau * Sigma), index=UNIVERSE, columns=UNIVERSE)
    Omega_inv = pd.DataFrame(np.linalg.inv(Omega), index=current_views.index, columns=current_views.index)
    
    # M_inv = ( (tau * Sigma)^-1 + P^T * Omega^-1 * P )^-1
    M = tau_Sigma_inv + P.T.dot(Omega_inv).dot(P)
    M_inv = pd.DataFrame(np.linalg.inv(M), index=UNIVERSE, columns=UNIVERSE)
    
    Pi_posterior = M_inv.dot(tau_Sigma_inv.dot(Pi) + P.T.dot(Omega_inv).dot(Q))
    
    # Optimize to get final weights
    def objective(w):
        w = pd.Series(w, index=UNIVERSE)
        port_ret = w.dot(Pi_posterior)
        port_var = w.dot(Sigma).dot(w)
        # Maximize risk-adjusted return
        return -(port_ret - (risk_aversion / 2) * port_var)
        
    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
    bounds = [(0, 1) for _ in range(len(UNIVERSE))]
    
    res = sco.minimize(objective, w_eq.values, method='SLSQP', bounds=bounds, constraints=constraints)
    w_target = pd.Series(res.x, index=UNIVERSE)
    
    if w_prev is not None:
        w_target = enforce_turnover(w_target, w_prev)
        
    return w_target
