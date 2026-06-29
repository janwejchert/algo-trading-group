# CLAUDE.md

Guidance for Claude Code (and humans) working on this project.

## Project

**Dynamic Asset Allocation Competition** for the Algorithmic Trading course at IE University.
Rule-based weekly portfolio across 4 ETFs.

- Live evaluation: **June 1 to June 29, 2026**
- Final presentation: **June 30, 2026**
- Submissions: every Friday from **May 29 to June 26** by email (CSV attachment)

## Team & verticals

The final strategy combines four independent signal models. Each member owns one vertical:

| Member  | Vertical     | Inputs                                          |
| ------- | ------------ | ----------------------------------------------- |
| Jan     | Fundamental  | Rates, inflation, growth proxies                |
| Sacha   | Technical    | MA crossovers, RSI                              |
| Rayane  | Macro regime | VIX level + yield curve slope -> risk-on/off    |
| Cesar   | Sentiment    | Fear/greed, put/call, news NLP                  |

Final portfolio = weighted blend of the four vertical signal portfolios. The blending weights `w_J + w_S + w_R + w_C = 1` are calibrated in the combination step (lives in `src/`, owned jointly).

## Hard constraints (from project rules)

**Universe** (Yahoo Finance tickers; no other assets allowed):

- `ACWI`: iShares MSCI ACWI ETF
- `AGG`: iShares Core U.S. Aggregate Bond ETF
- `GLD`: SPDR Gold Shares
- `BSV`: Invesco Short Term Treasury ETF

**Portfolio rules:**

- Weights sum to 100%
- Each weight is in [0%, 100%]
- Long-only (no shorts)
- At most 25 percentage points total absolute change vs. the previous week's submission
- Model-driven only. **No discretionary overrides anywhere in the code.**

**Weekly submission (CSV) format:**

- File name: `TeamXX_YYYY-MM-DD.csv`
- Header: `week,team_id,acwi,agg,gld,bsv`
- Exactly one data row, percentages without `%`, dot decimal separator
- Example: `2026-06-06,Team03,25,35,20,20`
- Email subject: `Algorithmic Trading Project | Team XX | Portfolio for Week YYYY-MM-DD`
- Send to: `imunarriz@faculty.ie.edu`
- Save a copy of every submitted CSV under `submissions/` so we have a full history.

## Branch workflow

- `main` is the shared, validated branch. **Never push to it directly.**
- Each member works on their own branch:
  - `jan-fundamental`
  - `sacha-technical`
  - `rayane-macro`
  - `cesar-sentiment`
- Open a Pull Request to merge into `main`. At least one teammate reviews before merge.
- Pull or rebase `main` into your branch before opening a PR to minimize conflicts.
- Commit message format: `<vertical>: <imperative summary>`. Example: `fundamental: add CPI z-score signal`.

## Repo layout

```
jan-fundamental/      Jan's vertical: notebooks/, src/, results/, submissions/
sacha-technical/      Sacha's vertical: notebooks/, outputs/, results/, submissions/
rayane-macro/         Rayane's vertical: notebooks/, outputs/, results/, submissions/
cesar-sentiment/      Cesar's vertical: notebooks/, results/, submissions/
shared/               canonical.py (KPI/turnover/submission helpers inlined verbatim into
                      each notebook) and parity_check.py (asserts the four stay in sync)
src/combiner.py       Blends the four vertical views; Tier 1 (equal), Tier 2A (inverse-vol,
                      live), Tier 2B (Black-Litterman) are implemented; Tier 2A is used
run_pipeline.py       End-to-end weekly run: refresh data, execute the four notebooks,
                      blend (Tier 2A), enforce the 25pp cap, write Team03_<date>.csv
submissions/          Final Team03_YYYY-MM-DD.csv files (one per Friday)
presentation/         reveal.js final-presentation deck, figures, speaker notes
data/                 Local raw-data cache (gitignored, regenerable from code)
CLAUDE.md             This file. Shared conventions.
README.md             Project overview for collaborators.
requirements.txt      Python dependencies.
```

Each vertical is self-contained in its own folder and exposes the same
`get_weights(as_of_date)` contract. Reusable shared logic lives in `shared/` and `src/`.
**Don't duplicate logic.** The canonical KPI/turnover/submission code in `shared/canonical.py`
is the single source of truth; `shared/parity_check.py` verifies every notebook matches it.

## Environment setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Everyone installs from the same `requirements.txt` so package versions stay consistent across the team. If you add a dependency, update `requirements.txt` in the same PR.

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

The combiner reads each vertical's `get_weights`, blends with `w_J, w_S, w_R, w_C`, and enforces the 25pp turnover cap against the prior week's submission. **Individual verticals don't need to handle turnover.** That's the combiner's job.

## Python style

- Python 3.11+; use `python3`.
- PEP 8. Four-space indents, `snake_case` for functions and variables.
- Type hints on every public function.
- Imports grouped: stdlib, then third-party, then local. One import per line.
- No hardcoded absolute paths. Use `pathlib.Path` relative to project root.
- Fix random seeds wherever randomness is used.
- Default stack: `numpy`, `pandas`, `yfinance`, `matplotlib`, `scipy`, `scikit-learn`, `pandas-datareader`. Discuss in the group chat before adding others.

## Notebook style

- **File name:** `NN_topic_owner.ipynb`. Examples: `01_eda_acwi_jan.ipynb`, `02_rsi_signal_sacha.ipynb`. `NN` orders them on disk.
- **First cell (Markdown)** must contain: title, author, one-paragraph purpose, last-updated date.
- **Section headers** (Markdown H2), in this order:
  1. Setup (imports, config)
  2. Data
  3. Analysis / signal logic
  4. Results
  5. Notes / next steps
- **Clear all outputs before committing** (`Kernel` then `Restart & Clear Output`). Keeps diffs reviewable.
- Import logic from `src/` rather than redefining it inline. Notebooks are for figures, exploration, and writeups.
- Kernel: `Python 3` (generic, not environment-specific).
- Add to the setup cell for consistent number formatting:

  ```python
  import pandas as pd
  pd.options.display.float_format = '{:.4f}'.format
  ```

## Writing style

- **No em dashes (`—`)** in code, comments, commit messages, docs, or notebook prose. Use a colon, comma, period, parentheses, or rephrase. Regular hyphens (`-`) for compound words and en dashes (`–`) for date ranges are fine.

## Data & reproducibility

- Public sources only (Yahoo Finance, FRED, etc.).
- Cache raw data locally in `data/` (gitignored). Processed data is regenerable from cache plus code. Never commit it.
- A backtest must be **deterministic**: same inputs and same code produce the same weights every time.

## Don'ts

- Don't push to `main` directly.
- Don't commit Jupyter outputs.
- Don't commit `data/`, secrets, `.env`, `__pycache__`, or anything in `.gitignore`.
- Don't introduce discretionary fallbacks. The model produces the weights.
- Don't add dependencies outside the approved stack without team agreement.
- Don't use em dashes in any committed file.
