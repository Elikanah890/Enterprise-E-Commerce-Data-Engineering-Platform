"""Clean the products table."""

from __future__ import annotations

import pandas as pd


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns, fill unknown categories, and cast measures.

    The source file misspells ``length`` as ``lenght``. The two categories
    missing from the translation file are handled by the SQL cleaning step.
    """
    out = df.rename(
        columns={
            "product_name_lenght": "product_name_length",
            "product_description_lenght": "product_description_length",
        }
    ).copy()

    out["product_category_name"] = (
        out["product_category_name"].astype(str).str.strip().replace("", "unknown")
    )

    numeric_columns = [
        "product_name_length",
        "product_description_length",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ]
    for column in numeric_columns:
        out[column] = pd.to_numeric(out[column].replace("", None), errors="coerce")
    return out
