"""
Telegram Bot - Strategy Optimizer v3

Commands:
/start - Help
/set ASSET - Set target asset
/add STRATEGY PARAMS - Add new strategy
/optimize - Run optimization with learning
/results - Show results
/status - Show settings
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from comprehensive_backtest import (
    BacktestEngine, RSIStrategy, MACDStrategy, 
    MovingAverageCrossover, EMACrossStrategy, ATRStrategy, StochasticStrategy
)

class CustomStrategy:
    """Dynamic strategy that learns from data"""
    def __init__(self, params=None):
        self.params = params or {}
        self.name = self.params.get('name', 'Custom')
    
    def generate_signal(self, df):
        """Generate signal based on learned parameters"""
        if len(df) < 20:
            return 0
        
        # Use learned parameters
        period = self.params.get('period', 14)
        
        # Calculate moving average
        ma = df['close'].rolling(period).mean()
        std = df['close'].rolling(period).std()
        
        # Bollinger-like bands
        upper = ma + (std * 2)
        lower = ma - (std * 2)
        
        current = df['close'].iloc[-1]
        prev = df['close'].iloc[-2]
        
        # Signal based on price position
        if prev < lower.iloc[-2] and current > lower.iloc[-1]:
            return 1  # Buy
        elif prev > upper.iloc[-2] and current < upper.iloc[-1]:
            return -1  # Sell
        
        return 0


class OptimizerBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        raw_ids = os.getenv("TELEGRAM_CHAT_ID", "")
        self.chat_ids = [cid.strip() for cid in raw_ids.split(",") if cid.strip()]
        self.chat_id = self.chat_ids[0] if self.chat_ids else None
        self._active_chat_id = self.chat_id
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.engine = None
        self.target_roi = 20.0
        self.selected_asset = "BTCUSDT"
        self.custom_strategies = []
        self.counter_trade = False
        
        # Wizard state
        self.wizard_state = None  # None, 'asset', 'timeframe', 'strategies'
        self.wizard_data = {}
        self._waiting_for_pine_add = False  # True after bare /add command
        
        # Auto-scheduler
        self.auto_schedule = False
        self.schedule_interval = 5 * 60  # 5 minutes (change to 4 * 3600 for production)
        self.last_optimize_time = None
        self._auto_index = 0  # Tracks which strategy to optimize next (round-robin)
        
        # Custom Pine Script
        self.custom_pine_script = None
        
        # Process tracking
        self._is_running = False  # True when bot is executing a command
        self._current_process = None  # Name of current process
        self._process_start_time = None  # When current process started
        self._process_progress = None  # Progress info (e.g., "5/20")
        
        self.load_settings()
    
    def _storage_path(self, filename):
        """Get absolute path for a file in the storage directory"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        storage_dir = os.path.join(base_dir, '..', 'storage')
        os.makedirs(storage_dir, exist_ok=True)
        return os.path.join(storage_dir, filename)
    
    def _start_process(self, process_name, progress=None):
        """Mark the start of a process"""
        self._is_running = True
        self._current_process = process_name
        self._process_start_time = datetime.now()
        self._process_progress = progress
    
    def _update_progress(self, progress):
        """Update process progress"""
        self._process_progress = progress
    
    def _end_process(self):
        """Mark the end of a process"""
        self._is_running = False
        self._current_process = None
        self._process_start_time = None
        self._process_progress = None
    
    def load_settings(self):
        settings_file = self._storage_path('bot_settings.json')
        try:
            with open(settings_file, 'r') as f:
                s = json.load(f)
                self.selected_asset = s.get('selected_asset', 'BTCUSDT')
        except: pass
        
        custom_file = self._storage_path('custom_strategies.json')
        try:
            with open(custom_file, 'r') as f:
                self.custom_strategies = json.load(f)
        except: self.custom_strategies = {}
    
    def save_settings(self):
        settings_file = self._storage_path('bot_settings.json')
        with open(settings_file, 'w') as f:
            json.dump({'selected_asset': self.selected_asset}, f)
    
    def send(self, text, parse_mode="Markdown"):
        target = self._active_chat_id or self.chat_id
        if not self.token or not target:
            print("Telegram not configured")
            return False
        try:
            r = requests.post(f"{self.api_url}/sendMessage", json={
                "chat_id": target, "text": text, "parse_mode": parse_mode
            }, timeout=30)
            return r.status_code == 200
        except: return False
    
    def send_typing(self):
        if self.token:
            try:
                requests.post(f"{self.api_url}/sendChatAction",
                           json={"chat_id": self._active_chat_id or self.chat_id, "action": "typing"})
            except: pass
    
    def get_updates(self, offset=None):
        if not self.token:
            return []
        try:
            p = {"timeout": 60}
            if offset: p["offset"] = offset
            r = requests.get(f"{self.api_url}/getUpdates", params=p, timeout=65)
            return r.json().get("result", [])
        except: return []
    
    def process(self, cmd, args=None):
        cmd = (cmd or "").lower().strip("/")
        args = args or []
        
        if cmd == "namaste":
            return """Namaste ji! Swagat hai aapka.

Quick commands:
/run      - start instantly (BTC, ETH, SOL on best timeframes)
/results  - see saved results
/status   - check current settings
/help     - full command list"""

        elif cmd == "suno":
            return f"""*Ha ji! Bilkul ready hoon aapki seva mein!*

Asset: *{self.selected_asset}*  |  ROI target: *{self.target_roi}%*

Quick commands:
/run      - start instantly (BTC, ETH, SOL — no setup needed)
/results  - dekho saved results
/status   - current settings
/strategies - top strategies from CSVs
/optimize - run optimization
/help     - poori list dekho"""


        elif cmd in ("start", "hi", "hello"):
            return f"""*Trading Bot — Ready*

Asset: {self.selected_asset}  |  Target ROI: {self.target_roi}%

Send /help to see all commands."""

        elif cmd == "help":
            return """*All Commands*

━━━━━━━━━━━━━━━
SETUP
/set ASSET       — set asset (BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT)
/timeframe TF    — set timeframe (15m, 1h, 4h)
/wizard          — step-by-step guided setup

━━━━━━━━━━━━━━━
RUN STRATEGIES (BATCHES)
/strategies              — show top 20 results from all CSVs
/strategies ETHUSDT      — filter results for one asset
/strategies ETHUSDT 10   — top 10 results for that asset
/run                     — quick start: BTC+ETH+SOL on 15m/1h/4h (no setup)
/backtest                — run optimization on current selected asset

━━━━━━━━━━━━━━━
BATCH SHORTCUTS (1-20)
/batch1   — run batch 1 strategies
/batch2   — run batch 2 strategies
/batch3   — run batch 3 strategies
/batch4   — run batch 4 strategies
/batch5   — run batch 5 strategies
/batch1-5 — run batches 1 through 5
/batchall — run all 20 batches

━━━━━━━━━━━━━━━
OPTIMIZATION
/optimize        — compare built-in strategies (RSI, MACD, EMA, ATR, STOCH)
/learn           — auto-learn best RSI parameters from data

━━━━━━━━━━━━━━━
CUSTOM STRATEGIES
/add NAME p:v    — add strategy with params (e.g. /add MYRSI period:10)
/add             — then paste Pine Script in next message
/pine            — save a Pine Script (for reference)
/getpine         — view saved Pine Script

━━━━━━━━━━━━━━━
INFO & SETTINGS
/results         — show saved backtest results
/status          — show current config and saved files
/auto            — toggle auto-run every 5 min
/counter         — toggle counter-trade mode
/restart         — reload settings & reset bot state

━━━━━━━━━━━━━━━
EXAMPLES
/set ETHUSDT
/strategies BTCUSDT 15
/batch3
/batch1-5
/add BOLLINGER period:20 std:2"""

        elif cmd == "strategies":
            return self.run_batch_strategies(args)

        elif cmd.startswith("batch"):
            # /batch1  /batch3  /batch1-5  /batchall
            suffix = cmd[len("batch"):]   # e.g. "1", "1-5", "all", ""
            if not suffix:
                return "Usage: /batch1  /batch1-5  /batchall"
            return self.run_batch_strategies([suffix] + args)

        # Wizard commands
        elif cmd == "wizard":
            return self.start_wizard()
        
        elif cmd == "timeframe":
            return self.set_timeframe(args)
        
        elif cmd == "auto":
            return self.toggle_auto_schedule()
        
        # Handle wizard state
        elif self.wizard_state:
            return self.handle_wizard_input(cmd, args)
        
        elif cmd == "run":
            return self.run_quick()

        elif cmd == "backtest":
            if self.selected_asset:
                return self.run_optimization()
            return "Set asset first: /set ASSET"
        
        elif cmd == "counter":
            self.counter_trade = not self.counter_trade
            status = "ON" if self.counter_trade else "OFF"
            return f"[OK] Counter-trade mode: {status}"
        
        elif cmd == "restart":
            # Reload settings and reinitialize
            try:
                if hasattr(self, 'load_settings'):
                    self.load_settings()
                if hasattr(self, '_is_running'):
                    self._is_running = False
                if hasattr(self, '_current_process'):
                    self._current_process = None
                if hasattr(self, '_process_start_time'):
                    self._process_start_time = None
                if hasattr(self, '_process_progress'):
                    self._process_progress = None
                return "[OK] Bot restarted!\n\nSettings reloaded. Bot is ready."
            except Exception as e:
                return f"[ERROR] Restart failed: {str(e)}"
        
        elif cmd == "set":
            return self.set_asset(args)
        
        elif cmd == "add":
            return self.add_strategy(args)
        
        elif cmd == "status":
            import glob
            cs = self.custom_strategies
            if isinstance(cs, dict) and cs:
                strategies = "\n".join(f"  - {k}" for k in cs.keys())
            elif isinstance(cs, list) and cs:
                strategies = "\n".join(f"  - {s}" for s in cs)
            else:
                strategies = "  (none saved yet)"

            # Use absolute path for storage directory
            base_dir = os.path.dirname(os.path.abspath(__file__))
            storage_dir = os.path.join(base_dir, '..', 'storage')
            os.makedirs(storage_dir, exist_ok=True)
            
            # Check which result files exist
            result_files = []
            json_result = os.path.join(storage_dir, 'optimized_results.json')
            if os.path.exists(json_result):
                size = os.path.getsize(json_result)
                result_files.append(f"  ✅ storage/optimized_results.json  ({size // 1024} KB)")
            
            for f in ["all_assets_strategies_combined.csv"] + sorted(glob.glob("*_all_results.csv")):
                if os.path.exists(f):
                    size = os.path.getsize(f)
                    result_files.append(f"  ✅ {f}  ({size // 1024} KB)")
            results_str = "\n".join(result_files) if result_files else "  ❌ None — run /backtest first"

            interval_min = self.schedule_interval // 60
            auto_label = f"ON (every {interval_min} min)" if self.auto_schedule else "OFF"
            pine_saved = "✅ saved" if self.custom_pine_script else "None"

            # Check for ongoing processes
            if self._is_running and self._current_process:
                elapsed = ""
                if self._process_start_time:
                    elapsed_secs = (datetime.now() - self._process_start_time).total_seconds()
                    elapsed = f" ({int(elapsed_secs)}s ago)"
                progress_info = f" - {self._process_progress}" if self._process_progress else ""
                ongoing = f"\n⚡ Running  : {self._current_process}{progress_info}{elapsed}"
            else:
                ongoing = "\n⚡ Running  : None (idle)"

            return f"""*Bot Status*{ongoing}

Asset       : {self.selected_asset}
Target ROI  : {self.target_roi}%
Auto-run    : {auto_label}
Counter mode: {"ON" if self.counter_trade else "OFF"}
Pine Script : {pine_saved}

Custom Strategies:
{strategies}

Result Files:
{results_str}"""
        
        elif cmd == "optimize":
            return f"""*Ready to optimize?*

Current settings:
- Asset  : {self.selected_asset}
- Target : {self.target_roi}% ROI

What /optimize does:
  Runs 6 built-in Python strategies (RSI, MACD, EMA cross,
  MA crossover, ATR, Stochastic) on your selected asset and
  compares their ROI, win rate, and Sharpe ratio.
  The best performing strategy + params is saved as LEARNED.

What it does NOT do:
  It does not execute Pine Script code. Pine Script saved via
  /pine is stored for reference only (/getpine to view it).

Options:
1. /wizard  — custom setup (choose asset, timeframe, strategies)
2. /run     — start now with current settings ({self.selected_asset})
3. /set ETHUSDT — change asset first"""
        
        elif cmd == "learn":
            return self.learn_from_data()
        
        elif cmd == "results":
            return self.show_results()
        
        elif cmd == "pine":
            return self.handle_pine_script()
        
        elif cmd == "getpine":
            return self.get_pine_script()
        
        return f"Unknown: /{cmd}"
    
    def set_asset(self, args):
        if not args:
            return f"Current: {self.selected_asset}\n\n/set BTCUSDT"
        
        asset = args[0].upper()
        valid = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
        
        if asset not in valid:
            return f"Invalid. Use: {', '.join(valid)}"
        
        self.selected_asset = asset
        self.save_settings()
        return f"[OK] Asset set to {asset}"
    
    def set_timeframe(self, args):
        """Set timeframe"""
        if not args:
            return "Current: 1h\n\n/timeframe 1h"
        
        tf = args[0].lower()
        valid = ["15m", "1h", "4h", "1d"]
        
        if tf not in valid:
            return f"Invalid. Use: {', '.join(valid)}"
        
        self.wizard_data['timeframe'] = tf
        return f"[OK] Timeframe set to {tf}"
    
    def toggle_auto_schedule(self):
        """Toggle auto-schedule for 4-hour optimization"""
        self.auto_schedule = not self.auto_schedule
        
        if self.auto_schedule:
            self.last_optimize_time = datetime.now()
            return f"""*✅ Auto-Schedule Enabled!*

Bot will automatically run /backtest every 5 minutes.

Current settings:
- Asset     : {self.selected_asset}
- Target ROI: {self.target_roi}%

Use /auto again to disable.
Note: Bot must stay running for auto-schedule to work."""
        else:
            return "✅ Auto-schedule disabled."
    
    def run_batch_strategies(self, args=None):
        """Show strategy results from CSV files with full metrics."""
        import pandas as pd
        import glob

        args = args or []

        # ── Parse asset filter from args ──────────────────────────────────────
        asset_filter = None
        top_n = 20
        for a in args:
            a_up = a.upper()
            if a_up in ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
                        "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT"):
                asset_filter = a_up
            else:
                try:
                    top_n = int(a)
                except ValueError:
                    pass

        # ── Load result CSVs ──────────────────────────────────────────────────
        csv_files = sorted(glob.glob("*_all_results.csv"))
        combined_file = "all_assets_strategies_combined.csv"
        if os.path.exists(combined_file):
            csv_files = [combined_file] + [f for f in csv_files if f != combined_file]

        df = None
        source = ""
        for f in csv_files:
            try:
                tmp = pd.read_csv(f)
                if len(tmp) > 0:
                    df = tmp
                    source = f
                    break
            except Exception:
                continue

        if df is None or df.empty:
            return ("No result CSV files found.\n\n"
                    "Run strategy scripts first:\n"
                    "  python run_btc_strategies.py\n"
                    "  python run_eth_strategies.py\n"
                    "  (etc.)")

        # ── Normalise column names ────────────────────────────────────────────
        df.columns = [c.strip() for c in df.columns]

        # Map common variations to standard names
        col_map = {
            "Win_Rate_Percent": "win_rate",
            "Profit_Factor":    "profit_factor",
            "Max_Drawdown":     "drawdown",
            "Gross_Drawdown":   "gross_drawdown",
            "Net_Drawdown":     "net_drawdown",
            "Sharpe_Ratio":     "sharpe",
            "Total_Trades":     "trades",
            "Avg_Trade_Percent":"avg_trade",
            "roi":              "roi",
            "Strategy":         "strategy",
            "Asset":            "asset",
            "Timeframe":        "timeframe",
            "Performance_Grade":"grade",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        required = ["roi", "strategy"]
        if not all(c in df.columns for c in required):
            return f"CSV missing required columns. Found: {list(df.columns[:8])}"

        # ── Apply asset filter ────────────────────────────────────────────────
        if asset_filter and "asset" in df.columns:
            df = df[df["asset"].str.upper() == asset_filter]
            if df.empty:
                return f"No results for {asset_filter}."

        # ── Sort by ROI, keep profitable only ────────────────────────────────
        df = df[df["roi"] > 0].sort_values("roi", ascending=False).reset_index(drop=True)

        if df.empty:
            return "No profitable strategies found in results."

        top = df.head(top_n)

        # ── Build message ─────────────────────────────────────────────────────
        filter_label = f" — {asset_filter}" if asset_filter else " — All Assets"
        header = (f"TOP {len(top)} STRATEGIES{filter_label}\n"
                  f"Source: {source}  |  Total profitable: {len(df)}\n\n")

        rows = []
        for i, r in top.iterrows():
            rank        = i + 1
            name        = str(r.get("strategy", "?"))[:28]
            asset       = str(r.get("asset", "?"))
            tf          = str(r.get("timeframe", "?"))
            roi         = r.get("roi", 0)
            wr          = r.get("win_rate", 0)
            pf          = r.get("profit_factor", 0)
            gross_dd    = r.get("gross_drawdown", r.get("drawdown", 0))
            net_dd      = r.get("net_drawdown", 0)
            sharpe      = r.get("sharpe", 0)
            trades      = int(r.get("trades", 0))
            avg_trade   = r.get("avg_trade", 0)
            grade       = r.get("grade", "")

            row  = f"{rank:>2}. {name:<28} {asset} {tf}\n"
            row += f"    ROI      : {roi:>7.2f}%  |  Grade    : {grade}\n"
            row += f"    Win Rate : {wr:>6.1f}%  |  Gross DD : {gross_dd:.1f}%\n"
            row += f"    Prof.Fac : {pf:>6.2f}   |  Net DD   : {net_dd:.1f}%\n"
            row += f"    Trades   : {trades:>5}    |  Avg/Trade: {avg_trade:+.2f}%\n"
            rows.append(row)

        # Split into chunks ≤ 4000 chars and send mid-way if needed
        current = header
        for row in rows:
            if len(current) + len(row) + 1 > 3900:
                self.send(current)
                current = row
            else:
                current += "\n" + row
        return current
    
    def check_auto_schedule(self):
        """Check if it's time to run auto-optimization"""
        if not self.auto_schedule:
            return
        
        if not self.last_optimize_time:
            return
        
        # Check if 4 hours have passed
        elapsed = (datetime.now() - self.last_optimize_time).total_seconds()
        
        if elapsed >= self.schedule_interval:
            self.send("[AUTO] Running scheduled optimization...")
            try:
                self.run_optimization()
                self.last_optimize_time = datetime.now()
                self.send("[AUTO] Optimization complete! Next run in 5 minutes.")
            except Exception as e:
                self.send(f"[AUTO] Error: {str(e)}")
    
    def start_wizard(self):
        """Start interactive wizard"""
        self.wizard_state = 'asset'
        self.wizard_data = {}
        
        return """*🎯 WIZARD - Step 1 of 3*

Please enter the ASSET you want to trade:

Available:
- BTCUSDT
- ETHUSDT
- BNBUSDT
- SOLUSDT
- XRPUSDT

Reply with asset name (e.g., ETHUSDT)"""
    
    def handle_wizard_input(self, cmd, args):
        """Handle wizard input"""
        if cmd == "cancel":
            self.wizard_state = None
            self.wizard_data = {}
            return "[OK] Wizard cancelled. Send /wizard to start again."
        
        if self.wizard_state == 'asset':
            asset_input = (cmd + " " + " ".join(args)).upper().strip()
            valid = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
            
            # Parse assets
            if asset_input == "ALL":
                selected_assets = valid
            elif "," in asset_input:
                selected_assets = [a.strip() for a in asset_input.split(",")]
                for a in selected_assets:
                    if a not in valid:
                        return f"Invalid asset: {a}. Use: {', '.join(valid)}"
            else:
                if asset_input not in valid:
                    return f"Invalid. Use: {', '.join(valid)}, ALL, or multiple (ETHUSDT,BTCUSDT)"
                selected_assets = [asset_input]
            
            self.wizard_data['assets'] = selected_assets
            self.wizard_state = 'timeframe'
            
            asset_str = ", ".join(selected_assets) if len(selected_assets) <= 2 else f"{len(selected_assets)} assets"
            
            return f"""*✅ Step 1 Complete!*

Assets: {asset_str}

*🎯 Step 2 of 3*

Enter TIMEFRAME:
- 15m (15 minutes)
- 1h (1 hour)
- 4h (4 hours)
- 1d (1 day)

Options:
- ALL - Test all timeframes
- 1h,4h - Multiple timeframes (comma separated)

Reply with timeframe (e.g., 1h or ALL)"""
        
        elif self.wizard_state == 'timeframe':
            tf_input = cmd.lower()
            valid = ["15m", "1h", "4h", "1d"]
            
            # Parse timeframes
            if tf_input == "all":
                selected_tfs = valid
            elif "," in tf_input:
                selected_tfs = [t.strip() for t in tf_input.split(",")]
                for t in selected_tfs:
                    if t not in valid:
                        return f"Invalid timeframe: {t}. Use: {', '.join(valid)}"
            else:
                if tf_input not in valid:
                    return f"Invalid. Use: {', '.join(valid)}, ALL, or 1h,4h"
                selected_tfs = [tf_input]
            
            self.wizard_data['timeframes'] = selected_tfs
            self.wizard_state = 'strategies'
            
            assets_str = ", ".join(self.wizard_data['assets']) if len(self.wizard_data['assets']) <= 2 else f"{len(self.wizard_data['assets'])} assets"
            tf_str = ", ".join(selected_tfs) if len(selected_tfs) <= 2 else f"{len(selected_tfs)} timeframes"
            
            return f"""*✅ Step 2 Complete!*

Assets: {assets_str}
Timeframes: {tf_str}

*🎯 Step 3 of 3*

Enter STRATEGIES to test:

Built-in:
- RSI
- MACD
- MA (Moving Average)
- EMA
- ATR
- STOCH (Stochastic)

Options:
- ALL - Test all strategies
- RSI,MACD,EMA - Test specific (comma separated)

Reply with your choice (e.g., RSI,MACD or ALL)"""
        
        elif self.wizard_state == 'strategies':
            strategies_input = (cmd + " " + " ".join(args)).upper().strip()
            
            # Parse strategies
            if strategies_input == "ALL":
                selected = ["RSI", "MACD", "MA", "EMA", "ATR", "STOCH"]
            else:
                selected = [s.strip() for s in strategies_input.split(",")]
            
            # Save settings (use first asset)
            if self.wizard_data['assets']:
                self.selected_asset = self.wizard_data['assets'][0]
                self.save_settings()
            
            # Run optimization
            assets = self.wizard_data['assets']
            tfs = self.wizard_data['timeframes']
            
            self.wizard_state = None
            
            return self.run_optimization_wizard(assets, tfs, selected)
        
        return "Unknown state. Send /cancel to restart."
    
    def run_optimization_wizard(self, assets, timeframes, selected_strategies):
        """Run optimization with wizard settings - supports multiple assets/timeframes"""
        self._start_process("Wizard Optimization", "0%")
        
        # Build asset/timeframe string for display
        if len(assets) == 1:
            asset_display = assets[0]
        else:
            asset_display = f"{len(assets)} assets"
        
        if len(timeframes) == 1:
            tf_display = timeframes[0]
        else:
            tf_display = f"{len(timeframes)} timeframes"
        
        self.send(f"[START] Analyzing {asset_display} on {tf_display}...")
        
        self.engine = BacktestEngine()
        
        # Strategy mapping
        strategy_map = {
            "RSI": RSIStrategy,
            "MACD": MACDStrategy,
            "MA": MovingAverageCrossover,
            "EMA": EMACrossStrategy,
            "ATR": ATRStrategy,
            "STOCH": StochasticStrategy,
        }
        
        all_results = []
        
        # Calculate total combinations
        total = len(assets) * len(timeframes) * len(selected_strategies)
        done = 0
        
        # Loop through all combinations
        for asset in assets:
            for tf in timeframes:
                for strat_name in selected_strategies:
                    self.send_typing()
                    done += 1
                    self._update_progress(f"{done}/{total}")

                    # Check if custom
                    if strat_name in self.custom_strategies:
                        params = self.custom_strategies[strat_name]
                        if 'rsi_period' in params:
                            strat = RSIStrategy(params)
                        else:
                            strat = CustomStrategy(params)
                    else:
                        strat_cls = strategy_map.get(strat_name)
                        if not strat_cls:
                            continue
                        strat = strat_cls({})

                    result = self.engine.run_backtest(strat, asset, tf, "2024-01-01", "2025-01-01")

                    if result.total_trades > 5:
                        rec = {
                            'strategy': strat_name,
                            'symbol': asset,
                            'timeframe': tf,
                            'roi': result.roi_per_annum,
                            'roi_pct': result.total_return_pct,
                            'sharpe': result.sharpe_ratio,
                            'sortino': result.sortino_ratio,
                            'calmar': result.calmar_ratio,
                            'win_rate': result.win_rate * 100,
                            'drawdown': result.max_drawdown,
                            'drawdown_pct': result.max_drawdown_pct,
                            'gross_drawdown': result.gross_drawdown,
                            'gross_drawdown_pct': result.gross_drawdown_pct,
                            'net_drawdown': result.net_drawdown,
                            'net_drawdown_pct': result.net_drawdown_pct,
                            'trades': result.total_trades,
                            'wins': result.winning_trades,
                            'losses': result.losing_trades,
                            'profit_factor': result.profit_factor,
                            'avg_win': result.avg_win_pct,
                            'avg_loss': result.avg_loss_pct,
                            'counter': False,
                        }
                        score = self._score_result(rec)
                        rec['score'] = score
                        rec['grade'] = self._score_grade(score)
                        all_results.append(rec)

                        emoji = "✅" if result.roi_per_annum >= self.target_roi else "⚡"
                        self.send(f"[Run {done}] {emoji} {self._display_name(strat_name)} {asset} {tf}  Score:{score:.0f}\n"
                                  f"   ROI: {result.roi_per_annum:.2f}% | Win: {result.win_rate*100:.1f}%\n"
                                  f"   Sharpe: {result.sharpe_ratio:.2f} | Gross DD: {result.gross_drawdown:.1f}% | Net DD: {result.net_drawdown:.1f}%\n"
                                  f"   Trades: {result.total_trades} | PF: {result.profit_factor:.2f}")

                        # Counter-trade if negative
                        if result.roi_per_annum < 0:
                            self.send_typing()
                            result_ct = self.engine.run_backtest(strat, asset, tf, "2024-01-01", "2025-01-01", counter_trade=True)

                            if result_ct.total_trades > 5:
                                rec_ct = {
                                    'strategy': f"{strat_name} CTR",
                                    'symbol': asset,
                                    'timeframe': tf,
                                    'roi': result_ct.roi_per_annum,
                                    'roi_pct': result_ct.total_return_pct,
                                    'sharpe': result_ct.sharpe_ratio,
                                    'sortino': result_ct.sortino_ratio,
                                    'calmar': result_ct.calmar_ratio,
                                    'win_rate': result_ct.win_rate * 100,
                                    'drawdown': result_ct.max_drawdown,
                                    'drawdown_pct': result_ct.max_drawdown_pct,
                                    'gross_drawdown': result_ct.gross_drawdown,
                                    'gross_drawdown_pct': result_ct.gross_drawdown_pct,
                                    'net_drawdown': result_ct.net_drawdown,
                                    'net_drawdown_pct': result_ct.net_drawdown_pct,
                                    'trades': result_ct.total_trades,
                                    'wins': result_ct.winning_trades,
                                    'losses': result_ct.losing_trades,
                                    'profit_factor': result_ct.profit_factor,
                                    'avg_win': result_ct.avg_win_pct,
                                    'avg_loss': result_ct.avg_loss_pct,
                                    'counter': True,
                                }
                                score_ct = self._score_result(rec_ct)
                                rec_ct['score'] = score_ct
                                rec_ct['grade'] = self._score_grade(score_ct)
                                all_results.append(rec_ct)

                                emoji2 = "✅" if result_ct.roi_per_annum >= self.target_roi else "⚡"
                                self.send(f"[CTR] {emoji2} {self._display_name(strat_name)} CTR {tf}  Score:{score_ct:.0f}\n"
                                          f"   ROI: {result_ct.roi_per_annum:.2f}% | Win: {result_ct.win_rate*100:.1f}%\n"
                                          f"   PF: {result_ct.profit_factor:.2f}")
                    else:
                        self.send(f"[Run {done}] ❌ {self._display_name(strat_name)} {asset} {tf}: No trades")
        
        # Sort by score (same as run_optimization)
        all_results.sort(key=lambda x: x.get('score', x.get('roi', 0)), reverse=True)
        
        # Ensure storage directory exists and use absolute path
        storage_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'storage')
        os.makedirs(storage_dir, exist_ok=True)
        results_file = os.path.join(storage_dir, 'optimized_results.json')
        with open(results_file, 'w') as f:
            json.dump(all_results, f, indent=2)
        
        # Final message - show ALL results, grouped by asset/timeframe
        msg = f"\n*ANALYSIS COMPLETE*\n\n"
        msg += f"Assets: {asset_display}\n"
        msg += f"Timeframes: {tf_display}\n"
        base_results = [r for r in all_results if not r.get('counter', False)]
        ctr_results  = [r for r in all_results if r.get('counter', False)]
        msg += f"Strategies run  : {total} ({len(base_results)} with results, {len(ctr_results)} CTR)\n"
        msg += f"Target ROI: {self.target_roi}%\n\n"
        
        # Group by asset and timeframe
        from collections import defaultdict
        grouped = defaultdict(list)
        for r in all_results:
            key = f"{r['symbol']} {r['timeframe']}"
            grouped[key].append(r)
        
        # Show results for each combination
        for combo_key in sorted(grouped.keys()):
            results = grouped[combo_key]
            msg += f"=== {combo_key} ===\n"
            for i, r in enumerate(results[:3]):  # Top 3 per combo
                msg += (f"{i+1}. {self._display_name(r['strategy'])}: "
                        f"ROI {r['roi']:.2f}% | Score:{r.get('score',0):.0f} ({r.get('grade','?')}) | "
                        f"Win: {r['win_rate']:.1f}% | PF: {r.get('profit_factor', 0):.2f}\n")
            msg += "\n"
        
        self.send(msg)
        self._end_process()
        
        return msg
    
    def _parse_pine_to_params(self, pine_code):
        """
        Extract usable parameters from Pine Script code.
        Looks for:
          - input.int / input.float / input() declarations
          - ta.rsi / ta.ema / ta.macd / ta.bb usage
          - strategy.entry stop_loss / take_profit
          - strategy() title for the name
        Returns a dict of params compatible with custom_strategies.
        """
        import re
        params = {}

        # Strategy/indicator name
        name_match = re.search(r'(?:strategy|indicator)\s*\(\s*["\']([^"\']+)["\']', pine_code)
        params['name'] = name_match.group(1) if name_match else 'PineStrategy'

        # input.int / input.float / input declarations
        # e.g.  rsiLen = input.int(14, "RSI Length")
        #        fastLen = input(9, "Fast EMA")
        input_matches = re.findall(
            r'(\w+)\s*=\s*input(?:\.int|\.float|\.source|\.bool|\.string|\.color)?\s*\(([^,\)]+)',
            pine_code
        )
        for var, default in input_matches:
            default = default.strip().strip('"\'')
            try:
                val = int(default)
            except ValueError:
                try:
                    val = float(default)
                except ValueError:
                    continue
            # map common variable names to standard keys
            key = var.lower()
            if any(x in key for x in ('rsi', 'rsi_len', 'rsilen', 'rsi_period')):
                params['rsi_period'] = val
            elif any(x in key for x in ('fast', 'short', 'ema_fast')):
                params['fast_period'] = val
            elif any(x in key for x in ('slow', 'long', 'ema_slow')):
                params['slow_period'] = val
            elif any(x in key for x in ('over_sold', 'oversold', 'os')):
                params['oversold'] = val
            elif any(x in key for x in ('over_bought', 'overbought', 'ob')):
                params['overbought'] = val
            elif any(x in key for x in ('period', 'length', 'len')):
                params.setdefault('period', val)
            elif any(x in key for x in ('stop', 'sl', 'stoploss')):
                params['stop_loss'] = val / 100 if val > 1 else val
            elif any(x in key for x in ('profit', 'tp', 'takeprofit')):
                params['take_profit'] = val / 100 if val > 1 else val
            else:
                params[key] = val

        # Detect which indicator family this script uses
        if re.search(r'ta\.rsi|rsi\(', pine_code, re.IGNORECASE):
            params.setdefault('type', 'RSI')
            params.setdefault('rsi_period', 14)
        if re.search(r'ta\.macd|macd\(', pine_code, re.IGNORECASE):
            params.setdefault('type', 'MACD')
        if re.search(r'ta\.ema|ema\(', pine_code, re.IGNORECASE):
            params.setdefault('type', 'EMA')
            params.setdefault('fast_period', 9)
            params.setdefault('slow_period', 21)
        if re.search(r'ta\.bb|bollinger|bb_upper|bb_lower', pine_code, re.IGNORECASE):
            params.setdefault('type', 'BOLLINGER')
            params.setdefault('period', 20)
        if re.search(r'ta\.stoch|stoch\(', pine_code, re.IGNORECASE):
            params.setdefault('type', 'STOCH')

        # strategy.exit stop_loss / take_profit (in points or percent)
        sl_match = re.search(r'stop_loss\s*=\s*([0-9.]+)', pine_code)
        tp_match = re.search(r'take_profit\s*=\s*([0-9.]+)', pine_code)
        if sl_match:
            val = float(sl_match.group(1))
            params['stop_loss'] = val / 100 if val > 1 else val
        if tp_match:
            val = float(tp_match.group(1))
            params['take_profit'] = val / 100 if val > 1 else val

        params['source'] = 'pine_script'
        return params

    def add_strategy(self, args):
        """Add custom strategy with parameters or Pine Script code"""
        # Rejoin args to check if this is Pine Script pasted inline
        full_text = ' '.join(args)
        is_pine = '@version' in full_text or 'strategy(' in full_text or 'indicator(' in full_text

        if is_pine:
            self._waiting_for_pine_add = False
            return self._add_from_pine(full_text)

        if len(args) < 2:
            self._waiting_for_pine_add = True   # next message = Pine Script
            return """*Format: /add NAME param1:value1 param2:value2*

Examples:
/add MYRSI period:10 threshold:0.03
/add BOLLINGER period:20 std:2
/add MYSTRAT period:14 oversold:25 overbought:75

Or just paste your Pine Script code now (next message) ↓"""

        name = args[0].upper()
        params = {'name': name}

        for arg in args[1:]:
            if ':' in arg:
                k, v = arg.split(':', 1)
                try:
                    params[k] = int(v)
                except ValueError:
                    try:
                        params[k] = float(v)
                    except ValueError:
                        params[k] = v

        self.custom_strategies[name] = params

        with open(self._storage_path('custom_strategies.json'), 'w') as f:
            json.dump(self.custom_strategies, f, indent=2)

        msg = f"[OK] Strategy '{name}' added!\nParams: {params}\n\nRun /backtest to test"
        return msg

    def _add_from_pine(self, pine_code):
        """Parse Pine Script and register it as a custom strategy with extracted params."""
        import re
        params = self._parse_pine_to_params(pine_code)
        name   = params.get('name', 'PineStrategy')
        key    = re.sub(r'[^A-Za-z0-9_]', '_', name).upper()

        # Save raw code too
        self.custom_pine_script = pine_code
        params['pine_code_preview'] = pine_code[:300]

        self.custom_strategies[key] = params
        with open(self._storage_path('custom_strategies.json'), 'w') as f:
            json.dump(self.custom_strategies, f, indent=2)

        # Build summary of what was extracted
        extracted = {k: v for k, v in params.items()
                     if k not in ('name', 'source', 'pine_code_preview')}
        extracted_str = '\n'.join(f"  {k}: {v}" for k, v in extracted.items()) or '  (no inputs found)'

        return f"""*✅ Pine Script parsed and added!*

Strategy name : {name}
Stored as key : {key}

Parameters extracted from your script:
{extracted_str}

Saved to storage/custom_strategies.json

Next steps:
- /backtest  — run backtest with these parameters on {self.selected_asset}
- /getpine   — view the saved Pine Script
- /status    — see all saved strategies

⚠️ The bot runs Python backtests — it uses the extracted parameters
   above (period, rsi_period, stop_loss etc.) to simulate your strategy.
   If the logic looks wrong, override with /add {key} period:X rsi_period:Y"""

    def learn_from_data(self):
        """Learn optimal parameters from historical data"""
        asset = self.selected_asset
        self.send_typing()
        
        self.send(f"[LEARNING] Analyzing {asset} data...")
        self.engine = BacktestEngine()
        
        # Fetch data
        df = self.engine.get_cached_data(asset, "1h", "2024-01-01", "2025-01-01")
        
        if df.empty or len(df) < 100:
            return f"[ERROR] Not enough data for {asset}"
        
        # Analyze price movements
        returns = df['close'].pct_change().dropna()
        
        # Learn optimal parameters
        best_params = {}
        
        # Find best RSI period
        best_roi = -999
        for period in [7, 10, 14, 21, 28]:
            # Test this period
            params = {'rsi_period': period, 'oversold': 30, 'overbought': 70}
            strat = RSIStrategy(params)
            result = self.engine.run_backtest(strat, asset, "1h", "2024-01-01", "2025-01-01")
            
            if result.total_trades > 5:
                score = result.roi_per_annum - (result.max_drawdown * 0.5)
                if score > best_roi:
                    best_roi = score
                    best_params['rsi_period'] = period
        
        # Learn threshold based on volatility
        volatility = returns.std()
        best_params['threshold'] = round(volatility * 2, 4)
        
        # Learn optimal stop loss
        avg_loss = returns[returns < 0].mean()
        best_params['stop_loss'] = round(abs(avg_loss) * 1.5, 4)
        
        # Learn take profit
        avg_win = returns[returns > 0].mean()
        best_params['take_profit'] = round(avg_win * 2, 4)
        
        rsi_period = best_params.get('rsi_period', 14)
        best_params['type'] = 'RSI'
        best_params['name'] = f"RSI {asset} p{rsi_period}"

        # Save under a unique asset-specific key (not the generic 'LEARNED')
        strat_key = f"RSI_{asset}_P{rsi_period}"
        self.custom_strategies[strat_key] = best_params
        with open(self._storage_path('custom_strategies.json'), 'w') as f:
            json.dump(self.custom_strategies, f, indent=2)

        # Validate — test the learned params
        strat = RSIStrategy(best_params)
        result = self.engine.run_backtest(strat, asset, "1h", "2024-01-01", "2025-01-01")

        return f"""*[LEARN COMPLETE] - {asset}*

Strategy saved as: {strat_key}
(RSI strategy tuned on {asset} 1h data)

Learned Parameters:
- RSI Period : {rsi_period}
- Stop Loss  : {best_params.get('stop_loss', 0.02)}
- Take Profit: {best_params.get('take_profit', 0.04)}

Validation Backtest:
- ROI/Year   : {result.roi_per_annum:.2f}%
- Win Rate   : {result.win_rate*100:.1f}%
- Sharpe     : {result.sharpe_ratio:.2f}
- Drawdown   : {result.max_drawdown*100:.1f}%
- Trades     : {result.total_trades}

Run /backtest to run it with all other strategies."""
    
    # ── Scoring ──────────────────────────────────────────────────────────────

    def _display_name(self, name):
        """Convert stored key (AI_EMA_RIBBON_AGGRESSOR) to readable name (AI EMA RIBBON AGGRESSOR)."""
        return str(name).replace('_', ' ').strip()

    def _score_result(self, r):
        """
        Composite score 0–100.
        ROI 35% | Win Rate 20% | Profit Factor 20% | Drawdown 15% | Sharpe 10%
        """
        roi   = r.get('roi', 0)
        wr    = r.get('win_rate', 0)          # already in %
        pf    = r.get('profit_factor', 0)
        dd    = r.get('drawdown_pct', r.get('drawdown', 0)) or 0
        if dd < 1:                            # stored as fraction (0.15) → convert
            dd = dd * 100
        sharpe = r.get('sharpe', 0)

        score = (
            min(max(roi, 0), 300) / 300 * 35 +   # ROI: 0–35 pts (capped 300%)
            min(wr, 100)          / 100 * 20 +   # Win Rate: 0–20 pts
            min(max(pf, 0), 5)    / 5   * 20 +   # PF: 0–20 pts (capped 5)
            max(0, 1 - dd / 100)        * 15 +   # Drawdown: 0–15 pts (lower=better)
            min(max(sharpe, 0), 3) / 3  * 10     # Sharpe: 0–10 pts (capped 3)
        )
        return round(score, 2)

    def _score_grade(self, score):
        if score >= 80: return "A+"
        if score >= 65: return "A"
        if score >= 50: return "B+"
        if score >= 35: return "B"
        if score >= 20: return "C"
        return "D"

    # ── Random parameter generation ───────────────────────────────────────────

    def _random_params(self, strat_type):
        """Return a random parameter dict for the given strategy type."""
        import random
        strat_type = strat_type.upper()
        if strat_type == "RSI":
            return {
                'rsi_period':  random.choice([7, 10, 14, 21, 28]),
                'oversold':    random.choice([20, 25, 30, 35]),
                'overbought':  random.choice([65, 70, 75, 80]),
                'stop_loss':   random.choice([0.01, 0.015, 0.02, 0.025, 0.03]),
                'take_profit': random.choice([0.03, 0.05, 0.07, 0.10, 0.12]),
            }
        if strat_type == "MACD":
            fast = random.choice([8, 12, 21])
            slow = random.choice([21, 26, 50])
            if slow <= fast:
                slow = fast + 10
            return {
                'fast_period':   fast,
                'slow_period':   slow,
                'signal_period': random.choice([7, 9, 13]),
                'stop_loss':     random.choice([0.01, 0.015, 0.02, 0.025]),
                'take_profit':   random.choice([0.03, 0.05, 0.08, 0.10]),
            }
        if strat_type == "EMA":
            fast = random.choice([5, 8, 13, 21])
            slow = random.choice([20, 34, 55])
            if slow <= fast:
                slow = fast + 15
            return {
                'fast_period': fast,
                'slow_period': slow,
                'stop_loss':   random.choice([0.01, 0.015, 0.02]),
                'take_profit': random.choice([0.03, 0.05, 0.08]),
            }
        if strat_type == "MA":
            short = random.choice([10, 20, 50])
            long  = random.choice([50, 100, 200])
            if long <= short:
                long = short * 3
            return {
                'short_period': short,
                'long_period':  long,
                'stop_loss':    random.choice([0.01, 0.02, 0.03]),
                'take_profit':  random.choice([0.04, 0.06, 0.10]),
            }
        if strat_type == "ATR":
            return {
                'period':     random.choice([10, 14, 20]),
                'multiplier': random.choice([1.5, 2.0, 2.5, 3.0]),
                'stop_loss':  random.choice([0.01, 0.015, 0.02]),
                'take_profit':random.choice([0.03, 0.05, 0.08]),
            }
        if strat_type == "STOCH":
            return {
                'k_period':  random.choice([5, 9, 14]),
                'd_period':  random.choice([3, 5]),
                'oversold':  random.choice([15, 20, 25]),
                'overbought':random.choice([75, 80, 85]),
                'stop_loss': random.choice([0.01, 0.015, 0.02]),
                'take_profit':random.choice([0.03, 0.05, 0.08]),
            }
        return {}

    # ── Load / merge best results ─────────────────────────────────────────────

    def _load_best_results(self):
        """Load saved best results keyed by strategy|asset|timeframe."""
        try:
            with open(self._storage_path('optimized_results.json'), 'r') as f:
                data = json.load(f)
            return {f"{r['strategy']}|{r.get('symbol','?')}|{r['timeframe']}": r
                    for r in data if isinstance(r, dict)}
        except Exception:
            return {}

    def _merge_and_save(self, new_results, best_map):
        """
        For each new result, keep it only if its score beats the saved best
        for that strategy+asset+timeframe combination.
        Returns (saved_count, improved_count, summary_lines).
        """
        saved = 0
        improved = 0
        summary = []

        for r in new_results:
            key   = f"{r['strategy']}|{r.get('symbol','?')}|{r['timeframe']}"
            score = self._score_result(r)
            r['score'] = score
            r['grade'] = self._score_grade(score)

            existing = best_map.get(key)
            if existing is None:
                best_map[key] = r
                saved += 1
            elif score > existing.get('score', 0):
                old_score = existing.get('score', 0)
                best_map[key] = r
                improved += 1
                summary.append(
                    f"  {self._display_name(r['strategy'])} {r['timeframe']}: "
                    f"score {old_score:.1f} → {score:.1f} "
                    f"(ROI {r['roi']:.1f}%)"
                )
            # else: existing is better, discard new result

        # Persist - use absolute path for storage directory
        storage_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'storage')
        os.makedirs(storage_dir, exist_ok=True)
        results_file = os.path.join(storage_dir, 'optimized_results.json')
        all_best = sorted(best_map.values(), key=lambda x: x.get('score', 0), reverse=True)
        with open(results_file, 'w') as f:
            json.dump(all_best, f, indent=2)

        return saved, improved, summary

    def run_quick(self):
        """
        Zero-config quick run: tests the 3 best assets (BTC, ETH, SOL)
        on their 3 best timeframes (15m, 1h, 4h) using randomised params.
        No setup needed — just /run and go.
        """
        self._start_process("Quick Run", "0%")
        
        assets     = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        timeframes = ["15m", "1h", "4h"]

        self.send("[QUICK RUN] Starting — BTC, ETH, SOL on 15m / 1h / 4h...")
        self.engine = BacktestEngine()

        strategies = [
            (RSIStrategy,           "RSI"),
            (MACDStrategy,          "MACD"),
            (EMACrossStrategy,      "EMA"),
        ]

        best_map = self._load_best_results()
        all_new  = []
        total    = len(assets) * len(timeframes) * len(strategies)
        done     = 0
        ctr_count = 0

        def _make_rec(strat_name, asset, tf, params, result, is_ctr=False):
            name = f"{strat_name} CTR" if is_ctr else strat_name
            return {
                'strategy':     name,
                'symbol':       asset,
                'timeframe':    tf,
                'params':       params,
                'roi':          result.roi_per_annum,
                'roi_pct':      result.total_return_pct,
                'sharpe':       result.sharpe_ratio,
                'sortino':      result.sortino_ratio,
                'calmar':       result.calmar_ratio,
                'win_rate':     result.win_rate * 100,
                'drawdown':     result.max_drawdown,
                'drawdown_pct': result.max_drawdown_pct,
                'gross_drawdown': result.gross_drawdown,
                'gross_drawdown_pct': result.gross_drawdown_pct,
                'net_drawdown': result.net_drawdown,
                'net_drawdown_pct': result.net_drawdown_pct,
                'trades':       result.total_trades,
                'wins':         result.winning_trades,
                'losses':       result.losing_trades,
                'profit_factor':result.profit_factor,
                'avg_win':      result.avg_win_pct,
                'avg_loss':     result.avg_loss_pct,
                'counter':      is_ctr,
            }

        for asset in assets:
            for tf in timeframes:
                for strat_cls, strat_name in strategies:
                    self.send_typing()
                    done += 1
                    self._update_progress(f"{done}/{total}")
                    params = self._random_params(strat_name)
                    strat  = strat_cls(params)
                    result = self.engine.run_backtest(strat, asset, tf, "2024-01-01", "2025-01-01")

                    if result.total_trades > 5:
                        rec   = _make_rec(strat_name, asset, tf, params, result)
                        score = self._score_result(rec)
                        rec['score'] = score
                        rec['grade'] = self._score_grade(score)
                        all_new.append(rec)
                        emoji = "✅" if result.roi_per_annum >= self.target_roi else "⚡"
                        self.send(f"[Run {done}/{total}] {emoji} {asset} {tf} {self._display_name(strat_name)}  Score:{score:.0f}\n"
                                  f"   ROI:{result.roi_per_annum:.1f}%  Win:{result.win_rate*100:.1f}%  "
                                  f"PF:{result.profit_factor:.2f}  Gross DD:{result.gross_drawdown:.1f}%  Net DD:{result.net_drawdown:.1f}%")

                        if result.roi_per_annum < 0:
                            self.send_typing()
                            res_ct = self.engine.run_backtest(strat, asset, tf, "2024-01-01", "2025-01-01", counter_trade=True)
                            if res_ct.total_trades > 5:
                                rec_ct   = _make_rec(strat_name, asset, tf, params, res_ct, is_ctr=True)
                                score_ct = self._score_result(rec_ct)
                                rec_ct['score'] = score_ct
                                rec_ct['grade'] = self._score_grade(score_ct)
                                all_new.append(rec_ct)
                                ctr_count += 1
                                emoji2 = "✅" if res_ct.roi_per_annum >= self.target_roi else "⚡"
                                self.send(f"[CTR] {emoji2} {self._display_name(strat_name)} CTR {asset} {tf}  Score:{score_ct:.0f}\n"
                                          f"   ROI:{res_ct.roi_per_annum:.1f}%  PF:{res_ct.profit_factor:.2f}")
                    else:
                        self.send(f"[Run {done}/{total}] ❌ {asset} {tf} {self._display_name(strat_name)}: No trades")

        saved, improved, summary = self._merge_and_save(all_new, best_map)

        base_count = len(all_new) - ctr_count
        msg  = f"\nQUICK RUN COMPLETE\n\n"
        msg += f"Assets     : BTC, ETH, SOL\n"
        msg += f"Timeframes : 15m, 1h, 4h\n"
        msg += f"Strategies : RSI, MACD, EMA\n"
        msg += f"Runs       : {total} ({base_count} results, {ctr_count} CTR)\n"
        msg += f"Improved   : {improved} all-time bests updated\n\n"

        top5 = sorted(best_map.values(), key=lambda x: x.get('score', 0), reverse=True)[:5]
        msg += "TOP 5 ALL-TIME (by score):\n"
        for i, r in enumerate(top5, 1):
            dd = r.get('drawdown_pct', r.get('drawdown', 0) * 100)
            msg += (f"{i}. {self._display_name(r['strategy'])} {r.get('symbol','?')} {r['timeframe']}  "
                    f"Score:{r.get('score',0):.0f} ({r.get('grade','?')})\n"
                    f"   ROI:{r['roi']:.1f}%  Win:{r['win_rate']:.1f}%  DD:{dd:.1f}%\n")

        self.send(msg)
        self._end_process()
        return msg

    def run_optimization(self):
        """Run optimization ONE strategy at a time (round-robin).
        Each /auto cycle picks the next strategy, tests it across timeframes
        with fresh random params, scores it, and moves on.
        Next cycle picks the next strategy — so every 6 cycles, all strategies
        have been re-tested with new params."""
        self._start_process("Optimization", "0%")
        
        asset = self.selected_asset
        self.engine = BacktestEngine()
        timeframes = ["1h", "4h"]

        all_strategies = [
            (RSIStrategy,           "RSI"),
            (MACDStrategy,          "MACD"),
            (MovingAverageCrossover,"MA"),
            (EMACrossStrategy,      "EMA"),
            (ATRStrategy,           "ATR"),
            (StochasticStrategy,    "STOCH"),
        ]

        # Add custom strategies to the rotation
        cs = self.custom_strategies
        custom_list = []
        if isinstance(cs, dict):
            for name, params in cs.items():
                custom_list.append((name, params))

        total_pool = len(all_strategies) + len(custom_list)
        idx = self._auto_index % total_pool
        self._auto_index += 1  # Advance for next run

        best_map = self._load_best_results()
        all_new  = []
        ctr_count = 0

        if idx < len(all_strategies):
            # Built-in strategy
            strat_cls, strat_name = all_strategies[idx]
            self.send(f"[OPTIMIZE] {self._display_name(strat_name)} on {asset} — trying new params "
                      f"(strategy {idx + 1}/{total_pool})...")

            def _make_record(sname, params, result, tf, is_ctr=False):
                name = f"{sname} CTR" if is_ctr else sname
                return {
                    'strategy': name, 'symbol': asset, 'timeframe': tf,
                    'params': params,
                    'roi': result.roi_per_annum, 'roi_pct': result.total_return_pct,
                    'sharpe': result.sharpe_ratio, 'sortino': result.sortino_ratio,
                    'calmar': result.calmar_ratio, 'win_rate': result.win_rate * 100,
                    'drawdown': result.max_drawdown, 'drawdown_pct': result.max_drawdown_pct,
                    'gross_drawdown': result.gross_drawdown, 'gross_drawdown_pct': result.gross_drawdown_pct,
                    'net_drawdown': result.net_drawdown, 'net_drawdown_pct': result.net_drawdown_pct,
                    'trades': result.total_trades, 'wins': result.winning_trades,
                    'losses': result.losing_trades, 'profit_factor': result.profit_factor,
                    'avg_win': result.avg_win_pct, 'avg_loss': result.avg_loss_pct,
                    'counter': is_ctr,
                }

            for run_num, tf in enumerate(timeframes, 1):
                self.send_typing()
                self._update_progress(f"Strategy {idx+1}/{total_pool}, TF {run_num}/{len(timeframes)}")
                params = self._random_params(strat_name)
                strat  = strat_cls(params)
                result = self.engine.run_backtest(strat, asset, tf, "2024-01-01", "2025-01-01")

                if result.total_trades > 5:
                    rec   = _make_record(strat_name, params, result, tf)
                    score = self._score_result(rec)
                    rec['score'] = score
                    rec['grade'] = self._score_grade(score)
                    all_new.append(rec)

                    emoji = "✅" if result.roi_per_annum >= self.target_roi else "⚡"
                    p_str = f"RSI={params.get('rsi_period', params.get('fast_period', '?'))}"
                    self.send(f"[{tf}] {emoji} {self._display_name(strat_name)}  Score:{score:.0f}\n"
                              f"   Params: {p_str} SL={params.get('stop_loss','?')} TP={params.get('take_profit','?')}\n"
                              f"   ROI:{result.roi_per_annum:.1f}% Win:{result.win_rate*100:.1f}% "
                              f"PF:{result.profit_factor:.2f} Gross DD:{result.gross_drawdown:.1f}% Net DD:{result.net_drawdown:.1f}%")

                    # Counter-trade if negative ROI
                    if result.roi_per_annum < 0:
                        self.send_typing()
                        result_ct = self.engine.run_backtest(strat, asset, tf, "2024-01-01", "2025-01-01", counter_trade=True)
                        if result_ct.total_trades > 5:
                            rec_ct   = _make_record(strat_name, params, result_ct, tf, is_ctr=True)
                            score_ct = self._score_result(rec_ct)
                            rec_ct['score'] = score_ct
                            rec_ct['grade'] = self._score_grade(score_ct)
                            all_new.append(rec_ct)
                            ctr_count += 1
                            emoji2 = "✅" if result_ct.roi_per_annum >= self.target_roi else "⚡"
                            self.send(f"[CTR {tf}] {emoji2} {self._display_name(strat_name)} CTR  Score:{score_ct:.0f}\n"
                                      f"   ROI:{result_ct.roi_per_annum:.1f}% Win:{result_ct.win_rate*100:.1f}% "
                                      f"PF:{result_ct.profit_factor:.2f}")
                else:
                    self.send(f"[{tf}] ❌ {self._display_name(strat_name)}: No trades")

        else:
            # Custom strategy turn
            custom_idx = idx - len(all_strategies)
            name, params = custom_list[custom_idx]
            self.send(f"[OPTIMIZE] Custom: {self._display_name(name)} on {asset} — trying new params "
                      f"(strategy {idx + 1}/{total_pool})...")

            def _make_record(sname, params, result, tf, is_ctr=False):
                rname = f"{sname} CTR" if is_ctr else sname
                return {
                    'strategy': rname, 'symbol': asset, 'timeframe': tf,
                    'params': params,
                    'roi': result.roi_per_annum, 'roi_pct': result.total_return_pct,
                    'sharpe': result.sharpe_ratio, 'sortino': result.sortino_ratio,
                    'calmar': result.calmar_ratio, 'win_rate': result.win_rate * 100,
                    'drawdown': result.max_drawdown, 'drawdown_pct': result.max_drawdown_pct,
                    'trades': result.total_trades, 'wins': result.winning_trades,
                    'losses': result.losing_trades, 'profit_factor': result.profit_factor,
                    'avg_win': result.avg_win_pct, 'avg_loss': result.avg_loss_pct,
                    'counter': is_ctr,
                }

            strat_type = params.get('type', 'RSI')
            for tf in timeframes:
                self.send_typing()
                rand_p = {**params, **self._random_params(strat_type)}
                strat  = RSIStrategy(rand_p) if 'rsi_period' in rand_p else CustomStrategy(rand_p)
                result = self.engine.run_backtest(strat, asset, tf, "2024-01-01", "2025-01-01")
                if result.total_trades > 5:
                    rec   = _make_record(name, rand_p, result, tf)
                    score = self._score_result(rec)
                    rec['score'] = score
                    rec['grade'] = self._score_grade(score)
                    all_new.append(rec)
                    emoji = "✅" if result.roi_per_annum >= self.target_roi else "⚡"
                    self.send(f"[{tf}] {emoji} {self._display_name(name)}  Score:{score:.0f}\n"
                              f"   ROI:{result.roi_per_annum:.1f}% Win:{result.win_rate*100:.1f}%")

        # Merge with all-time best and save
        saved, improved, summary = self._merge_and_save(all_new, best_map)

        # Determine which strategy is next
        next_idx = self._auto_index % total_pool
        if next_idx < len(all_strategies):
            next_name = all_strategies[next_idx][1]
        else:
            next_name = custom_list[next_idx - len(all_strategies)][0]

        base_count = len(all_new) - ctr_count
        msg  = f"\nRUN COMPLETE\n\n"
        msg += f"Tested          : {base_count} timeframe(s), {ctr_count} CTR\n"
        msg += f"New entries     : {saved}\n"
        msg += f"Improved scores : {improved}\n"
        msg += f"Next up         : {self._display_name(next_name)}\n\n"
        if summary:
            msg += "Improvements:\n" + "\n".join(summary[:5]) + "\n\n"

        top5 = sorted(best_map.values(), key=lambda x: x.get('score', 0), reverse=True)[:5]
        msg += "ALL-TIME TOP 5:\n"
        for i, r in enumerate(top5, 1):
            dd = r.get('drawdown_pct', r.get('drawdown', 0) * 100)
            msg += (f"{i}. {self._display_name(r['strategy'])} {r['timeframe']}  "
                    f"Score:{r.get('score',0):.0f} ({r.get('grade','?')})\n"
                    f"   ROI:{r['roi']:.1f}% Win:{r['win_rate']:.1f}% "
                    f"PF:{r.get('profit_factor',0):.2f} DD:{dd:.1f}%\n")

        self.send(msg)
        self._end_process()
        return msg
    
    def show_results(self):
        import glob
        import pandas as pd
        
        # Use absolute path for storage directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
        storage_dir = os.path.join(base_dir, '..', 'storage')
        os.makedirs(storage_dir, exist_ok=True)
        
        # First, try optimized_results.json
        results = []
        source  = ""
        json_files = [os.path.join(storage_dir, 'optimized_results.json'), 
                      os.path.join(storage_dir, 'custom_strategies.json')]
        for fname in json_files:
            if os.path.exists(fname):
                try:
                    with open(fname, 'r') as f:
                        data = json.load(f)
                    if isinstance(data, list) and data:
                        results = data
                        source  = os.path.basename(fname)
                        break
                    elif isinstance(data, dict) and data:
                        # custom_strategies dict — show as strategy list
                        msg = f"*Saved Strategies* (from {os.path.basename(fname)})\n\n"
                        for k, v in list(data.items())[:10]:
                            msg += f"  {k}: {v}\n"
                        msg += "\nRun /backtest to get ROI results."
                        return msg
                except Exception as e:
                    return f"Error reading {fname}: {e}"

        # If no JSON results, try CSV files
        if not results:
            csv_files = sorted(glob.glob("*_all_results.csv"))
            combined_file = "all_assets_strategies_combined.csv"
            if os.path.exists(combined_file):
                csv_files = [combined_file] + [f for f in csv_files if f != combined_file]
            
            for f in csv_files:
                try:
                    df = pd.read_csv(f)
                    if len(df) > 0:
                        results = df.to_dict('records')
                        source = f
                        break
                except: continue

        if not results:
            return ("No results yet.\n\n"
                    "Run /backtest (or /run) to generate results first.\n"
                    "Then /results will show ROI, win rate, and drawdown.")

        # Sort by score if available, else by ROI
        results.sort(key=lambda x: x.get('score', x.get('roi', 0)), reverse=True)

        msg = f"ALL-TIME BEST RESULTS (by score)\nSource: {source}\n\n"
        for i, r in enumerate(results[:10]):
            score = r.get('score')
            grade = r.get('grade', '?')
            dd    = r.get('drawdown_pct', r.get('drawdown', 0))
            gross_dd = r.get('gross_drawdown_pct', r.get('gross_drawdown', 0))
            net_dd = r.get('net_drawdown_pct', r.get('net_drawdown', 0))
            if dd and dd < 1:
                dd = dd * 100
            if gross_dd and gross_dd < 1:
                gross_dd = gross_dd * 100
            if net_dd and net_dd < 1:
                net_dd = net_dd * 100
            score_str = f"Score:{score:.0f} ({grade})" if score is not None else "Score:n/a"
            params = r.get('params', {})
            p_str  = "  ".join(f"{k}={v}" for k, v in list(params.items())[:3]) if params else "default"
            msg += (f"{i+1}. {self._display_name(r.get('strategy','?'))} {r.get('timeframe','?')}  {score_str}\n"
                    f"   ROI:{r.get('roi',0):.1f}%  Win:{r.get('win_rate',0):.1f}%  "
                    f"PF:{r.get('profit_factor',0):.2f}  Gross DD:{gross_dd:.1f}%  Net DD:{net_dd:.1f}%\n"
                    f"   Params: {p_str}\n\n")
        return msg
    
    def handle_pine_script(self):
        """Handle Pine Script code submission - expects code in next message"""
        return """*📝 Pine Script Upload*

Paste your Pine Script v5 code in the next message.
I'll validate it and save it for backtesting.

Note: Only basic validation is performed.
For full backtesting, use TradingView's native tools."""
    
    def get_pine_script(self):
        """Return the saved Pine Script"""
        if not self.custom_pine_script:
            return "No custom Pine Script saved. Use /pine to add one."
        
        return f"""*📊 Saved Pine Script*

{self.custom_pine_script[:3000]}"""
    
    def handle_text_message(self, text):
        """Handle regular text messages - check for Pine Script code"""
        # If user sent /add alone, treat the very next message as Pine Script
        if self._waiting_for_pine_add and text and not text.startswith('/'):
            self._waiting_for_pine_add = False
            return self._add_from_pine(text)

        # Check if it looks like Pine Script
        if text and ('@version' in text or 'strategy(' in text or 'indicator(' in text):
            # Save raw Pine Script code
            self.custom_pine_script = text

            # Extract strategy name from: strategy("My Name", ...)
            import re
            name_match = re.search(r'(?:strategy|indicator)\s*\(\s*["\']([^"\']+)["\']', text)
            name = name_match.group(1) if name_match else "PineScript_Strategy"

            # Sanitise name for use as a dict key (no spaces/special chars)
            key = re.sub(r'[^A-Za-z0-9_]', '_', name).upper()

            # Also register it in custom_strategies so /optimize can see it
            self.custom_strategies[key] = {
                "name": name,
                "source": "pine_script",
                "pine_code": text[:500],   # first 500 chars for reference
            }
            with open(self._storage_path('custom_strategies.json'), 'w') as f:
                json.dump(self.custom_strategies, f, indent=2)

            return f"""*✅ Pine Script Saved!*

Strategy name : {name}
Stored as key : {key}
Script length : {len(text)} characters

Saved to:
  • storage/custom_strategies.json  (key: {key})
  • /getpine  — to view the full script

⚠️ Note: /optimize runs Python backtests (RSI, MACD, EMA etc.)
   Pine Script is stored for reference — it is not executed by the bot.
   To backtest this logic, re-implement it via /add with parameters."""

        return None  # Not handled
    
    def run(self):
        if not self.token or not self.chat_ids:
            print("Configure TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID")
            return
        
        print(f"Bot running. Asset: {self.selected_asset}")
        print("Commands: /wizard, /set, /add, /optimize, /learn, /results, /status, /pine, /getpine")
        
        # Welcome message only sent when user sends /start or /help
        
        offset = None
        
        while True:
            try:
                # Check auto-schedule
                self.check_auto_schedule()
                
                try:
                    updates = self.get_updates(offset)
                except Exception as e:
                    print(f"Get updates error: {e}")
                    updates = []
                
                for u in updates:
                    try:
                        offset = u.get("update_id", 0) + 1
                        msg = u.get("message", {})
                        incoming_chat_id = str(msg.get("chat", {}).get("id"))
                        if incoming_chat_id not in self.chat_ids:
                            continue
                        self._active_chat_id = incoming_chat_id
                        
                        parts = (msg.get("text") or "").split()
                        cmd = parts[0] if parts else ""
                        args = parts[1:]
                        
                        print(f"Command: {cmd}")
                        
                        try:
                            text = msg.get("text", "") or ""
                            # Pine Script check FIRST — //@version=5 starts with /
                            # but is not a bot command
                            is_pine = (
                                '@version' in text or
                                'strategy(' in text or
                                'indicator(' in text
                            )
                            if is_pine:
                                pine_resp = self.handle_text_message(text)
                                if pine_resp:
                                    self.send(pine_resp)
                            elif cmd.startswith('/'):
                                resp = self.process(cmd, args)
                                self.send(resp)
                            # plain text that is not Pine Script → silently ignore
                        except Exception as e:
                            print(f"Process error: {e}")
                            self.send(f"Error: {str(e)}")
                    except Exception as e:
                        print(f"Update error: {e}")
            
            except Exception as e:
                print(f"Loop error: {e}")
            
            import time
            time.sleep(1)


if __name__ == "__main__":
    OptimizerBot().run()
