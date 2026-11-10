"""Shared helpers for the business and engineering Streamlit dashboards."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL

PRIMARY = "#4A9EFF"
SUCCESS = "#00C853"
WARNING = "#FFB300"
DANGER = "#E53935"

COLOR_SEQUENCE = [
    PRIMARY,
    SUCCESS,
    WARNING,
    DANGER,
    "#7C4DFF",
    "#00BCD4",
    "#FF7043",
    "#9E9E9E",
]

DATA_DIR = Path(__file__).resolve().parent / "data"

GOLD_VIEWS = {
    "vw_sales_daily",
    "vw_delivery_performance",
    "vw_customer_rfm",
    "vw_category_performance",
    "vw_seller_performance",
    "vw_payment_mix",
    "vw_review_summary",
    "vw_payment_reconciliation",
    "vw_data_quality_flags",
}

AUDIT_TABLES = {
    "bronze_load_batches": "bronze.load_batches",
    "bronze_rejected_rows": "bronze.rejected_rows",
    "silver_rejected_rows": "silver.rejected_rows",
}


def _safe_name(name: str) -> str:
    return name.replace(".", "_")


def get_engine() -> Engine | None:
    """Return a SQLAlchemy engine, or None when DB env vars are incomplete."""
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    if not all([host, port, name, user, password]):
        return None

    try:
        url = URL.create(
            "postgresql+psycopg2",
            username=user,
            password=password,
            host=host,
            port=int(port),
            database=name,
        )
        return create_engine(url, pool_pre_ping=True, future=True)
    except (TypeError, ValueError):
        return None


def load_csv_or_db(view_name: str) -> pd.DataFrame:
    """Load a Gold view or audit table from CSV first, then PostgreSQL."""
    csv_path = DATA_DIR / f"{_safe_name(view_name)}.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)

    if view_name not in GOLD_VIEWS and view_name not in AUDIT_TABLES:
        raise ValueError(f"Unknown data source: {view_name!r}")

    engine = get_engine()
    if engine is None:
        raise RuntimeError(
            f"No CSV at {csv_path} and DB env vars are not set. "
            "Export CSVs into dashboards/data/ or set DB_HOST, DB_PORT, "
            "DB_NAME, DB_USER, DB_PASSWORD."
        )

    table = AUDIT_TABLES.get(view_name, f"gold.{view_name}")
    try:
        with engine.connect() as connection:
            return pd.read_sql(f"SELECT * FROM {table}", connection)
    finally:
        engine.dispose()


def apply_theme(fig, height: int = 380, title: str | None = None):
    """Apply the shared dark Plotly theme and colour sequence."""
    fig.update_layout(
        template="plotly_dark",
        colorway=COLOR_SEQUENCE,
        title=title,
        height=height,
        margin=dict(l=24, r=24, t=56 if title else 24, b=24),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#FAFAFA"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.08)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.08)", zeroline=False)
    return fig


def style_plotly(fig, height: int = 380, title: str | None = None):
    """Backward-compatible alias for apply_theme."""
    return apply_theme(fig, height=height, title=title)


def brl(value: float) -> str:
    """Format a number as Brazilian reais without relying on locale."""
    try:
        return f"R$ {value:,.2f}"
    except (TypeError, ValueError):
        return "<TBD>"


def pct(value: float) -> str:
    try:
        return f"{value:.2f}%"
    except (TypeError, ValueError):
        return "<TBD>"


def safe_sum(series: pd.Series) -> float:
    value = pd.to_numeric(series, errors="coerce").fillna(0).sum()
    return float(value)


def metric_or_tbd(value: str, needs_data: list[str], label: str) -> str:
    if value == "<TBD>":
        needs_data.append(label)
    return value
