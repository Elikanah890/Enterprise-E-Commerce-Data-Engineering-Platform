"""Execute SQL DDL/DML files as a single database command."""

from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy.engine import Engine

from .postgres_connection import get_engine

_TRANSACTION_CONTROL = re.compile(
    r"(?im)^\s*(BEGIN|COMMIT|START\s+TRANSACTION|END)\s*;\s*$"
)


def execute_sql_file(path: str | Path, engine: Engine | None = None) -> None:
    """Execute a SQL file atomically.

    psycopg2 accepts multiple statements in one ``execute`` call, so the file
    is sent to PostgreSQL as-is. Explicit ``BEGIN``/``COMMIT`` lines are
    stripped because SQLAlchemy's ``engine.begin()`` already owns the
    transaction. This preserves semicolons inside string literals and comments.
    """
    engine = engine or get_engine()
    sql = Path(path).read_text(encoding="utf-8")
    sql = _TRANSACTION_CONTROL.sub("", sql)
    with engine.begin() as connection:
        connection.exec_driver_sql(sql)
