"""Logging helpers for the GPT hotkey application."""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

LOG_FILE_NAME = "gpt_hotkey_app.log"
LOG_MAX_BYTES = 1_048_576  # 1 MiB
LOG_BACKUP_COUNT = 3


def setup_logging(level: str = "INFO", log_dir: Optional[Path] = None) -> logging.Logger:
    """Configure logging for the application.

    Args:
        level: Textual log level such as ``"INFO"`` or ``"DEBUG"``.
        log_dir: Optional directory where the rotating log file should be placed.

    Returns:
        The configured root logger instance.
    """

    log_level = getattr(logging, level.upper(), logging.INFO)
    logger = logging.getLogger("gpt_hotkey_app")
    logger.setLevel(log_level)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(threadName)s %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_dir is None:
        log_dir = Path.cwd()
    log_dir.mkdir(parents=True, exist_ok=True)
    file_path = log_dir / LOG_FILE_NAME

    file_handler = logging.handlers.RotatingFileHandler(
        file_path,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.debug("Logging configured at level %s", level)
    return logger
