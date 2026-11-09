"""Paths independent of the shell working directory."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_RUN = "training_run_001"
MODEL_DIR = PROJECT_ROOT / "models" / DEFAULT_MODEL_RUN
TRAINING_RESULTS = PROJECT_ROOT / "experiments" / "training" / DEFAULT_MODEL_RUN
