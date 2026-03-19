import time
import statistics
from pathlib import Path
import json

METRICS_PATH = Path("state/metrics.json")

class Metrics:
    def __init__(self):
        self.total = 0
        self.duplicates = 0
        self.rejects = 0
        self.latencies = []
        self.critical_incidents = 0

    def record_signal(self):
        self.total += 1

    def record_duplicate(self):
        self.duplicates += 1

    def record_reject(self):
        self.rejects += 1

    def record_latency(self, latency_ms):
        self.latencies.append(latency_ms)

    def record_critical(self):
        self.critical_incidents += 1

    def save(self):
        METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "total": self.total,
            "duplicates": self.duplicates,
            "rejects": self.rejects,
            "duplicate_rate": self.duplicate_rate(),
            "reject_rate": self.reject_rate(),
            "p95_latency_ms": self.p95_latency(),
            "critical_incidents": self.critical_incidents,
            "timestamp": time.time()
        }

        with open(METRICS_PATH, "w") as f:
            json.dump(data, f, indent=2)

    def duplicate_rate(self):
        return (self.duplicates / self.total) if self.total else 0

    def reject_rate(self):
        return (self.rejects / self.total) if self.total else 0

    def p95_latency(self):
        if len(self.latencies) < 1:
            return 0
        return statistics.quantiles(self.latencies, n=100)[94]