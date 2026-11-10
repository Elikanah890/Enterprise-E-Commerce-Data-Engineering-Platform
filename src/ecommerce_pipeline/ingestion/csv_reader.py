"""CSV reader that preserves identifiers and handles the UTF-8 BOM."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..config.settings import RAW_DIR


def read_csv(path: str | Path, **kwargs) -> pd.DataFrame:
    """Read a CSV as all-string data.

    Parameters
    ----------
    path:
        CSV file path.
    **kwargs:
        Extra keyword arguments forwarded to :func:`pandas.read_csv`.

    Notes
    -----
    - ``dtype=str`` preserves leading zeros in zip codes.
    - ``keep_default_na=False`` keeps empty strings distinguishable from ``NA``.
    - ``encoding="utf-8-sig"`` strips the BOM present in the translation file.
    """
    options = {
        "dtype": str,
        "keep_default_na": False,
        "na_filter": False,
        "encoding": "utf-8-sig",
        "low_memory": False,
    }
    options.update(kwargs)
    return pd.read_csv(path, **options)


def read_raw(name: str) -> pd.DataFrame:
    """Read a raw file by logical name (see ``settings.RAW_FILES``)."""
    from ..config.settings import RAW_FILES

    if name not in RAW_FILES:
        raise KeyError(f"Unknown raw file: {name!r}. Known: {sorted(RAW_FILES)}")
    return read_csv(RAW_DIR / RAW_FILES[name])
