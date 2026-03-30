"""
Telegram Bot for Comprehensive Backtest

Commands:
/start - Help
/backtest - Quick backtest (BTCUSDT 1h only, no optimization)
/full - Full backtest (all symbols, with optimization)
/status - Check status
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from src.comprehensive_backtest import (
    BacktestEngine,
    RSIStrategy, MACDStrategy, MovingAverageCrossover,
    EMACrossStrategy, ATRStrategy, StochasticStrategy
)


class TelegramBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.engine = None
        self.last_result = None
    
    def send(self, text, parse_mode="Markdown"):
        if not self.token or not self.chat_id:
            print("Telegram not configured")
            return False
        
        url = f"{self.api_url}/sendMessage"
        try:
            r = requests.post(url, json={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode
            }, timeout=30)
            return r.status_code == 200
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def send_typing(self):
        if not self.token:
            return
        requests.post(f"{self.api_url}/sendChatAction", 
                     json={"chat_id": self.chat_id, "action": "typing"})
    
    def get_updates(self, offset=None):
        if not self.token:
            return []
        url = f"{self.api_url}/getUpdates"
        params = {"timeout": 60}
        if offset:
            params["offset"] = offset
        try:
            r = requests.get(url, params=params, timeout=65)
            return r.json().get("result", [])
        except:
            return []
    
    def process_command(self, cmd, args=None):
        args = args or []
        cmd = cmd.lower().strip("/")
        
        if cmd in ["start", "help"]:
            return """*Trading Bot Commands*

/backtest - Quick test (BTCUSDT 1h)
/full - Full backtest (all symbols)
/status - Bot status

*Data Source:* Binance API"""
        
        elif cmd == "backtest":
            return self.run_quick_backtest()
        
        elif cmd == "full":
            return self.run_full_backtest()
        
        elif cmd == "status":
            msg = "*Bot Status*\n\n"
            msg += f"Data: Binance API\n"
            msg += f"Symbols: BTC, ETH, BNB, SOL, XRP\n"
            msg += f"Timeframes: 15m, 1h, 4h, 1d\n"
            msg += f"Strategies: RSI, MACD, MA, EMA, ATR, STOCH\n"
            return msg
        
        return f"Unknown: /{cmd}"
    
    def run_quick_backtest(self):
        """Quick single-symbol backtest"""
        self.send_typing()
        self.send("Running quick backtest...")
        
        self.engine = BacktestEngine()
        
        # Test RSI on BTCUSDT 1h
        result = self.engine.run_backtest(
            RSIStrategy(), "BTCUSDT", "1h", "2024-01-01", "2025-01-01"
        )
        
        msg = f"""*QUICK BACKTEST RESULTS*

*Symbol:* BTCUSDT
*Timeframe:* 1h
*Strategy:* RSI

*Trades:* {result.total_trades}
*Win Rate:* {result.win_rate*100:.1f}%
*ROI/Year:* {result.roi_per_annum:.2f}%
*Sharpe:* {result.sharpe_ratio:.2f}
*Max DD:* {result.max_drawdown:.2f}%
*Profit Factor:* {result.profit_factor:.2f}

_Data from: Binance API_"""
        
        self.last_result = result
        return msg
    
    def run_full_backtest(self):
        """Full backtest with all symbols"""
        self.send_typing()
        self.send("Running FULL backtest...\n(This may take a few minutes)")
        
        from src.comprehensive_backtest import StrategyOptimizer, SYMBOLS, TIMEFRAMES
        
        self.engine = BacktestEngine()
        
        results = []
        symbols = ["BTCUSDT", "ETHUSDT"]  # Reduced for speed
        timeframes = ["1h", "4h"]
        strategies = [RSIStrategy, MACDStrategy, MovingAverageCrossover]
        
        for sym in symbols:
            for tf in timeframes:
                for strat_cls in strategies:
                    self.send_typing()
                    s = strat_cls()
                    r = self.engine.run_backtest(s, sym, tf, "2024-01-01", "2025-01-01")
                    if r.total_trades > 0:
                        results.append(r)
        
        if not results:
            return "No trades generated!"
        
        # Sort by ROI
        results.sort(key=lambda x: x.roi_per_annum, reverse=True)
        
        # Save all results to file
        results_data = []
        for r in results:
            results_data.append({
                'strategy': r.strategy_name,
                'symbol': r.symbol,
                'timeframe': r.timeframe,
                'trades': r.total_trades,
                'win_rate': round(r.win_rate * 100, 1),
                'roi_annum': round(r.roi_per_annum, 2),
                'sharpe': round(r.sharpe_ratio, 2),
                'max_dd': round(r.max_drawdown, 2),
                'profit_factor': round(r.profit_factor, 2)
            })
        
        # Save to JSON
        with open('storage/backtest_results.json', 'w') as f:
            json.dump(results_data, f, indent=2)
        
        # Build message - show ALL results
        msg = "*FULL BACKTEST RESULTS*\n\n"
        msg += f"Total: {len(results)} strategies\n"
        msg += f"Results saved to storage/backtest_results.json\n\n"
        
        for i, r in enumerate(results):
            msg += f"{i+1}. {r.strategy_name} {r.symbol} {r.timeframe}\n"
            msg += f"   ROI: {r.roi_per_annum:.1f}% | Sharpe: {r.sharpe_ratio:.2f}\n"
            msg += f"   Win: {r.win_rate*100:.0f}% | DD: {r.max_drawdown:.1f}%\n\n"
        
        msg += "_Data: Binance API_"
        return msg
    
    def run(self):
        if not self.token or not self.chat_id:
            print("Configure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
            return
        
        print("Bot running... Waiting for commands.")
        offset = None
        
        while True:
            updates = self.get_updates(offset)
            
            for u in updates:
                offset = u.get("update_id", 0) + 1
                msg = u.get("message", {})
                chat = msg.get("chat", {}).get("id")
                text = msg.get("text", "")
                
                if str(chat) != str(self.chat_id):
                    continue
                
                if text.startswith("/"):
                    parts = text.split()
                    cmd = parts[0]
                    args = parts[1:]
                    
                    print(f"Command: {cmd}")
                    resp = self.process_command(cmd, args)
                    self.send(resp)
            
            import time
            time.sleep(1)


if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()
