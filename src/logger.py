"""
Structured JSON logging with rotation.

Provides a centralized logger that:
- Outputs JSON-formatted log lines (machine-parseable)
- Rotates log files (10MB max, keeps 5 backups)
- Logs to both file and console
- Supports log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)

Usage:
    from src.logger import get_logger
    logger = get_logger("manager")
    logger.info("Order placed", extra={"symbol": "BTCUSDT", "qty": 0.1})
    logger.error("Order failed", extra={"symbol": "BTCUSDT", "error": "timeout"})
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(_ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "garima.log")
MAX_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5

os.makedirs(LOG_DIR, exist_ok=True)


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Merge extra fields (passed via extra={})
        for key in ("symbol", "side", "price", "qty", "pnl", "error",
                     "reason", "signal_id", "latency_ms", "event_type",
                     "strategy", "timeframe", "mode", "action"):
            val = getattr(record, key, None)
            if val is not None:
                entry[key] = val
        if record.exc_info and record.exc_info[0]:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def get_logger(name: str = "garima", level: int = logging.INFO) -> logging.Logger:
    """Get or create a structured JSON logger.

    Args:
        name: Logger name (e.g. "manager", "webhook", "monitor")
        level: Logging level (default INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(f"garima.{name}")

    if logger.handlers:
        return logger  # already configured

    logger.setLevel(level)
    logger.propagate = False

    # File handler with rotation
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(JSONFormatter())
    file_handler.setLevel(level)
    logger.addHandler(file_handler)

    # Console handler (compact format for readability)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    ))
    console_handler.setLevel(logging.WARNING)  # only warnings+ to console
    logger.addHandler(console_handler)

    return logger


# ── Legacy compatibility ─────────────────────────────────────────────

class EventLogger:
    """Backwards-compatible wrapper for old EventLogger API."""

    def __init__(self, log_file="logs/audit_trail.log"):
        self._logger = get_logger("audit")

    def log_event(self, event_type, data):
        self._logger.info(
            event_type,
            extra={"event_type": event_type, **{k: v for k, v in data.items() if k in (
                "symbol", "side", "price", "qty", "pnl", "error", "reason",
                "signal_id", "strategy", "timeframe", "mode", "action"
            )}}
        )
