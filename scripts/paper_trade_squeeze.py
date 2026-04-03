#!/usr/bin/env python3
"""
Paper Trading — BB Squeeze V2 on Binance Testnet.
Monitors live prices, enters when squeeze releases, tracks PnL.
Uses tradingview-screener for real-time data.
No real money — testnet only.
"""
import time
import json
import os
import requests
from datetime import datetime, timezone
from tradingview_screener import Query, Column

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE = os.path.join(ROOT, "storage")
TRADES_FILE = os.path.join(STORAGE, "paper_trades.json")
STATE_FILE = os.path.join(STORAGE, "paper_state.json")

# Best assets + params from TV validation
WATCHLIST = {
    "LDOUSDT": {"tp": 0.14, "sl": 0.015, "bb": 14, "roi_yr": 74.53},
    "ETHUSDT": {"tp": 0.10, "sl": 0.015, "bb": 14, "roi_yr": 51.76},
    "SUIUSDT": {"tp": 0.15, "sl": 0.015, "bb": 14, "roi_yr": 63.54},
}

INITIAL_CAPITAL = 10000
CHECK_INTERVAL = 300  # 5 min

# Telegram
BOT_TOKEN = ""
CHAT_ID = ""
try:
    for line in open(os.path.join(ROOT, ".env")):
        if "BOT_TOKEN" in line and "=" in line:
            BOT_TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
        if "CHAT_ID" in line and "=" in line:
            CHAT_ID = line.split("=", 1)[1].strip().strip('"').strip("'")
except:
    pass


def notify(msg):
    if BOT_TOKEN and CHAT_ID:
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                         json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        except:
            pass


def load_state():
    try:
        return json.load(open(STATE_FILE))
    except:
        return {
            "capital": INITIAL_CAPITAL,
            "positions": {},
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "total_pnl": 0,
            "prev_squeeze": {},
        }


def save_state(state):
    json.dump(state, open(STATE_FILE, "w"), indent=2)


def load_trades():
    try:
        return json.load(open(TRADES_FILE))
    except:
        return []


def save_trade(trade):
    trades = load_trades()
    trades.append(trade)
    json.dump(trades, open(TRADES_FILE, "w"), indent=2)


def get_prices():
    try:
        q = (Query()
            .select('name', 'close', 'RSI', 'ADX', 'BB.upper', 'BB.lower',
                    'EMA20', 'ATR', 'MACD.macd', 'MACD.signal')
            .where(Column('exchange') == 'BINANCE',
                   Column('name').isin(list(WATCHLIST.keys())))
            .set_markets('crypto'))
        _, data = q.get_scanner_data()
        return {row['name']: row for _, row in data.iterrows()}
    except:
        return {}


def check_squeeze(prices, prev_squeeze):
    """Check squeeze state for each asset."""
    signals = {}
    for asset, row in prices.items():
        bb_upper = row.get('BB.upper', 0)
        bb_lower = row.get('BB.lower', 0)
        ema20 = row.get('EMA20', 0)
        atr = row.get('ATR', 0)
        close = row.get('close', 0)
        adx = row.get('ADX', 0)
        macd = row.get('MACD.macd', 0)
        macd_sig = row.get('MACD.signal', 0)

        if not all([bb_upper, bb_lower, ema20, atr, close]):
            continue

        kc_upper = ema20 + 1.5 * atr
        kc_lower = ema20 - 1.5 * atr

        squeeze_on = bb_upper < kc_upper and bb_lower > kc_lower
        was_on = prev_squeeze.get(asset, False)
        released = was_on and not squeeze_on

        direction = "LONG" if macd > macd_sig else "SHORT"

        signals[asset] = {
            "squeeze": squeeze_on,
            "released": released,
            "direction": direction,
            "price": close,
            "adx": adx,
            "adx_ok": adx > 20,
        }

    return signals


