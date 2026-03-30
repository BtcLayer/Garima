import os
import sys
import json
import threading
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import requests

load_dotenv()

try:
    from src.logger import get_logger
    _log = get_logger("manager")
except Exception:
    import logging
    _log = logging.getLogger("manager")

try:
    from binance_client import BinanceClient
except ImportError:
    BinanceClient = None

TRADE_LOG = "storage/trades.jsonl"
STATE_FILE = "storage/manager_state.json"

# Telegram configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}" if TELEGRAM_TOKEN else None

# ── Risk Configuration ──────────────────────────────────────────────
RISK_PER_TRADE_PCT = 0.02       # Risk 2% of equity per trade
MAX_POSITION_PER_ASSET_PCT = 0.10  # Max 10% of equity in one asset
MAX_TOTAL_EXPOSURE_PCT = 0.30   # Max 30% of equity across all positions
MAX_DAILY_LOSS_USD = 500.0      # Daily loss circuit breaker
MAX_WEEKLY_LOSS_USD = 1000.0    # Weekly loss circuit breaker
SL_TP_MONITOR_INTERVAL = 10    # Seconds between SL/TP price checks
PAPER_TRADING = os.getenv("TRADING_MODE", "PAPER").upper() != "LIVE"  # Default: PAPER (safe)


# ── State ────────────────────────────────────────────────────────────
_kill_switch_active = False
_active_positions = {}
_daily_pnl = 0.0
_weekly_pnl = 0.0
_daily_reset_date = datetime.utcnow().date()
_weekly_reset_date = datetime.utcnow().date()
_monitor_thread = None
_monitor_running = False

# Initialize Binance client safely
try:
    bnc = BinanceClient() if BinanceClient else None
except Exception as e:
    _log.warning("BinanceClient init failed: %s", e)
    bnc = None


# ── Persistence ──────────────────────────────────────────────────────

def _save_state():
    state = {
        "kill_switch": _kill_switch_active,
        "positions": _active_positions,
        "daily_pnl": _daily_pnl,
        "weekly_pnl": _weekly_pnl,
        "daily_reset": str(_daily_reset_date),
        "weekly_reset": str(_weekly_reset_date),
        "paper_trading": PAPER_TRADING,
    }
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        _log.warning("State save failed: %s", e)


def _load_state():
    global _kill_switch_active, _active_positions, _daily_pnl, _weekly_pnl
    global _daily_reset_date, _weekly_reset_date, PAPER_TRADING
    if not os.path.exists(STATE_FILE):
        return
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        _kill_switch_active = state.get("kill_switch", False)
        _active_positions = state.get("positions", {})
        _daily_pnl = state.get("daily_pnl", 0.0)
        _weekly_pnl = state.get("weekly_pnl", 0.0)
        _daily_reset_date = datetime.fromisoformat(state["daily_reset"]).date() if "daily_reset" in state else datetime.utcnow().date()
        _weekly_reset_date = datetime.fromisoformat(state["weekly_reset"]).date() if "weekly_reset" in state else datetime.utcnow().date()
        PAPER_TRADING = state.get("paper_trading", True)
    except Exception as e:
        _log.warning("State load failed: %s", e)


# ── Telegram ─────────────────────────────────────────────────────────

def send_telegram(message):
    if not TELEGRAM_API_URL or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except Exception as e:
        _log.warning("Telegram send failed: %s", e)


# ── Kill Switch ──────────────────────────────────────────────────────

def activate_kill_switch(close_all=True):
    global _kill_switch_active
    _kill_switch_active = True
    msg = "KILL SWITCH ACTIVATED — all new trades blocked."
    _log.critical("Kill switch activated")
    send_telegram(f"🚨 {msg}")
    if close_all:
        close_all_positions("KILL_SWITCH")
    _save_state()


def deactivate_kill_switch():
    global _kill_switch_active
    _kill_switch_active = False
    msg = "Kill switch deactivated — trading resumed."
    _log.info("Kill switch deactivated")
    send_telegram(f"✅ {msg}")
    _save_state()


def is_kill_switch_active():
    return _kill_switch_active


# ── Circuit Breaker (daily/weekly loss limits) ───────────────────────

def _reset_pnl_counters():
    global _daily_pnl, _weekly_pnl, _daily_reset_date, _weekly_reset_date
    today = datetime.utcnow().date()
    if today > _daily_reset_date:
        _daily_pnl = 0.0
        _daily_reset_date = today
    if (today - _weekly_reset_date).days >= 7:
        _weekly_pnl = 0.0
        _weekly_reset_date = today


