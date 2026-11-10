"""Relationship and orphan analysis."""

from __future__ import annotations

import pandas as pd


def orphan_count(
    child: pd.DataFrame,
    child_column: str,
    parent: pd.DataFrame,
    parent_column: str,
) -> int:
    """Count distinct child key values that do not exist in the parent."""
    child_values = set(child[child_column].dropna().astype(str))
    parent_values = set(parent[parent_column].dropna().astype(str))
    return len(child_values - parent_values)


def coverage_gaps(
    child: pd.DataFrame,
    child_column: str,
    parent: pd.DataFrame,
    parent_column: str,
) -> dict:
    """Return orphan count, child distinct count, and parent distinct count."""
    return {
        "child_column": child_column,
        "parent_column": parent_column,
        "child_distinct": int(child[child_column].nunique()),
        "parent_distinct": int(parent[parent_column].nunique()),
        "orphans": orphan_count(child, child_column, parent, parent_column),
    }
