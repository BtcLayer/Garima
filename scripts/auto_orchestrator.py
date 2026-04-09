#!/usr/bin/env python3
"""Master automation orchestrator — runs all idle tasks on a schedule.
Deploy on server via cron or run as daemon alongside the Telegram bot.

Usage:
  python scripts/auto_orchestrator.py          # Run once (for cron)
  python scripts/auto_orchestrator.py --daemon  # Run continuously (every 6h)
  python scripts/auto_orchestrator.py --task daily_review  # Run specific task
"""
import sys, os, json, time, datetime, subprocess, traceback, requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

STORAGE = os.path.join(ROOT, "storage")
REPORTS = os.path.join(ROOT, "reports")
STATE_FILE = os.path.join(STORAGE, "orchestrator_state.json")

# ── Telegram ──
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


def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print(f"[NO TG] {msg[:100]}")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
    except Exception:
        pass


def load_state():
    try:
        return json.load(open(STATE_FILE))
    except Exception:
        return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def should_run(task_name, interval_hours, state):
    """Check if task should run based on last run time."""
    last = state.get(f"last_{task_name}")
    if not last:
        return True
    try:
        last_dt = datetime.datetime.fromisoformat(last)
        return (datetime.datetime.now() - last_dt).total_seconds() > interval_hours * 3600
    except Exception:
        return True


def mark_done(task_name, state):
    state[f"last_{task_name}"] = datetime.datetime.now().isoformat()
    save_state(state)


# ═══════════════════════════════════════════════════════════════
# TASK 1: Daily paper review (every 12h during paper window)
# ═══════════════════════════════════════════════════════════════
def task_daily_review(state):
    print("\n[TASK] Daily paper review...")
    try:
        from auto_daily_review import run as review_run
        review_run()
        mark_done("daily_review", state)
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        traceback.print_exc()
        return False


# ═══════════════════════════════════════════════════════════════
# TASK 2: Backtest G11-G22 (once — results cached)
# ═══════════════════════════════════════════════════════════════
def task_backtest_new(state):
    result_file = os.path.join(REPORTS, "G11_G22_BACKTEST_RESULTS.json")
    if os.path.exists(result_file):
        print("\n[TASK] G11-G22 backtest: already completed, skipping.")
        return True

    print("\n[TASK] Backtesting G11-G22 strategies...")
    try:
        from batch_test_g11_g22 import run as backtest_run
        backtest_run()
        mark_done("backtest_g11_g22", state)
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        traceback.print_exc()
        return False


# ═══════════════════════════════════════════════════════════════
# TASK 3: ML score new strategies (once — results cached)
# ═══════════════════════════════════════════════════════════════
def task_ml_score(state):
    result_file = os.path.join(REPORTS, "G11_G22_ML_SCORES.json")
    if os.path.exists(result_file):
        print("\n[TASK] ML scoring: already completed, skipping.")
        return True

    print("\n[TASK] ML scoring G11-G22...")
    try:
        from auto_ml_score_new import run as ml_run
        ml_run()
        mark_done("ml_score", state)
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        traceback.print_exc()
        return False


# ═══════════════════════════════════════════════════════════════
# TASK 4: Server health check (every 6h)
# ═══════════════════════════════════════════════════════════════
def task_health_check(state):
    print("\n[TASK] Server health check...")
    checks = {"webhook": False, "dashboard": False, "bot": False}

    try:
        r = requests.get("http://15.207.152.119:8501/health", timeout=10)
        checks["webhook"] = r.status_code == 200
    except Exception:
        pass

    try:
        r = requests.get("http://15.207.152.119:8502/", timeout=10)
        checks["dashboard"] = r.status_code == 200
    except Exception:
        pass

    # Bot health — check heartbeat file
    hb_file = os.path.join(ROOT, "archive", "bot", "state", "bot_heartbeat.json")
    if os.path.exists(hb_file):
        try:
            hb = json.load(open(hb_file))
            last = hb.get("timestamp", "")
            if last:
                hb_dt = datetime.datetime.fromisoformat(last)
                checks["bot"] = (datetime.datetime.now() - hb_dt).total_seconds() < 300
        except Exception:
            pass

    status_line = " | ".join(f"{k}: {'UP' if v else 'DOWN'}" for k, v in checks.items())
    print(f"  {status_line}")

    if not all(checks.values()):
        down = [k for k, v in checks.items() if not v]
        send_telegram(f"*Health Alert*: {', '.join(down)} DOWN\n{status_line}")

    mark_done("health_check", state)
    return True


