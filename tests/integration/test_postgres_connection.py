"""PostgreSQL connection integration test.

Runs whenever the configured database is reachable. The project ``.env`` is
loaded by ``settings``.
"""

from __future__ import annotations

from ecommerce_pipeline.config.settings import DATABASE_URL
from ecommerce_pipeline.loading.postgres_connection import test_connection as check_connection


def test_connection() -> None:
    assert DATABASE_URL
    assert check_connection()
