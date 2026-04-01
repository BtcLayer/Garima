#!/usr/bin/env python3
"""Auto-notify on Telegram when new ML results are found. Runs every 60s."""
import json, os, time, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

STORAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage")
STATE_FILE = os.path.join(STORAGE, "ml_notify_state.json")
ML_FILE = os.path.join(STORAGE, "ml_results.json")

# Load bot token
BOT_TOKEN = ""
CHAT_ID = ""
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
try:
    for line in open(env_path):
        line = line.strip()
        if "BOT_TOKEN" in line and "=" in line:
            BOT_TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
        if "CHAT_ID" in line and "=" in line:
            CHAT_ID = line.split("=", 1)[1].strip().strip('"').strip("'")
except:
    pass

if not BOT_TOKEN or not CHAT_ID:
    print("No BOT_TOKEN or CHAT_ID found in .env")
    sys.exit(1)

print(f"Auto-notify running (checking every 60s)", flush=True)

while True:
    try:
        results = json.load(open(ML_FILE))
    except:
        results = []

    try:
        state = json.load(open(STATE_FILE))
    except:
        state = {"count": 0}

    if results and len(results) > state.get("count", 0):
        state["count"] = len(results)
        json.dump(state, open(STATE_FILE, "w"))

        best = results[0]
        above_01 = len([r for r in results if r.get("roi_day", 0) >= 0.1])
        msg = (
            f"*ML Update* ({len(results)} strategies found)\n\n"
            f"Best: `{best.get('roi_day', 0):.3f}%/day` {best.get('asset', '')} {best.get('tf', '4h')}\n"
            f"PF={best.get('pf', 0)} WR={best.get('wr', 0)}% GDD={best.get('gdd', 0)}%\n"
            f"Trades={best.get('trades', 0)} | TP={best.get('tp_pct', 0)*100:.0f}% SL={best.get('sl_pct', 0)*100:.0f}%\n"
            f">= 0.1%/day: {above_01}\n\n"
            f"Use `/ml results` for full list"
        )

        import requests
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        print(f"  Notified: {len(results)} results, best {best.get('roi_day', 0):.3f}%/day", flush=True)

    time.sleep(60)
