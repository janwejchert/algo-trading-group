import pandas as pd
from src.combiner import get_tier1_weights, get_tier2a_weights, get_tier2b_weights, UNIVERSE, RESULTS_DIRS

# Fetch the current views from the last row of each vertical's history
views = {}
for vert, path in RESULTS_DIRS.items():
    df = pd.read_csv(path / "weekly_weights_history.csv", index_col=0, parse_dates=True)
    # The last row represents the most recent target weight output
    views[vert] = df.iloc[-1][UNIVERSE]
    
current_views = pd.DataFrame(views).T

print("Current Extracted Strategy Target Weights (P matrix):")
print(current_views.to_string())

print("\n--- Tier 1 (Equal Weight) ---")
t1 = get_tier1_weights(current_views)
print(t1.round(4).to_dict())

print("\n--- Tier 2A (Inverse-Volatility) ---")
t2a = get_tier2a_weights(current_views)
print(t2a.round(4).to_dict())

print("\n--- Tier 2B (Black-Litterman) ---")
t2b = get_tier2b_weights(current_views)
print(t2b.round(4).to_dict())
