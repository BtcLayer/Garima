#!/usr/bin/env python3
"""
Live BB Squeeze Screener — uses tradingview-screener to find squeeze setups.
Monitors 20+ crypto assets, alerts when squeeze releases.
Runs continuously on server, notifies via Telegram.
"""
import time
import json
import os
import requests
from datetime import datetime
from tradingview_screener import Query, Column

# Config
ASSETS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "LINKUSDT",
    "DOTUSDT", "LTCUSDT", "BNBUSDT", "XRPUSDT", "AVAXUSDT",
    "SUIUSDT", "LDOUSDT", "NEARUSDT", "INJUSDT", "APTUSDT",
    "DOGEUSDT", "ARBUSDT", "UNIUSDT", "AAVEUSDT", "ATOMUSDT",
]
CHECK_INTERVAL = 300  # 5 minutes

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


def send_telegram(msg):
    if BOT_TOKEN and CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        except:
            pass


def get_crypto_data():
    """Pull live data from TradingView for all assets."""
    try:
        q = (Query()
            .select('name', 'close', 'RSI', 'ADX', 'BB.upper', 'BB.lower',
                    'MACD.macd', 'MACD.signal', 'Stoch.K', 'EMA20', 'EMA50',
                    'EMA200', 'change', 'volume', 'ATR', 'Volatility.D')
            .where(
                Column('exchange') == 'BINANCE',
                Column('name').isin(ASSETS)
            )
            .set_markets('crypto'))

        count, data = q.get_scanner_data()
        return data
    except Exception as e:
        print(f"  Error fetching data: {e}", flush=True)
        return None


def detect_squeeze(row):
    """Detect BB Squeeze conditions from TV data."""
    try:
        bb_upper = row.get('BB.upper', 0)
        bb_lower = row.get('BB.lower', 0)
        close = row.get('close', 0)
        rsi = row.get('RSI', 50)
        adx = row.get('ADX', 0)
        macd = row.get('MACD.macd', 0)
        macd_sig = row.get('MACD.signal', 0)
        ema20 = row.get('EMA20', 0)
        ema50 = row.get('EMA50', 0)
        ema200 = row.get('EMA200', 0)
        change = row.get('change', 0)
        stoch = row.get('Stoch.K', 50)

        if not all([bb_upper, bb_lower, close]):
            return None

        # BB Width (narrow = squeeze)
        bb_width = (bb_upper - bb_lower) / close * 100 if close > 0 else 0

        # Trend
        trend_up = ema20 > ema50 > 0 if ema20 and ema50 else False
        trend_down = ema20 < ema50 if ema20 and ema50 else False
        above_200 = close > ema200 if ema200 else False

        # MACD momentum
        macd_bull = macd > macd_sig if macd and macd_sig else False

        # Score the setup (0-100)
        score = 0
        if bb_width < 5: score += 20  # tight squeeze
        if bb_width < 3: score += 15  # very tight
        if adx and adx > 20: score += 15  # trending
        if trend_up: score += 10
        if above_200: score += 10
        if macd_bull: score += 10
        if rsi and 40 < rsi < 65: score += 10  # not overbought
        if stoch and 30 < stoch < 70: score += 10  # neutral zone

        # Kelly position size
        wr = 0.82  # our average WR on BB Squeeze
        rr = 6.67  # TP/SL ratio
        kelly = max(0, (rr * wr - (1 - wr)) / rr)
        half_kelly = kelly / 2

        return {
            "name": row.get('name', ''),
            "close": close,
            "bb_width": round(bb_width, 2),
            "rsi": round(rsi, 1) if rsi else 0,
            "adx": round(adx, 1) if adx else 0,
            "trend": "UP" if trend_up else "DOWN" if trend_down else "FLAT",
            "above_200": above_200,
            "macd_bull": macd_bull,
            "score": score,
            "kelly_size": round(half_kelly * 100, 1),
            "change_pct": round(change, 2) if change else 0,
        }
    except:
        return None


def run_screener():
    """Main screener loop."""
    print("=" * 60, flush=True)
    print("  BB SQUEEZE SCREENER — Live from TradingView", flush=True)
    print(f"  Monitoring {len(ASSETS)} assets every {CHECK_INTERVAL}s", flush=True)
    print("=" * 60, flush=True)

    prev_scores = {}

    while True:
        now = datetime.now().strftime("%H:%M:%S")
        data = get_crypto_data()

        if data is None or len(data) == 0:
            print(f"  [{now}] No data received", flush=True)
            time.sleep(CHECK_INTERVAL)
            continue

        setups = []
        for _, row in data.iterrows():
            result = detect_squeeze(row)
            if result and result["score"] >= 40:
                setups.append(result)

        setups.sort(key=lambda x: -x["score"])

        # Print status
        print(f"\n  [{now}] Scanned {len(data)} assets | {len(setups)} setups found", flush=True)
        for s in setups[:10]:
            prev = prev_scores.get(s["name"], 0)
            arrow = "NEW!" if prev == 0 else ("UP" if s["score"] > prev else "=")
            print(f"    {s['name']:<12} Score={s['score']:<3} BB={s['bb_width']:<5} RSI={s['rsi']:<5} "
                  f"ADX={s['adx']:<5} Trend={s['trend']:<5} Kelly={s['kelly_size']}% {arrow}", flush=True)

        # Alert on high-score setups (score >= 70)
        for s in setups:
            prev = prev_scores.get(s["name"], 0)
            if s["score"] >= 70 and prev < 70:
                msg = (
                    f"*SQUEEZE ALERT* {s['name']}\n\n"
                    f"Score: `{s['score']}/100`\n"
                    f"BB Width: `{s['bb_width']}%` (tight!)\n"
                    f"RSI: `{s['rsi']}` | ADX: `{s['adx']}`\n"
                    f"Trend: `{s['trend']}` | MACD: `{'Bull' if s['macd_bull'] else 'Bear'}`\n"
                    f"Kelly Size: `{s['kelly_size']}%`\n"
                    f"Price: `${s['close']:,.4f}`\n\n"
                    f"Check BB Squeeze V2 on TradingView!"
                )
                send_telegram(msg)
                print(f"    >>> ALERT SENT for {s['name']}!", flush=True)

        # Save scores for comparison
        prev_scores = {s["name"]: s["score"] for s in setups}

        # Save to file
        save_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                  "storage", "squeeze_screener.json")
        try:
            json.dump({
                "timestamp": now,
                "setups": setups,
                "total_scanned": len(data),
            }, open(save_path, "w"), indent=2)
        except:
            pass

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run_screener()
