import requests

url = "http://127.0.0.1:8000/tv/webhook"
headers = {"Content-Type": "application/json", "X-Webhook-Token": "supersecret123"}
payload = {
    "schema_version": "1.0",
    "strategy_id": "BTC_Scalp_v1",
    "strategy_version": "1.0",
    "param_hash": "abc123",
    "event_type": "order_fill",
    "timestamp": "2026-02-26T10:00:00Z",
    "payload": {"entry_price": 50000, "qty": 0.1, "side": "buy"}
}

r = requests.post(url, json=payload, headers=headers)
print(r.status_code, r.json())