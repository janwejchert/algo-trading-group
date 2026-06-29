# Algorithmic Trading: Dynamic Asset Allocation

Group project for IE University. Rule-based weekly portfolio allocation across `ACWI`, `AGG`, `GLD`, `BSV`.

- **Live evaluation:** June 1 to June 29, 2026
- **Final presentation:** June 30, 2026

## Team & verticals

| Member  | Vertical     |
| ------- | ------------ |
| Jan     | Fundamental  |
| Sacha   | Technical    |
| Rayane  | Macro regime |
| Cesar   | Sentiment    |

Each vertical produces an independent signal portfolio. The four signal portfolios are then blended into the final submitted weights.

## Repo layout

```
jan-fundamental/      Jan's vertical: notebooks/, src/, results/, submissions/
sacha-technical/      Sacha's vertical: notebooks/, outputs/, results/, submissions/
rayane-macro/         Rayane's vertical: notebooks/, outputs/, results/, submissions/
cesar-sentiment/      Cesar's vertical: notebooks/, results/, submissions/
shared/               canonical.py (KPI/turnover/submission code inlined into each
                      notebook) and parity_check.py (verifies the four notebooks match)
src/combiner.py       Blends the four vertical views (Tier 2A inverse-volatility, live)
run_pipeline.py       End-to-end weekly run: refresh data, run notebooks, blend, write CSV
submissions/          Final Team03_YYYY-MM-DD.csv files (one per Friday)
presentation/         reveal.js final-presentation deck, figures, speaker notes
data/                 Local raw-data cache (gitignored, regenerable from code)
CLAUDE.md             Shared rules and conventions (read first)
requirements.txt      Python dependencies
```

Each vertical exposes the same `get_weights(as_of_date)` contract. The combiner reads
each vertical's latest view from its `results/weekly_weights_history.csv`, blends them,
and enforces the 25pp turnover cap.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Workflow

- `main` is the shared, validated branch. Don't push directly. Merge via PR.
- Each member works on their own branch: `jan-fundamental`, `sacha-technical`, `rayane-macro`, `cesar-sentiment`.
- Read **CLAUDE.md** before writing code. It covers the signal interface, notebook style, the project's hard constraints, and the writing-style rules.
