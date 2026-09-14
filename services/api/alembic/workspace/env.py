"""Reuse the API Alembic environment for the dedicated workspace stream."""

from pathlib import Path
from runpy import run_path

run_path(str(Path(__file__).parents[1] / "env.py"), run_name="__main__")
