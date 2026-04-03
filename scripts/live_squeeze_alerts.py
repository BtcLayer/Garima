#!/usr/bin/env python3
"""
LIVE BB SQUEEZE ALERT SYSTEM
Monitors all assets via tradingview-screener every 5 min.
When squeeze releases + momentum confirms → sends Telegram alert with:
  - Asset, direction, confidence score
  - Exact SL/TP/Trail params to use
  - Kelly position size
  - Time filter status (good day/bad day)

This replaces manual TV checking.
"""
import time
import json
import os
import requests
from datetime import datetime, timezone
from tradingview_screener import Query, Column

# ── CONFIG ──
ASSETS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "LINKUSDT",
    "DOTUSDT", "LTCUSDT", "BNBUSDT", "XRPUSDT", "AVAXUSDT",
    "SUIUSDT", "LDOUSDT", "NEARUSDT", "INJUSDT", "APTUSDT",
    "DOGEUSDT", "ARBUSDT", "UNIUSDT", "AAVEUSDT", "ATOMUSDT",
]

# Best params per asset (from TV validation)
BEST_PARAMS = {
    "LDOUSDT": {"tp": 14, "sl": 1.5, "trail": 4, "bb": 14, "tier": "TIER_2", "roi_yr": 74.53},
    "SUIUSDT": {"tp": 15, "sl": 1.5, "trail": 5, "bb": 14, "tier": "TIER_2", "roi_yr": 63.54},
    "ETHUSDT": {"tp": 10, "sl": 1.5, "trail": 3.5, "bb": 14, "tier": "TIER_2", "roi_yr": 51.76},
    "DOTUSDT": {"tp": 10, "sl": 1.5, "trail": 3.5, "bb": 14, "tier": "PAPER", "roi_yr": 35.70},
    "BTCUSDT": {"tp": 10, "sl": 1.5, "trail": 3.5, "bb": 14, "tier": "PAPER", "roi_yr": 19.47},
    "LTCUSDT": {"tp": 10, "sl": 1.5, "trail": 3.5, "bb": 20, "tier": "PAPER", "roi_yr": 22.38},
}
DEFAULT_PARAMS = {"tp": 10, "sl": 1.5, "trail": 3.5, "bb": 14, "tier": "UNKNOWN", "roi_yr": 0}

CHECK_INTERVAL = 300  # 5 min

# Good/bad days (from time analysis)
# dayofweek: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
GOOD_DAYS = [0, 2, 5]  # Mon, Wed, Sat
BAD_DAYS = [3]  # Thursday

# Load bot token
BOT_TOKEN = ""
CHAT_ID = ""
try:
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    for line in open(env_path):
        line = line.strip()
        if "BOT_TOKEN" in line and "=" in line:
            BOT_TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
        if "CHAT_ID" in line and "=" in line:
            CHAT_ID = line.split("=", 1)[1].strip().strip('"').strip("'")
except:
    pass


def send_alert(msg):
    if BOT_TOKEN and CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        except:
            pass


def get_data():
    try:
        q = (Query()
            .select('name', 'close', 'RSI', 'ADX', 'BB.upper', 'BB.lower',
                    'MACD.macd', 'MACD.signal', 'Stoch.K', 'EMA20', 'EMA50',
                    'EMA200', 'change', 'volume', 'ATR', 'open')
            .where(Column('exchange') == 'BINANCE', Column('name').isin(ASSETS))
            .set_markets('crypto'))
        count, data = q.get_scanner_data()
        return data
    except:
        return None


