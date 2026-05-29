"""Parity checker: confirm the four vertical notebooks inline the same canonical blocks.

Two checks:

1. Block-text parity: each notebook contains the exact text of every canonical
   block from shared/canonical.py, delimited with the
   `# === BEGIN canonical:<name> ===` / `# === END canonical:<name> ===` markers.

2. Runtime parity: feed a fixed synthetic weekly return series into each notebook's
   inlined compute_kpis and assert the produced dict matches the canonical reference
   within 1e-12. Asserts the same for project_to_turnover_ball and the writer schema.

Run from the repo root:

    python shared/parity_check.py
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from shared.canonical import (  # noqa: E402
    UNIVERSE,
    compute_kpis,
    project_to_turnover_ball,
    write_submission_csv,
)

CANONICAL_PATH = REPO_ROOT / "shared" / "canonical.py"
BLOCK_NAMES = ["constants", "kpis", "turnover", "submission"]

NOTEBOOKS = {
    "jan": REPO_ROOT
    / "jan-fundamental"
    / "notebooks"
    / "00_fundamental_self_contained_jan.ipynb",
    "sacha": REPO_ROOT
    / "sacha-technical"
    / "technical_analysis_dynamic_asset_allocation.ipynb",
    "rayane": REPO_ROOT / "rayane-macro" / "macro_regime_strategy.ipynb",
    "cesar": REPO_ROOT
    / "cesar-sentiment"
    / "notebooks"
    / "cesar_sentiment_simple.ipynb",
}


def _extract_blocks(text: str) -> dict[str, str]:
    """Extract `# === BEGIN canonical:NAME ===` / `# === END canonical:NAME ===` blocks."""
    blocks: dict[str, str] = {}
    pattern = re.compile(
        r"# === BEGIN canonical:(?P<name>[a-z_]+) ===\n(?P<body>.*?)\n# === END canonical:(?P=name) ===",
        re.DOTALL,
    )
    for m in pattern.finditer(text):
        blocks[m.group("name")] = m.group("body").rstrip()
    return blocks


def _notebook_concat_source(path: Path) -> str:
    nb = json.loads(path.read_text())
    chunks: list[str] = []
    for cell in nb["cells"]:
        if cell["cell_type"] != "code":
            continue
        chunks.append("".join(cell.get("source", [])))
    return "\n\n".join(chunks)


def check_block_parity() -> list[str]:
    """Return a list of error strings; empty list means parity holds."""
    errors: list[str] = []
    canonical_blocks = _extract_blocks(CANONICAL_PATH.read_text())
    missing_in_canonical = [n for n in BLOCK_NAMES if n not in canonical_blocks]
    if missing_in_canonical:
        errors.append(
            f"shared/canonical.py is missing blocks: {missing_in_canonical}"
        )
        return errors
    for owner, nb_path in NOTEBOOKS.items():
        if not nb_path.exists():
            errors.append(f"{owner}: notebook not found at {nb_path}")
            continue
        nb_text = _notebook_concat_source(nb_path)
        nb_blocks = _extract_blocks(nb_text)
        for name in BLOCK_NAMES:
            if name not in nb_blocks:
                errors.append(
                    f"{owner}: missing canonical block `{name}` in {nb_path.name}"
                )
                continue
            if nb_blocks[name] != canonical_blocks[name]:
                errors.append(
                    f"{owner}: canonical block `{name}` drifted in {nb_path.name}"
                )
    return errors


def check_runtime_parity() -> list[str]:
    """Confirm the canonical functions produce stable, expected output."""
    errors: list[str] = []
    np.random.seed(42)
    idx = pd.date_range("2024-01-05", periods=100, freq="W-FRI")
    r = pd.Series(np.random.normal(0.001, 0.02, 100), index=idx)
    bench = pd.Series(np.random.normal(0.0005, 0.018, 100), index=idx)
    k = compute_kpis(r, bench)
    expected_keys = {
        "n_periods",
        "total_return",
        "CAGR",
        "ann_return",
        "ann_vol",
        "Sharpe",
        "Sortino",
        "max_drawdown",
        "calmar",
        "hit_rate",
        "best_period",
        "worst_period",
        "active_sharpe_vs_bench",
        "excess_ann_return",
    }
    if set(k.keys()) != expected_keys:
        errors.append(
            f"compute_kpis keys mismatch: {sorted(k.keys())} vs {sorted(expected_keys)}"
        )
    if k["n_periods"] != 100:
        errors.append(f"compute_kpis n_periods: {k['n_periods']} != 100")

    target = pd.Series(
        {"ACWI": 0.50, "AGG": 0.20, "GLD": 0.20, "BSV": 0.10}
    ).reindex(UNIVERSE)
    prev = pd.Series(
        {"ACWI": 0.25, "AGG": 0.25, "GLD": 0.25, "BSV": 0.25}
    ).reindex(UNIVERSE)
    projected = project_to_turnover_ball(target, prev)
    if abs(float(projected.sum()) - 1.0) > 1e-9:
        errors.append(f"project_to_turnover_ball sum: {projected.sum()} != 1")
    turnover = float((projected - prev).abs().sum())
    if abs(turnover - 0.25) > 1e-9:
        errors.append(
            f"project_to_turnover_ball turnover: {turnover} != 0.25 for over-cap target"
        )

    with tempfile.TemporaryDirectory() as tmp:
        path = write_submission_csv(
            target, "2026-05-29", "TeamXX", Path(tmp), vertical_tag="parity",
        )
        df = pd.read_csv(path)
        if list(df.columns) != ["week", "team_id", "acwi", "agg", "gld", "bsv"]:
            errors.append(f"submission columns: {list(df.columns)}")
        if len(df) != 1:
            errors.append(f"submission row count: {len(df)} != 1")
        total = float(df.iloc[0][["acwi", "agg", "gld", "bsv"]].sum())
        if abs(total - 100.0) > 1e-6:
            errors.append(f"submission sum: {total} != 100")
        if path.name != "TeamXX_parity_2026-05-29.csv":
            errors.append(f"submission filename: {path.name}")

    # Exec each notebook's inlined canonical:kpis block on the same synthetic series
    # and assert each produces an identical KPI dict.
    for owner, nb_path in NOTEBOOKS.items():
        if not nb_path.exists():
            continue
        nb_text = _notebook_concat_source(nb_path)
        blocks = _extract_blocks(nb_text)
        if "constants" not in blocks or "kpis" not in blocks:
            continue
        ns: dict = {"np": np, "pd": pd}
        try:
            exec(blocks["constants"], ns)
            exec(blocks["kpis"], ns)
            nb_k = ns["compute_kpis"](r, bench)
        except Exception as e:
            errors.append(f"{owner}: failed to exec inlined kpis block ({e})")
            continue
        for key, ref_val in k.items():
            nb_val = nb_k.get(key)
            if isinstance(ref_val, float) and np.isnan(ref_val):
                if not (isinstance(nb_val, float) and np.isnan(nb_val)):
                    errors.append(f"{owner}: KPI {key} expected NaN, got {nb_val}")
            else:
                if nb_val is None or abs(nb_val - ref_val) > 1e-12:
                    errors.append(f"{owner}: KPI {key} mismatch ({nb_val} vs {ref_val})")

    return errors


def main() -> int:
    block_errors = check_block_parity()
    runtime_errors = check_runtime_parity()
    if not block_errors and not runtime_errors:
        print("parity check passed")
        return 0
    if block_errors:
        print("BLOCK PARITY ERRORS:")
        for e in block_errors:
            print(f"  - {e}")
    if runtime_errors:
        print("RUNTIME PARITY ERRORS:")
        for e in runtime_errors:
            print(f"  - {e}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
