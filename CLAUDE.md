# CLAUDE.md

Guidance for Claude Code (and humans) working on this project.

## Project

**Dynamic Asset Allocation Competition** — Algorithmic Trading, IE University.
Rule-based weekly portfolio across 4 ETFs.

- Live evaluation: **June 1 – June 29, 2026**
- Final presentation: **June 30, 2026**
- Submissions: every Friday **May 29 – June 26** by email (CSV attachment)

## Team & verticals

The final strategy combines four independent signal models. Each member owns one vertical:

| Member  | Vertical     | Inputs                                          |
| ------- | ------------ | ----------------------------------------------- |
| Jan     | Fundamental  | Rates, inflation, growth proxies                |
| Sacha   | Technical    | MA crossovers, RSI                              |
| Rayane  | Macro regime | VIX level + yield curve slope → risk-on/off    |
| Cesar   | Sentiment    | Fear/greed, put/call, news NLP                  |

Final portfolio = weighted blend of the four vertical signal portfolios. The blending weights `w_J + w_S + w_R + w_C = 1` are calibrated in the combination step (lives in `src/`, owned jointly).

## Hard constraints (from project rules)

**Universe** (Yahoo Finance tickers — no other assets allowed):

- `ACWI` — iShares MSCI ACWI ETF
- `AGG` — iShares Core U.S. Aggregate Bond ETF
- `GLD` — SPDR Gold Shares
- `BSV` — Invesco Short Term Treasury ETF

**Portfolio rules:**

- Weights sum to 100%
- Each weight ∈ [0%, 100%]
- Long-only (no shorts)
- ≤ 25 percentage points total absolute change vs. the previous week's submission
- Model-driven only — **no discretionary overrides anywhere in the code**

**Weekly submission (CSV) format:**

- File name: `TeamXX_YYYY-MM-DD.csv`
- Header: `week,team_id,acwi,agg,gld,bsv`
- Exactly one data row, percentages without `%`, dot decimal separator
- Example: `2026-06-06,Team03,25,35,20,20`
- Email subject: `Algorithmic Trading Project | Team XX | Portfolio for Week YYYY-MM-DD`
- Send to: `imunarriz@faculty.ie.edu`

## Branch workflow

- `main` is the shared, validated branch — **never push to it directly**.
- Each member works on their own branch:
  - `jan-fundamental`
  - `sacha-technical`
  - `rayane-macro`
  - `cesar-sentiment`
- Open a Pull Request to merge into `main`. At least one teammate reviews before merge.
- Pull/rebase `main` into your branch before opening a PR to minimize conflicts.
- Commit messages: `<vertical>: <imperative summary>` — e.g. `fundamental: add CPI z-score signal`.

## Repo layout

```
src/         Python modules (data loaders, signal logic per vertical, combiner, backtest)
notebooks/   Exploration, EDA, backtest reports
CLAUDE.md    This file — shared conventions
README.md    Project overview for collaborators
```

`src/` holds reusable code; `notebooks/` holds analysis. **Don't duplicate logic** — notebooks import from `src/`.

## Signal interface (the contract between verticals)

Every vertical exposes the same function, returning target weights for a given as-of date:

```python
import pandas as pd

def get_weights(as_of_date: pd.Timestamp) -> pd.Series:
    """
    Returns a pd.Series indexed exactly ['ACWI', 'AGG', 'GLD', 'BSV']
    with values in [0, 1] summing to 1.
    """
```

The combiner reads each vertical's `get_weights`, blends with `w_J, w_S, w_R, w_C`, and enforces the 25pp turnover cap against the prior week's submission. **Individual verticals don't need to handle turnover** — that's the combiner's job.

## Python style

- Python 3.11+; use `python3`.
- PEP 8. Four-space indents, `snake_case` for functions and variables.
- Type hints on every public function.
- Imports grouped: stdlib → third-party → local. One import per line.
- No hardcoded absolute paths — use `pathlib.Path` relative to project root.
- Fix random seeds wherever randomness is used.
- Default stack: `numpy`, `pandas`, `yfinance`, `matplotlib`, `scipy`, `scikit-learn`, `pandas_datareader`. Discuss in the group chat before adding others.

## Notebook style

- **File name:** `NN_topic_owner.ipynb` — e.g. `01_eda_acwi_jan.ipynb`, `02_rsi_signal_sacha.ipynb`. `NN` orders them on disk.
- **First cell (Markdown)** must contain: title, author, one-paragraph purpose, last-updated date.
- **Section headers** (Markdown H2), in this order:
  1. Setup (imports, config)
  2. Data
  3. Analysis / signal logic
  4. Results
  5. Notes / next steps
- **Clear all outputs before committing** — `Kernel → Restart & Clear Output`. Keeps diffs reviewable.
- Import logic from `src/` rather than redefining it inline. Notebooks are for figures, exploration, and writeups.
- Kernel: `Python 3` (generic, not environment-specific).
- Add to the setup cell for consistent number formatting:

  ```python
  import pandas as pd
  pd.options.display.float_format = '{:.4f}'.format
  ```

## Data & reproducibility

- Public sources only (Yahoo Finance, FRED, etc.).
- Cache raw data locally in `data/` (gitignored). Processed data is regenerable from cache + code — never commit it.
- A backtest must be **deterministic**: same inputs + same code → same weights.

## Don'ts

- Don't push to `main` directly.
- Don't commit Jupyter outputs.
- Don't commit `data/`, secrets, `.env`, `__pycache__`, or anything in `.gitignore`.
- Don't introduce discretionary fallbacks — the model produces the weights.
- Don't add dependencies outside the approved stack without team agreement.