def check_squeeze(row, prev_state):
    """Check if squeeze just released on this asset."""
    name = row.get('name', '')
    bb_upper = row.get('BB.upper', 0)
    bb_lower = row.get('BB.lower', 0)
    close = row.get('close', 0)
    ema20 = row.get('EMA20', 0)
    ema50 = row.get('EMA50', 0)
    ema200 = row.get('EMA200', 0)
    adx = row.get('ADX', 0)
    rsi = row.get('RSI', 50)
    macd = row.get('MACD.macd', 0)
    macd_sig = row.get('MACD.signal', 0)
    atr = row.get('ATR', 0)
    change = row.get('change', 0)

    if not all([bb_upper, bb_lower, close, ema20]):
        return None

    # Approximate KC (using EMA20 + 1.5 * ATR)
    kc_upper = ema20 + 1.5 * atr if atr else bb_upper
    kc_lower = ema20 - 1.5 * atr if atr else bb_lower

    # Squeeze state
    squeeze_on = bb_upper < kc_upper and bb_lower > kc_lower
    was_squeeze = prev_state.get(name, {}).get('squeeze', False)

    # Squeeze RELEASE = was on, now off
    squeeze_release = was_squeeze and not squeeze_on

    # Momentum direction
    mom_bull = macd > macd_sig if macd and macd_sig else change > 0
    trend_up = ema50 > ema200 if ema50 and ema200 else False
    adx_ok = adx > 20 if adx else False

    # Time filter
    now = datetime.now(timezone.utc)
    dow = now.weekday()  # 0=Mon, 6=Sun
    is_good_day = dow in GOOD_DAYS
    is_bad_day = dow in BAD_DAYS

    # Get params for this asset
    params = BEST_PARAMS.get(name, DEFAULT_PARAMS)

    # Kelly size
    wr = 0.82
    rr = params["tp"] / params["sl"]
    kelly = max(0, (rr * wr - (1 - wr)) / rr)
    half_kelly = round(kelly / 2 * 100, 1)

    # Build state
    state = {
        'squeeze': squeeze_on,
        'release': squeeze_release,
        'direction': 'LONG' if mom_bull else 'SHORT',
        'trend_up': trend_up,
        'adx_ok': adx_ok,
        'is_good_day': is_good_day,
        'is_bad_day': is_bad_day,
    }

    # ALERT if squeeze just released
    if squeeze_release and adx_ok and not is_bad_day:
        direction = "LONG" if mom_bull else "SHORT"
        trend = "WITH trend" if (mom_bull and trend_up) or (not mom_bull and not trend_up) else "COUNTER trend"
        confidence = "HIGH" if is_good_day and trend_up == mom_bull else "MEDIUM"

        alert_msg = (
            f"*SQUEEZE ALERT - {name}*\n\n"
            f"Direction: `{direction}` ({trend})\n"
            f"Confidence: `{confidence}`\n"
            f"Price: `${close:,.4f}`\n\n"
            f"*Params to use:*\n"
            f"BB Length: `{params['bb']}`\n"
            f"TP: `{params['tp']}%` | SL: `{params['sl']}%` | Trail: `{params['trail']}%`\n"
            f"Kelly Size: `{half_kelly}%`\n\n"
            f"*Indicators:*\n"
            f"RSI: `{rsi:.1f}` | ADX: `{adx:.1f}`\n"
            f"Day: `{'GOOD' if is_good_day else 'BAD' if is_bad_day else 'NEUTRAL'}`\n"
            f"Tier: `{params['tier']}` | Historical ROI: `{params['roi_yr']}%/yr`\n\n"
            f"Open BB Squeeze V2 on TradingView and enter!"
        )
        return state, alert_msg

    return state, None


def run():
    print("=" * 60, flush=True)
    print("  LIVE BB SQUEEZE ALERT SYSTEM", flush=True)
    print(f"  Monitoring {len(ASSETS)} assets every {CHECK_INTERVAL}s", flush=True)
    print(f"  Alerts via Telegram when squeeze releases", flush=True)
    print("=" * 60, flush=True)

    send_alert(
        "*BB Squeeze Alert System STARTED*\n\n"
        f"Monitoring `{len(ASSETS)}` assets\n"
        f"Checking every `{CHECK_INTERVAL}s`\n"
        f"Time filter: Skip Thursday, prefer Mon/Wed/Sat\n"
        f"Will alert when squeeze releases with entry params"
    )

    prev_state = {}

    while True:
        now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        data = get_data()

        if data is None or len(data) == 0:
            print(f"  [{now}] No data", flush=True)
            time.sleep(CHECK_INTERVAL)
            continue

        squeezing = []
        alerts_sent = 0

        for _, row in data.iterrows():
            name = row.get('name', '')
            result = check_squeeze(row, prev_state)
            if result is None:
                continue
            state, alert_msg = result

            if state['squeeze']:
                squeezing.append(name)

            if alert_msg:
                send_alert(alert_msg)
                alerts_sent += 1
                print(f"  [{now}] ALERT: {name} {state['direction']}!", flush=True)

            prev_state[name] = state

        print(f"  [{now}] Scanned {len(data)} | Squeezing: {len(squeezing)} {squeezing[:5]} | Alerts: {alerts_sent}", flush=True)

        # Save state
        try:
            save_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                      "storage", "squeeze_live_state.json")
            json.dump({
                "timestamp": now,
                "squeezing": squeezing,
                "total_monitored": len(data),
                "prev_state": {k: {"squeeze": v.get("squeeze", False)} for k, v in prev_state.items()},
            }, open(save_path, "w"), indent=2)
        except:
            pass

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run()