def _record_pnl(pnl: float):
    global _daily_pnl, _weekly_pnl
    _reset_pnl_counters()
    _daily_pnl += pnl
    _weekly_pnl += pnl

    if _daily_pnl <= -MAX_DAILY_LOSS_USD:
        send_telegram(f"🚨 DAILY LOSS LIMIT hit (${_daily_pnl:.2f}). Activating kill switch.")
        activate_kill_switch(close_all=True)
    elif _weekly_pnl <= -MAX_WEEKLY_LOSS_USD:
        send_telegram(f"🚨 WEEKLY LOSS LIMIT hit (${_weekly_pnl:.2f}). Activating kill switch.")
        activate_kill_switch(close_all=True)
    _save_state()


# ── Position Sizing ──────────────────────────────────────────────────

def _get_equity() -> float:
    if not bnc:
        return 0.0
    try:
        bal = bnc.get_balance("USDT")
        return bal["total"] if bal else 0.0
    except Exception:
        return 0.0


def _current_exposure() -> float:
    total = 0.0
    for pos in _active_positions.values():
        total += pos["entry_price"] * pos["quantity"]
    return total


def _compute_quantity(symbol: str, entry_price: float, sl_pct: float) -> float:
    equity = _get_equity()
    if equity <= 0 or entry_price <= 0 or sl_pct <= 0:
        return 0.0

    # Risk-based: risk RISK_PER_TRADE_PCT of equity, divided by SL distance
    risk_usd = equity * RISK_PER_TRADE_PCT
    qty_from_risk = risk_usd / (entry_price * sl_pct)

    # Cap: max POSITION per asset
    max_asset_usd = equity * MAX_POSITION_PER_ASSET_PCT
    qty_from_asset_cap = max_asset_usd / entry_price

    # Cap: total exposure
    current_exp = _current_exposure()
    remaining_exp = max(0, equity * MAX_TOTAL_EXPOSURE_PCT - current_exp)
    qty_from_total_cap = remaining_exp / entry_price

    qty = min(qty_from_risk, qty_from_asset_cap, qty_from_total_cap)
    return round(qty, 6) if qty > 0 else 0.0


# ── Order Execution ──────────────────────────────────────────────────

def process_signal(signal: dict):
    symbol = signal.get("symbol")
    side = signal.get("side")
    price = float(signal.get("price", 0))
    sl_pct = float(signal.get("sl_pct", 0.02))
    tp_pct = float(signal.get("tp_pct", 0.04))
    ts_pct = float(signal.get("ts_pct", 0.0))

    if not symbol or price <= 0:
        return

    _reset_pnl_counters()

    if _kill_switch_active:
        _log.info("Kill switch active — ignoring %s signal", symbol, extra={"symbol": symbol, "side": side})
        return

    # OPEN
    if side == "BUY" and symbol not in _active_positions:
        quantity = _compute_quantity(symbol, price, sl_pct)
        if quantity <= 0:
            send_telegram(f"⚠️ {symbol} BUY skipped — insufficient equity or exposure limit reached.")
            return

        mode = "PAPER" if PAPER_TRADING else "LIVE"
        entry_price = price
        order = None

        if not PAPER_TRADING:
            if not bnc:
                _log.error("BinanceClient not available, skipping order", extra={"symbol": symbol})
                return
            order = bnc.place_order(symbol=symbol, side="BUY", order_type="MARKET", quantity=quantity)
            if not order:
                send_telegram(f"❌ {symbol} BUY order FAILED.")
                return
            entry_price = float(order["fills"][0]["price"]) if "fills" in order else price

        sl_price = entry_price * (1 - sl_pct)
        tp_price = entry_price * (1 + tp_pct)

        _active_positions[symbol] = {
            "entry_price": entry_price,
            "stop_loss": sl_price,
            "take_profit": tp_price,
            "trailing_stop_pct": ts_pct,
            "peak_price": entry_price,
            "quantity": quantity,
            "entry_at": datetime.utcnow().isoformat(),
            "mode": mode,
        }
        _save_state()
        msg = (
            f"[{mode}] OPENED {symbol}\n"
            f"Qty: {quantity} | Entry: {entry_price:.4f}\n"
            f"SL: {sl_price:.4f} | TP: {tp_price:.4f}"
        )
        if ts_pct > 0:
            msg += f" | TS: {ts_pct*100:.1f}%"
        _log.info("Position opened", extra={"symbol": symbol, "side": "BUY", "price": entry_price, "qty": quantity, "mode": mode})
        send_telegram(msg)

    # CLOSE on signal
    elif side == "SELL" and symbol in _active_positions:
        _execute_exit(symbol, price, "SIGNAL")


