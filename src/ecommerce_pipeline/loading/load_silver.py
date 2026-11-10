"""Load cleaned data into the silver schema."""

from __future__ import annotations

from sqlalchemy.engine import Engine

from .postgres_connection import get_engine


def load_silver(engine: Engine | None = None) -> None:
    """Run the silver cleaning SQL.

    The SQL file ``sql/silver/cleaning_transformations.sql`` is the source of
    truth. This function is a thin programmatic entry point.
    """
    from ..config.settings import SQL_DIR
    from .create_tables import execute_sql_file

    engine = engine or get_engine()
    execute_sql_file(SQL_DIR / "silver" / "cleaning_transformations.sql", engine)
