import os
import time
import json
from pathlib import Path
from fastapi import FastAPI

app = FastAPI()

QUEUE_PATH = Path("storage/signals.jsonl")
QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
HEARTBEAT_PATH = Path("state/bot_heartbeat.json")
METRICS_PATH = Path("state/metrics.json")

VERSION = "1.0.0"
SERVICE_NAME = "trading_bot"

@app.get("/health")
def health():
    metrics_data = {}
    if METRICS_PATH.exists():
        with open(METRICS_PATH) as f:
            metrics_data = json.load(f)

    queue_size = QUEUE_PATH.stat().st_size if QUEUE_PATH.exists() else 0

    last_signal_ts = None
    if QUEUE_PATH.exists():
        with open(QUEUE_PATH, "r") as f:
            lines = f.readlines()
            if lines:
                last_signal_ts = json.loads(lines[-1]).get("timestamp")

    last_processed_offset = None
    if HEARTBEAT_PATH.exists():
        with open(HEARTBEAT_PATH, "r") as f:
            hb = json.load(f)
            last_processed_offset = hb.get("last_processed_offset")

    return {
        "ok": True,
        "service": SERVICE_NAME,
        "version": VERSION,
        "queue_path": str(QUEUE_PATH),
        "queue_size_bytes": queue_size,
        "last_signal_ts": last_signal_ts,
        "last_processed_offset": last_processed_offset,
        "metrics": metrics_data
    }

@app.post("/webhook")
def webhook(payload: dict):

    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(QUEUE_PATH, "a") as f:
        f.write(json.dumps(payload) + "\n")

    print("Webhook received and signal written to queue")

    return {"status": "received"}