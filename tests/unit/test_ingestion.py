"""Unit tests for ingestion."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ecommerce_pipeline.ingestion.csv_reader import read_csv


def test_read_csv_preserves_leading_zero(tmp_path: Path) -> None:
    path = tmp_path / "sample.csv"
    path.write_text(
        "customer_id,customer_zip_code_prefix\n"
        "abc,01037\n"
        "def,14409\n",
        encoding="utf-8",
    )

    df = read_csv(path)

    assert df.loc[0, "customer_zip_code_prefix"] == "01037"
    assert df.loc[1, "customer_zip_code_prefix"] == "14409"
    assert df.loc[0, "customer_id"] == "abc"


def test_read_csv_keeps_empty_strings(tmp_path: Path) -> None:
    path = tmp_path / "sample.csv"
    path.write_text("a,b\n1,\n", encoding="utf-8")

    df = read_csv(path)

    assert df.loc[0, "b"] == ""
    assert not pd.isna(df.loc[0, "b"])


def test_read_csv_strips_bom(tmp_path: Path) -> None:
    path = tmp_path / "sample.csv"
    path.write_text("\ufeffproduct_category_name\nbeleza_saude\n", encoding="utf-8")

    df = read_csv(path)

    assert df.columns.tolist() == ["product_category_name"]
