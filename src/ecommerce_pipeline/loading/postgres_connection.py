"""PostgreSQL connection helpers."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from ..config.settings import DATABASE_URL


def get_engine(url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine.

    The URL can be supplied explicitly or read from ``DATABASE_URL``.
    """
    return create_engine(url or DATABASE_URL, pool_pre_ping=True, future=True)


def test_connection(engine: Engine | None = None) -> bool:
    """Return True when a simple ``SELECT 1`` succeeds."""
    from sqlalchemy import text

    engine = engine or get_engine()
    with engine.connect() as connection:
        return connection.execute(text("SELECT 1")).scalar_one() == 1
