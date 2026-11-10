"""Unit tests for validation helpers."""

from __future__ import annotations

import pandas as pd

from ecommerce_pipeline.validation.duplicate_checks import duplicate_row_count
from ecommerce_pipeline.validation.foreign_key_checks import orphan_count
from ecommerce_pipeline.validation.null_checks import null_summary
from ecommerce_pipeline.validation.primary_key_checks import duplicate_key_count


def test_duplicate_helpers() -> None:
    df = pd.DataFrame({"id": ["a", "a", "b"], "value": [1, 1, 2]})

    assert duplicate_row_count(df) == 1
    assert duplicate_key_count(df, ["id"]) == 1


def test_null_summary_counts_empty_strings() -> None:
    df = pd.DataFrame({"a": ["x", ""], "b": ["y", "z"]})

    summary = null_summary(df).set_index("column")

    assert summary.loc["a", "nulls"] == 1
    assert summary.loc["b", "nulls"] == 0


def test_orphan_count() -> None:
    child = pd.DataFrame({"parent_id": ["a", "b", "z"]})
    parent = pd.DataFrame({"id": ["a", "b"]})

    assert orphan_count(child, "parent_id", parent, "id") == 1
