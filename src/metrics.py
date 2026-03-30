"""
Signal processing metrics tracker.

Tracks signal counts, latency, duplicates, rejections, and critical incidents.
Persists to state/metrics.json for monitoring.
"""

import json
import statistics
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
METRICS_PATH = _ROOT / "state" / "metrics.json"


class Metrics:
    def __init__(self):
        self.total = 0
        self.duplicates = 0
        self.rejects = 0
        self.executed = 0
        self.latencies = []
        self.critical_incidents = 0
        self._load()

    # ── Recording ────────────────────────────────────────────────────

    def record_signal(self):
        self.total += 1
        self.save()

    def record_duplicate(self):
        self.duplicates += 1
        self.save()

    def record_reject(self, reason: str = ""):
        self.rejects += 1
        self.save()

    def record_executed(self):
        self.executed += 1
        self.save()

    def record_latency(self, latency_ms: float):
        self.latencies.append(latency_ms)
        # Keep last 1000 latencies
        if len(self.latencies) > 1000:
            self.latencies = self.latencies[-1000:]

    def record_critical(self):
        self.critical_incidents += 1
        self.save()

    # ── Computed ─────────────────────────────────────────────────────

    def duplicate_rate(self) -> float:
        return (self.duplicates / self.total) if self.total else 0.0

    def reject_rate(self) -> float:
        return (self.rejects / self.total) if self.total else 0.0

    def p95_latency(self) -> float:
        if len(self.latencies) < 2:
            return 0.0
        return statistics.quantiles(self.latencies, n=100)[94]

    def avg_latency(self) -> float:
        return sum(self.latencies) / len(self.latencies) if self.latencies else 0.0

    # ── Persistence ──────────────────────────────────────────────────

    def save(self):
        METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "total_signals": self.total,
            "executed": self.executed,
            "duplicates": self.duplicates,
            "rejects": self.rejects,
            "duplicate_rate": round(self.duplicate_rate(), 4),
            "reject_rate": round(self.reject_rate(), 4),
            "p95_latency_ms": round(self.p95_latency(), 2),
            "avg_latency_ms": round(self.avg_latency(), 2),
            "critical_incidents": self.critical_incidents,
            "last_updated": time.time(),
        }
        with open(METRICS_PATH, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self):
        if not METRICS_PATH.exists():
            return
        try:
            with open(METRICS_PATH) as f:
                data = json.load(f)
            self.total = data.get("total_signals", 0)
            self.executed = data.get("executed", 0)
            self.duplicates = data.get("duplicates", 0)
            self.rejects = data.get("rejects", 0)
            self.critical_incidents = data.get("critical_incidents", 0)
        except Exception:
            pass

    def to_dict(self) -> dict:
        return {
            "total_signals": self.total,
            "executed": self.executed,
            "duplicates": self.duplicates,
            "rejects": self.rejects,
            "duplicate_rate": round(self.duplicate_rate(), 4),
            "reject_rate": round(self.reject_rate(), 4),
            "p95_latency_ms": round(self.p95_latency(), 2),
            "critical_incidents": self.critical_incidents,
        }
