"""Shared project constants: train/val/test split and team identity."""
import pandas as pd

TRAIN_END = pd.Timestamp("2024-12-31")
VAL_END = pd.Timestamp("2025-12-31")
# Test set: 2026-01-01 onwards. Must not be touched until live evaluation.

# Team identifier used in submission filenames and CSV rows.
TEAM_ID = "Team03"
PROFESSOR_EMAIL = "imunarriz@faculty.ie.edu"