# ═══════════════════════════════════════════════════════════════
# TASK 5: Generate TV validation priority list from ML + backtest
# ═══════════════════════════════════════════════════════════════
def task_tv_priority(state):
    bt_file = os.path.join(REPORTS, "G11_G22_BACKTEST_RESULTS.json")
    ml_file = os.path.join(REPORTS, "G11_G22_ML_SCORES.json")
    out_file = os.path.join(REPORTS, "G11_G22_TV_PRIORITY.json")

    if os.path.exists(out_file):
        print("\n[TASK] TV priority list: already generated, skipping.")
        return True

    if not os.path.exists(bt_file) or not os.path.exists(ml_file):
        print("\n[TASK] TV priority: waiting for backtest + ML results first.")
        return False

    print("\n[TASK] Generating TV validation priority list...")
    bt = json.load(open(bt_file))
    ml = json.load(open(ml_file))

    # Merge scores
    ml_lookup = {(m["strategy"], m["asset"]): m["ml_score"] for m in ml}

    priority = []
    for r in bt:
        key = (r["strategy"], r["asset"])
        ml_score = ml_lookup.get(key, 0)
        # Combined score: OOS ROI weight + ML score weight
        combined = r["oos_roi"] * 0.6 + ml_score * 0.4 if r["status"] == "PASS" else ml_score * 0.2
        priority.append({
            **r,
            "ml_score": ml_score,
            "combined_score": round(combined, 2),
            "action": "TV_VALIDATE" if combined > 1.0 and r["status"] == "PASS" else "SKIP",
        })

    priority.sort(key=lambda x: x["combined_score"], reverse=True)

    with open(out_file, "w") as f:
        json.dump(priority, f, indent=2)

    tv_ready = [p for p in priority if p["action"] == "TV_VALIDATE"]
    print(f"  {len(tv_ready)} strategies recommended for TV validation")

    if tv_ready:
        msg = f"*TV Validation Priority*\n{len(tv_ready)} strategies ready:\n\n"
        for p in tv_ready[:5]:
            msg += f"`{p['strategy']}` {p['asset']}: OOS={p['oos_roi']:.1f}% ML={p['ml_score']:.1f}\n"
        msg += "\nAdd these to TradingView for validation."
        send_telegram(msg)

    mark_done("tv_priority", state)
    return True


# ═══════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════

TASKS = [
    # (name, function, interval_hours, description)
    ("daily_review", task_daily_review, 12, "Paper trading review"),
    ("backtest_g11_g22", task_backtest_new, 999, "Backtest G11-G22 (once)"),
    ("ml_score", task_ml_score, 999, "ML score G11-G22 (once)"),
    ("tv_priority", task_tv_priority, 999, "TV priority list (once)"),
    ("health_check", task_health_check, 6, "Server health check"),
]


def run_all():
    state = load_state()
    now = datetime.datetime.now()
    print(f"{'='*60}")
    print(f"GARIMA ORCHESTRATOR — {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")

    results = {}
    for name, func, interval, desc in TASKS:
        if should_run(name, interval, state):
            try:
                ok = func(state)
                results[name] = "OK" if ok else "PARTIAL"
            except Exception as e:
                results[name] = f"ERROR: {e}"
                print(f"  TASK {name} FAILED: {e}")
        else:
            results[name] = "SKIPPED (recent)"
            print(f"\n[SKIP] {desc} — ran recently")

    # Summary
    print(f"\n{'='*60}")
    print("ORCHESTRATOR SUMMARY:")
    for name, status in results.items():
        print(f"  {name:25s} {status}")
    print(f"{'='*60}")

    return results


def run_single(task_name):
    state = load_state()
    for name, func, _, desc in TASKS:
        if name == task_name:
            print(f"Running: {desc}")
            return func(state)
    print(f"Unknown task: {task_name}")
    return False


def daemon_mode():
    print("ORCHESTRATOR DAEMON MODE — running every 6 hours")
    print("Press Ctrl+C to stop\n")
    send_telegram("*Orchestrator started* (daemon mode, 6h interval)")

    while True:
        try:
            run_all()
        except Exception as e:
            print(f"Orchestrator error: {e}")
            traceback.print_exc()
        print(f"\nNext run in 6 hours. Sleeping...")
        time.sleep(6 * 3600)


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        daemon_mode()
    elif "--task" in sys.argv:
        idx = sys.argv.index("--task")
        if idx + 1 < len(sys.argv):
            run_single(sys.argv[idx + 1])
        else:
            print("Usage: --task <task_name>")
    else:
        run_all()
