import os 
import sys
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import requests
from binance_client import BinanceClient

load_dotenv()

TRADE_LOG = "storage/trades.jsonl"

# Telegram configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}" if TELEGRAM_TOKEN else None

# Configuration for Guardrails
STOP_LOSS_PCT = 0.01   # 1% loss limit
TAKE_PROFIT_PCT = 0.02 # 2% profit target

# Initialize Binance client safely
try:
    bnc = BinanceClient()
except Exception as e:
    print(f"Warning: BinanceClient init failed: {e}")
    bnc = None

active_positions = {}


def send_telegram(message):
    """Send message to Telegram."""
    if not TELEGRAM_API_URL or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except Exception as e:
        print(f"Warning: Telegram send failed: {e}")

def process_signal(signal):
    global active_positions
    symbol = signal.get("symbol")
    side = signal.get("side")
    price = float(signal.get("price", 0))
    
    if not symbol or price <= 0:
        return

    # 1. OPEN POSITION (Signal-based)
    if side == "BUY" and symbol not in active_positions:
        if not bnc:
            print("BinanceClient not available, skipping order.")
            return
        print(f"Sending BUY Order to Binance for {symbol}...")
        send_telegram(f"BUY signal for {symbol}")
        order = bnc.place_order(symbol=symbol, side='BUY', order_type='MARKET', quantity=0.01)
        
        if order:
            entry_price = float(order['fills'][0]['price']) if 'fills' in order else price
            # Calculate safety levels based on actual entry price
            sl_price = entry_price * (1 - STOP_LOSS_PCT)
            tp_price = entry_price * (1 + TAKE_PROFIT_PCT)
            
            active_positions[symbol] = {
                "entry_price": entry_price,
                "stop_loss": sl_price,
                "take_profit": tp_price,
                "quantity": 0.01,
                "entry_at": datetime.utcnow().isoformat()
            }
            print(f"[OPEN] {symbol} | Entry: {entry_price} | SL: {sl_price} | TP: {tp_price}")
            send_telegram(f"POSITION OPENED: {symbol}\nEntry: {entry_price}\nSL: {sl_price}\nTP: {tp_price}")

    # 2. MONITOR FOR EXIT (Signal, SL, or TP)
    elif symbol in active_positions:
        pos = active_positions[symbol]
        exit_reason = None

        if side == "SELL":
            exit_reason = "SIGNAL"
        elif price <= pos["stop_loss"]:
            exit_reason = "STOP_LOSS"
        elif price >= pos["take_profit"]:
            exit_reason = "TAKE_PROFIT"

        if exit_reason:
            execute_exit(symbol, price, exit_reason)

def execute_exit(symbol, price, reason):
    global active_positions
    print(f"{reason} triggered for {symbol}. Closing on Binance...")
    send_telegram(f"Closing {symbol} position...")
    
    # Execute the actual SELL order
    if not bnc:
        print("BinanceClient not available, skipping order.")
        return
    order = bnc.place_order(symbol=symbol, side='SELL', order_type='MARKET', quantity=0.01)
    
    if order:
        entry_data = active_positions.pop(symbol)
        exit_price = float(order['fills'][0]['price']) if 'fills' in order else price
        pnl = (exit_price - entry_data["entry_price"]) * entry_data["quantity"]
        
        # Log to trades.jsonl for your Dashboard
        trade_record = {
            "logged_at": datetime.utcnow().isoformat(),
            "symbol": symbol,
            "exit_reason": reason,
            "entry_price": entry_data["entry_price"],
            "exit_price": exit_price,
            "pnl": round(pnl, 4)
        }
        
        with open(TRADE_LOG, "a") as f:
            f.write(json.dumps(trade_record) + "\n")
            
        print(f"[CLOSE] {symbol} via {reason} | PnL: {pnl}")
        send_telegram(f"POSITION CLOSED: {symbol}\nReason: {reason}\nPnL: {pnl}")
