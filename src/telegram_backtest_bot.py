"""
Telegram Bot for Backtesting Results

This module provides a Telegram bot interface to:
1. Receive commands to trigger backtesting/optimization
2. Send backtest results automatically to Telegram
3. Allow users to check current strategy parameters
4. Provide trade analysis summaries

Commands:
/start - Welcome message and help
/backtest [symbol] [batch] - Run batch backtest (e.g. /backtest BTCUSDT_15m 1)
/comprehensive - Run full comprehensive backtest (all symbols × timeframes)
/optimize - Run strategy optimization
/params - Show current strategy parameters
/stats - Show trade statistics
/status - Show bot status
/results - Show last backtest results
"""

import os
import sys
import json
import random
import logging
import threading
import requests
from datetime import datetime
from typing import Dict, Any, List, Tuple

from dotenv import load_dotenv

load_dotenv()

# Add project root to path so we can import from root-level modules
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Import our optimizer modules
from src.backtest_optimizer import (
    TradeAnalyzer,
    TRADES_FILE,
    OPTIMIZED_PARAMS_FILE,
)
from src.auto_optimizer import AutoOptimizer, OptimizedStrategyManager

# Import batch runner helpers (root-level script)
from run_strategies_batch import (
    run_batch_strategies,
    load_data,
    calculate_indicators,
    apply_strategy,
    run_backtest as _batch_run_backtest,
    DATA_FILES,
)
from strategies import get_strategies_by_batch, get_all_strategies

# Import comprehensive backtest engine
from src.comprehensive_backtest import (
    run_comprehensive_backtest,
    SYMBOLS,
    TIMEFRAMES,
    START_DATE,
    END_DATE,
)

# Multi-year historical data fetcher
from src.data_fetcher import DataFetcher

# AI brain (optional — disabled gracefully if ANTHROPIC_API_KEY is missing)
try:
    from src.brain import TradingBrain
    _BRAIN_AVAILABLE = True
except ImportError:
    _BRAIN_AVAILABLE = False

# File that persists the user's default trade symbol + batch across restarts
_DEFAULT_TRADE_FILE = os.path.join(_ROOT, "storage", "default_trade.json")

# ── Auto-optimization thresholds ──────────────────────────────────────────────
# Trigger optimization when EITHER condition is true after a backtest:
_POOR_PROFITABLE_PCT = 20.0   # fewer than 20 % of strategies are profitable
_POOR_BEST_ROI       = 20.0   # best single-strategy ROI is below 20 %

# How many years of historical data to use when optimizing (1–5)
_OPT_LOOKBACK_YEARS = 3

# Parameter search space for SL / TP / Trailing-Stop random search
_SL_CANDIDATES  = [0.010, 0.015, 0.020, 0.025, 0.030, 0.040, 0.050]
_TP_CANDIDATES  = [0.020, 0.030, 0.040, 0.050, 0.060, 0.080, 0.100, 0.150]
_TS_CANDIDATES  = [0.005, 0.010, 0.015, 0.020, 0.025, 0.030]
_OPT_TRIALS     = 40   # random combinations to try per optimization run

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram message length limit
_TG_LIMIT = 4000


