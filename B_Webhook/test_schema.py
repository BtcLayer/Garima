from jsonschema import validate
import json

with open("schemas/event_schema_v1.json") as f:
    schema = json.load(f)

example_event = {
    "schema_version": "1.0",
    "strategy_id": "BTC_Scalp_v1",
    "strategy_version": "1.0",
    "param_hash": "abc123",
    "event_type": "order_fill",
    "timestamp": "2026-02-26T10:00:00Z",
    "payload": {"entry_price": 50000, "qty": 0.1, "side": "buy"}
}

validate(instance=example_event, schema=schema)
print("Schema validation passed ✅")