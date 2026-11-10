"""Load raw data into the bronze schema with idempotent, auditable batches.

Design
------
- Each source file is identified by its SHA-256 hash.
- ``bronze.load_batches`` stores one row per file hash.
- A successful batch is never reloaded; repeated runs are no-ops.
- A failed batch is retried after clearing any partial rows.
- Rows are inserted in bounded batches with ``_load_id``,
  ``_source_file``, and ``_source_row_number``.
- CSV rows with the wrong field count or NUL bytes are written to
  ``bronze.rejected_rows`` instead of being silently dropped.
"""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Iterable

from psycopg2.extras import execute_values
from sqlalchemy.engine import Engine

from ..config.logging_config import get_logger
from ..config.settings import RAW_DIR, RAW_FILES
from .postgres_connection import get_engine

log = get_logger(__name__)

AUDIT_COLUMNS = ("_load_id", "_source_file", "_source_row_number", "_loaded_at")
BATCH_SIZE = 10_000
REJECT_BATCH_SIZE = 1_000


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_columns(cursor, entity: str) -> list[str]:
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'bronze'
          AND table_name = %s
          AND column_name <> ALL(%s)
        ORDER BY ordinal_position
        """,
        (entity, list(AUDIT_COLUMNS)),
    )
    return [row[0] for row in cursor.fetchall()]


def _acquire_batch(
    cursor,
    entity: str,
    filename: str,
    file_hash: str,
) -> tuple[int, str, int]:
    """Return (load_id, status, row_count), creating or retrying a batch."""
    cursor.execute(
        """
        SELECT load_id, status, row_count
        FROM bronze.load_batches
        WHERE file_sha256 = %s
        FOR UPDATE
        """,
        (file_hash,),
    )
    row = cursor.fetchone()
    if row:
        load_id, status, row_count = row
        if status == "success":
            return load_id, status, row_count

        # Failed or interrupted: retry in place after clearing partial rows.
        cursor.execute(
            """
            UPDATE bronze.load_batches
            SET status = 'started',
                started_at = now(),
                finished_at = NULL,
                error_message = NULL
            WHERE load_id = %s
            """,
            (load_id,),
        )
        cursor.execute(f"DELETE FROM bronze.{entity} WHERE _load_id = %s", (load_id,))
        return load_id, "started", 0

    cursor.execute(
        """
        INSERT INTO bronze.load_batches (source_file, file_sha256, status)
        VALUES (%s, %s, 'started')
        RETURNING load_id
        """,
        (filename, file_hash),
    )
    return cursor.fetchone()[0], "started", 0


def _insert_rejects(cursor, load_id: int, filename: str, rejects: list[tuple]) -> None:
    if not rejects:
        return
    execute_values(
        cursor,
        """
        INSERT INTO bronze.rejected_rows
            (load_id, source_file, source_row_number, raw_line, reason)
        VALUES %s
        """,
        [(load_id, filename, row_no, raw[:4000], reason) for row_no, raw, reason in rejects],
        page_size=REJECT_BATCH_SIZE,
    )


def _load_file(engine: Engine, entity: str, filename: str) -> int:
    path = RAW_DIR / filename
    file_hash = _sha256(path)

    connection = engine.raw_connection()
    try:
        cursor = connection.cursor()
        load_id, status, previous_count = _acquire_batch(
            cursor, entity, filename, file_hash
        )
        connection.commit()

        if status == "success":
            log.info(
                "skip %-20s (%s) already loaded: %d rows",
                entity,
                file_hash[:12],
                previous_count,
            )
            return previous_count

        db_columns = _source_columns(cursor, entity)
        if not db_columns:
            raise RuntimeError(f"bronze.{entity} has no source columns")

        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            try:
                header = next(reader)
            except StopIteration as exc:
                raise ValueError(f"{filename} is empty") from exc

            missing = [column for column in db_columns if column not in header]
            unexpected = [column for column in header if column not in db_columns]
            if missing or unexpected:
                raise ValueError(
                    f"{filename} header mismatch: missing={missing}, unexpected={unexpected}"
                )
            positions = [header.index(column) for column in db_columns]

            insert_sql = (
                f"INSERT INTO bronze.{entity} "
                f"({', '.join(db_columns)}, _load_id, _source_file, _source_row_number) "
                f"VALUES %s"
            )

            batch: list[tuple] = []
            rejects: list[tuple] = []
            valid_rows = 0
            rejected_rows = 0
            source_rows = 0

            for row_number, row in enumerate(reader, start=1):
                source_rows += 1
                if len(row) != len(header):
                    rejects.append(
                        (row_number, ",".join(row), f"expected {len(header)} fields, got {len(row)}")
                    )
                    rejected_rows += 1
                elif any("\x00" in value for value in row):
                    rejects.append((row_number, ",".join(row), "NUL byte in field"))
                    rejected_rows += 1
                else:
                    values = [row[position] for position in positions]
                    batch.append((*values, load_id, filename, row_number))
                    valid_rows += 1

                if len(batch) >= BATCH_SIZE:
                    execute_values(cursor, insert_sql, batch, page_size=BATCH_SIZE)
                    batch.clear()
                if len(rejects) >= REJECT_BATCH_SIZE:
                    _insert_rejects(cursor, load_id, filename, rejects)
                    rejects.clear()

            if batch:
                execute_values(cursor, insert_sql, batch, page_size=BATCH_SIZE)
            _insert_rejects(cursor, load_id, filename, rejects)

            if valid_rows == 0 and source_rows > 0:
                raise ValueError(f"{filename}: no valid rows (all {source_rows} rejected)")

            cursor.execute(
                """
                UPDATE bronze.load_batches
                SET status = 'success',
                    row_count = %s,
                    finished_at = now(),
                    error_message = NULL
                WHERE load_id = %s
                """,
                (valid_rows, load_id),
            )
            connection.commit()

        log.info(
            "load %-20s rows=%-9d rejected=%-5d source=%-9d load_id=%d",
            entity,
            valid_rows,
            rejected_rows,
            source_rows,
            load_id,
        )
        return valid_rows

    except Exception as exc:
        connection.rollback()
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE bronze.load_batches
                SET status = 'failed',
                    finished_at = now(),
                    error_message = %s
                WHERE source_file = %s
                  AND file_sha256 = %s
                  AND status <> 'success'
                """,
                (str(exc)[:2000], filename, file_hash),
            )
            connection.commit()
        except Exception:
            connection.rollback()
        raise
    finally:
        connection.close()


def load_bronze(engine: Engine | None = None) -> dict[str, int]:
    """Load every raw CSV into ``bronze.<entity>``.

    Returns a mapping of ``bronze.<entity>`` to loaded row count.
    Repeated calls with unchanged files are no-ops.
    """
    engine = engine or get_engine()
    counts: dict[str, int] = {}
    for entity, filename in RAW_FILES.items():
        counts[f"bronze.{entity}"] = _load_file(engine, entity, filename)
    return counts