def run():
    state = load_state()
    print("=" * 60, flush=True)
    print("  PAPER TRADING — BB Squeeze V2", flush=True)
    print(f"  Capital: ${state['capital']:,.2f}", flush=True)
    print(f"  Watching: {list(WATCHLIST.keys())}", flush=True)
    print("=" * 60, flush=True)

    notify(
        f"*Paper Trading STARTED*\n\n"
        f"Capital: `${state['capital']:,.2f}`\n"
        f"Watching: `{', '.join(WATCHLIST.keys())}`\n"
        f"Trades so far: `{state['total_trades']}`\n"
        f"Total PnL: `${state['total_pnl']:,.2f}`"
    )

    while True:
        now = datetime.now(timezone.utc).strftime("%H:%M:%S")
        prices = get_prices()

        if not prices:
            time.sleep(CHECK_INTERVAL)
            continue

        signals = check_squeeze(prices, state.get("prev_squeeze", {}))

        # Check existing positions
        for asset, pos in list(state["positions"].items()):
            if asset not in prices:
                continue
            current_price = prices[asset]["close"]
            entry_price = pos["entry_price"]
            direction = pos["direction"]
            params = WATCHLIST.get(asset, {"tp": 0.10, "sl": 0.015})

            # Check TP/SL
            if direction == "LONG":
                pnl_pct = (current_price - entry_price) / entry_price
                hit_tp = pnl_pct >= params["tp"]
                hit_sl = pnl_pct <= -params["sl"]
            else:
                pnl_pct = (entry_price - current_price) / entry_price
                hit_tp = pnl_pct >= params["tp"]
                hit_sl = pnl_pct <= -params["sl"]

            if hit_tp or hit_sl:
                pnl_usd = pnl_pct * pos["size_usd"]
                state["capital"] += pnl_usd
                state["total_pnl"] += pnl_usd
                state["total_trades"] += 1
                if pnl_usd > 0:
                    state["wins"] += 1
                else:
                    state["losses"] += 1

                reason = "TP" if hit_tp else "SL"
                wr = state["wins"] / state["total_trades"] * 100 if state["total_trades"] > 0 else 0

                trade = {
                    "asset": asset, "direction": direction,
                    "entry": entry_price, "exit": current_price,
                    "pnl_pct": round(pnl_pct * 100, 2), "pnl_usd": round(pnl_usd, 2),
                    "reason": reason, "time": now,
                }
                save_trade(trade)
                del state["positions"][asset]

                notify(
                    f"*Paper Trade CLOSED — {reason}*\n\n"
                    f"Asset: `{asset}` {direction}\n"
                    f"Entry: `${entry_price:,.4f}` Exit: `${current_price:,.4f}`\n"
                    f"PnL: `{pnl_pct*100:+.2f}%` (`${pnl_usd:+,.2f}`)\n"
                    f"Capital: `${state['capital']:,.2f}`\n"
                    f"Record: `{state['wins']}W/{state['losses']}L` (WR: `{wr:.0f}%`)"
                )
                print(f"  [{now}] CLOSED {asset} {direction} {reason} PnL={pnl_pct*100:+.2f}%", flush=True)

        # Check for new entries
        for asset, sig in signals.items():
            if asset in state["positions"]:
                continue  # already in position
            if sig["released"] and sig["adx_ok"]:
                params = WATCHLIST.get(asset, {"tp": 0.10, "sl": 0.015})
                size_usd = state["capital"] * 0.3  # 30% per position (conservative)
                entry_price = sig["price"]

                state["positions"][asset] = {
                    "direction": sig["direction"],
                    "entry_price": entry_price,
                    "size_usd": size_usd,
                    "time": now,
                }

                notify(
                    f"*Paper Trade OPENED*\n\n"
                    f"Asset: `{asset}` {sig['direction']}\n"
                    f"Entry: `${entry_price:,.4f}`\n"
                    f"Size: `${size_usd:,.2f}` (30% of capital)\n"
                    f"TP: `{params['tp']*100}%` SL: `{params['sl']*100}%`\n"
                    f"ADX: `{sig['adx']:.1f}`"
                )
                print(f"  [{now}] OPENED {asset} {sig['direction']} @ ${entry_price:,.4f}", flush=True)

        # Update squeeze state
        state["prev_squeeze"] = {a: s["squeeze"] for a, s in signals.items()}
        save_state(state)

        active = len(state["positions"])
        squeezing = sum(1 for s in signals.values() if s["squeeze"])
        print(f"  [{now}] Positions: {active} | Squeezing: {squeezing} | Capital: ${state['capital']:,.2f}", flush=True)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run()
