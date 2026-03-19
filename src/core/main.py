import time 
from src.core.metrics import Metrics
metrics = Metrics()

start = time.time()

metrics.record_signal()

# process order here

latency_ms = (time.time() - start) * 1000
metrics.record_latency(latency_ms)

metrics.save()

metrics.record_duplicate()

metrics.record_reject()

metrics.record_critical()