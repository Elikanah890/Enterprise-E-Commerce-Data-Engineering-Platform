"""Clean the reviews table."""

from __future__ import annotations

import pandas as pd

TIMESTAMP_COLUMNS = ["review_creation_date", "review_answer_timestamp"]
TEXT_COLUMNS = ["review_comment_title", "review_comment_message"]


def clean_reviews(df: pd.DataFrame) -> pd.DataFrame:
    """Cast dates, scores, and convert empty text to null."""
    out = df.copy()
    out["review_score"] = pd.to_numeric(out["review_score"], errors="coerce").astype("Int64")
    for column in TIMESTAMP_COLUMNS:
        out[column] = pd.to_datetime(out[column].replace("", None), errors="coerce")
    for column in TEXT_COLUMNS:
        out[column] = out[column].replace("", None)
    return out
