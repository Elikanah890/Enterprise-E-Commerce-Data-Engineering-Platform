"""Load gold star-schema tables."""

from __future__ import annotations

from sqlalchemy.engine import Engine

from .postgres_connection import get_engine


def load_gold(engine: Engine | None = None) -> None:
    """Build gold dimensions, facts, and analytical views from silver."""
    from ..config.settings import SQL_DIR
    from .create_tables import execute_sql_file

    engine = engine or get_engine()
    for filename in [
        "dimensions.sql",
        "fact_orders.sql",
        "fact_order_items.sql",
        "fact_payments.sql",
        "fact_reviews.sql",
        "analytical_views.sql",
    ]:
        execute_sql_file(SQL_DIR / "gold" / filename, engine)
