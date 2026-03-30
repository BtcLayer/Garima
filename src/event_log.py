"""
Event logger — JSONL-based event persistence.

Replaces the SQLAlchemy EventRaw/Trade/Run models from archive
with a simple append-only JSONL file. Each line is a JSON object
with timestamp, event_type, and payload.
"""

import json
import os
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENT_LOG_PATH = os.path.join(_ROOT, "storage", "events.jsonl")


def log_event(event_type: str, payload: dict, source: str = "webhook") -> dict:
    """Append an event to the JSONL log. Returns the logged record."""
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "source": source,
        "payload": payload,
    }
    os.makedirs(os.path.dirname(EVENT_LOG_PATH), exist_ok=True)
    with open(EVENT_LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")
    return record


def read_events(event_type: str = None, limit: int = 100) -> list:
    """Read recent events, optionally filtered by type."""
    if not os.path.exists(EVENT_LOG_PATH):
        return []
    events = []
    with open(EVENT_LOG_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if event_type and record.get("event_type") != event_type:
                    continue
                events.append(record)
            except json.JSONDecodeError:
                continue
    return events[-limit:]


def count_events() -> dict:
    """Count events by type."""
    counts = {}
    if not os.path.exists(EVENT_LOG_PATH):
        return counts
    with open(EVENT_LOG_PATH) as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                et = record.get("event_type", "unknown")
                counts[et] = counts.get(et, 0) + 1
            except (json.JSONDecodeError, AttributeError):
                continue
    return counts
