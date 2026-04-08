"""Application-wide logging: rotating file under robo/logs/."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler


_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(threadName)s | %(name)s | %(message)s"
)
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def log_file_path() -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "logs", "personal_assistant.log")


def configure_logging(level: int = logging.INFO) -> None:
    """Idempotent root setup: one file handler, no duplicate handlers on re-call."""
    path = os.path.abspath(log_file_path())
    log_dir = os.path.dirname(path)
    os.makedirs(log_dir, exist_ok=True)

    root = logging.getLogger()
    normalized = os.path.normcase(path)
    if any(
        isinstance(h, RotatingFileHandler)
        and os.path.normcase(os.path.abspath(getattr(h, "baseFilename", ""))) == normalized
        for h in root.handlers
    ):
        root.setLevel(min(root.level, level))
        return

    root.setLevel(level)

    fh = RotatingFileHandler(
        path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setLevel(level)
    fh.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root.addHandler(fh)

    logging.getLogger(__name__).info(
        "logging configured | path=%s | level=%s",
        path,
        logging.getLevelName(level),
    )

