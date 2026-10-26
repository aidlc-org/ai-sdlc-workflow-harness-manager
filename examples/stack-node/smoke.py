"""Smoke: copy the skeleton, run init and doctor, check the pack landed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import stack_smoke  # noqa: E402

stack_smoke(
    Path(__file__).resolve().parent,
    [".pipeline/config.json", ".pipeline/hooks/before-shell.py", ".pipeline/loader/load_workflow.py"],
)
