"""
logger.py
=========
Centralised logging configuration for PawPal+.

Import the ``logger`` object from this module in any other file to write
structured log entries to both the console and the rotating log file at
``logs/pawpal_agent.log``.

Usage
-----
::

    from logger import logger

    logger.info("Agent loop started for owner: %s", owner.name)
    logger.warning("Medical task skipped: %s", task.name)
    logger.error("RAG index build failed: %s", str(exc))

Log format
----------
Each entry is written as::

    2024-01-15 14:32:07,123 | INFO     | Agent loop started for owner: Alice

The file handler uses a :class:`~logging.handlers.RotatingFileHandler` that
caps the log file at 1 MB and keeps 3 backup files, preventing unbounded disk
growth during long-running sessions.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
_LOG_FILE = os.path.join(_LOG_DIR, "pawpal_agent.log")

# Ensure the logs/ directory exists at import time so the handler never fails.
os.makedirs(_LOG_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Format
# ---------------------------------------------------------------------------
_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)

# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
# File handler — rotates at 1 MB, keeps 3 backups.
_file_handler = RotatingFileHandler(
    _LOG_FILE,
    maxBytes=1_000_000,
    backupCount=3,
    encoding="utf-8",
)
_file_handler.setLevel(logging.INFO)
_file_handler.setFormatter(_formatter)

# Console handler — useful during development and debugging.
_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(_formatter)

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
logger = logging.getLogger("pawpal")
logger.setLevel(logging.INFO)

# Guard against duplicate handlers if this module is imported more than once
# (e.g. in pytest sessions that reload modules).
if not logger.handlers:
    logger.addHandler(_file_handler)
    logger.addHandler(_console_handler)

# Do not propagate to the root logger to avoid duplicate output when other
# libraries also use the root logger.
logger.propagate = False
