# src/alerts/router.py

import os
import time
import json
import requests
from pathlib import Path
from threading import Lock
from dotenv import load_dotenv
load_dotenv()

ALERTS_LOG_PATH = Path("logs/alerts.jsonl")

class AlertRouter:
    def __init__(self, rate_limit_seconds: int = 60):
        self.rate_limit_seconds = rate_limit_seconds
        self._last_sent = {}
        self._lock = Lock()

        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    def _rate_limited(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            last = self._last_sent.get(key, 0)
            if now - last < self.rate_limit_seconds:
                return True
            self._last_sent[key] = now
        return False

    def _log_event(self, record: dict):
        ALERTS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(ALERTS_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def _send_telegram(self, message: str):
        if not self.telegram_token or not self.telegram_chat_id:
            return False

        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": message,
        }

        try:
            r = requests.post(url, json=payload, timeout=10)
            return r.status_code == 200
        except Exception:
            return False

    def send(self, level: str, message: str, event_key: str = "default"):

        record = {
            "timestamp": time.time(),
            "level": level,
            "message": message,
        }

        # Always log
        self._log_event(record)

        # Only rate limit Telegram
        if self._rate_limited(event_key):
            return

        self._send_telegram(f"[{level}] {message}")