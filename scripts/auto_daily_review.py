#!/usr/bin/env python3
"""V-05 / P-07: Automated daily paper trading review.
Compares paper results vs shortlist expectations, sends Telegram summary.
Designed to run once per day via cron or orchestrator.
"""
import sys, os, json, datetime, hashlib, requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

STORAGE = os.path.join(ROOT, "storage")
REPORTS = os.path.join(ROOT, "reports")
STATE_FILE = os.path.join(STORAGE, "daily_review_state.json")
APPROVED_FILE = os.path.join(STORAGE, "approved_strategies.json")
PAPER_LOG = os.path.join(STORAGE, "paper_trade_log.json")
DECISION_MEMO = os.path.join(REPORTS, "DECISION_MEMO_TEMPLATE.md")

# ── Load .env ──
BOT_TOKEN = ""
CHAT_ID = ""
env_path = os.path.join(ROOT, ".env")
try:
    for line in open(env_path):
        line = line.strip()
        if "BOT_TOKEN" in line and "=" in line and not line.startswith("#"):
            BOT_TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
        if "CHAT_ID" in line and "=" in line and not line.startswith("#"):
            CHAT_ID = line.split("=", 1)[1].strip().strip('"').strip("'").split(",")[0]
except Exception:
    pass

# ── Shortlist expectations ──
EXPECTED = {
    "CCI_Trend_ETH_4h": {
        "roi_pct": 5.91, "oos_roi": 3.10, "pf": 1.14,
        "freq_per_week": 2, "max_dd": 6.0,
    },
    "Donchian_Trend_ETH_4h": {
        "roi_pct": 3.26, "oos_roi": 4.65, "pf": 1.08,
        "freq_per_week": 2, "max_dd": 6.0,
    },
}

PAPER_START = datetime.date(2026, 4, 7)
PAPER_END = datetime.date(2026, 4, 14)


def load_state():
    try:
        return json.load(open(STATE_FILE))
    except Exception:
        return {"last_review": None, "daily_logs": {}}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def load_paper_trades():
    """Load paper trade log (written by bot or webhook system)."""
    if os.path.exists(PAPER_LOG):
        return json.load(open(PAPER_LOG))
    # Also check archive/bot/state
    alt = os.path.join(ROOT, "archive", "bot", "state", "bot_heartbeat.json")
    if os.path.exists(alt):
        return json.load(open(alt))
    return []


def fetch_paper_from_server():
    """Try to fetch paper trading state from Harsh's execution system."""
    try:
        r = requests.get("http://15.207.152.119:8501/metrics", timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def analyze_trades(trades, day_num):
    """Analyze paper trades and produce daily metrics."""
    today = str(datetime.date.today())

    by_strat = {}
    for t in trades:
        sid = t.get("strategy", "unknown")
        if sid not in by_strat:
            by_strat[sid] = {"buys": 0, "sells": 0, "pnl": 0.0, "trades": []}
        action = t.get("action", "").upper()
        if action in ("BUY", "LONG"):
            by_strat[sid]["buys"] += 1
        elif action in ("SELL", "SHORT", "CLOSE_LONG", "CLOSE_SHORT"):
            by_strat[sid]["sells"] += 1
        by_strat[sid]["pnl"] += float(t.get("pnl", 0))
        by_strat[sid]["trades"].append(t)

    # Check NO_GO triggers
    no_go = []
    for sid, data in by_strat.items():
        if sid not in ["CCI_Trend", "Donchian_Trend", "CCI Trend", "Donchian Trend"]:
            # Unapproved strategy fired
            if data["trades"]:
                no_go.append(f"Unapproved strategy {sid} fired ({len(data['trades'])} trades)")

    total_trades = sum(d["buys"] + d["sells"] for d in by_strat.values())
    buy_observed = any(d["buys"] > 0 for d in by_strat.values())
    sell_observed = any(d["sells"] > 0 for d in by_strat.values())
    total_pnl = sum(d["pnl"] for d in by_strat.values())

    return {
        "date": today,
        "day_num": day_num,
        "total_trades": total_trades,
        "by_strategy": by_strat,
        "buy_observed": buy_observed,
        "sell_observed": sell_observed,
        "total_pnl": round(total_pnl, 2),
        "no_go_triggers": no_go,
    }


def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print(f"[NO TELEGRAM] {msg}")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown",
        }, timeout=15)
    except Exception as e:
        print(f"Telegram send failed: {e}")


def build_report(analysis, server_metrics):
    """Build daily review message."""
    day = analysis["day_num"]
    lines = [
        f"*P-07 Daily Paper Review — Day {day}/7*",
        f"Date: {analysis['date']}",
        "",
    ]

    for sid, data in analysis["by_strategy"].items():
        lines.append(f"*{sid}*: {data['buys']} buys, {data['sells']} sells, PnL ${data['pnl']:.2f}")

    lines.append("")
    lines.append(f"Total trades: {analysis['total_trades']}")
    lines.append(f"BUY path: {'OBSERVED' if analysis['buy_observed'] else 'NOT YET'}")
    lines.append(f"SELL path: {'OBSERVED' if analysis['sell_observed'] else 'NOT YET'}")
    lines.append(f"Total PnL: ${analysis['total_pnl']:.2f}")

    if server_metrics:
        lines.append("")
        lines.append(f"Server: UP | Signals: {server_metrics.get('signals_received', '?')}")

    if analysis["no_go_triggers"]:
        lines.append("")
        lines.append("*NO_GO TRIGGERS:*")
        for t in analysis["no_go_triggers"]:
            lines.append(f"  - {t}")
    else:
        lines.append("\nNo NO_GO triggers.")

    # Compare vs shortlist
    lines.append("")
    days_elapsed = max(1, day)
    freq = analysis["total_trades"] / days_elapsed * 7
    lines.append(f"Trade frequency: ~{freq:.1f}/week (expected ~4/week)")

    return "\n".join(lines)


def run():
    today = str(datetime.date.today())
    state = load_state()

    if state.get("last_review") == today:
        print(f"Already reviewed today ({today}). Skipping.")
        return

    day_num = (datetime.date.today() - PAPER_START).days + 1
    if day_num < 1:
        print("Paper validation hasn't started yet.")
        return
    if day_num > 8:
        print("Paper validation window ended. Time for U-09 decision memo.")

    print(f"=== Daily Paper Review — Day {day_num}/7 ({today}) ===")

    # Load trades
    trades = load_paper_trades()
    server_metrics = fetch_paper_from_server()

    analysis = analyze_trades(trades, day_num)

    # Save daily log
    state["daily_logs"][today] = analysis
    state["last_review"] = today
    save_state(state)

    # Build and send report
    report = build_report(analysis, server_metrics)
    print(report)
    send_telegram(report)

    # Save to reports dir
    report_path = os.path.join(REPORTS, f"DAILY_REVIEW_{today}.md")
    with open(report_path, "w") as f:
        f.write(f"# Daily Paper Review — Day {day_num}/7\n\n")
        f.write(report.replace("*", "**"))
    print(f"\nSaved: {report_path}")


if __name__ == "__main__":
    run()