class TelegramBacktestBot:
    """Telegram bot for backtesting and optimization results."""

    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        raw_ids = os.getenv("TELEGRAM_CHAT_ID", "")
        # Support comma-separated list: TELEGRAM_CHAT_ID=-111,-222
        self.chat_ids = [cid.strip() for cid in raw_ids.split(",") if cid.strip()]
        self.chat_id = self.chat_ids[0] if self.chat_ids else None  # primary (for sending)
        self._active_chat_id: str = self.chat_id  # updated per-message, used by workers
        self.api_url = f"https://api.telegram.org/bot{self.token}"

        # Track running jobs so we don't start duplicates
        self._running: Dict[str, threading.Thread] = {}
        # Store last backtest results
        self._last_results: List[dict] = []
        # Years of historical data used for optimization (configurable via /optdata)
        self._opt_lookback_years: int = _OPT_LOOKBACK_YEARS
        # Default trade: symbol + batches (persisted to disk)
        self._default_symbol: str = "BTCUSDT_15m"
        self._default_batches: List[int] = [1]
        self._load_default_trade()

        # AI brain — disabled silently if ANTHROPIC_API_KEY is missing
        self._brain = None
        if _BRAIN_AVAILABLE:
            try:
                self._brain = TradingBrain()
                logger.info("AI brain initialized successfully")
            except ValueError as e:
                logger.warning(f"AI brain disabled: {e}")

        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN not found in environment")
        if not self.chat_ids:
            logger.warning("TELEGRAM_CHAT_ID not found in environment")

    # ------------------------------------------------------------------ #
    # Default trade persistence
    # ------------------------------------------------------------------ #

    def _load_default_trade(self) -> None:
        """Load default symbol/batches from disk (if previously saved)."""
        if not os.path.exists(_DEFAULT_TRADE_FILE):
            return
        try:
            with open(_DEFAULT_TRADE_FILE) as f:
                data = json.load(f)
            symbol = data.get("symbol", "BTCUSDT_15m").upper()
            batches = data.get("batches", [1])
            if symbol in DATA_FILES and isinstance(batches, list) and batches:
                self._default_symbol = symbol
                self._default_batches = batches
        except Exception as e:
            logger.warning(f"Could not load default trade: {e}")

    def _save_default_trade(self) -> None:
        """Persist current default symbol/batches to disk."""
        try:
            os.makedirs(os.path.dirname(_DEFAULT_TRADE_FILE), exist_ok=True)
            with open(_DEFAULT_TRADE_FILE, "w") as f:
                json.dump(
                    {"symbol": self._default_symbol, "batches": self._default_batches},
                    f, indent=2,
                )
        except Exception as e:
            logger.warning(f"Could not save default trade: {e}")

    # ------------------------------------------------------------------ #
    # Telegram API helpers
    # ------------------------------------------------------------------ #

    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Send a message to the active Telegram chat (auto-splits if too long)."""
        target = self._active_chat_id or self.chat_id
        if not self.token or not target:
            logger.error("Telegram bot not configured")
            return False

        # Split into chunks if over limit
        chunks = [text[i:i + _TG_LIMIT] for i in range(0, len(text), _TG_LIMIT)]
        url = f"{self.api_url}/sendMessage"
        ok = True
        for chunk in chunks:
            payload = {
                "chat_id": target,
                "text": chunk,
                "parse_mode": parse_mode,
            }
            try:
                r = requests.post(url, json=payload, timeout=30)
                if r.status_code != 200:
                    ok = False
            except Exception as e:
                logger.error(f"Failed to send Telegram message: {e}")
                ok = False
        return ok

    def send_typing_action(self) -> None:
        """Send typing indicator."""
        target = self._active_chat_id or self.chat_id
        if not self.token or not target:
            return
        try:
            requests.post(
                f"{self.api_url}/sendChatAction",
                json={"chat_id": target, "action": "typing"},
                timeout=10,
            )
        except Exception:
            pass

    def get_updates(self, offset: int = None, timeout: int = 60) -> list:
        """Long-poll for new messages."""
        if not self.token:
            return []
        params = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        try:
            r = requests.get(
                f"{self.api_url}/getUpdates", params=params, timeout=timeout + 5
            )
            data = r.json()
            if data.get("ok"):
                return data.get("result", [])
        except Exception as e:
            logger.error(f"Failed to get updates: {e}")
        return []

    # ------------------------------------------------------------------ #
    # Command dispatcher
    # ------------------------------------------------------------------ #

    def process_command(self, command: str, args: list = None) -> str:
        """Process a bot command and return the immediate response text."""
        command = command.lower().strip("/").split("@")[0]
        args = args or []

        if command in ("start", "help"):
            return self._get_help_message()
        elif command == "backtest":
            return self._start_batch_backtest(args)
        elif command == "comprehensive":
            return self._start_comprehensive_backtest()
        elif command == "optimize":
            return self._run_optimization()
        elif command == "params":
            return self._get_current_params()
        elif command == "stats":
            return self._get_trade_stats()
        elif command == "status":
            return self._get_bot_status()
        elif command == "results":
            return self._get_last_results()
        elif command == "apply" and args:
            return self._apply_params(args)
        elif command == "optdata":
            return self._set_opt_lookback(args)
        elif command == "setdefault":
            return self._set_default_trade(args)
        elif command == "ask":
            return self._ask_brain(args)
        elif command == "analyze":
            return self._analyze_last_results()
        else:
            return f"Unknown command: /{command}\nUse /help for available commands."

    # ------------------------------------------------------------------ #
    # Help
    # ------------------------------------------------------------------ #

    def _get_help_message(self) -> str:
        symbols = "\n".join(f"  • `{k}`" for k in DATA_FILES.keys())
        default_batch_str = self._format_batches(self._default_batches)
        return (
            "*Trading Bot Backtest Commands*\n\n"
            "*Default Trade (used when no args given):*\n"
            f"  Symbol : `{self._default_symbol}`\n"
            f"  Batches: `{default_batch_str}`\n"
            "/setdefault `<symbol>` `[batch]` — change default\n"
            "  Examples:\n"
            "    `/setdefault BTCUSDT_15m 1`\n"
            "    `/setdefault ETHUSDT_1h 1-3`\n"
            "    `/setdefault BNBUSDT_15m all`\n\n"
            "*Backtesting:*\n"
            "/backtest — run with default symbol & batch\n"
            "/backtest `<symbol>` `<batch>` — run specific\n"
            "  Examples:\n"
            "    `/backtest BTCUSDT_15m 1`\n"
            "    `/backtest ETHUSDT_1h 1-3`\n"
            "    `/backtest BNBUSDT_15m all`\n\n"
            "/comprehensive — full backtest (all symbols × timeframes)\n\n"
            f"*Available symbols:*\n{symbols}\n\n"
            "*Analysis & Optimization:*\n"
            "/optimize — run genetic-algorithm optimization\n"
            "/params   — show current strategy parameters\n"
            "/stats    — trade statistics from trades.jsonl\n"
            "/results  — show last backtest summary\n"
            "/status   — bot status\n\n"
            "*Parameter Tuning:*\n"
            "/apply `<rsi_len>` `<oversold>` `<overbought>`\n"
            "  Example: `/apply 12 35 65`\n\n"
            "*Optimization Data Window:*\n"
            f"/optdata `<years>` — set years of history for optimization (1–5)\n"
            f"  Current: `{self._opt_lookback_years}` year(s)\n"
            "  Example: `/optdata 3`\n\n"
            "*AI Brain:*\n"
            f"Status: `{'enabled' if self._brain else 'disabled (set ANTHROPIC_API_KEY)'}`\n"
            "/ask `<question>` — ask the AI anything about the bot or strategies\n"
            "  Example: `/ask What is the best strategy for BTC?`\n"
            "/analyze — AI analysis of the last backtest results"
        )

    # ------------------------------------------------------------------ #
    # Batch backtest (local parquet data)
    # ------------------------------------------------------------------ #

    def _start_batch_backtest(self, args: list) -> str:
        """Parse args and kick off batch backtest in a background thread."""
        # Use the user-configured default when no args are given
        symbol = self._default_symbol
        batches: List[int] = list(self._default_batches)

        if args:
            # First arg might be symbol or batch number
            first = args[0].upper()
            if first in DATA_FILES:
                symbol = first
                args = args[1:]
            elif first not in DATA_FILES and not any(c.isdigit() for c in first):
                return (
                    f"Unknown symbol `{args[0]}`.\n"
                    f"Available: {', '.join(DATA_FILES.keys())}"
                )

        if args:
            batch_arg = args[0].upper()
            if batch_arg == "ALL":
                batches = list(range(1, 21))
            elif "-" in batch_arg:
                try:
                    a, b = batch_arg.split("-")
                    batches = list(range(int(a), int(b) + 1))
                except ValueError:
                    return "Invalid batch range. Example: `1-3`"
            else:
                try:
                    batches = [int(batch_arg)]
                except ValueError:
                    return "Invalid batch number. Use 1-20 or `all`."

        job_key = f"batch_{symbol}"
        if job_key in self._running and self._running[job_key].is_alive():
            return f"A backtest on `{symbol}` is already running. Please wait."

        t = threading.Thread(
            target=self._batch_backtest_worker,
            args=(symbol, batches),
            daemon=True,
        )
        self._running[job_key] = t
        t.start()

        return (
            f"*Backtest started!*\n"
            f"Symbol : `{symbol}`\n"
            f"Batches: `{batches}`\n\n"
            "_Results will be sent when complete..._"
        )

    def _batch_backtest_worker(self, symbol: str, batches: List[int]) -> None:
        """Worker: runs batches sequentially, auto-optimizes if results are poor."""
        all_results = []

        for batch_num in batches:
            self.send_message(f"_Running batch {batch_num} on {symbol}..._")
            try:
                results = run_batch_strategies(data_key=symbol, batch_num=batch_num)
                if results:
                    all_results.extend(results)
            except Exception as e:
                self.send_message(f"Batch {batch_num} error: `{e}`")

        # Store for /results
        self._last_results = all_results

        if not all_results:
            self.send_message("No strategies produced results.")
            return

        all_results.sort(key=lambda x: x.get("roi", 0), reverse=True)
        self._send_backtest_summary(symbol, batches, all_results, label="BACKTEST COMPLETE")

        # ── AI brain analysis ─────────────────────────────────────────────
        if self._brain:
            try:
                self.send_message("_AI brain analysing results..._")
                insight = self._brain.analyze_backtest(all_results, symbol, batches)
                self.send_message(f"*AI Analysis:*\n{insight}")
            except Exception as e:
                logger.warning(f"Brain analysis failed: {e}")

        # ── Auto-optimization check ───────────────────────────────────────
        poor, reason = self._is_poor_results(all_results)
        if poor:
            self.send_message(
                f"*Results below threshold* ({reason})\n"
                "_Auto-optimizing parameters — please wait..._"
            )
            improved, best_params = self._auto_optimize_params(symbol, batches, all_results)
            if improved:
                improved.sort(key=lambda x: x.get("roi", 0), reverse=True)
                self._last_results = improved
                self._send_backtest_summary(
                    symbol, batches, improved,
                    label="AFTER AUTO-OPTIMIZATION"
                )
                # ── AI brain: compare before vs after optimization ────────
                if self._brain and best_params:
                    try:
                        insight = self._brain.analyze_optimization(
                            all_results, improved, best_params
                        )
                        self.send_message(f"*AI Optimization Analysis:*\n{insight}")
                    except Exception as e:
                        logger.warning(f"Brain opt analysis failed: {e}")
            else:
                self.send_message("_Auto-optimization did not improve results._")

        # CSV notice
        csv_path = os.path.join(_ROOT, "batch_backtest_results.csv")
        if os.path.exists(csv_path):
            self.send_message("_Full results saved to_ `batch_backtest_results.csv`")

    # ------------------------------------------------------------------ #
    # Auto-optimization helpers
    # ------------------------------------------------------------------ #

    def _is_poor_results(self, results: List[dict]) -> Tuple[bool, str]:
        """Return (True, reason) when results meet the 'poor' threshold."""
        if not results:
            return True, "no strategies produced results"
        profitable = [r for r in results if r.get("roi", 0) > 0]
        profitable_pct = len(profitable) / len(results) * 100
        best_roi = max(r.get("roi", 0) for r in results)
        if profitable_pct < _POOR_PROFITABLE_PCT:
            return True, f"only {profitable_pct:.0f}% of strategies are profitable"
        if best_roi < _POOR_BEST_ROI:
            return True, f"best ROI is only {best_roi:.2f}% (threshold: {_POOR_BEST_ROI}%)"
        return False, ""

    def _fetch_opt_data(self, symbol_key: str):
        """
        Fetch multi-year OHLCV data for optimization.
        Falls back to the local parquet if the Binance fetch fails.
        Returns a DataFrame with indicators already calculated, or None.
        """
        from datetime import timedelta

        # Parse "BTCUSDT_15m" → symbol="BTCUSDT", timeframe="15m"
        parts = symbol_key.rsplit("_", 1)
        if len(parts) != 2:
            return None
        binance_symbol, timeframe = parts[0], parts[1]

        end_dt   = datetime.now()
        start_dt = end_dt - timedelta(days=self._opt_lookback_years * 365)
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str   = end_dt.strftime("%Y-%m-%d")

        self.send_message(
            f"_Fetching {self._opt_lookback_years} year(s) of `{binance_symbol}` "
            f"`{timeframe}` data for optimization ({start_str} → {end_str})..._"
        )

        try:
            fetcher = DataFetcher(cache_enabled=True)
            df = fetcher.fetch_with_pagination(
                symbol=binance_symbol,
                timeframe=timeframe,
                start_date=start_str,
                end_date=end_str,
            )
            if df is not None and not df.empty:
                return calculate_indicators(df)
        except Exception as e:
            logger.warning(f"Multi-year fetch failed: {e} — falling back to local data")

        # Fallback: use the local parquet file
        df_raw = load_data(symbol_key)
        if df_raw is not None:
            return calculate_indicators(df_raw)
        return None

    def _set_opt_lookback(self, args: list) -> str:
        """Handle /optdata <years> command."""
        if not args:
            return (
                f"*Optimization lookback: `{self._opt_lookback_years}` year(s)*\n\n"
                "Change with `/optdata <years>` (1–5)\n"
                "Example: `/optdata 3`"
            )
        try:
            years = int(args[0])
            if not 1 <= years <= 5:
                return "Years must be between 1 and 5. Example: `/optdata 3`"
            self._opt_lookback_years = years
            return (
                f"*Optimization lookback set to `{years}` year(s).*\n"
                "_The next auto-optimization will use this window._"
            )
        except ValueError:
            return "Invalid value. Example: `/optdata 3`"

    # ------------------------------------------------------------------ #
    # Default trade
    # ------------------------------------------------------------------ #

    @staticmethod
    def _format_batches(batches: List[int]) -> str:
        """Format a batch list as a compact string, e.g. [1,2,3] → '1-3' or '1,5'."""
        if not batches:
            return "1"
        if len(batches) == 1:
            return str(batches[0])
        if batches == list(range(batches[0], batches[-1] + 1)):
            return f"{batches[0]}-{batches[-1]}"
        return ",".join(str(b) for b in batches)

    def _set_default_trade(self, args: list) -> str:
        """Handle /setdefault <symbol> [batch] command."""
        if not args:
            batch_str = self._format_batches(self._default_batches)
            return (
                f"*Current default trade:*\n"
                f"  Symbol : `{self._default_symbol}`\n"
                f"  Batches: `{batch_str}`\n\n"
                "Change with `/setdefault <symbol> [batch]`\n"
                "Examples:\n"
                "  `/setdefault BTCUSDT_15m 1`\n"
                "  `/setdefault ETHUSDT_1h 1-3`\n"
                "  `/setdefault BNBUSDT_15m all`"
            )

        symbol = args[0].upper()
        if symbol not in DATA_FILES:
            available = "\n".join(f"  • `{k}`" for k in DATA_FILES.keys())
            return f"Unknown symbol `{symbol}`.\n\nAvailable:\n{available}"

        # Parse optional batch argument
        batches: List[int] = [1]
        if len(args) > 1:
            batch_arg = args[1].upper()
            if batch_arg == "ALL":
                batches = list(range(1, 21))
            elif "-" in batch_arg:
                try:
                    a, b = batch_arg.split("-")
                    batches = list(range(int(a), int(b) + 1))
                except ValueError:
                    return "Invalid batch range. Example: `/setdefault BTCUSDT_15m 1-3`"
            else:
                try:
                    batches = [int(batch_arg)]
                except ValueError:
                    return "Invalid batch. Example: `/setdefault BTCUSDT_15m 1`"

        self._default_symbol = symbol
        self._default_batches = batches
        self._save_default_trade()

        batch_str = self._format_batches(batches)
        return (
            f"*Default trade updated!*\n\n"
            f"  Symbol : `{symbol}`\n"
            f"  Batches: `{batch_str}`\n\n"
            "_Just send `/backtest` to run with these settings._"
        )

    # ------------------------------------------------------------------ #
    # AI brain commands
    # ------------------------------------------------------------------ #

    def _ask_brain(self, args: list) -> str:
        """Handle /ask <question> — forward to TradingBrain."""
        if not self._brain:
            return (
                "AI brain is disabled.\n"
                "Set `ANTHROPIC_API_KEY` in your `.env` file to enable it."
            )
        if not args:
            return "Usage: `/ask <your question>`\nExample: `/ask What is the best BTC strategy?`"
        question = " ".join(args)
        try:
            self.send_typing_action()
            bot_context = {
                "default_symbol": self._default_symbol,
                "opt_years": self._opt_lookback_years,
                "last_results": self._last_results,
            }
            return self._brain.answer_question(question, bot_context)
        except Exception as e:
            logger.error(f"Brain /ask failed: {e}")
            return f"AI brain error: `{e}`"

    def _analyze_last_results(self) -> str:
        """Handle /analyze — AI analysis of the most recent backtest."""
        if not self._brain:
            return (
                "AI brain is disabled.\n"
                "Set `ANTHROPIC_API_KEY` in your `.env` file to enable it."
            )
        if not self._last_results:
            return "No backtest results yet. Run `/backtest` first."
        try:
            self.send_typing_action()
            return self._brain.analyze_backtest(
                self._last_results, self._default_symbol, self._default_batches
            )
        except Exception as e:
            logger.error(f"Brain /analyze failed: {e}")
            return f"AI brain error: `{e}`"

    def _auto_optimize_params(
        self, symbol: str, batches: List[int], original_results: List[dict]
    ) -> List[dict]:
        """
        Random-search over stop_loss / take_profit / trailing_stop using
        multi-year historical data. Re-runs all batches with the best-found
        combination and returns the improved result list.
        """
        # Fetch multi-year data (with Binance pagination + local fallback)
        df_ind = self._fetch_opt_data(symbol)
        if df_ind is None:
            return [], {}

        # Collect strategy definitions for the requested batches
        strategy_defs = []
        for b in batches:
            strategy_defs.extend(get_strategies_by_batch(b))

        # Take up to 8 best original strategies as the evaluation set
        top_names = {r["name"] for r in original_results[:8]}
        eval_strategies = [s for s in strategy_defs if s["name"] in top_names]
        if not eval_strategies:
            eval_strategies = strategy_defs[:8]

        best_score = max(r.get("roi", 0) for r in original_results[:8])
        best_params: Dict[str, float] = {}

        for _ in range(_OPT_TRIALS):
            sl = random.choice(_SL_CANDIDATES)
            tp = random.choice(_TP_CANDIDATES)
            ts = random.choice(_TS_CANDIDATES)

            # TP must be at least 1.5× SL to maintain positive expectancy
            if tp < sl * 1.5:
                continue

            trial_rois = []
            for strat in eval_strategies:
                try:
                    df_copy = apply_strategy(
                        df_ind.copy(),
                        strat["strategies"],
                        strat.get("min_agreement", 1),
                    )
                    _, trades = _batch_run_backtest(df_copy, sl, tp, ts)
                    if len(trades) >= 5:
                        from run_strategies_batch import INITIAL_CAPITAL
                        final_cap = sum(t["pnl"] for t in trades) + INITIAL_CAPITAL
                        roi = (final_cap - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
                        trial_rois.append(roi)
                except Exception:
                    continue

            if not trial_rois:
                continue
            avg_roi = sum(trial_rois) / len(trial_rois)
            if avg_roi > best_score:
                best_score = avg_roi
                best_params = {"stop_loss": sl, "take_profit": tp, "trailing_stop": ts}

        if not best_params:
            return [], {}

        self.send_message(
            f"*Best parameters found:*\n"
            f"  Stop-Loss    : `{best_params['stop_loss']*100:.1f}%`\n"
            f"  Take-Profit  : `{best_params['take_profit']*100:.1f}%`\n"
            f"  Trailing-Stop: `{best_params['trailing_stop']*100:.1f}%`\n\n"
            "_Re-running all batches with optimized parameters..._"
        )

        # Re-run all batches with optimized params applied to every strategy
        improved_results = []
        from run_strategies_batch import INITIAL_CAPITAL
        for b in batches:
            strats = get_strategies_by_batch(b)
            for strat in strats:
                try:
                    df_copy = apply_strategy(
                        df_ind.copy(),
                        strat["strategies"],
                        strat.get("min_agreement", 1),
                    )
                    final_cap, trades = _batch_run_backtest(
                        df_copy,
                        best_params["stop_loss"],
                        best_params["take_profit"],
                        best_params["trailing_stop"],
                    )
                    if len(trades) >= 5:
                        wins = [t for t in trades if t["pnl"] > 0]
                        win_rate = len(wins) / len(trades) * 100
                        roi = (final_cap - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
                        improved_results.append({
                            "id": strat["id"],
                            "name": strat["name"],
                            "strategies": ", ".join(strat["strategies"]),
                            "trades": len(trades),
                            "wins": len(wins),
                            "losses": len(trades) - len(wins),
                            "win_rate": round(win_rate, 2),
                            "roi": round(roi, 2),
                            "final_capital": round(final_cap, 2),
                            "opt_sl": best_params["stop_loss"],
                            "opt_tp": best_params["take_profit"],
                            "opt_ts": best_params["trailing_stop"],
                        })
                except Exception:
                    continue

        return improved_results, best_params

    def _send_backtest_summary(
        self, symbol: str, batches: List[int], results: List[dict], label: str
    ) -> None:
        """Format and send a backtest results summary to Telegram."""
        profitable = [r for r in results if r.get("roi", 0) > 0]
        msg = (
            f"*{label}*\n"
            f"Symbol    : `{symbol}`\n"
            f"Batches   : `{batches}`\n"
            f"Tested    : {len(results)} strategies\n"
            f"Profitable: {len(profitable)}"
            f" ({len(profitable)/len(results)*100:.0f}%)\n"
            f"Best ROI  : {results[0].get('roi', 0):.2f}%\n\n"
            "*Top 15 Strategies (by ROI %):*\n"
            "```\n"
            f"{'ID':<4} {'Name':<22} {'Trades':<7} {'Win%':<7} {'ROI%'}\n"
            f"{'-'*55}\n"
        )
        for r in results[:15]:
            msg += (
                f"{str(r['id']):<4} "
                f"{r['name'][:22]:<22} "
                f"{r['trades']:<7} "
                f"{r['win_rate']:<7} "
                f"{r['roi']}\n"
            )
        msg += "```"
        self.send_message(msg)

    # ------------------------------------------------------------------ #
    # Comprehensive backtest (all symbols × timeframes × strategies)
    # ------------------------------------------------------------------ #

    def _start_comprehensive_backtest(self) -> str:
        """Kick off the comprehensive backtest in a background thread."""
        job_key = "comprehensive"
        if job_key in self._running and self._running[job_key].is_alive():
            return "Comprehensive backtest is already running. Please wait."

        t = threading.Thread(
            target=self._comprehensive_backtest_worker, daemon=True
        )
        self._running[job_key] = t
        t.start()

        return (
            "*Comprehensive Backtest started!*\n"
            f"Period  : {START_DATE} → {END_DATE}\n"
            f"Symbols : {', '.join(SYMBOLS)}\n"
            f"Timeframes: {', '.join(TIMEFRAMES)}\n\n"
            "_This may take several minutes. Results will be sent when done..._"
        )

    def _comprehensive_backtest_worker(self) -> None:
        """Worker: runs the comprehensive backtest and reports to Telegram."""
        try:
            self.send_message("_Fetching data and running strategies..._")
            all_results = run_comprehensive_backtest()

            if not all_results:
                self.send_message("No results were produced.")
                return

            # Top 10 by ROI
            top = sorted(all_results, key=lambda r: r.roi_per_annum, reverse=True)[:10]

            msg = (
                "*COMPREHENSIVE BACKTEST COMPLETE*\n"
                f"Total strategies tested: {len(all_results)}\n\n"
                "*Top 10 by Annual ROI:*\n"
                "```\n"
                f"{'Strategy':<25} {'Symbol':<10} {'TF':<5} {'ROI%/yr':<9} {'Sharpe':<8} {'WR%'}\n"
                f"{'-'*65}\n"
            )
            for r in top:
                msg += (
                    f"{r.strategy_name[:25]:<25} "
                    f"{r.symbol:<10} "
                    f"{r.timeframe:<5} "
                    f"{r.roi_per_annum:<9.2f} "
                    f"{r.sharpe_ratio:<8.2f} "
                    f"{r.win_rate * 100:.1f}\n"
                )
            msg += "```"
            self.send_message(msg)

            # Best by Sharpe
            by_sharpe = sorted(all_results, key=lambda r: r.sharpe_ratio, reverse=True)[:3]
            sharpe_msg = "*Best by Sharpe Ratio:*\n"
            for r in by_sharpe:
                sharpe_msg += (
                    f"• `{r.strategy_name}` {r.symbol} {r.timeframe}: "
                    f"Sharpe={r.sharpe_ratio:.2f}, ROI={r.roi_per_annum:.2f}%\n"
                )
            self.send_message(sharpe_msg)

            self.send_message(
                "_Full results saved to_ `storage/comprehensive_backtest_results.json`"
            )

        except Exception as e:
            logger.exception("Comprehensive backtest failed")
            self.send_message(f"Comprehensive backtest error: `{e}`")

    # ------------------------------------------------------------------ #
    # Optimization
    # ------------------------------------------------------------------ #

    def _run_optimization(self) -> str:
        try:
            self.send_typing_action()
            optimizer = AutoOptimizer()
            result = optimizer.run_optimization(auto_apply=True)

            if result.get("status") == "success":
                optimized = result.get("optimized_params", {})
                improvement = result.get("improvement", {})

                msg = "*OPTIMIZATION COMPLETE*\n\n*New Parameters:*\n"
                for key, value in optimized.items():
                    msg += f"  {key}: `{value}`\n"

                msg += (
                    f"\n*Improvement:*\n"
                    f"  Current Score : {improvement.get('current_score', 0):.4f}\n"
                    f"  Optimized Score: {improvement.get('optimized_score', 0):.4f}\n"
                    f"  Improvement   : {improvement.get('improvement_pct', 0):.1f}%\n"
                )
                if result.get("auto_applied"):
                    msg += "\n*Parameters have been auto-applied!*"
                return msg
            else:
                return f"Optimization skipped: {result.get('reason', 'unknown')}"

        except Exception as e:
            return f"Error running optimization: `{e}`"

    # ------------------------------------------------------------------ #
    # Params / Stats / Status / Results
    # ------------------------------------------------------------------ #

    def _get_current_params(self) -> str:
        try:
            manager = OptimizedStrategyManager()
            params = manager.get_active_params()

            msg = "*Current Strategy Parameters:*\n\n"
            msg += f"RSI Strategy:\n"
            msg += f"  Length   : `{params.get('rsi_length', 14)}`\n"
            msg += f"  Oversold : `{params.get('rsi_oversold', 30)}`\n"
            msg += f"  Overbought: `{params.get('rsi_overbought', 70)}`\n\n"
            msg += f"SMC Lux:\n"
            msg += f"  Lookback : `{params.get('smc_lookback', 10)}`\n\n"
            msg += f"Squeeze Momentum:\n"
            msg += f"  Length   : `{params.get('squeeze_length', 20)}`\n"

            source = "optimized" if os.path.exists(OPTIMIZED_PARAMS_FILE) else "default"
            msg += f"\n_Using {source} parameters_"
            return msg

        except Exception as e:
            return f"Error getting parameters: `{e}`"

    def _get_trade_stats(self) -> str:
        try:
            analyzer = TradeAnalyzer()
            stats = analyzer.get_pnl_statistics()

            msg = "*Trade Statistics:*\n\n"
            msg += f"Total Trades : {stats.get('total_trades', 0)}\n"
            msg += f"Winning      : {stats.get('winning_trades', 0)}\n"
            msg += f"Losing       : {stats.get('losing_trades', 0)}\n"
            msg += f"Win Rate     : {stats.get('win_rate', 0)*100:.1f}%\n\n"
            msg += f"*PnL Summary:*\n"
            msg += f"  Total PnL : {stats.get('total_pnl', 0):.4f}\n"
            msg += f"  Average   : {stats.get('avg_pnl', 0):.4f}\n"
            msg += f"  Median    : {stats.get('median_pnl', 0):.4f}\n"
            msg += f"  Best Win  : {stats.get('max_win', 0):.4f}\n"
            msg += f"  Worst Loss: {stats.get('max_loss', 0):.4f}\n"
            return msg

        except Exception as e:
            return f"Error getting stats: `{e}`"

    def _get_bot_status(self) -> str:
        try:
            trades_exist = os.path.exists(TRADES_FILE)
            trades_count = 0
            if trades_exist:
                with open(TRADES_FILE, "r") as f:
                    trades_count = sum(1 for line in f if line.strip())

            running_jobs = [k for k, t in self._running.items() if t.is_alive()]

            batch_str = self._format_batches(self._default_batches)
            msg = "*Bot Status:*\n\n"
            msg += f"Default Symbol : `{self._default_symbol}`\n"
            msg += f"Default Batches: `{batch_str}`\n"
            msg += f"Opt Lookback   : `{self._opt_lookback_years}` year(s)\n\n"
            msg += f"Trades File    : {'OK' if trades_exist else 'Missing'}\n"
            msg += f"Total Trades   : {trades_count}\n"
            msg += f"Optimized Params: {'Loaded' if os.path.exists(OPTIMIZED_PARAMS_FILE) else 'Not Set'}\n"
            msg += f"Telegram       : {'Configured' if self.token else 'Not Configured'}\n"
            msg += f"Running Jobs   : {running_jobs if running_jobs else 'None'}\n"
            msg += f"AI Brain       : {'Enabled' if self._brain else 'Disabled'}\n"
            msg += f"Last Updated   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            return msg

        except Exception as e:
            return f"Error getting status: `{e}`"

    def _get_last_results(self) -> str:
        """Return a summary of the last batch backtest results."""
        if not self._last_results:
            # Try loading from saved CSV
            csv_path = os.path.join(_ROOT, "batch_backtest_results.csv")
            if os.path.exists(csv_path):
                try:
                    import pandas as pd
                    df = pd.read_csv(csv_path)
                    records = df.sort_values("roi", ascending=False).head(15).to_dict("records")
                    self._last_results = records
                except Exception:
                    pass

        if not self._last_results:
            return "No backtest results available yet. Run `/backtest` first."

        results = sorted(self._last_results, key=lambda x: x.get("roi", 0), reverse=True)
        profitable = [r for r in results if r.get("roi", 0) > 0]

        msg = (
            f"*Last Backtest Results*\n"
            f"Strategies tested : {len(results)}\n"
            f"Profitable        : {len(profitable)}\n\n"
            "*Top 15 by ROI %:*\n"
            "```\n"
            f"{'ID':<4} {'Name':<22} {'Trades':<7} {'Win%':<7} {'ROI%'}\n"
            f"{'-'*55}\n"
        )
        for r in results[:15]:
            msg += (
                f"{str(r.get('id','?')):<4} "
                f"{str(r.get('name',''))[:22]:<22} "
                f"{r.get('trades',0):<7} "
                f"{r.get('win_rate',0):<7} "
                f"{r.get('roi',0)}\n"
            )
        msg += "```"
        return msg

    # ------------------------------------------------------------------ #
    # Apply custom parameters
    # ------------------------------------------------------------------ #

    def _apply_params(self, args: list) -> str:
        try:
            if len(args) < 3:
                return "Usage: `/apply rsi_length rsi_oversold rsi_overbought`\nExample: `/apply 12 35 65`"

            params = {
                "rsi_length": int(args[0]),
                "rsi_oversold": int(args[1]),
                "rsi_overbought": int(args[2]),
            }
            manager = OptimizedStrategyManager()
            manager.apply_params(params)

            return (
                f"*Parameters Applied:*\n\n"
                f"rsi_length   : `{params['rsi_length']}`\n"
                f"rsi_oversold : `{params['rsi_oversold']}`\n"
                f"rsi_overbought: `{params['rsi_overbought']}`\n\n"
                "_Parameters saved and active!_"
            )
        except ValueError:
            return "Parameters must be integers. Example: `/apply 12 35 65`"
        except Exception as e:
            return f"Error applying parameters: `{e}`"

    # ------------------------------------------------------------------ #
    # Main polling loop
    # ------------------------------------------------------------------ #

    def handle_updates(self):
        """Main long-poll loop."""
        offset = None
        print("Telegram bot started. Waiting for commands...")

        while True:
            try:
                updates = self.get_updates(offset=offset, timeout=60)

                for update in updates:
                    offset = update.get("update_id", 0) + 1

                    message = update.get("message")
                    if not message:
                        continue

                    chat_id = message.get("chat", {}).get("id")
                    text = message.get("text", "")

                    # Only respond to the configured chat(s)
                    if str(chat_id) not in self.chat_ids:
                        continue
                    # Point replies at whoever sent this message
                    self._active_chat_id = str(chat_id)

                    parts = text.strip().split()
                    command = parts[0] if parts else ""
                    args = parts[1:] if len(parts) > 1 else []

                    if command.startswith("/"):
                        logger.info(f"Command: {command} {args}")
                        self.send_typing_action()
                        response = self.process_command(command, args)
                        self.send_message(response)

            except KeyboardInterrupt:
                print("Bot stopped.")
                break
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                import time
                time.sleep(5)


def run_telegram_bot():
    """Main entry point."""
    bot = TelegramBacktestBot()

    if not bot.token or not bot.chat_ids:
        print("ERROR: Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        return

    bot.handle_updates()


if __name__ == "__main__":
    run_telegram_bot()
