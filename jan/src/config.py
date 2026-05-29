"""Shared project constants: train/val/test split and team identity."""
import pandas as pd

TRAIN_END = pd.Timestamp("2024-12-31")
VAL_END = pd.Timestamp("2025-12-31")
# Test set: 2026-01-01 onwards. Must not be touched until live evaluation.

# Team identifier used in submission filenames and CSV rows.
# Update this once the team's official number is assigned by the professor.
TEAM_ID = "TeamXX"
PROFESSOR_EMAIL = "imunarriz@faculty.ie.edu"
