"""Small shared helpers."""

from __future__ import annotations

import re


def safe_divide(numerator: float, denominator: float) -> float | None:
    """Return numerator / denominator, or None when the denominator is zero."""
    if denominator in (0, None):
        return None
    return numerator / denominator


def to_snake_case(value: str) -> str:
    """Convert a label to snake_case."""
    cleaned = re.sub(r"[^0-9a-zA-Z]+", "_", value.strip())
    return re.sub(r"(?<!^)(?=[A-Z])", "_", cleaned).lower().strip("_")
