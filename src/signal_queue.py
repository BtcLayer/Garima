"""
SQLite-based signal queue.

Replaces the file-based JSONL queue (storage/signals.jsonl) with a durable
SQLite database. Signals survive crashes, support status tracking, and
can be queried/replayed.

Usage:
    from src.signal_queue import SignalQueue
    q = SignalQueue()
    q.push({"symbol": "BTCUSDT", "side": "BUY", "price": 50000})
    signal = q.pop()       # returns oldest pending signal
    q.mark_done(signal["id"])
    q.mark_failed(signal["id"], "execution error")
"""

import json
import os
import sqlite3
import threading
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(_ROOT, "storage", "signal_queue.db")

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    payload TEXT NOT NULL,
    idempotency_key TEXT,
    error TEXT,
    processed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_status ON signals(status);
CREATE INDEX IF NOT EXISTS idx_idem ON signals(idempotency_key);
"""


class SignalQueue:
    def __init__(self, db_path: str = None):
        self._db_path = db_path or DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript(_CREATE_TABLE)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def push(self, payload: dict, idempotency_key: str = None) -> int:
        """Add a signal to the queue. Returns the signal ID."""
        with self._lock:
            with self._connect() as conn:
                # Check duplicate
                if idempotency_key:
                    existing = conn.execute(
                        "SELECT id FROM signals WHERE idempotency_key = ?",
                        (idempotency_key,)
                    ).fetchone()
                    if existing:
                        return -1  # duplicate

                cursor = conn.execute(
                    "INSERT INTO signals (created_at, status, payload, idempotency_key) VALUES (?, ?, ?, ?)",
                    (datetime.utcnow().isoformat(), "pending", json.dumps(payload), idempotency_key)
                )
                return cursor.lastrowid

    def pop(self) -> dict | None:
        """Get the oldest pending signal and mark it as processing."""
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM signals WHERE status = 'pending' ORDER BY id ASC LIMIT 1"
                ).fetchone()
                if not row:
                    return None
                conn.execute(
                    "UPDATE signals SET status = 'processing' WHERE id = ?",
                    (row["id"],)
                )
                return {
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "payload": json.loads(row["payload"]),
                    "idempotency_key": row["idempotency_key"],
                }

    def mark_done(self, signal_id: int):
        """Mark a signal as successfully processed."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE signals SET status = 'done', processed_at = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), signal_id)
            )

    def mark_failed(self, signal_id: int, error: str = ""):
        """Mark a signal as failed."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE signals SET status = 'failed', error = ?, processed_at = ? WHERE id = ?",
                (error, datetime.utcnow().isoformat(), signal_id)
            )

    def retry_failed(self) -> int:
        """Reset all failed signals back to pending. Returns count."""
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE signals SET status = 'pending', error = NULL, processed_at = NULL WHERE status = 'failed'"
            )
            return cursor.rowcount

    def pending_count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) as c FROM signals WHERE status = 'pending'").fetchone()
            return row["c"]

    def stats(self) -> dict:
        """Queue statistics."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) as c FROM signals GROUP BY status"
            ).fetchall()
            counts = {row["status"]: row["c"] for row in rows}
            total = sum(counts.values())
            return {"total": total, **counts}

    def recent(self, limit: int = 20) -> list:
        """Get recent signals (any status)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM signals ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "created_at": r["created_at"],
                    "status": r["status"],
                    "payload": json.loads(r["payload"]),
                    "error": r["error"],
                }
                for r in rows
            ]

    def purge_old(self, keep_days: int = 30) -> int:
        """Delete processed signals older than keep_days."""
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM signals WHERE status = 'done' AND processed_at < datetime('now', ?)",
                (f"-{keep_days} days",)
            )
            return cursor.rowcount
