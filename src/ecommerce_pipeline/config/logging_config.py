"""Logging configuration."""

from __future__ import annotations

import logging
import sys

from .settings import LOG_DIR, LOG_LEVEL


def configure_logging(level: str | None = None) -> None:
    """Configure root logging once with a console and file handler."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    resolved = (level or LOG_LEVEL).upper()

    root = logging.getLogger()
    if root.handlers:
        root.setLevel(resolved)
        return

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)

    file_handler = logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8")
    file_handler.setFormatter(formatter)

    root.setLevel(resolved)
    root.addHandler(console)
    root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
