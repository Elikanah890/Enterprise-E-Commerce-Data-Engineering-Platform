#!/usr/bin/env python3
"""Create the local project directories and verify the Python environment."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DIRECTORIES = [
    "data/raw",
    "data/processed/cleaned",
    "data/processed/validated",
    "data/warehouse/bronze",
    "data/warehouse/silver",
    "data/warehouse/gold",
    "data/sample",
    "logs",
]

REQUIRED = ["pandas", "numpy", "sqlalchemy", "dotenv"]


def main() -> int:
    for relative in DIRECTORIES:
        (ROOT / relative).mkdir(parents=True, exist_ok=True)
        print(f"ok  {relative}")

    print(f"\nPython {sys.version.split()[0]}")
    missing = []
    for package in REQUIRED:
        found = importlib.util.find_spec(package) is not None
        print(f"{'ok ' if found else 'MISS'} {package}")
        if not found:
            missing.append(package)

    if missing:
        print("\nInstall missing packages: pip install -r requirements.txt")
        return 1
    print("\nEnvironment ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
