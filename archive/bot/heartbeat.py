import json
import time
from pathlib import Path

HEARTBEAT_PATH = Path("state/bot_heartbeat.json")

def write_heartbeat(offset: int):
    HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "timestamp": time.time(),
        "last_processed_offset": offset
    }

    with open(HEARTBEAT_PATH, "w") as f:
        json.dump(data, f)