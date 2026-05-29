import pandas as pd
from src.combiner import get_tier1_weights, get_tier2a_weights, get_tier2b_weights, UNIVERSE

# Mock current views
current_views = pd.DataFrame(
    [
        [0.2, 0.3, 0.4, 0.1],
        [0.5, 0.0, 0.2, 0.3],
        [0.1, 0.1, 0.1, 0.7],
        [0.25, 0.25, 0.25, 0.25]
    ],
    index=["jan", "sacha", "rayane", "cesar"],
    columns=UNIVERSE
)

print("Tier 1:")
print(get_tier1_weights(current_views))

print("\nTier 2A:")
print(get_tier2a_weights(current_views))

print("\nTier 2B:")
print(get_tier2b_weights(current_views))
