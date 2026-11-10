"""Foreign-key checks."""

from __future__ import annotations

import pandas as pd


def orphan_count(
    child: pd.DataFrame,
    child_column: str,
    parent: pd.DataFrame,
    parent_column: str,
) -> int:
    """Count distinct child values missing from the parent key."""
    child_values = set(child[child_column].dropna().astype(str))
    parent_values = set(parent[parent_column].dropna().astype(str))
    return len(child_values - parent_values)


def assert_no_orphans(
    child: pd.DataFrame,
    child_column: str,
    parent: pd.DataFrame,
    parent_column: str,
) -> None:
    """Raise ValueError when orphan records are found."""
    count = orphan_count(child, child_column, parent, parent_column)
    if count:
        raise ValueError(
            f"{count} orphan values in {child_column!r} -> {parent_column!r}"
        )
