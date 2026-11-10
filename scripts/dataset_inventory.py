#!/usr/bin/env python3
"""Read-only dataset inventory for the raw Olist CSVs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ecommerce_pipeline.config.settings import PROCESSED_DIR, RAW_DIR  # noqa: E402
from ecommerce_pipeline.profiling.dataset_inventory import build_inventory  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROCESSED_DIR / "validated" / "dataset_inventory.csv",
        help="CSV output path",
    )
    args = parser.parse_args()

    inventory = build_inventory(RAW_DIR)
    print(inventory.to_string(index=False))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    inventory.to_csv(args.output, index=False)
    print(f"\nSaved inventory to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
