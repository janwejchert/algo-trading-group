"""Weekly submission file generator.

Usage:
    python -m src.submit 2026-05-29

Calls fundamental.get_weights() for the given Friday, formats the result as the
required CSV (`TeamXX_YYYY-MM-DD.csv` with header `week,team_id,acwi,agg,gld,bsv`),
saves to submissions/, and prints the email subject and recipient.
"""
import argparse
from pathlib import Path

import pandas as pd

from src.config import PROFESSOR_EMAIL, TEAM_ID
from src.fundamental import get_weights

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SUBMISSIONS_DIR = PROJECT_ROOT / "submissions"
MAX_WEEKLY_TURNOVER_PP = 25.0


def _validate_team_id(team_id: str, allow_placeholder: bool = False) -> None:
    if team_id == "TeamXX" and not allow_placeholder:
        raise ValueError(
            "TEAM_ID is still 'TeamXX'. Set src.config.TEAM_ID or pass --team-id with your real team."
        )


def _load_submission_weights_percent(path: Path) -> pd.Series:
    df = pd.read_csv(path)
    required = ["acwi", "agg", "gld", "bsv"]
    if any(col not in df.columns for col in required) or df.empty:
        raise ValueError(f"Invalid submission file format: {path}")
    row = df.iloc[0]
    return pd.Series(
        {"ACWI": row["acwi"], "AGG": row["agg"], "GLD": row["gld"], "BSV": row["bsv"]},
        dtype=float,
    )


def _latest_prior_submission(submission_date: pd.Timestamp, team_id: str, output_dir: Path) -> Path | None:
    pattern = f"{team_id}_*.csv"
    candidates = sorted(output_dir.glob(pattern))
    dated_candidates: list[tuple[pd.Timestamp, Path]] = []
    for candidate in candidates:
        date_part = candidate.stem.replace(f"{team_id}_", "")
        try:
            file_date = pd.Timestamp(date_part)
        except ValueError:
            continue
        if file_date < submission_date:
            dated_candidates.append((file_date, candidate))
    if not dated_candidates:
        return None
    dated_candidates.sort(key=lambda item: item[0])
    return dated_candidates[-1][1]


def _enforce_turnover_cap(
    current_weights_percent: pd.Series,
    submission_date: pd.Timestamp,
    team_id: str,
    output_dir: Path,
) -> None:
    previous = _latest_prior_submission(submission_date, team_id, output_dir)
    if previous is None:
        return
    previous_weights = _load_submission_weights_percent(previous)
    turnover = (current_weights_percent - previous_weights).abs().sum()
    if turnover - MAX_WEEKLY_TURNOVER_PP > 1e-9:
        raise ValueError(
            f"Turnover cap breach: {turnover:.2f}pp > {MAX_WEEKLY_TURNOVER_PP:.2f}pp "
            f"vs previous submission {previous.name}"
        )


def build_submission_row(
    submission_date: pd.Timestamp | str,
    team_id: str = TEAM_ID,
    *,
    output_dir: Path = SUBMISSIONS_DIR,
    enforce_turnover: bool = True,
    allow_placeholder_team_id: bool = False,
) -> dict:
    """Compute weights and return the CSV row as a dict (percentages, sum = 100)."""
    date = pd.Timestamp(submission_date)
    _validate_team_id(team_id, allow_placeholder=allow_placeholder_team_id)
    weights = get_weights(date) * 100  # to percentages
    rounded = weights.round(2)
    # Ensure exact sum=100 after rounding by adjusting the largest weight by the residual.
    residual = round(100.0 - rounded.sum(), 2)
    largest = rounded.idxmax()
    rounded.loc[largest] = round(rounded.loc[largest] + residual, 2)

    if not (rounded >= 0).all() or not (rounded <= 100).all():
        raise ValueError(f"Weights out of [0, 100] after rounding: {rounded.to_dict()}")
    if abs(rounded.sum() - 100.0) > 1e-6:
        raise ValueError(f"Weights do not sum to 100 after rounding: {rounded.sum()}")
    if enforce_turnover:
        _enforce_turnover_cap(rounded, date, team_id, output_dir)

    return {
        "week": date.strftime("%Y-%m-%d"),
        "team_id": team_id,
        "acwi": rounded["ACWI"],
        "agg":  rounded["AGG"],
        "gld":  rounded["GLD"],
        "bsv":  rounded["BSV"],
    }


def write_submission(
    submission_date: pd.Timestamp | str,
    team_id: str = TEAM_ID,
    output_dir: Path = SUBMISSIONS_DIR,
    *,
    enforce_turnover: bool = True,
    allow_placeholder_team_id: bool = False,
    vertical_tag: str | None = None,
) -> Path:
    """Write the submission CSV and return the file path.

    When `vertical_tag` is provided, the filename becomes
    `{team_id}_{vertical_tag}_{date}.csv` (per-vertical draft form). The default
    (`None`) produces `{team_id}_{date}.csv` for the final team submission.
    """
    output_dir.mkdir(exist_ok=True)
    date = pd.Timestamp(submission_date)
    row = build_submission_row(
        date,
        team_id=team_id,
        output_dir=output_dir,
        enforce_turnover=enforce_turnover,
        allow_placeholder_team_id=allow_placeholder_team_id,
    )
    df = pd.DataFrame([row], columns=["week", "team_id", "acwi", "agg", "gld", "bsv"])
    if vertical_tag:
        filename = f"{team_id}_{vertical_tag}_{date.strftime('%Y-%m-%d')}.csv"
    else:
        filename = f"{team_id}_{date.strftime('%Y-%m-%d')}.csv"
    output_path = output_dir / filename
    df.to_csv(output_path, index=False, float_format="%.2f")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate weekly submission CSV.")
    parser.add_argument("date", help="Submission Friday in YYYY-MM-DD format.")
    parser.add_argument("--team-id", default=TEAM_ID, help=f"Team identifier (default: {TEAM_ID}).")
    parser.add_argument(
        "--skip-turnover-check",
        action="store_true",
        help="Skip 25pp turnover cap check against the latest prior submission file.",
    )
    parser.add_argument(
        "--allow-placeholder-team-id",
        action="store_true",
        help="Allow TEAM_ID='TeamXX' for local dry-runs.",
    )
    args = parser.parse_args()

    path = write_submission(
        args.date,
        team_id=args.team_id,
        enforce_turnover=not args.skip_turnover_check,
        allow_placeholder_team_id=args.allow_placeholder_team_id,
    )
    contents = path.read_text()
    date_str = pd.Timestamp(args.date).strftime("%Y-%m-%d")
    team_number = args.team_id.replace("Team", "")
    subject = f"Algorithmic Trading Project | Team {team_number} | Portfolio for Week {date_str}"

    print(f"Wrote: {path}")
    print()
    print("CSV contents:")
    print(contents)
    print(f"Email subject: {subject}")
    print(f"Email to:      {PROFESSOR_EMAIL}")


if __name__ == "__main__":
    main()
