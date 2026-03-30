"""
Trading Bot with Telegram Integration

This bot:
1. Reads signals from storage/signals.jsonl
2. Processes them via manager.py
3. Sends trade notifications to Telegram
4. Monitors positions and health
"""

import time
import json
import os
import sys
import requests
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.heartbeat import write_heartbeat
from manager import process_signal
from dotenv import load_dotenv

load_dotenv()

SIGNAL_FILE = "storage/signals.jsonl"

# Telegram configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}" if TELEGRAM_TOKEN else None


def send_telegram(message):
    """Send message to Telegram."""
    if not TELEGRAM_API_URL or not TELEGRAM_CHAT_ID:
        print(f"[Telegram] Not configured: {message}")
        return
    
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"[Telegram] Error: {e}")


def run():
    offset = 0
    print("Bot Engine Started...")
    send_telegram("Trading Bot Started!")

    while True:
        try:
            # 1. Check if signal file exists
            if os.path.exists(SIGNAL_FILE):
                with open(SIGNAL_FILE, "r") as f:
                    lines = f.readlines()
                    
                    # 2. Process only NEW lines based on offset
                    if len(lines) > offset:
                        for i in range(offset, len(lines)):
                            try:
                                signal = json.loads(lines[i].strip())
                                print(f"Processing signal: {signal}")
                                send_telegram(f"Signal received: {signal}")
                                process_signal(signal)
                            except Exception as e:
                                print(f"Error parsing signal: {e}")
                                send_telegram(f"Error: {e}")
                        
                        offset = len(lines) # Update offset to the last line processed

            # 3. Standard heartbeat
            write_heartbeat(offset)
            time.sleep(5) # Faster check for signals (5 seconds)
            
        except KeyboardInterrupt:
            print("Bot stopped by user")
            send_telegram("Trading Bot Stopped!")
            break
        except Exception as e:
            print(f"Error: {e}")
            send_telegram(f"Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    run()
