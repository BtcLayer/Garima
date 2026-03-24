import requests
import time
import random

URL = "http://127.0.0.1:8000/webhook"

for i in range(500):
    payload = {
        "symbol": "BTCUSDT",
        "side": random.choice(["BUY", "SELL"]),
        "timestamp": time.time()
    }

    requests.post(URL, json=payload)

    time.sleep(0.05)  # small delay