# Algorithmic Trading — Dynamic Asset Allocation

Group project for IE University: rule-based weekly portfolio allocation across `ACWI`, `AGG`, `GLD`, `BSV`.

- **Live evaluation:** June 1 – June 29, 2026
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
src/         Python modules (data, signals, combiner, backtest)
notebooks/   Exploration, EDA, backtests
CLAUDE.md    Shared rules and conventions — read first
```

## Workflow

- `main` is the shared, validated branch. Don't push directly — merge via PR.
- Each member works on their own branch: `jan-fundamental`, `sacha-technical`, `rayane-macro`, `cesar-sentiment`.
- Read **CLAUDE.md** before writing code — it covers the signal interface, notebook style, and the project's hard constraints.