def _execute_exit(symbol: str, price: float, reason: str):
    if symbol not in _active_positions:
        return
    pos = _active_positions.pop(symbol)
    mode = pos.get("mode", "LIVE")
    exit_price = price

    if mode != "PAPER" and bnc:
        order = bnc.place_order(symbol=symbol, side="SELL", order_type="MARKET", quantity=pos["quantity"])
        if order and "fills" in order:
            exit_price = float(order["fills"][0]["price"])

    pnl = (exit_price - pos["entry_price"]) * pos["quantity"]
    _record_pnl(pnl)

    trade_record = {
        "logged_at": datetime.utcnow().isoformat(),
        "symbol": symbol,
        "mode": mode,
        "exit_reason": reason,
        "entry_price": pos["entry_price"],
        "exit_price": exit_price,
        "quantity": pos["quantity"],
        "pnl": round(pnl, 4),
    }
    try:
        os.makedirs(os.path.dirname(TRADE_LOG), exist_ok=True)
        with open(TRADE_LOG, "a") as f:
            f.write(json.dumps(trade_record) + "\n")
    except Exception as e:
        _log.error("Trade log write failed: %s", e)

    msg = f"[{mode}] CLOSED {symbol} — {reason}\nPnL: ${pnl:.2f}"
    _log.info("Position closed", extra={"symbol": symbol, "pnl": round(pnl, 4), "reason": reason, "mode": mode})
    send_telegram(msg)
    _save_state()


def close_all_positions(reason="MANUAL"):
    symbols = list(_active_positions.keys())
    if not symbols:
        send_telegram("No open positions to close.")
        return
    for symbol in symbols:
        current_price = 0.0
        if bnc:
            try:
                p = bnc.get_ticker_price(symbol)
                current_price = float(p) if p else 0.0
            except Exception:
                pass
        _execute_exit(symbol, current_price, reason)


# ── Continuous SL/TP/TS Monitor (background thread) ─────────────────

def _monitor_loop():
    global _monitor_running
    while _monitor_running:
        try:
            _check_positions()
        except Exception as e:
            _log.error("Monitor error: %s", e)
        time.sleep(SL_TP_MONITOR_INTERVAL)


def _check_positions():
    if not _active_positions or not bnc:
        return
    for symbol in list(_active_positions.keys()):
        pos = _active_positions.get(symbol)
        if not pos:
            continue
        try:
            raw_price = bnc.get_ticker_price(symbol)
            if not raw_price:
                continue
            price = float(raw_price)
        except Exception:
            continue

        # Update trailing stop peak
        ts_pct = pos.get("trailing_stop_pct", 0)
        if ts_pct > 0 and price > pos.get("peak_price", pos["entry_price"]):
            pos["peak_price"] = price
            new_sl = price * (1 - ts_pct)
            if new_sl > pos["stop_loss"]:
                pos["stop_loss"] = new_sl

        # Check SL/TP
        if price <= pos["stop_loss"]:
            _execute_exit(symbol, price, "STOP_LOSS")
        elif price >= pos["take_profit"]:
            _execute_exit(symbol, price, "TAKE_PROFIT")


def start_monitor():
    global _monitor_thread, _monitor_running
    if _monitor_running:
        return
    _monitor_running = True
    _monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
    _monitor_thread.start()
    _log.info("SL/TP monitor started (every %ds)", SL_TP_MONITOR_INTERVAL)


def stop_monitor():
    global _monitor_running
    _monitor_running = False
    _log.info("SL/TP monitor stopped")


# ── Status ───────────────────────────────────────────────────────────

def get_status() -> str:
    _reset_pnl_counters()
    mode = "PAPER" if PAPER_TRADING else "LIVE"
    lines = [
        f"Mode: {mode}",
        f"Kill switch: {'ACTIVE' if _kill_switch_active else 'OFF'}",
        f"Open positions: {len(_active_positions)}",
        f"Daily PnL: ${_daily_pnl:.2f} (limit: -${MAX_DAILY_LOSS_USD})",
        f"Weekly PnL: ${_weekly_pnl:.2f} (limit: -${MAX_WEEKLY_LOSS_USD})",
        f"Monitor: {'running' if _monitor_running else 'stopped'}",
    ]
    for sym, pos in _active_positions.items():
        lines.append(f"  {sym}: qty={pos['quantity']} entry={pos['entry_price']:.4f} SL={pos['stop_loss']:.4f} TP={pos['take_profit']:.4f}")
    return "\n".join(lines)


# ── Init ─────────────────────────────────────────────────────────────

_load_state()
