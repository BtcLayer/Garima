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

# ── Checkpoint system ────────────────────────────────────────────
CHECKPOINT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "checkpoints")
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

def _save_checkpoint(cmd: str, timeframe: str, data: dict) -> None:
    """Save progress checkpoint for a long-running command."""
    path = os.path.join(CHECKPOINT_DIR, f"{cmd}_{timeframe}.json")
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception:
        pass

def _load_checkpoint(cmd: str, timeframe: str) -> dict:
    """Load checkpoint if it exists. Returns {} if none."""
    path = os.path.join(CHECKPOINT_DIR, f"{cmd}_{timeframe}.json")
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _clear_checkpoint(cmd: str, timeframe: str) -> None:
    """Remove checkpoint after successful completion."""
    path = os.path.join(CHECKPOINT_DIR, f"{cmd}_{timeframe}.json")
    if os.path.exists(path):
        os.remove(path)

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
import numpy as np
from run_strategies_batch import (
    run_batch_strategies,
    load_data,
    calculate_indicators,
    apply_strategy,
    run_backtest as _batch_run_backtest,
    DATA_FILES,
    INITIAL_CAPITAL,
    FEE,
)
from strategies import get_strategies_by_batch, get_all_strategies, get_strategy_by_id

# Import comprehensive backtest engine
from src.comprehensive_backtest import (
    run_comprehensive_backtest,
    BacktestEngine,
    BacktestResult,
    RSIStrategy,
    MovingAverageCrossover,
    MACDStrategy,
    EMACrossStrategy,
    ATRStrategy,
    StochasticStrategy,
    BollingerBandsStrategy,
    VWAPStrategy,
    SYMBOLS,
    TIMEFRAMES,
    START_DATE,
    END_DATE,
    INITIAL_CAPITAL as COMPREHENSIVE_INITIAL_CAPITAL,
    COMMISSION as COMPREHENSIVE_COMMISSION,
)

# Multi-year historical data fetcher
from src.data_fetcher import DataFetcher

# Pine Script parser & backtester (optional)
try:
    from src.pine_backtest import run_pine_backtest, format_pine_result
    _PINE_BT_AVAILABLE = True
except ImportError:
    _PINE_BT_AVAILABLE = False
    run_pine_backtest = None
    format_pine_result = None

# AI brain (optional — disabled gracefully if GEMINI_API_KEY is missing)
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

# How many years of historical data to use when optimizing (1–6)
_OPT_LOOKBACK_YEARS = 6

# Parameter search space for SL / TP / Trailing-Stop random search
_SL_CANDIDATES  = [0.010, 0.015, 0.020, 0.025, 0.030, 0.040, 0.050]
_TP_CANDIDATES  = [0.020, 0.030, 0.040, 0.050, 0.060, 0.080, 0.100, 0.150]
_TS_CANDIDATES  = [0.005, 0.010, 0.015, 0.020, 0.025, 0.030]
_OPT_TRIALS     = 20   # reduced from 40 to speed up optimization

# ── Built-in strategy name → class mapping ──────────────────────────────────
BUILTIN_STRATEGIES = {
    "RSI":       RSIStrategy,
    "MACD":      MACDStrategy,
    "MA":        MovingAverageCrossover,
    "EMA":       EMACrossStrategy,
    "ATR":       ATRStrategy,
    "STOCH":     StochasticStrategy,
    "BB":        BollingerBandsStrategy,
    "VWAP":      VWAPStrategy,
}

# Elite strategy default list — moved after function definitions below


def _grade_performance(roi_pct: float, win_rate: float, profit_factor: float) -> str:
    """Assign a performance grade based on ROI, win rate, and profit factor."""
    if roi_pct > 100 and win_rate > 0.50 and profit_factor > 2.0:
        return "A+"
    elif roi_pct > 50 and win_rate > 0.45 and profit_factor > 1.75:
        return "A"
    elif roi_pct > 30 and win_rate > 0.40 and profit_factor > 1.5:
        return "B+"
    elif roi_pct > 20 and win_rate > 0.35 and profit_factor > 1.3:
        return "B"
    elif roi_pct > 10 and win_rate > 0.30 and profit_factor > 1.0:
        return "C"
    else:
        return "D"


def _verdict_line(roi_pct: float, grade: str) -> str:
    """Return a nature-themed sarcastic verdict based on performance."""
    if roi_pct > 500:
        return "☄️ Meteor strike — either this is real or the universe is glitching. Triple-check on TV."
    elif roi_pct > 100:
        return "🌋 Erupting — this strategy is on fire. Validate before it cools down."
    elif roi_pct > 50:
        return "⛰️ Mountain top — solid view from up here. Worth a TV cross-check."
    elif roi_pct > 20:
        return "🌊 Riding the wave — decent momentum. Run /validate to see if it holds."
    elif roi_pct > 5:
        return "🌱 Sprouting — there's life here but it needs nurturing."
    elif roi_pct > 0:
        return "🍂 Barely breathing — one gust of wind and it's gone."
    elif roi_pct > -20:
        return "🌧️ Drizzling losses — not a storm yet, but bring an umbrella."
    elif roi_pct > -50:
        return "🌪️ Getting ugly — this strategy is blowing away your capital."
    else:
        return "☠️ Scorched earth — nothing survives here. Move on."


def _deployment_status(grade: str, total_trades: int, max_dd: float) -> str:
    """Decide if a strategy is deployable based on grade, trades, and drawdown."""
    if grade in ("A+", "A") and total_trades >= 20 and max_dd < 25:
        return "READY 🌞"
    elif grade in ("B+", "B") and total_trades >= 15 and max_dd < 30:
        return "REVIEW 🌤️"
    else:
        return "NOT READY 🌑"


def _compute_score(roi_pct: float, win_rate: float, profit_factor: float, max_dd: float) -> float:
    """Compute a composite score (0-100) for ranking strategies.
    Weights: ROI 35%, Win Rate 20%, Profit Factor 20%, Drawdown 15%, Consistency 10%.
    """
    roi_score = min(max(roi_pct, -100), 500) / 5  # normalize to 0-100 range
    wr_score = win_rate  # already 0-100
    pf_score = min(profit_factor * 25, 100)  # PF 4.0 = 100
    dd_score = max(100 - max_dd * 2, 0)  # lower DD = higher score
    consistency = min((wr_score * pf_score) / 100, 100)  # combined metric

    return (roi_score * 0.35 + wr_score * 0.20 + pf_score * 0.20
            + dd_score * 0.15 + consistency * 0.10)


def _save_elite_ranking(names: list, results: list) -> None:
    """Save optimized elite ranking and scores to disk."""
    save_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "storage", "elite_ranking.json",
    )
    try:
        data = {"updated": datetime.now().isoformat(), "ranking": names, "results": results}
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Could not save elite ranking: {e}")


def _load_elite_ranking() -> list:
    """Load previously saved elite ranking from disk."""
    save_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "storage", "elite_ranking.json",
    )
    if os.path.exists(save_path):
        try:
            with open(save_path) as f:
                data = json.load(f)
            return data.get("ranking", [])
        except Exception:
            pass
    return []


def _load_optimized_strategy_params(strategy_name: str) -> dict:
    """Load optimized SL/TP/TS parameters for a strategy from elite_ranking.json.
    
    Returns dict with 'stop_loss', 'take_profit', 'trailing_stop' if found,
    otherwise returns empty dict to use defaults.
    """
    save_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "storage", "elite_ranking.json",
    )
    if os.path.exists(save_path):
        try:
            with open(save_path) as f:
                data = json.load(f)
            results = data.get("results", [])
            for r in results:
                if r.get("name") == strategy_name:
                    # Return optimized parameters if found
                    return {
                        "stop_loss": r.get("sl", 0.015),
                        "take_profit": r.get("tp", 0.03),
                        "trailing_stop": r.get("ts", 0.015),
                    }
        except Exception:
            pass
    return {}


# ── Elite strategies (profitable across multiple assets, ROI/yr >= 20%) ──────
_DEFAULT_ELITE = [
    "ADX_Stochastic_VWAP",
    "RSI_Stochastic_VWAP_ADX",
    "RSI_BB_MACD_Stochastic",
    "Supertrend_BB_Entry",
    "Scalp_Trade",
    "Mean_Reversion_Pro",
    "Oversold_Recovery",
    "BB_Stochastic_Trade",
    "RSI_Confirmation",
    "Double_Bottom_Formation",
    "RSI_Extreme_Reversal",
    "RSI_Stochastic_Pro",
    "VWAP_Break_Entry",
    "Volume_Breakout_Pro",
    "RSI_Recovery",
    "EMA_Cloud_Strength",
    "Breakout_Retest",
    "Supertrend_Multi_Entry",
    "ADX_Stochastic_BB",
    "EMA_RSI_Momentum",
]
_saved_ranking = _load_elite_ranking()
ELITE_STRATEGY_NAMES = _saved_ranking if _saved_ranking else list(_DEFAULT_ELITE)


def _normalize_symbol(raw: str) -> str:
    """Normalize symbol key: uppercase asset, lowercase timeframe (e.g. BTCUSDT_1h)."""
    parts = raw.rsplit("_", 1)
    if len(parts) == 2:
        return f"{parts[0].upper()}_{parts[1].lower()}"
    return raw.upper()


def _find_batch_strategy_by_name(name: str):
    """Search all 230+ batch strategies for one matching *name* (case-insensitive)."""
    target = name.strip().lower()
    for strat in get_all_strategies():
        if strat["name"].lower() == target:
            return strat
    return None


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
        # Stop flag — checked by workers to abort
        self._stop_flag = threading.Event()
        # Store last backtest results
        self._last_results: List[dict] = []
        # Pine Script pending state: {chat_id: {"symbol": ..., "timeframe": ...}}
        self._pine_pending: Dict[str, Dict[str, str]] = {}
        # Years of historical data used for optimization (configurable via /optdata)
        self._opt_lookback_years: int = _OPT_LOOKBACK_YEARS
        # Default trade: symbol + batches (persisted to disk)
        self._default_symbol: str = "BTCUSDT_15m"
        self._default_batches: List[int] = [1]
        self._load_default_trade()

        # Auto Alpha Hunter flag
        self._auto_hunt_running = False

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
        """Send a message to the active Telegram chat (auto-splits if too long).
        Falls back to plain text if Markdown fails.
        """
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
                if r.status_code == 429:
                    # Rate limited — wait and retry once
                    retry_after = r.json().get("parameters", {}).get("retry_after", 5)
                    logger.warning(f"Telegram rate limit hit, waiting {retry_after}s")
                    import time; time.sleep(retry_after)
                    r = requests.post(url, json=payload, timeout=30)
                if r.status_code != 200:
                    logger.warning(f"Markdown send failed ({r.status_code}), retrying plain text")
                    payload.pop("parse_mode", None)
                    r2 = requests.post(url, json=payload, timeout=30)
                    if r2.status_code == 429:
                        retry_after = r2.json().get("parameters", {}).get("retry_after", 5)
                        import time; time.sleep(retry_after)
                        r2 = requests.post(url, json=payload, timeout=30)
                    if r2.status_code != 200:
                        logger.error(f"Plain text send also failed: {r2.text}")
                        ok = False
            except Exception as e:
                logger.error(f"Failed to send Telegram message: {e}")
                ok = False
        return ok

    def send_document(self, file_path: str, caption: str = "") -> bool:
        """Send a file (CSV, JSON, etc.) to the active Telegram chat."""
        target = self._active_chat_id or self.chat_id
        if not self.token or not target:
            return False
        try:
            url = f"{self.api_url}/sendDocument"
            with open(file_path, "rb") as f:
                files = {"document": (os.path.basename(file_path), f)}
                data = {"chat_id": target}
                if caption:
                    data["caption"] = caption
                r = requests.post(url, data=data, files=files, timeout=60)
                return r.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send document: {e}")
            return False

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
        """Route commands to handlers. Groups:
        1. Greetings     — hello, hi, suno, namaste, hui
        2. Backtesting   — test, backtest, comprehensive, pine
        3. Elite         — elite (list / run / all assets)
        4. Optimization  — optimize, auto, validate
        5. Controls      — stop, pause, ruko, bas
        6. Info          — status, results, params, stats
        7. Settings      — setdefault, apply, optdata
        8. AI Brain      — ask, analyze
        """
        command = command.lower().strip("/").split("@")[0]
        args = args or []

        # Auto-pause hunt if another command comes in (except autohunt itself)
        if self._auto_hunt_running and command != "autohunt":
            self._auto_hunt_paused = True

        # ── 1. Greetings ──
        if command in ("start", "help"):
            return self._get_help_message()
        elif command in ("hello", "hi"):
            return self._greet("Hello! Kaunsi command use karna chahenge?")
        elif command == "suno":
            return self._greet("Sunao ji, konsi command use karna chahenge?")
        elif command == "namaste":
            return self._greet("Namaste ji, command dijiye muje!")
        elif command == "hui":
            return self._greet("Arey bhai! Kya haal chaal? Bolo kya karna hai, bot tayyar hai!")

        # ── 2. Backtesting ──
        elif command == "test":
            return self._start_single_test(args)
        elif command == "backtest":
            return self._start_batch_backtest(args)
        elif command == "comprehensive":
            return self._start_comprehensive_backtest()
        elif command == "pine":
            return self._start_pine_backtest(args)

        # ── 3. Elite strategies ──
        elif command == "elite":
            return self._start_elite_backtest(args)

        # ── 4. Optimization ──
        elif command == "optimize":
            return self._run_optimization(args)
        elif command == "auto":
            return self._start_auto(args)
        elif command == "validate":
            return self._start_validate(args)

        # ── 5. Controls ──
        elif command in ("stop", "pause", "ruko", "bas"):
            return self._stop_running()
        elif command == "restart":
            return self._restart_bot()

        # ── 5b. Live Trading Controls ──
        elif command == "killswitch":
            return self._toggle_kill_switch(args)
        elif command == "paper":
            return self._toggle_paper_mode(args)
        elif command == "positions":
            return self._show_positions()
        elif command == "closeall":
            return self._close_all_positions()
        elif command == "autohunt":
            return self._start_auto_hunt(args)
        elif command == "generate":
            return self._start_generate(args)
        elif command == "ml":
            return self._start_ml(args)
        elif command == "evolve":
            return self._evolve_cmd(args)

        # ── 6. Info ──
        elif command == "status":
            return self._get_bot_status()
        elif command == "results":
            return self._get_last_results(args)
        elif command == "params":
            return self._get_current_params()
        elif command == "stats":
            return self._get_trade_stats()

        # ── 7. Settings ──
        elif command == "setdefault":
            return self._set_default_trade(args)
        elif command == "apply" and args:
            return self._apply_params(args)
        elif command == "optdata":
            return self._set_opt_lookback(args)

        # ── 8. AI Brain ──
        elif command == "ask":
            return self._ask_brain(args)
        elif command == "analyze":
            return self._analyze_last_results()

        # ── 9. Strategy Analysis ──
        elif command == "analysis":
            return self._run_strategy_analysis()
        elif command == "pinescript":
            return self._generate_pine_script(args)

        else:
            result = f"Unknown command: `/{command}` — try /help"
            return result

        # After any command: if hunt was paused, ask about resuming
        # (handled below in the caller since this returns a string)

    def _post_command_hook(self):
        """Called after sending command result. If hunt was paused, prompt resume."""
        if getattr(self, '_auto_hunt_paused', False) and self._auto_hunt_running:
            self._auto_hunt_paused = False  # unpause so it continues
            self.send_message(
                "Alpha Hunter was paused for your command.\n"
                "Resuming automatically...\n"
                "Use `/autohunt stop` to stop."
            )

    # ------------------------------------------------------------------ #
    # Greetings
    # ------------------------------------------------------------------ #

    def _greet(self, greeting_line: str) -> str:
        """Return a greeting with quick-start command options."""
        return (
            f"{greeting_line}\n\n"
            "*Quick start:*\n"
            "`/auto 4h` — full pipeline (backtest + optimize)\n"
            "`/validate all 4h` — confirm results\n"
            "`/results` — see latest output\n"
            "`/help` — all commands"
        )

    # ------------------------------------------------------------------ #
    # Help
    # ------------------------------------------------------------------ #

    def _get_help_message(self) -> str:
        brain_tag = "ON" if self._brain else "OFF"
        return (
            "*GARIMA — Strategy Command Center*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

            "*WORKFLOW (run in order)*\n\n"

            "1. `/auto 4h` — Full pipeline\n"
            "   230+ strategies > top 20 > optimize SL/TP/TS\n"
            "   `/auto 1h` — same for 1h\n\n"

            "2. `/validate all 4h` — Confirm params hold\n"
            "   `/validate all 1h` — same for 1h\n\n"

            "3. *Review results*\n"
            "   `/analysis` — full strategy breakdown\n"
            "   `/results` — last run summary\n"
            "   `/pinescript top 5` — TV verification scripts\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "*INDIVIDUAL RUNS*\n\n"
            "  `/elite BNB 4h` — elite strats, one asset\n"
            "  `/backtest BTCUSDT_4h` — all strats, one asset\n"
            "  `/comprehensive` — all assets x all TFs\n"
            "  `/optimize BTCUSDT_4h` — tune one asset\n"
            "  `/test BTCUSDT 4h RSI` — spot-check one\n"
            "  `/pinescript <name>` — generate Pine Script\n"
            "  `/pine BTCUSDT 1h` — paste & run Pine\n\n"

            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "*RESULTS & AI*\n\n"
            "  `/results` — last run summary\n"
            "  `/results 4h` — results filtered by timeframe\n"
            "  `/analysis` — full strategy breakdown\n"
            "  `/status` — bot health check\n"
            "  `/stats` — trade statistics\n"
            "  `/params` — current parameters\n"
            f"  `/analyze` — AI analysis ({brain_tag})\n"
            "  `/ask <q>` — ask AI anything\n\n"

            "*CONTROLS*\n\n"
            "  `/stop` — kill running job\n"
            "  `/restart` — reset bot state\n"
            "  `/setdefault BTCUSDT_4h` — set default\n"
            "  `/optdata 6` — set lookback years\n\n"

            "*LIVE TRADING*\n\n"
            "  `/killswitch` — toggle kill switch (closes all)\n"
            "  `/paper on|off` — paper/live trading mode\n"
            "  `/positions` — show open positions & PnL\n"
            "  `/closeall` — close all open positions\n\n"

            "*AUTO HUNT*\n\n"
            "  `/autohunt` — auto-find ALPHA strategies (runs in background)\n"
            "  `/autohunt stop` — stop hunting\n\n"

            "*STRATEGY GENERATOR*\n\n"
            "  `/generate` — generate NEW strategies targeting 1%/day\n"
            "  `/generate stop` — stop generator\n"
            "  Methods: ATR-adaptive, mean reversion, random mutation, high-TP, trend+dip hybrid\n\n"

            "*ML SCANNER (Advanced)*\n\n"
            "  `/ml` — ML strategy scanner (Random Forest + GBM, 40+ features)\n"
            "  `/ml 1h` — scan on 1h timeframe\n"
            "  `/ml stop` — stop scanner\n"
            "  Walk-forward validated (70/30 train/test, OOS results only)\n\n"

            "10 assets · 3 TFs · 260+ strategies · 6yr data"
        )

    # ------------------------------------------------------------------ #
    # Elite strategy backtest (/elite)
    # ------------------------------------------------------------------ #

    def _start_elite_backtest(self, args: list) -> str:
        """Run elite strategies on a given symbol.

        Usage:
          /elite                          → list all 20 elite strategies
          /elite BTCUSDT_4h               → run all 20 on BTCUSDT_4h
          /elite BTCUSDT_4h 1             → run elite #1 only
          /elite BTCUSDT_4h 1,3,5         → run elite #1, #3, #5
          /elite BTCUSDT_4h 1-5           → run elite #1 through #5
          /elite BTCUSDT_4h Scalp_Trade   → run by name
          /elite BTCUSDT_4h Scalp_Trade,RSI_Recovery → multiple by name
        """
        # No args → show the list
        if not args:
            lines = ["*Elite Strategies (Top 20):*\n"]
            for i, name in enumerate(ELITE_STRATEGY_NAMES, 1):
                lines.append(f"{i}. {name}")
            lines.append("")
            lines.append("*Usage:*")
            lines.append("/elite BTCUSDT_4h — run all 20")
            lines.append("/elite BTCUSDT_4h 1 — run #1 only")
            lines.append("/elite BTCUSDT_4h 1-5 — run range")
            lines.append("/elite BTCUSDT_4h 1,3,5 — pick multiple")
            lines.append("/elite BTCUSDT_4h Scalp_Trade — by name")
            lines.append("/elite all 4h — run on ALL assets (15m/1h/4h)")
            lines.append("/elite all 4h 1 — run #1 on all assets")
            return "\n".join(lines)

        # Handle "all" — run across all 10 assets
        if args[0].lower() == "all":
            if len(args) < 2:
                return "Usage: /elite all <timeframe> [strategy]\nExample: /elite all 4h\nExample: /elite all 1h 1,3,5"
            tf = args[1].lower()
            strat_selector = args[2] if len(args) > 2 else None
            return self._start_elite_all_assets(tf, strat_selector)

        symbol = _normalize_symbol(args[0])
        if symbol not in DATA_FILES:
            available = ", ".join(sorted(DATA_FILES.keys()))
            return f"Unknown symbol `{symbol}`.\nAvailable: {available}"

        # Parse which elite strategies to run
        selected_names = list(ELITE_STRATEGY_NAMES)  # default: all 20
        if len(args) > 1:
            selector = args[1]
            # Check if it's a number range like "1-5"
            if "-" in selector and selector.replace("-", "").isdigit():
                try:
                    a, b = selector.split("-")
                    indices = list(range(int(a) - 1, int(b)))
                    selected_names = [ELITE_STRATEGY_NAMES[i] for i in indices if i < len(ELITE_STRATEGY_NAMES)]
                except (ValueError, IndexError):
                    return "Invalid range. Use e.g. `1-5`"
            # Check if it's comma-separated numbers like "1,3,5"
            elif "," in selector and all(p.strip().isdigit() for p in selector.split(",")):
                indices = [int(p.strip()) - 1 for p in selector.split(",")]
                selected_names = [ELITE_STRATEGY_NAMES[i] for i in indices if 0 <= i < len(ELITE_STRATEGY_NAMES)]
            # Single number like "3"
            elif selector.isdigit():
                idx = int(selector) - 1
                if 0 <= idx < len(ELITE_STRATEGY_NAMES):
                    selected_names = [ELITE_STRATEGY_NAMES[idx]]
                else:
                    return f"Invalid number. Choose 1-{len(ELITE_STRATEGY_NAMES)}"
            # Names: comma-separated like "Scalp_Trade,RSI_Recovery"
            else:
                names = [n.strip() for n in selector.split(",")]
                # Also check remaining args in case user wrote: /elite BTCUSDT_4h Scalp_Trade RSI_Recovery
                names.extend(args[2:])
                matched = [n for n in names if n in ELITE_STRATEGY_NAMES]
                if not matched:
                    # Try case-insensitive
                    name_map = {n.lower(): n for n in ELITE_STRATEGY_NAMES}
                    matched = [name_map[n.lower()] for n in names if n.lower() in name_map]
                if not matched:
                    return (
                        f"No matching elite strategies for: `{selector}`\n"
                        "Use `/elite` to see the full list."
                    )
                selected_names = matched

        job_key = f"elite_{symbol}"
        if job_key in self._running and self._running[job_key].is_alive():
            return f"Elite backtest on `{symbol}` is already running."

        t = threading.Thread(
            target=self._elite_backtest_worker,
            args=(symbol, selected_names),
            daemon=True,
        )
        self._running[job_key] = t
        t.start()

        names_display = ", ".join(selected_names) if len(selected_names) <= 5 else f"{len(selected_names)} strategies"
        return (
            f"*Elite Backtest started!*\n"
            f"Symbol: `{symbol}`\n"
            f"Strategies: `{names_display}`\n\n"
            "_Results will be sent when complete._"
        )

    def _elite_backtest_worker(self, symbol: str, selected_names: list = None) -> None:
        """Worker: run selected elite strategies + counter for negatives.
        Produces full CSV with all columns including drawdown.
        """
        try:
         self._elite_backtest_worker_inner(symbol, selected_names)
        except Exception as e:
            logger.error(f"Elite backtest worker crashed: {e}", exc_info=True)
            self.send_message(f"Elite backtest crashed: `{e}`\nRun /restart and retry.")

    def _elite_backtest_worker_inner(self, symbol: str, selected_names: list = None) -> None:
        target_names = set(selected_names or ELITE_STRATEGY_NAMES)
        all_strats = get_all_strategies()
        elite_strats = [s for s in all_strats if s["name"] in target_names]

        if not elite_strats:
            self.send_message("No matching elite strategies found in batch definitions.")
            return

        self.send_message(
            f"Running {len(elite_strats)} elite strategies on {symbol}..."
        )

        # Parse asset/timeframe from symbol key
        _parts = symbol.rsplit("_", 1)
        _asset = _parts[0] if len(_parts) == 2 else symbol
        _timeframe = _parts[1] if len(_parts) == 2 else "unknown"

        all_results = []
        df = load_data(symbol)
        if df is None:
            self.send_message(f"Data not found for {symbol}.")
            return
        df = calculate_indicators(df)

        # Detect time range from data
        if "timestamp" in df.columns:
            time_start = str(df["timestamp"].iloc[0])[:10]
            time_end = str(df["timestamp"].iloc[-1])[:10]
        else:
            time_start, time_end = "unknown", "unknown"
        try:
            from datetime import datetime as _dt
            _years = max((_dt.fromisoformat(time_end) - _dt.fromisoformat(time_start)).days / 365.25, 0.01)
        except Exception:
            _years = 1.0

        def _build_full_result(strat, final_cap, trades, is_counter=False):
            """Build result dict with ALL columns."""
            wins = [t for t in trades if t["pnl"] > 0]
            losses_list = [t for t in trades if t["pnl"] <= 0]
            wr = len(wins) / len(trades) * 100 if trades else 0
            net = final_cap - INITIAL_CAPITAL
            roi = net / INITIAL_CAPITAL * 100
            roi_annum = ((final_cap / INITIAL_CAPITAL) ** (1 / _years) - 1) * 100 if _years > 0 else 0

            total_wins = sum(t["pnl"] for t in trades if t["pnl"] > 0)
            total_losses = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
            pf = total_wins / total_losses if total_losses > 0 else 0

            returns = [t.get("return_pct", t["pnl"] / INITIAL_CAPITAL * 100) for t in trades]
            avg_trade = sum(returns) / len(returns) if returns else 0
            import numpy as _np
            # TV-style daily Sharpe
            from collections import defaultdict as _dd_s
            _daily_pnl = _dd_s(float)
            for t in trades:
                _d = t.get("exit_date", "")[:10]
                if _d:
                    _daily_pnl[_d] += t["pnl"] / INITIAL_CAPITAL * 100
            _total_d = max(int(_years * 365), 30)
            _all_d = [0.0] * _total_d
            for _i, (_d, _v) in enumerate(sorted(_daily_pnl.items())):
                if _i < _total_d:
                    _all_d[_i] = _v
            _m = _np.mean(_all_d)
            _s = _np.std(_all_d) if len(_all_d) > 1 else 1
            sharpe = (_m / _s) * _np.sqrt(252) if _s > 0 else 0

            # Gross DD (compounding equity curve — peak to trough %)
            equity = INITIAL_CAPITAL
            peak = equity
            max_dd = 0
            gross_dd_date = "N/A"
            gross_dd_capital = INITIAL_CAPITAL
            for t in trades:
                equity += t["pnl"]
                peak = max(peak, equity)
                dd = (peak - equity) / peak * 100
                if dd > max_dd:
                    max_dd = dd
                    gross_dd_date = t.get("exit_date", "N/A")
                    gross_dd_capital = round(equity, 2)
            gross_dd = max_dd

            # Net DD — how far capital dropped below initial $10k
            # Net DD = (initial - lowest_capital) / initial * 100
            # Only >0 when capital goes below starting amount
            equity2 = INITIAL_CAPITAL
            min_capital = INITIAL_CAPITAL
            net_dd = 0
            net_dd_date = "N/A"
            net_dd_capital = INITIAL_CAPITAL
            for t in trades:
                equity2 += t["pnl"]
                if equity2 < min_capital:
                    min_capital = equity2
                    net_dd_date = t.get("exit_date", "N/A")
                    net_dd_capital = round(equity2, 2)
            if min_capital < INITIAL_CAPITAL:
                net_dd = (INITIAL_CAPITAL - min_capital) / INITIAL_CAPITAL * 100
            else:
                net_dd = 0

            grade = _grade_performance(roi, wr / 100, pf)
            deploy = _deployment_status(grade, len(trades), gross_dd)
            name = f"{strat['name']}_COUNTER" if is_counter else strat["name"]

            return {
                "Rank": 0,
                "id": strat["id"],
                "name": name,
                "Strategy": ", ".join(strat["strategies"]),
                "Asset": _asset,
                "Timeframe": _timeframe,
                "Initial_Capital_USD": INITIAL_CAPITAL,
                "Final_Capital_USD": round(final_cap, 2),
                "Net_Profit_USD": round(net, 2),
                "ROI_per_annum": round(roi_annum, 2),
                "ROI_Percent": round(roi, 2),
                "Total_Trades": len(trades),
                "Winning_Trades": len(wins),
                "Losing_Trades": len(losses_list),
                "Win_Rate_Percent": round(wr, 2),
                "Profit_Factor": round(pf, 2),
                "Sharpe_Ratio": round(sharpe, 2),
                "Avg_Trade_Percent": round(avg_trade, 4),
                "Gross_DD_Percent": round(gross_dd, 2),
                "Gross_DD_Date": gross_dd_date,
                "Gross_DD_Capital": gross_dd_capital,
                "Net_DD_Percent": round(net_dd, 2),
                "Net_DD_Date": net_dd_date,
                "Net_DD_Capital": net_dd_capital,
                "Performance_Grade": grade,
                "Deployment_Status": deploy,
                "Data_Source": "Binance Spot",
                "Time_Period": f"{time_start} to {time_end}",
                "Time_Start": time_start,
                "Time_End": time_end,
                "Fees_Exchange": f"{FEE*100}%",
                "Candle_Period": _timeframe,
                "Parameters": f"SL={strat['stop_loss']*100}%, TP={strat['take_profit']*100}%, TS={strat['trailing_stop']*100}%",
                "Is_Counter": is_counter,
                # Bot summary keys
                "trades": len(trades),
                "wins": len(wins),
                "losses": len(losses_list),
                "win_rate": round(wr, 2),
                "roi": round(roi, 2),
                "final_capital": round(final_cap, 2),
            }

        for strat in elite_strats:
            try:
                # Load optimized params if available
                optimized_params = _load_optimized_strategy_params(strat.get("name", ""))
                
                # Use optimized params if found, otherwise use default
                if optimized_params:
                    sl = optimized_params.get("stop_loss", strat["stop_loss"])
                    tp = optimized_params.get("take_profit", strat["take_profit"])
                    ts = optimized_params.get("trailing_stop", strat["trailing_stop"])
                else:
                    sl = strat["stop_loss"]
                    tp = strat["take_profit"]
                    ts = strat["trailing_stop"]
                
                df_copy = apply_strategy(
                    df.copy(),
                    strat["strategies"],
                    strat.get("min_agreement", 1),
                )
                final_cap, trades = _batch_run_backtest(
                    df_copy,
                    sl,
                    tp,
                    ts,
                )
                if len(trades) >= 5:
                    result = _build_full_result(strat, final_cap, trades)
                    all_results.append(result)

                    # Counter-trade if ROI is negative
                    if result["roi"] < 0:
                        df_counter = df_copy.copy()
                        df_counter["entry_signal"], df_counter["exit_signal"] = (
                            df_counter["exit_signal"], df_counter["entry_signal"],
                        )
                        counter_cap, counter_trades = _batch_run_backtest(
                            df_counter,
                            sl,
                            tp,
                            ts,
                        )
                        if len(counter_trades) >= 5:
                            c_result = _build_full_result(strat, counter_cap, counter_trades, is_counter=True)
                            if c_result["roi"] > result["roi"]:
                                all_results.append(c_result)
            except Exception as e:
                logger.warning(f"Elite strategy {strat['name']} error: {e}")

        if not all_results:
            self.send_message("No results from elite strategies.")
            return

        # Sort and assign ranks
        all_results.sort(key=lambda x: x.get("roi", 0), reverse=True)
        for i, r in enumerate(all_results, 1):
            r["Rank"] = i

        self._last_results = all_results
        self._send_backtest_summary(symbol, ["elite"], all_results, label="ELITE BACKTEST RESULTS")

        # Save and send CSV with all columns
        csv_columns = [
            "Rank", "name", "Strategy", "Asset", "Timeframe",
            "Initial_Capital_USD", "Final_Capital_USD", "Net_Profit_USD",
            "ROI_per_annum", "ROI_Percent", "Total_Trades", "Winning_Trades",
            "Losing_Trades", "Win_Rate_Percent", "Profit_Factor", "Sharpe_Ratio",
            "Avg_Trade_Percent", "Gross_DD_Percent", "Net_DD_Percent", "Performance_Grade",
            "Deployment_Status", "Data_Source", "Time_Period", "Time_Start",
            "Time_End", "Fees_Exchange", "Candle_Period", "Parameters", "Is_Counter",
        ]
        import pandas as pd
        csv_path = os.path.join(_ROOT, "batch_backtest_results.csv")
        df_csv = pd.DataFrame(all_results)[csv_columns]
        df_csv.to_csv(csv_path, index=False)
        self.send_document(csv_path, caption="Elite backtest results (full details)")

    # ------------------------------------------------------------------ #
    # Elite ALL assets (/elite all <tf>)
    # ------------------------------------------------------------------ #

    def _start_elite_all_assets(self, timeframe: str, strat_selector: str = None) -> str:
        """Run elite strategies across all 10 assets for a given timeframe."""
        # Find all symbols for this timeframe
        symbols = [k for k in DATA_FILES if k.endswith(f"_{timeframe}")]
        if not symbols:
            return f"No data found for timeframe {timeframe}.\nAvailable: 15m, 1h, 4h"

        # Parse strategy selection
        selected_names = list(ELITE_STRATEGY_NAMES)
        if strat_selector:
            if "-" in strat_selector and strat_selector.replace("-", "").isdigit():
                a, b = strat_selector.split("-")
                selected_names = [ELITE_STRATEGY_NAMES[i] for i in range(int(a)-1, int(b)) if i < len(ELITE_STRATEGY_NAMES)]
            elif "," in strat_selector and all(p.strip().isdigit() for p in strat_selector.split(",")):
                indices = [int(p.strip())-1 for p in strat_selector.split(",")]
                selected_names = [ELITE_STRATEGY_NAMES[i] for i in indices if 0 <= i < len(ELITE_STRATEGY_NAMES)]
            elif strat_selector.isdigit():
                idx = int(strat_selector) - 1
                if 0 <= idx < len(ELITE_STRATEGY_NAMES):
                    selected_names = [ELITE_STRATEGY_NAMES[idx]]
            else:
                names = [n.strip() for n in strat_selector.split(",")]
                name_map = {n.lower(): n for n in ELITE_STRATEGY_NAMES}
                matched = [name_map.get(n.lower(), n) for n in names if n.lower() in name_map]
                if matched:
                    selected_names = matched

        job_key = "elite_all"
        if job_key in self._running and self._running[job_key].is_alive():
            return "Elite all-assets backtest is already running."

        t = threading.Thread(
            target=self._elite_all_assets_worker,
            args=(symbols, selected_names, timeframe),
            daemon=True,
        )
        self._running[job_key] = t
        t.start()

        n_strats = len(selected_names)
        return (
            f"Elite ALL Assets Backtest started!\n"
            f"Timeframe: {timeframe}\n"
            f"Assets: {len(symbols)}\n"
            f"Strategies: {n_strats}\n"
            f"Total runs: {len(symbols) * n_strats}\n\n"
            "Results will be sent when complete..."
        )

    def _elite_all_assets_worker(self, symbols: list, selected_names: list, timeframe: str) -> None:
        """Worker: run elite strategies on all assets, report per-asset and combined."""
        try:
            self._elite_all_assets_worker_inner(symbols, selected_names, timeframe)
        except Exception as e:
            logger.error(f"Elite all-assets worker crashed: {e}", exc_info=True)
            self.send_message(f"Elite all-assets crashed: `{e}`\nRun /restart and retry.")

    def _elite_all_assets_worker_inner(self, symbols: list, selected_names: list, timeframe: str) -> None:
        import pandas as pd
        import numpy as _np
        from datetime import datetime as _dt

        target_names = set(selected_names)
        all_strats = get_all_strategies()
        elite_strats = [s for s in all_strats if s["name"] in target_names]

        if not elite_strats:
            self.send_message("No matching elite strategies found.")
            return

        all_results = []       # every individual result
        per_asset_summary = {} # asset → {best_roi, avg_roi, ...}

        for symbol in sorted(symbols):
            if self._should_stop():
                self.send_message("Stopped by user.")
                return
            _parts = symbol.rsplit("_", 1)
            _asset = _parts[0] if len(_parts) == 2 else symbol

            self.send_message(f"Running {_asset} {timeframe}...")

            df = load_data(symbol)
            if df is None:
                per_asset_summary[_asset] = {"status": "NO DATA"}
                continue
            df = calculate_indicators(df)

            # Detect time range
            if "timestamp" in df.columns:
                time_start = str(df["timestamp"].iloc[0])[:10]
                time_end = str(df["timestamp"].iloc[-1])[:10]
            else:
                time_start, time_end = "unknown", "unknown"
            try:
                _years = max((_dt.fromisoformat(time_end) - _dt.fromisoformat(time_start)).days / 365.25, 0.01)
            except Exception:
                _years = 1.0

            asset_results = []
            for strat in elite_strats:
                try:
                    df_copy = apply_strategy(df.copy(), strat["strategies"], strat.get("min_agreement", 1))
                    final_cap, trades = _batch_run_backtest(df_copy, strat["stop_loss"], strat["take_profit"], strat["trailing_stop"])
                    if len(trades) >= 5:
                        wins = [t for t in trades if t["pnl"] > 0]
                        roi = (final_cap - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
                        roi_annum = ((final_cap / INITIAL_CAPITAL) ** (1 / _years) - 1) * 100 if _years > 0 else 0
                        wr = len(wins) / len(trades) * 100
                        total_wins_pnl = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                        total_losses_pnl = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                        pf = total_wins_pnl / total_losses_pnl if total_losses_pnl > 0 else 0

                        # Drawdowns
                        equity = INITIAL_CAPITAL
                        peak = equity
                        gross_dd = 0
                        min_capital = INITIAL_CAPITAL
                        for t in trades:
                            equity += t["pnl"]
                            peak = max(peak, equity)
                            dd = (peak - equity) / peak * 100
                            gross_dd = max(gross_dd, dd)
                            min_capital = min(min_capital, equity)
                        net_dd = max(0, (INITIAL_CAPITAL - min_capital) / INITIAL_CAPITAL * 100)

                        grade = _grade_performance(roi, wr / 100, pf)
                        asset_results.append({
                            "name": strat["name"],
                            "Asset": _asset,
                            "Timeframe": timeframe,
                            "roi": round(roi, 2),
                            "ROI_per_annum": round(roi_annum, 2),
                            "trades": len(trades),
                            "win_rate": round(wr, 2),
                            "Profit_Factor": round(pf, 2),
                            "Gross_DD_Percent": round(gross_dd, 2),
                            "Net_DD_Percent": round(net_dd, 2),
                            "Performance_Grade": grade,
                            "Parameters": f"SL={strat['stop_loss']*100}%, TP={strat['take_profit']*100}%, TS={strat['trailing_stop']*100}%",
                            "final_capital": round(final_cap, 2),
                            "Time_Period": f"{time_start} to {time_end}",
                        })
                except Exception as e:
                    logger.warning(f"{_asset} {strat['name']} error: {e}")

            all_results.extend(asset_results)

            if asset_results:
                best = max(asset_results, key=lambda x: x["ROI_per_annum"])
                avg_roi_a = sum(r["ROI_per_annum"] for r in asset_results) / len(asset_results)
                profitable = [r for r in asset_results if r["ROI_per_annum"] >= 20]
                per_asset_summary[_asset] = {
                    "best_strategy": best["name"],
                    "best_roi_annum": best["ROI_per_annum"],
                    "avg_roi_annum": round(avg_roi_a, 2),
                    "profitable": len(profitable),
                    "total": len(asset_results),
                }
            else:
                per_asset_summary[_asset] = {"status": "NO RESULTS"}

        if not all_results:
            self.send_message("No results from any asset.")
            return

        self._last_results = all_results

        # Build per-asset summary message
        msg_lines = [f"ELITE BACKTEST — ALL ASSETS ({timeframe})", "=" * 45, ""]
        msg_lines.append(f"{'Asset':<10} {'Best ROI/yr':<12} {'Avg ROI/yr':<12} {'Best Strategy'}")
        msg_lines.append("-" * 55)

        combined_roi_annums = []
        for asset in sorted(per_asset_summary.keys()):
            info = per_asset_summary[asset]
            if "status" in info:
                msg_lines.append(f"{asset:<10} {info['status']}")
                continue
            msg_lines.append(
                f"{asset:<10} {info['best_roi_annum']:>8.1f}%    {info['avg_roi_annum']:>8.1f}%    {info['best_strategy']}"
            )
            combined_roi_annums.append(info["avg_roi_annum"])

        # Combined stats
        if combined_roi_annums:
            combined_avg = sum(combined_roi_annums) / len(combined_roi_annums)
            combined_best = max(combined_roi_annums)
            total_profitable = sum(
                info.get("profitable", 0) for info in per_asset_summary.values() if "profitable" in info
            )
            total_tested = sum(
                info.get("total", 0) for info in per_asset_summary.values() if "total" in info
            )
            msg_lines.append("-" * 55)
            msg_lines.append(f"{'COMBINED':<10} {'':>12} {combined_avg:>8.1f}%")
            msg_lines.append("")
            msg_lines.append(f"Total strategies tested: {total_tested}")
            msg_lines.append(f"Profitable (ROI/yr >= 20%): {total_profitable}")
            msg_lines.append(f"Best asset avg ROI/yr: {combined_best:.1f}%")

        self.send_message("```\n" + "\n".join(msg_lines) + "\n```")

        # Top 10 overall
        all_results.sort(key=lambda x: x.get("ROI_per_annum", 0), reverse=True)
        top_msg = "TOP 10 OVERALL (by ROI/annum):\n\n"
        for i, r in enumerate(all_results[:10], 1):
            top_msg += (
                f"{i}. {r['name']} on {r['Asset']}\n"
                f"   ROI/yr={r['ROI_per_annum']}% | WR={r['win_rate']}% | "
                f"Gross DD={r['Gross_DD_Percent']}% | Net DD={r.get('Net_DD_Percent', 0)}% | Grade={r['Performance_Grade']}\n"
            )
        self.send_message(top_msg)

        # Save CSV
        csv_path = os.path.join(_ROOT, "batch_backtest_results.csv")
        df_csv = pd.DataFrame(all_results)
        df_csv.insert(0, "Rank", range(1, len(df_csv) + 1))
        df_csv.to_csv(csv_path, index=False)
        self.send_document(csv_path, caption=f"Elite all-assets results ({timeframe})")

    # ------------------------------------------------------------------ #
    # Walk-forward validation (/validate)
    # ------------------------------------------------------------------ #

    def _start_validate(self, args: list) -> str:
        """Walk-forward validation: train on 2020-2024, test on 2024-2026.
        Usage:
          /validate BTCUSDT_4h          — validate all 20 elite strategies
          /validate BTCUSDT_4h 1        — validate elite #1 only
          /validate BTCUSDT_4h 1,3,5    — validate specific ones
          /validate all 4h              — validate on all assets
        """
        if not args:
            return (
                "Walk-Forward Validation\n\n"
                "Splits data into:\n"
                "  Train: 2020-2024 (in-sample)\n"
                "  Test:  2024-2026 (out-of-sample)\n\n"
                "Only strategies that perform in BOTH periods are trustworthy.\n\n"
                "Usage:\n"
                "/validate BTCUSDT_4h — all elite strategies\n"
                "/validate BTCUSDT_4h 1 — elite #1 only\n"
                "/validate all 4h — all assets"
            )

        # Handle "all" assets
        if args[0].lower() == "all":
            if len(args) < 2:
                return "Usage: /validate all <timeframe>\nExample: /validate all 4h"
            tf = args[1].lower()
            symbols = [k for k in DATA_FILES if k.endswith(f"_{tf}")]
            if not symbols:
                return f"No data for timeframe {tf}"
            strat_selector = args[2] if len(args) > 2 else None
        else:
            symbol = _normalize_symbol(args[0])
            if symbol not in DATA_FILES:
                return f"Unknown symbol {symbol}"
            symbols = [symbol]
            strat_selector = args[1] if len(args) > 1 else None

        # Parse strategy selection
        selected_names = list(ELITE_STRATEGY_NAMES)
        if strat_selector:
            if "-" in strat_selector and strat_selector.replace("-", "").isdigit():
                a, b = strat_selector.split("-")
                selected_names = [ELITE_STRATEGY_NAMES[i] for i in range(int(a)-1, int(b)) if i < len(ELITE_STRATEGY_NAMES)]
            elif "," in strat_selector and all(p.strip().isdigit() for p in strat_selector.split(",")):
                indices = [int(p.strip())-1 for p in strat_selector.split(",")]
                selected_names = [ELITE_STRATEGY_NAMES[i] for i in indices if 0 <= i < len(ELITE_STRATEGY_NAMES)]
            elif strat_selector.isdigit():
                idx = int(strat_selector) - 1
                if 0 <= idx < len(ELITE_STRATEGY_NAMES):
                    selected_names = [ELITE_STRATEGY_NAMES[idx]]

        job_key = "validate"
        if job_key in self._running and self._running[job_key].is_alive():
            return "Validation is already running."

        t = threading.Thread(
            target=self._validate_worker,
            args=(symbols, selected_names),
            daemon=True,
        )
        self._running[job_key] = t
        t.start()

        return (
            f"Walk-Forward Validation started!\n"
            f"Assets: {len(symbols)}\n"
            f"Strategies: {len(selected_names)}\n"
            f"Train: 2020-01-01 to 2024-01-01\n"
            f"Test:  2024-01-01 to 2026-03-21\n\n"
            "Results will be sent when complete..."
        )

    def _validate_worker(self, symbols: list, selected_names: list) -> None:
        """Worker: run walk-forward validation on selected strategies."""
        try:
            self._validate_worker_inner(symbols, selected_names)
        except Exception as e:
            logger.error(f"Validate worker crashed: {e}", exc_info=True)
            self.send_message(f"Validation crashed: `{e}`\nRun /restart and retry.")

    def _validate_worker_inner(self, symbols: list, selected_names: list) -> None:
        import pandas as pd
        import numpy as _np
        from datetime import datetime as _dt

        TRAIN_SPLIT = "2024-01-01"

        target_names = set(selected_names)
        all_strats = get_all_strategies()
        elite_strats = [s for s in all_strats if s["name"] in target_names]

        if not elite_strats:
            self.send_message("No matching strategies found.")
            return

        # Load saved optimized params from central store
        saved_params = {}
        try:
            ranking_path = os.path.join(_ROOT, "storage", "elite_ranking.json")
            if os.path.exists(ranking_path):
                with open(ranking_path) as f:
                    _rdata = json.load(f)
                for r in _rdata.get("results", []):
                    if r.get("name") and r.get("sl"):
                        saved_params[r["name"]] = {
                            "stop_loss": r["sl"],
                            "take_profit": r["tp"],
                            "trailing_stop": r["ts"],
                        }
        except Exception:
            pass

        results = []  # each entry: {name, asset, train_roi, test_roi, verdict}

        for symbol in sorted(symbols):
            if self._should_stop():
                self.send_message("Stopped by user.")
                return
            _parts = symbol.rsplit("_", 1)
            _asset = _parts[0] if len(_parts) == 2 else symbol
            _tf = _parts[1] if len(_parts) == 2 else "?"

            df = load_data(symbol)
            if df is None:
                continue
            df = calculate_indicators(df)

            # Split into train/test
            if "timestamp" in df.columns:
                split_ts = pd.Timestamp(TRAIN_SPLIT)
                df_train = df[df["timestamp"] < split_ts].copy()
                df_test = df[df["timestamp"] >= split_ts].copy()
            else:
                split_idx = int(len(df) * 0.65)
                df_train = df.iloc[:split_idx].copy()
                df_test = df.iloc[split_idx:].copy()

            if len(df_train) < 100 or len(df_test) < 100:
                continue

            train_start = str(df_train["timestamp"].iloc[0])[:10] if "timestamp" in df_train.columns else "?"
            train_end = str(df_train["timestamp"].iloc[-1])[:10] if "timestamp" in df_train.columns else "?"
            test_start = str(df_test["timestamp"].iloc[0])[:10] if "timestamp" in df_test.columns else "?"
            test_end = str(df_test["timestamp"].iloc[-1])[:10] if "timestamp" in df_test.columns else "?"

            try:
                train_years = max((_dt.fromisoformat(train_end) - _dt.fromisoformat(train_start)).days / 365.25, 0.01)
                test_years = max((_dt.fromisoformat(test_end) - _dt.fromisoformat(test_start)).days / 365.25, 0.01)
            except Exception:
                train_years, test_years = 4.0, 2.0

            self.send_message(f"Validating {_asset} {_tf}...")

            for strat in elite_strats:
                try:
                    _p = saved_params.get(strat["name"], {})
                    _sl = _p.get("stop_loss", strat["stop_loss"])
                    _tp = _p.get("take_profit", strat["take_profit"])
                    _ts = _p.get("trailing_stop", strat["trailing_stop"])

                    # Train period
                    df_tr = apply_strategy(df_train.copy(), strat["strategies"], strat.get("min_agreement", 1))
                    tr_cap, tr_trades = _batch_run_backtest(df_tr, _sl, _tp, _ts)

                    # Test period
                    df_te = apply_strategy(df_test.copy(), strat["strategies"], strat.get("min_agreement", 1))
                    te_cap, te_trades = _batch_run_backtest(df_te, _sl, _tp, _ts)

                    if len(tr_trades) < 5 or len(te_trades) < 3:
                        continue

                    tr_roi = (tr_cap - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
                    te_roi = (te_cap - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
                    tr_roi_a = ((tr_cap / INITIAL_CAPITAL) ** (1 / train_years) - 1) * 100
                    te_roi_a = ((te_cap / INITIAL_CAPITAL) ** (1 / test_years) - 1) * 100

                    tr_wr = len([t for t in tr_trades if t["pnl"] > 0]) / len(tr_trades) * 100
                    te_wr = len([t for t in te_trades if t["pnl"] > 0]) / len(te_trades) * 100

                    # Verdict
                    if te_roi_a >= 20 and tr_roi_a >= 20:
                        verdict = "PASS"
                    elif te_roi_a >= 0 and tr_roi_a >= 20:
                        verdict = "WEAK"
                    elif te_roi_a < 0 and tr_roi_a >= 20:
                        verdict = "OVERFIT"
                    elif tr_roi_a < 0 and te_roi_a >= 0:
                        verdict = "REVERSED"
                    else:
                        verdict = "FAIL"

                    results.append({
                        "name": strat["name"],
                        "Asset": _asset,
                        "Timeframe": _tf,
                        "Train_ROI_Annum": round(tr_roi_a, 2),
                        "Test_ROI_Annum": round(te_roi_a, 2),
                        "Train_WR": round(tr_wr, 1),
                        "Test_WR": round(te_wr, 1),
                        "Train_Trades": len(tr_trades),
                        "Test_Trades": len(te_trades),
                        "Train_Period": f"{train_start} to {train_end}",
                        "Test_Period": f"{test_start} to {test_end}",
                        "Verdict": verdict,
                    })
                except Exception as e:
                    logger.warning(f"Validate {_asset} {strat['name']} error: {e}")

        if not results:
            self.send_message("No validation results produced.")
            return

        self._last_results = results

        # Summary counts
        verdicts = {"PASS": 0, "WEAK": 0, "OVERFIT": 0, "REVERSED": 0, "FAIL": 0}
        for r in results:
            verdicts[r["Verdict"]] = verdicts.get(r["Verdict"], 0) + 1

        # Build message
        msg = (
            "WALK-FORWARD VALIDATION RESULTS\n"
            "================================\n\n"
            f"PASS = ROI/yr >= 20% in BOTH periods (trustworthy)\n"
            f"WEAK = Profitable in test but < 20%/yr\n"
            f"OVERFIT = Good in train, negative in test\n"
            f"FAIL = Poor in both periods\n\n"
            f"Results: {verdicts['PASS']} PASS | {verdicts['WEAK']} WEAK | "
            f"{verdicts['OVERFIT']} OVERFIT | {verdicts['FAIL']} FAIL\n\n"
        )

        # Show PASS results first
        passed = [r for r in results if r["Verdict"] == "PASS"]
        if passed:
            passed.sort(key=lambda x: x["Test_ROI_Annum"], reverse=True)
            msg += "PASSED STRATEGIES (deploy-ready):\n"
            for r in passed:
                msg += (
                    f"  {r['name']} ({r['Asset']} {r['Timeframe']})\n"
                    f"    Train: {r['Train_ROI_Annum']}%/yr WR={r['Train_WR']}% ({r['Train_Trades']} trades)\n"
                    f"    Test:  {r['Test_ROI_Annum']}%/yr WR={r['Test_WR']}% ({r['Test_Trades']} trades)\n"
                )
        else:
            msg += "No strategies passed validation.\n"

        # Show OVERFIT warnings
        overfit = [r for r in results if r["Verdict"] == "OVERFIT"]
        if overfit:
            msg += f"\nOVERFIT WARNING ({len(overfit)} strategies):\n"
            for r in overfit[:5]:
                msg += (
                    f"  {r['name']} ({r['Asset']}): "
                    f"Train={r['Train_ROI_Annum']}%/yr -> Test={r['Test_ROI_Annum']}%/yr\n"
                )

        self.send_message(msg)

        # Save CSV
        csv_path = os.path.join(_ROOT, "validation_results.csv")
        df_csv = pd.DataFrame(results)
        df_csv.to_csv(csv_path, index=False)
        self.send_document(csv_path, caption="Walk-forward validation results")

    # ------------------------------------------------------------------ #
    # Auto optimization (/auto)
    # ------------------------------------------------------------------ #

    def _start_auto(self, args: list) -> str:
        """Autonomous optimization loop.
        Phase 1: Run all elite strategies on each asset → top 10 per asset
        Phase 2: Find universal winners across assets
        Phase 3: Optimize SL/TP/TS for universal winners
        Phase 4: Report final ranking

        Usage: /auto 4h  or  /auto 1h  or  /auto (defaults to 4h)
        """
        tf = args[0].lower() if args else "4h"
        if tf not in ("15m", "1h", "4h"):
            return "Usage: /auto <timeframe>\nExample: /auto 4h\nTimeframes: 15m, 1h, 4h"

        symbols = [k for k in DATA_FILES if k.endswith(f"_{tf}")]
        if not symbols:
            return f"No data for timeframe {tf}"

        job_key = "auto"
        if job_key in self._running and self._running[job_key].is_alive():
            return "Auto optimization is already running. Please wait."

        t = threading.Thread(
            target=self._auto_worker,
            args=(symbols, tf),
            daemon=True,
        )
        self._running[job_key] = t
        t.start()

        all_count = len(get_all_strategies())
        return (
            f"AUTO OPTIMIZATION STARTED\n\n"
            f"Timeframe: {tf}\n"
            f"Assets: {len(symbols)}\n"
            f"Strategies: ALL {all_count}\n\n"
            f"Phase 1: Test ALL {all_count} strategies on each asset\n"
            f"Phase 2: Pick top 20 universal winners\n"
            f"Phase 3: Optimize SL/TP/TS for top 20\n"
            f"Phase 4: Final ranking + save to elite_ranking.json\n\n"
            "This will take a while. Results sent automatically."
        )

    def _auto_worker(self, symbols: list, timeframe: str) -> None:
        """Worker: autonomous 4-phase optimization."""
        try:
            import pandas as pd
            import numpy as _np
            from datetime import datetime as _dt
            from collections import Counter

            global ELITE_STRATEGY_NAMES

            self.send_message("Initializing auto optimization...")

            all_strats = get_all_strategies()

            if not all_strats:
                self.send_message("No strategies found.")
                return

            # Limit Phase 1 to top 50 strategies (by elite ranking or first 50)
            _MAX_PHASE1 = 50
            if len(ELITE_STRATEGY_NAMES) >= _MAX_PHASE1:
                # Use saved elite ranking as filter
                elite_set = set(ELITE_STRATEGY_NAMES[:_MAX_PHASE1])
                elite_strats = [s for s in all_strats if s["name"] in elite_set]
                # Fill remaining slots if some names didn't match
                if len(elite_strats) < _MAX_PHASE1:
                    used = {s["name"] for s in elite_strats}
                    for s in all_strats:
                        if s["name"] not in used:
                            elite_strats.append(s)
                            used.add(s["name"])
                        if len(elite_strats) >= _MAX_PHASE1:
                            break
            else:
                elite_strats = all_strats[:_MAX_PHASE1]

            self.send_message(
                f"Found {len(all_strats)} total strategies.\n"
                f"Phase 1 will test top {len(elite_strats)}, then pick top 20 for optimization."
            )

            # ================================================
            # PHASE 1: Run all elite on each asset → top 10
            # ================================================
            # Load checkpoint if resuming
            ckpt = _load_checkpoint("auto", timeframe)
            top10_per_asset = ckpt.get("top10_per_asset", {})
            all_phase1 = ckpt.get("all_phase1", [])
            done_assets = set(ckpt.get("done_assets", []))

            if done_assets:
                self.send_message(f"Resuming Phase 1 — {len(done_assets)} assets already done, continuing...")
            else:
                self.send_message("PHASE 1: Testing all strategies on each asset...")

            for symbol in sorted(symbols):
                if self._should_stop():
                    self.send_message("Stopped by user. Progress saved — use /auto to resume.")
                    return
                _parts = symbol.rsplit("_", 1)
                _asset = _parts[0] if len(_parts) == 2 else symbol

                # Skip already-completed assets
                if _asset in done_assets:
                    continue

                df = load_data(symbol)
                if df is None:
                    continue
                df = calculate_indicators(df)

                # Get time range
                if "timestamp" in df.columns:
                    time_start = str(df["timestamp"].iloc[0])[:10]
                    time_end = str(df["timestamp"].iloc[-1])[:10]
                else:
                    time_start, time_end = "unknown", "unknown"
                try:
                    _years = max((_dt.fromisoformat(time_end) - _dt.fromisoformat(time_start)).days / 365.25, 0.01)
                except Exception:
                    _years = 1.0

                asset_results = []
                for strat in elite_strats:
                    try:
                        df_copy = apply_strategy(df.copy(), strat["strategies"], strat.get("min_agreement", 1))
                        final_cap, trades = _batch_run_backtest(df_copy, strat["stop_loss"], strat["take_profit"], strat["trailing_stop"])
                        if len(trades) >= 5:
                            wins = [t for t in trades if t["pnl"] > 0]
                            roi = (final_cap - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
                            roi_a = ((final_cap / INITIAL_CAPITAL) ** (1 / _years) - 1) * 100 if _years > 0 else 0
                            wr = len(wins) / len(trades) * 100
                            total_w = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                            total_l = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                            pf = total_w / total_l if total_l > 0 else 0
                            score = _compute_score(roi, wr, pf, 0)

                            asset_results.append({
                                "name": strat["name"],
                                "asset": _asset,
                                "roi_annum": round(roi_a, 2),
                                "roi": round(roi, 2),
                                "win_rate": round(wr, 2),
                                "pf": round(pf, 2),
                                "score": round(score, 2),
                                "trades": len(trades),
                            })
                    except Exception:
                        pass

                asset_results.sort(key=lambda x: x["score"], reverse=True)
                top10 = asset_results[:10]
                top10_per_asset[_asset] = top10
                all_phase1.extend(asset_results)
                done_assets.add(_asset)

                # Save checkpoint after each asset
                _save_checkpoint("auto", timeframe, {
                    "phase": 1,
                    "top10_per_asset": top10_per_asset,
                    "all_phase1": all_phase1,
                    "done_assets": list(done_assets),
                })

                # Report top 3 per asset
                if top10:
                    msg = f"{_asset} ({len(done_assets)}/{len(symbols)}): "
                    for r in top10[:3]:
                        msg += f"{r['name']}({r['roi_annum']}%/yr) "
                    self.send_message(msg)

            if not all_phase1:
                self.send_message("Phase 1 produced no results.")
                return

            # ================================================
            # PHASE 2: Find universal winners
            # ================================================
            self.send_message("PHASE 2: Finding universal winners across assets...")

            # Count how many assets each strategy appears in top 10
            strat_counter = Counter()
            strat_scores = {}  # name → list of scores across assets
            for asset, top10 in top10_per_asset.items():
                for r in top10:
                    strat_counter[r["name"]] += 1
                    if r["name"] not in strat_scores:
                        strat_scores[r["name"]] = []
                    strat_scores[r["name"]].append(r["score"])

            # Universal winners: appear in top 10 of 3+ assets, sorted by avg score
            universal = []
            for name, count in strat_counter.most_common():
                if count >= 2:
                    avg_score = sum(strat_scores[name]) / len(strat_scores[name])
                    universal.append({"name": name, "assets": count, "avg_score": round(avg_score, 2)})

            if not universal:
                # Fall back to top 10 by avg score
                for name in strat_scores:
                    avg_score = sum(strat_scores[name]) / len(strat_scores[name])
                    universal.append({"name": name, "assets": len(strat_scores[name]), "avg_score": round(avg_score, 2)})

            universal.sort(key=lambda x: x["avg_score"], reverse=True)
            universal = universal[:20]

            msg = "Universal Winners (top 20 across assets):\n"
            for i, u in enumerate(universal, 1):
                msg += f"  {i}. {u['name']} — {u['assets']} assets, avg score={u['avg_score']}\n"
            self.send_message(msg)

            # ================================================
            # PHASE 3: Optimize SL/TP/TS for universal winners
            # ================================================
            self.send_message("PHASE 3: Optimizing parameters for universal winners...")

            universal_names = {u["name"] for u in universal}
            universal_strats = [s for s in elite_strats if s["name"] in universal_names]

            # Load Phase 3 checkpoint if exists
            p3_ckpt = ckpt.get("phase3_done", [])
            optimized_results = ckpt.get("optimized_results", [])
            p3_done_names = {r["name"] for r in optimized_results}

            total_strats = len(universal_strats)
            for idx, strat in enumerate(universal_strats, 1):
                # Skip already-optimized strategies
                if strat["name"] in p3_done_names:
                    continue

                # Progress message every 2 strategies
                if idx % 2 == 1:
                    self.send_message(f"Phase 3: Optimizing {idx}/{total_strats} strategies...")

                if self._should_stop():
                    _save_checkpoint("auto", timeframe, {
                        "phase": 3,
                        "top10_per_asset": top10_per_asset,
                        "all_phase1": all_phase1,
                        "done_assets": list(done_assets),
                        "universal": universal,
                        "optimized_results": optimized_results,
                        "phase3_done": list(p3_done_names),
                    })
                    self.send_message("Stopped by user. Phase 3 progress saved — use /auto to resume.")
                    return
                
                best_avg_score = -999
                best_params = {"sl": strat["stop_loss"], "tp": strat["take_profit"], "ts": strat["trailing_stop"]}

                # Test each param combo across ALL assets
                for _ in range(_OPT_TRIALS):
                    sl = random.choice(_SL_CANDIDATES)
                    tp = random.choice(_TP_CANDIDATES)
                    ts = random.choice(_TS_CANDIDATES)
                    if tp < sl * 1.5:
                        continue

                    trial_scores = []
                    for symbol in symbols:
                        df = load_data(symbol)
                        if df is None:
                            continue
                        df = calculate_indicators(df)
                        try:
                            df_copy = apply_strategy(df.copy(), strat["strategies"], strat.get("min_agreement", 1))
                            final_cap, trades = _batch_run_backtest(df_copy, sl, tp, ts)
                            if len(trades) >= 5:
                                wins = [t for t in trades if t["pnl"] > 0]
                                roi = (final_cap - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
                                wr = len(wins) / len(trades) * 100
                                total_w = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                                total_l = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                                pf = total_w / total_l if total_l > 0 else 0
                                trial_scores.append(_compute_score(roi, wr, pf, 0))
                        except Exception:
                            pass

                    if trial_scores:
                        avg = sum(trial_scores) / len(trial_scores)
                        if avg > best_avg_score:
                            best_avg_score = avg
                            best_params = {"sl": sl, "tp": tp, "ts": ts}

                optimized_results.append({
                    "name": strat["name"],
                    "score": round(best_avg_score, 2),
                    "sl": best_params["sl"],
                    "tp": best_params["tp"],
                    "ts": best_params["ts"],
                })
                p3_done_names.add(strat["name"])

                # Save checkpoint after each strategy
                _save_checkpoint("auto", timeframe, {
                    "phase": 3,
                    "top10_per_asset": top10_per_asset,
                    "all_phase1": all_phase1,
                    "done_assets": list(done_assets),
                    "universal": universal,
                    "optimized_results": optimized_results,
                    "phase3_done": list(p3_done_names),
                })

            optimized_results.sort(key=lambda x: x["score"], reverse=True)

            # ================================================
            # PHASE 4: Final ranking & report
            # ================================================
            self.send_message("PHASE 4: Final ranking...")

            # Update elite order
            new_order = [r["name"] for r in optimized_results]
            remaining = [n for n in ELITE_STRATEGY_NAMES if n not in new_order]
            ELITE_STRATEGY_NAMES = new_order + remaining
            _save_elite_ranking(ELITE_STRATEGY_NAMES, optimized_results)

            # Clear checkpoint — auto completed successfully
            _clear_checkpoint("auto", timeframe)

            # Final report
            msg = (
                "*AUTO OPTIMIZATION COMPLETE*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"TF: `{timeframe}` · Assets: `{len(symbols)}` · "
                f"Strategies: `{len(elite_strats)}` · Trials: `{_OPT_TRIALS}`/strat\n\n"
                "*Optimized Ranking:*\n\n"
            )
            for i, r in enumerate(optimized_results, 1):
                score = r.get('score', 0)
                if i == 1 and score > 80:
                    tag = "☄️"
                elif i == 1:
                    tag = "🌋"
                elif i == 2:
                    tag = "⛰️"
                elif i == 3:
                    tag = "🌊"
                else:
                    tag = f"{i}."
                msg += (
                    f"{tag} {r['name']}\n"
                    f"   Score=`{r['score']}` | SL=`{r['sl']*100:.1f}%` | TP=`{r['tp']*100:.1f}%` | TS=`{r['ts']*100:.1f}%`\n"
                )

            self.send_message(msg)

            # Now run final validation with optimized params
            self.send_message("_Running final validation with optimized params..._")

            final_results = []
            for symbol in sorted(symbols):
                if self._should_stop():
                    self.send_message("Stopped by user.")
                    return
                _parts = symbol.rsplit("_", 1)
                _asset = _parts[0] if len(_parts) == 2 else symbol

                df = load_data(symbol)
                if df is None:
                    continue
                df = calculate_indicators(df)

                if "timestamp" in df.columns:
                    time_start = str(df["timestamp"].iloc[0])[:10]
                    time_end = str(df["timestamp"].iloc[-1])[:10]
                else:
                    time_start, time_end = "unknown", "unknown"
                try:
                    _years = max((_dt.fromisoformat(time_end) - _dt.fromisoformat(time_start)).days / 365.25, 0.01)
                except Exception:
                    _years = 1.0

                for opt_r in optimized_results:
                    strat = next((s for s in elite_strats if s["name"] == opt_r["name"]), None)
                    if not strat:
                        continue
                    try:
                        df_copy = apply_strategy(df.copy(), strat["strategies"], strat.get("min_agreement", 1))
                        final_cap, trades = _batch_run_backtest(df_copy, opt_r["sl"], opt_r["tp"], opt_r["ts"])
                        if len(trades) >= 5:
                            import numpy as _np2
                            wins = [t for t in trades if t["pnl"] > 0]
                            losses_list = [t for t in trades if t["pnl"] <= 0]
                            roi = (final_cap - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
                            roi_a = ((final_cap / INITIAL_CAPITAL) ** (1 / _years) - 1) * 100 if _years > 0 else 0
                            wr = len(wins) / len(trades) * 100
                            net = final_cap - INITIAL_CAPITAL
                            total_w = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                            total_l = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                            pf = total_w / total_l if total_l > 0 else 0
                            returns = [t.get("return_pct", t["pnl"] / INITIAL_CAPITAL * 100) for t in trades]
                            avg_trade = sum(returns) / len(returns) if returns else 0
                            # TV-style daily Sharpe
                            from collections import defaultdict as _dd_a
                            _daily_a = _dd_a(float)
                            for t in trades:
                                _da = t.get("exit_date", "")[:10]
                                if _da:
                                    _daily_a[_da] += t["pnl"] / INITIAL_CAPITAL * 100
                            _td = max(int(_years * 365), 30)
                            _ad = [0.0] * _td
                            for _ii, (_dd2, _vv) in enumerate(sorted(_daily_a.items())):
                                if _ii < _td:
                                    _ad[_ii] = _vv
                            _mm = _np2.mean(_ad)
                            _ss = _np2.std(_ad) if len(_ad) > 1 else 1
                            sharpe = (_mm / _ss) * _np2.sqrt(252) if _ss > 0 else 0
                            # Drawdowns
                            equity = INITIAL_CAPITAL
                            peak = equity
                            gross_dd = 0
                            gross_dd_date = "N/A"
                            gross_dd_capital = INITIAL_CAPITAL
                            min_capital = INITIAL_CAPITAL
                            net_dd_date = "N/A"
                            for t in trades:
                                equity += t["pnl"]
                                peak = max(peak, equity)
                                dd = (peak - equity) / peak * 100
                                if dd > gross_dd:
                                    gross_dd = dd
                                    gross_dd_date = t.get("exit_date", "N/A")
                                    gross_dd_capital = round(equity, 2)
                                if equity < min_capital:
                                    min_capital = equity
                                    net_dd_date = t.get("exit_date", "N/A")
                            net_dd = max(0, (INITIAL_CAPITAL - min_capital) / INITIAL_CAPITAL * 100)
                            grade = _grade_performance(roi, wr / 100, pf)
                            deploy = _deployment_status(grade, len(trades), gross_dd)
                            score = _compute_score(roi, wr, pf, gross_dd)

                            final_results.append({
                                "Rank": 0,
                                "name": opt_r["name"],
                                "Strategy": ", ".join(strat["strategies"]),
                                "Asset": _asset,
                                "Timeframe": timeframe,
                                "Initial_Capital_USD": INITIAL_CAPITAL,
                                "Final_Capital_USD": round(final_cap, 2),
                                "Net_Profit_USD": round(net, 2),
                                "ROI_per_annum": round(roi_a, 2),
                                "ROI_Percent": round(roi, 2),
                                "Total_Trades": len(trades),
                                "Winning_Trades": len(wins),
                                "Losing_Trades": len(losses_list),
                                "Win_Rate_Percent": round(wr, 2),
                                "Profit_Factor": round(pf, 2),
                                "Sharpe_Ratio": round(sharpe, 2),
                                "Avg_Trade_Percent": round(avg_trade, 4),
                                "Gross_DD_Percent": round(gross_dd, 2),
                                "Gross_DD_Date": gross_dd_date,
                                "Gross_DD_Capital": gross_dd_capital,
                                "Net_DD_Percent": round(net_dd, 2),
                                "Net_DD_Date": net_dd_date,
                                "Capital_At_Net_DD": round(min_capital, 2),
                                "Performance_Grade": grade,
                                "Deployment_Status": deploy,
                                "Score": round(score, 2),
                                "Data_Source": "Binance Spot",
                                "Time_Period": f"{time_start} to {time_end}",
                                "Time_Start": time_start,
                                "Time_End": time_end,
                                "Fees_Exchange": f"{FEE*100}%",
                                "Candle_Period": timeframe,
                                "Parameters": f"SL={opt_r['sl']*100:.1f}%, TP={opt_r['tp']*100:.1f}%, TS={opt_r['ts']*100:.1f}%",
                            })
                    except Exception:
                        pass

            if final_results:
                final_results.sort(key=lambda x: x["ROI_per_annum"], reverse=True)
                for i, r in enumerate(final_results, 1):
                    r["Rank"] = i

                self._last_results = final_results

                # Save results to CSV for persistence across restarts
                try:
                    import pandas as _pd_save
                    _csv_path = os.path.join(_ROOT, f"auto_results_{timeframe}.csv")
                    _pd_save.DataFrame(final_results).to_csv(_csv_path, index=False)
                except Exception:
                    pass

                # Per-strategy avg across assets
                strat_avg = {}
                for r in final_results:
                    if r["name"] not in strat_avg:
                        strat_avg[r["name"]] = []
                    strat_avg[r["name"]].append(r["ROI_per_annum"])

                # Aggregate per-strategy: avg ROI, avg GDD, avg NDD
                strat_dd = {}
                for r in final_results:
                    if r["name"] not in strat_dd:
                        strat_dd[r["name"]] = {"gdd": [], "ndd": []}
                    strat_dd[r["name"]]["gdd"].append(r.get("Gross_DD_Percent", 0))
                    strat_dd[r["name"]]["ndd"].append(r.get("Net_DD_Percent", 0))

                msg = "*FINAL RESULTS* — per strategy across ALL assets:\n\n"
                ranked = sorted(strat_avg.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True)
                for i, (name, rois) in enumerate(ranked, 1):
                    avg = sum(rois) / len(rois)
                    best = max(rois)
                    worst = min(rois)
                    avg_gdd = sum(strat_dd.get(name, {}).get("gdd", [0])) / max(len(rois), 1)
                    avg_ndd = sum(strat_dd.get(name, {}).get("ndd", [0])) / max(len(rois), 1)
                    verdict = _verdict_line(avg, "")
                    msg += (
                        f"{i}. *{name}*\n"
                        f"   Avg=`{avg:.1f}%/yr` | Best=`{best:.1f}%` | Worst=`{worst:.1f}%` | Assets=`{len(rois)}`\n"
                        f"   GrossDD=`{avg_gdd:.1f}%` | NetDD=`{avg_ndd:.1f}%`\n"
                        f"   {verdict}\n"
                    )
                self.send_message(msg)

                # Save CSV
                csv_path = os.path.join(_ROOT, "auto_optimization_results.csv")
                df_csv = pd.DataFrame(final_results)
                df_csv.to_csv(csv_path, index=False)
                self.send_document(csv_path, caption="Auto optimization — full results")

            self.send_message("Auto optimization complete! Elite ranking updated.")
        
        except Exception as e:
            import traceback
            error_msg = f"AUTO OPTIMIZATION ERROR: {str(e)}\n\n{traceback.format_exc()}"
            self.send_message(error_msg[:4000])  # Telegram limit
            print(error_msg)  # Also print to server logs

    # ------------------------------------------------------------------ #
    # Pine Script backtest (/pine)
    # ------------------------------------------------------------------ #

    def _start_pine_backtest(self, args: list) -> str:
        """Handle /pine command. Two-step flow:
        1. /pine BTCUSDT 1h  → bot asks user to paste Pine Script
        2. User pastes script → bot runs backtest and returns results
        """
        if not args:
            return (
                "*Usage:* `/pine <SYMBOL> <TIMEFRAME>`\n\n"
                "Example:\n"
                "  `/pine BTCUSDT 1h`\n"
                "  `/pine ETHUSDT 4h`\n\n"
                "After sending the command, paste your Pine Script code "
                "and the bot will backtest it."
            )

        symbol = args[0].upper()
        timeframe = args[1].lower() if len(args) > 1 else "1h"

        # Validate timeframe
        valid_tf = ["15m", "1h", "4h", "1d"]
        if timeframe not in valid_tf:
            return f"Invalid timeframe `{timeframe}`. Use: {', '.join(valid_tf)}"

        # Store pending state for this chat
        chat_id = self._active_chat_id or self.chat_id
        self._pine_pending[chat_id] = {
            "symbol": symbol,
            "timeframe": timeframe,
        }

        return (
            f"*Ready to backtest on `{symbol}` `{timeframe}`*\n\n"
            "Now paste your Pine Script code below.\n"
            "The bot will parse it and run a backtest automatically."
        )

    def _handle_pine_script(self, text: str) -> str:
        """Process a pasted Pine Script and run backtest."""
        chat_id = self._active_chat_id or self.chat_id
        pending = self._pine_pending.pop(chat_id, None)

        if not pending:
            return None  # not in pine mode

        symbol = pending["symbol"]
        timeframe = pending["timeframe"]

        self.send_message(
            f"_Parsing Pine Script and running backtest on "
            f"`{symbol}` `{timeframe}`..._"
        )

        try:
            result = run_pine_backtest(
                pine_script=text,
                symbol=symbol,
                timeframe=timeframe,
            )
            return format_pine_result(result)
        except Exception as e:
            logger.error(f"Pine backtest error: {e}")
            return f"*Pine Script Backtest Error:*\n`{e}`"

    # ------------------------------------------------------------------ #
    # Single strategy test (/test)
    # ------------------------------------------------------------------ #

    def _start_single_test(self, args: list) -> str:
        """Parse /test args and run a single strategy backtest.

        Usage:
            /test BTCUSDT 4h RSI
            /test ETHUSDT 1h MACD fast:8 slow:21
            /test SOLUSDT 4h EMA_RSI_Momentum
        """
        if len(args) < 3:
            return (
                "*Usage:* `/test <SYMBOL> <TIMEFRAME> <STRATEGY> [params]`\n\n"
                "*Built-in strategies:*\n"
                "  RSI, MACD, MA, EMA, ATR, STOCH, BB, VWAP\n\n"
                "*Batch strategies (230+):*\n"
                "  Use the exact name, e.g. `EMA_RSI_Momentum`\n\n"
                "*Custom params (optional):*\n"
                "  `key:value` pairs after strategy name\n"
                "  e.g. `/test BTCUSDT 4h RSI rsi_period:10 oversold:25`\n\n"
                "*Examples:*\n"
                "  `/test BTCUSDT 4h RSI`\n"
                "  `/test ETHUSDT 1h MACD fast:8 slow:21`\n"
                "  `/test SOLUSDT 4h EMA_RSI_Momentum`"
            )

        symbol = args[0].upper()
        if not symbol.endswith("USDT"):
            symbol += "USDT"

        timeframe = args[1].lower()
        if timeframe not in ("15m", "1h", "4h", "1d"):
            return f"Invalid timeframe `{timeframe}`. Use: 15m, 1h, 4h, 1d"

        strategy_name = args[2]

        # Parse optional key:value params
        custom_params = {}
        for arg in args[3:]:
            if ":" in arg:
                k, v = arg.split(":", 1)
                try:
                    custom_params[k] = float(v) if "." in v else int(v)
                except ValueError:
                    custom_params[k] = v

        job_key = f"test_{symbol}_{timeframe}_{strategy_name}"
        if job_key in self._running and self._running[job_key].is_alive():
            return "This test is already running. Please wait."

        t = threading.Thread(
            target=self._single_test_worker,
            args=(symbol, timeframe, strategy_name, custom_params),
            daemon=True,
        )
        self._running[job_key] = t
        t.start()

        params_str = (
            "\n".join(f"  {k}: `{v}`" for k, v in custom_params.items())
            if custom_params else "  (defaults)"
        )
        return (
            f"*Test launched*\n"
            f"`{symbol}` · `{timeframe}` · `{strategy_name}`\n"
            f"Params:\n{params_str}\n\n"
            "_Crunching numbers — results incoming..._"
        )

    def _single_test_worker(
        self, symbol: str, timeframe: str, strategy_name: str, custom_params: dict
    ) -> None:
        """Worker: runs a single strategy backtest and sends all 26 parameters."""
        try:
            self._single_test_worker_inner(symbol, timeframe, strategy_name, custom_params)
        except Exception as e:
            logger.error(f"Single test worker crashed: {e}", exc_info=True)
            self.send_message(f"Test crashed: `{e}`\nRun /restart and retry.")

    def _single_test_worker_inner(
        self, symbol: str, timeframe: str, strategy_name: str, custom_params: dict
    ) -> None:
        from datetime import timedelta

        # ── Determine if built-in or batch strategy ────────────────────────
        builtin_cls = BUILTIN_STRATEGIES.get(strategy_name.upper())
        batch_strat = None if builtin_cls else _find_batch_strategy_by_name(strategy_name)

        if not builtin_cls and not batch_strat:
            self.send_message(
                f"Strategy `{strategy_name}` not found.\n\n"
                f"*Built-in:* {', '.join(BUILTIN_STRATEGIES.keys())}\n"
                f"*Batch:* use exact name from 230+ strategies"
            )
            return

        # ── Fetch data ─────────────────────────────────────────────────────
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=self._opt_lookback_years * 365)
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")

        self.send_message(
            f"_Fetching `{symbol}` `{timeframe}` data "
            f"({start_str} → {end_str})..._"
        )

        try:
            fetcher = DataFetcher(cache_enabled=True)
            df = fetcher.fetch_with_pagination(
                symbol=symbol, timeframe=timeframe,
                start_date=start_str, end_date=end_str,
            )
            if df is None or df.empty:
                self.send_message(f"No data found for `{symbol}` `{timeframe}`.")
                return
        except Exception as e:
            self.send_message(f"Data fetch error: `{e}`")
            return

        data_source = "Binance API (cached parquet)"
        time_start = str(df["timestamp"].iloc[0] if "timestamp" in df.columns else start_str)
        time_end = str(df["timestamp"].iloc[-1] if "timestamp" in df.columns else end_str)

        # ── Run backtest ───────────────────────────────────────────────────
        self.send_message("_Running backtest..._")

        try:
            if builtin_cls:
                # Built-in strategy via BacktestEngine
                engine = BacktestEngine(
                    initial_capital=COMPREHENSIVE_INITIAL_CAPITAL,
                    commission=COMPREHENSIVE_COMMISSION,
                )
                strategy_obj = builtin_cls(custom_params or None)
                result: BacktestResult = engine.run_backtest(
                    strategy_obj, symbol, timeframe, start_str, end_str,
                )
                strat_display_name = strategy_name.upper()
                strat_params = custom_params or strategy_obj.params
                fees = COMPREHENSIVE_COMMISSION * 100  # as percent

                # Extract values from BacktestResult
                initial_cap = COMPREHENSIVE_INITIAL_CAPITAL
                final_cap = initial_cap + result.total_return
                net_profit = result.total_return
                roi_annum = result.roi_per_annum
                roi_pct = result.total_return_pct
                total_trades = result.total_trades
                winning = result.winning_trades
                losing = result.losing_trades
                win_rate = result.win_rate * 100
                pf = result.profit_factor
                sharpe = result.sharpe_ratio
                avg_trade = result.avg_trade_pct
                drawdown = result.max_drawdown

            else:
                # Batch strategy via run_strategies_batch engine
                df_ind = calculate_indicators(df.copy())
                
                # Try to load optimized parameters from /auto results
                optimized_params = _load_optimized_strategy_params(batch_strat.get("name", strategy_name))
                
                # Use optimized params if available, otherwise use defaults
                if optimized_params:
                    sl = custom_params.get("stop_loss", optimized_params.get("stop_loss", batch_strat["stop_loss"]))
                    tp = custom_params.get("take_profit", optimized_params.get("take_profit", batch_strat["take_profit"]))
                    ts = custom_params.get("trailing_stop", optimized_params.get("trailing_stop", batch_strat["trailing_stop"]))
                else:
                    sl = custom_params.get("stop_loss", batch_strat["stop_loss"])
                    tp = custom_params.get("take_profit", batch_strat["take_profit"])
                    ts = custom_params.get("trailing_stop", batch_strat["trailing_stop"])
                
                ma = custom_params.get("min_agreement", batch_strat.get("min_agreement", 1))

                df_sig = apply_strategy(df_ind, batch_strat["strategies"], ma)
                final_cap_raw, trades = _batch_run_backtest(df_sig, sl, tp, ts)

                strat_display_name = batch_strat["name"]
                strat_params = {
                    "indicators": ", ".join(batch_strat["strategies"]),
                    "stop_loss": f"{sl*100:.1f}%",
                    "take_profit": f"{tp*100:.1f}%",
                    "trailing_stop": f"{ts*100:.1f}%",
                    "min_agreement": ma,
                }
                strat_params.update({k: v for k, v in custom_params.items()
                                     if k not in ("stop_loss", "take_profit",
                                                  "trailing_stop", "min_agreement")})
                fees = FEE * 100
                initial_cap = INITIAL_CAPITAL
                final_cap = final_cap_raw
                net_profit = final_cap - initial_cap
                roi_pct = (net_profit / initial_cap) * 100

                total_trades = len(trades)
                wins_list = [t for t in trades if t["pnl"] > 0]
                losses_list = [t for t in trades if t["pnl"] <= 0]
                winning = len(wins_list)
                losing = len(losses_list)
                win_rate = (winning / total_trades * 100) if total_trades else 0

                total_wins_usd = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                total_losses_usd = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                pf = total_wins_usd / total_losses_usd if total_losses_usd else 0

                avg_trade = (
                    sum(t["return_pct"] for t in trades) / total_trades
                    if total_trades else 0
                )

                # Sharpe (from trade returns)
                if total_trades >= 2:
                    ret_arr = np.array([t["return_pct"] for t in trades])
                    sharpe = (
                        (np.mean(ret_arr) / np.std(ret_arr)) * np.sqrt(total_trades)
                        if np.std(ret_arr) > 0 else 0
                    )
                else:
                    sharpe = 0

                # Drawdown from equity curve
                equity = [initial_cap]
                running = initial_cap
                for t in trades:
                    running += t["pnl"]
                    equity.append(running)
                eq = np.array(equity)
                peak = np.maximum.accumulate(eq)
                dd = ((eq - peak) / peak) * 100
                drawdown = abs(min(dd)) if len(dd) > 0 else 0
                
                # Net Drawdown (cumulative loss from losing trades)
                cum_pnl = 0
                cum_peak = 0
                net_dd = 0
                for t in trades:
                    cum_pnl += t["pnl"]
                    cum_peak = max(cum_peak, cum_pnl)
                    net_dd = max(net_dd, (cum_peak - cum_pnl) / initial_cap * 100)

                # Annualized ROI
                days = (end_dt - start_dt).days
                years = days / 365.25 if days > 0 else 1
                roi_annum = ((final_cap / initial_cap) ** (1 / years) - 1) * 100

        except Exception as e:
            self.send_message(f"Backtest error: `{e}`")
            logger.exception("Single test worker failed")
            return

        # ── Grading & Deployment ───────────────────────────────────────────
        grade = _grade_performance(roi_pct, win_rate / 100, pf)
        deploy = _deployment_status(grade, total_trades, drawdown)

        # ── Format params string ───────────────────────────────────────────
        params_lines = "\n".join(f"  {k}: `{v}`" for k, v in strat_params.items())
        
        # Check if using optimized params
        param_source = "*OPTIMIZED* from /auto" if optimized_params else "*DEFAULT* values"

        # ── Build the 26-field report ──────────────────────────────────────
        days_total = (end_dt - start_dt).days
        verdict = _verdict_line(roi_pct, grade)

        msg = (
            f"*BACKTEST REPORT*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"*Strategy:* `{strat_display_name}`\n"
            f"*Asset:* `{symbol}` · `{timeframe}`\n"
            f"*Params:* {param_source}\n"
            f"  SL=`{sl*100:.1f}%` · TP=`{tp*100:.1f}%` · TS=`{ts*100:.1f}%`\n\n"
            f"*Capital*\n"
            f"  `${initial_cap:,.2f}` → `${final_cap:,.2f}` ({'+' if net_profit >= 0 else ''}`${net_profit:,.2f}`)\n\n"
            f"*Returns*\n"
            f"  ROI: `{roi_pct:.2f}%` · Annual: `{roi_annum:.2f}%`\n\n"
            f"*Trades*\n"
            f"  Total: `{total_trades}` · W/L: `{winning}/{losing}` · WR: `{win_rate:.1f}%`\n"
            f"  Avg trade: `{avg_trade:.2f}%`\n\n"
            f"*Risk*\n"
            f"  PF: `{pf:.2f}` · Sharpe: `{sharpe:.2f}`\n"
            f"  Gross DD: `{drawdown:.2f}%` · Net DD: `{net_dd:.2f}%`\n\n"
            f"*Verdict:* `{grade}` — {verdict}\n"
            f"*Deploy:* `{deploy}`\n\n"
            f"_Data: {data_source} · {days_total} days · {time_start} → {time_end} · Fee: {fees:.2f}%_\n"
        )

        self.send_message(msg)

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
            first = _normalize_symbol(args[0])
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
            return f"Already running on `{symbol}` — hold tight."

        t = threading.Thread(
            target=self._batch_backtest_worker,
            args=(symbol, batches),
            daemon=True,
        )
        self._running[job_key] = t
        t.start()

        return (
            f"*Backtest launched*\n"
            f"`{symbol}` · Batches `{batches}`\n\n"
            "_Crunching strategies — results incoming..._"
        )

    def _batch_backtest_worker(self, symbol: str, batches: List[int]) -> None:
        """Worker: runs batches sequentially, auto-optimizes if results are poor."""
        try:
            self._batch_backtest_worker_inner(symbol, batches)
        except Exception as e:
            logger.error(f"Batch backtest worker crashed: {e}", exc_info=True)
            self.send_message(f"Batch backtest crashed: `{e}`\nRun /restart and retry.")

    def _batch_backtest_worker_inner(self, symbol: str, batches: List[int]) -> None:
        all_results = []

        # Load saved optimized params once — shared across all batches
        saved_params = {}
        try:
            ranking_path = os.path.join(_ROOT, "storage", "elite_ranking.json")
            if os.path.exists(ranking_path):
                with open(ranking_path) as f:
                    _data = json.load(f)
                for r in _data.get("results", []):
                    if r.get("name") and r.get("sl"):
                        saved_params[r["name"]] = {
                            "stop_loss": r["sl"],
                            "take_profit": r["tp"],
                            "trailing_stop": r["ts"],
                        }
        except Exception:
            pass

        if saved_params:
            self.send_message(f"_Loaded optimized params for {len(saved_params)} strategies._")

        for batch_num in batches:
            self.send_message(f"_Batch {batch_num} · {symbol}..._")
            try:
                results = run_batch_strategies(data_key=symbol, batch_num=batch_num, params_override=saved_params)
                if results:
                    all_results.extend(results)
            except Exception as e:
                self.send_message(f"Batch {batch_num} error: `{e}`")

        # Store for /results
        self._last_results = all_results

        if not all_results:
            self.send_message("No strategies produced results — check data availability.")
            return

        all_results.sort(key=lambda x: x.get("roi", 0), reverse=True)
        self._send_backtest_summary(symbol, batches, all_results, label="BACKTEST COMPLETE")

        # ── Auto-optimization check ───────────────────────────────────────
        poor, reason = self._is_poor_results(all_results)
        if poor:
            self.send_message(
                f"Results below threshold ({reason})\n"
                "_Auto-optimizing — sit tight..._"
            )
            improved, best_params = self._auto_optimize_params(symbol, batches, all_results)
            if improved:
                improved.sort(key=lambda x: x.get("roi", 0), reverse=True)
                self._last_results = improved
                self._send_backtest_summary(
                    symbol, batches, improved,
                    label="AFTER AUTO-OPTIMIZATION"
                )
            else:
                self.send_message("_Auto-optimization did not improve results._")

        # Send CSV file to user
        csv_path = os.path.join(_ROOT, "batch_backtest_results.csv")
        if os.path.exists(csv_path):
            self.send_document(csv_path, caption="Full backtest results")

    # ------------------------------------------------------------------ #
    # Auto-optimization helpers
    # ------------------------------------------------------------------ #

    def _is_poor_results(self, results: List[dict]) -> Tuple[bool, str]:
        """Return (True, reason) when results meet the 'poor' threshold."""
        if not results:
            return True, "no strategies produced results"
        profitable = [r for r in results if r.get("roi", 0) >= 20]
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

        symbol = _normalize_symbol(args[0])
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
                            "sl": best_params["stop_loss"],
                            "tp": best_params["take_profit"],
                            "ts": best_params["trailing_stop"],
                        })
                except Exception:
                    continue

        return improved_results, best_params

    def _send_backtest_summary(
        self, symbol: str, batches: List[int], results: List[dict], label: str
    ) -> None:
        """Format and send a backtest results summary to Telegram."""
        profitable = [r for r in results if r.get("ROI_per_annum", r.get("roi", 0)) >= 20]
        pct = len(profitable)/len(results)*100 if results else 0
        best_roi = results[0].get('ROI_per_annum', results[0].get('roi', 0)) if results else 0

        # Contextual flair
        if best_roi > 500:
            roi_tag = f"☄️ *{best_roi:.2f}%*"
        elif best_roi > 100:
            roi_tag = f"🌋 *{best_roi:.2f}%*"
        elif best_roi > 20:
            roi_tag = f"⛰️ *{best_roi:.2f}%*"
        elif best_roi > 0:
            roi_tag = f"🌱 *{best_roi:.2f}%*"
        else:
            roi_tag = f"🌧️ *{best_roi:.2f}%*"

        msg = (
            f"*{label}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"`{symbol}` · Batches `{batches}`\n"
            f"Strategies tested: *{len(results)}*\n"
            f"Profitable (ROI>=20%): *{len(profitable)}* ({pct:.0f}%)\n"
            f"Best ROI: {roi_tag}\n\n"
        )

        # Top 15 with tier classification
        msg += "*Top 15:*\n```\n"
        msg += f"{'#':<3} {'Name':<16} {'Asset':<8} {'TF':<3} {'ROI%/yr':<7} {'WR%':<5} {'Sharpe':<6} {'GDD%':<5} {'Tier'}\n"
        msg += f"{'-'*65}\n"
        for i, r in enumerate(results[:15], 1):
            roi = r.get('ROI_per_annum', r.get('roi', 0))
            asset = r.get('Asset', r.get('asset', ''))
            tf = r.get('Timeframe', r.get('timeframe', ''))
            wr = r.get('Win_Rate_Percent', r.get('win_rate', 0))
            sharpe = r.get('Sharpe_Ratio', r.get('sharpe', 0))
            gdd = r.get('Gross_DD_Percent', r.get('gross_dd', 0))
            daily = roi / 365 if roi else 0

            # Classify tier
            a_pp = (daily >= 0.5 and sharpe >= 3.5 and wr >= 45 and gdd < 35) or \
                   (daily >= 0.6 and sharpe >= 4.0 and wr >= 45 and gdd < 30) or \
                   (sharpe >= 6.0 and daily >= 0.3 and gdd < 30)
            a = (daily >= 0.25 and sharpe >= 2.5 and wr >= 45 and gdd < 45) or \
                (daily >= 0.3 and sharpe >= 3.0 and wr >= 45 and gdd < 40) or \
                (sharpe >= 5.0 and daily >= 0.2 and gdd < 40)
            avg = (daily >= 0.1 and sharpe >= 1.5) or daily >= 0.05

            if a_pp:
                tier = "ALPHA++"
            elif a:
                tier = "ALPHA"
            elif avg and roi > 0:
                tier = "AVERAGE"
            elif roi > 0:
                tier = "OK"
            else:
                tier = "REJECT"

            name = r['name'][:15]
            msg += (
                f"{i:<3} "
                f"{name:<16} "
                f"{asset[:7]:<8} "
                f"{tf:<3} "
                f"{roi:<7.1f} "
                f"{wr:<5.1f} "
                f"{sharpe:<6.2f} "
                f"{gdd:<5.1f} "
                f"{tier}\n"
            )
        msg += "```\n"

        # Benchmark comparison
        if results:
            best = results[0]
            best_roi = round(best.get("ROI_per_annum", best.get("roi", 0)), 1)
            best_daily = round(best_roi / 365, 3)
            safest = min(results[:15], key=lambda x: x.get("Net_DD_Percent", x.get("net_dd", 100)))
            safest_ndd = round(safest.get("Net_DD_Percent", safest.get("net_dd", 0)), 1)
            safest_cap = int(safest.get("Net_DD_Capital", safest.get("Capital_At_Net_DD", 10000)))
            avg_roi = round(sum(r.get("ROI_per_annum", r.get("roi", 0)) for r in results[:15]) / min(len(results), 15), 1)

            msg += (
                f"*Benchmark:*\n"
                f"Best: `{best['name']}` = `{best_roi}%/yr` (`{best_daily}%/day`)\n"
                f"Safest: `{safest['name']}` NDD=`{safest_ndd}%` Cap=`${safest_cap}`\n"
                f"Avg top 15: `{avg_roi}%/yr`\n"
                f"Cat1 (2%/day): {'YES' if best_daily >= 2.0 else 'NO'} | "
                f"Cat2 (0.5%/day): {'YES' if best_daily >= 0.5 else 'NO'}"
            )
        self.send_message(msg)

        # Send worst-case DD detail for top 5
        dd_msg = "*Risk Report — Top 5:*\n"
        dd_msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        for r in results[:5]:
            g_dd   = r.get("Gross_DD_Percent", 0)
            g_date = r.get("Gross_DD_Date", "N/A")
            g_cap  = r.get("Gross_DD_Capital", "N/A")
            n_dd   = r.get("Net_DD_Percent", 0)
            n_date = r.get("Net_DD_Date", "N/A")
            n_cap  = r.get("Net_DD_Capital", "N/A")

            net_dd_label = f"`{n_dd:.1f}%`" if isinstance(n_dd, (int, float)) and n_dd > 0 else "`0%` (never below $10k)"

            # DD vibe
            if isinstance(g_dd, (int, float)) and g_dd > 50:
                dd_vibe = "🌪️"
            elif isinstance(g_dd, (int, float)) and g_dd > 25:
                dd_vibe = "🌧️"
            else:
                dd_vibe = "🌤️"

            dd_msg += (
                f"\n{dd_vibe} *{r['name']}*\n"
                f"  Gross DD: `{g_dd}%` on `{g_date}` → `${g_cap}`\n"
                f"  Net DD: {net_dd_label} on `{n_date}` → `${n_cap}`\n"
            )
        self.send_message(dd_msg)

    # ------------------------------------------------------------------ #
    # Comprehensive backtest (all symbols × timeframes × strategies)
    # ------------------------------------------------------------------ #

    def _start_comprehensive_backtest(self) -> str:
        """Kick off the comprehensive backtest in a background thread."""
        job_key = "comprehensive"
        if job_key in self._running and self._running[job_key].is_alive():
            return "Comprehensive backtest already running — hold tight."

        t = threading.Thread(
            target=self._comprehensive_backtest_worker, daemon=True
        )
        self._running[job_key] = t
        t.start()

        return (
            "*Comprehensive Backtest launched*\n"
            f"`{START_DATE}` → `{END_DATE}`\n"
            f"Assets: `{', '.join(SYMBOLS)}`\n"
            f"Timeframes: `{', '.join(TIMEFRAMES)}`\n\n"
            "_This takes a while — go grab a coffee..._"
        )

    def _comprehensive_backtest_worker(self) -> None:
        """Worker: runs the comprehensive backtest and reports to Telegram."""
        try:
            self.send_message("_Loading data across all assets and timeframes..._")
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
                f"{'Strategy':<22} {'Sym':<9} {'TF':<4} {'ROI%':<7} {'WR%':<5} {'GDD%':<6} {'NDD%'}\n"
                f"{'-'*60}\n"
            )
            for r in top:
                gdd = getattr(r, 'max_drawdown', 0)
                ndd = getattr(r, 'net_drawdown', 0)
                msg += (
                    f"{r.strategy_name[:21]:<22} "
                    f"{r.symbol[:8]:<9} "
                    f"{r.timeframe:<4} "
                    f"{r.roi_per_annum:<7.1f} "
                    f"{r.win_rate * 100:<5.1f} "
                    f"{gdd:<6.1f} "
                    f"{ndd:.1f}\n"
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

    def _run_optimization(self, args: list = None) -> str:
        """Optimize elite strategies by tuning SL/TP/TS.
        Usage: /optimize  or  /optimize BTCUSDT_4h
        """
        args = args or []
        symbol = _normalize_symbol(args[0]) if args else self._default_symbol
        if symbol not in DATA_FILES:
            available = ", ".join(sorted(DATA_FILES.keys()))
            return f"Unknown symbol {symbol}.\nAvailable: {available}"
        job_key = f"optimize_{symbol}"
        if job_key in self._running and self._running[job_key].is_alive():
            return f"Optimization on `{symbol}` is already running."

        t = threading.Thread(
            target=self._optimization_worker,
            args=(symbol,),
            daemon=True,
        )
        self._running[job_key] = t
        t.start()

        return (
            f"*Optimization started!*\n"
            f"Symbol: `{symbol}`\n"
            f"Testing {len(ELITE_STRATEGY_NAMES)} elite strategies with "
            f"{_OPT_TRIALS} parameter combinations...\n\n"
            "_This may take a few minutes. Results will be sent when done._"
        )

    def _optimization_worker(self, symbol: str) -> None:
        """Worker: optimize elite strategies SL/TP/TS, re-score and re-rank."""
        try:
            self._optimization_worker_inner(symbol)
        except Exception as e:
            logger.error(f"Optimization worker crashed: {e}", exc_info=True)
            self.send_message(f"Optimization crashed: `{e}`\nRun /restart and retry.")

    def _optimization_worker_inner(self, symbol: str) -> None:
        global ELITE_STRATEGY_NAMES

        df = load_data(symbol)
        if df is None:
            self.send_message(f"Data not found for `{symbol}`.")
            return
        df = calculate_indicators(df)

        all_strats = get_all_strategies()
        elite_strats = [s for s in all_strats if s["name"] in ELITE_STRATEGY_NAMES]
        if not elite_strats:
            self.send_message("No elite strategies found.")
            return

        self.send_message(f"_Running {len(elite_strats)} strategies with default params..._")

        # Phase 1: run with default params and score
        before_results = []
        for strat in elite_strats:
            try:
                df_copy = apply_strategy(df.copy(), strat["strategies"], strat.get("min_agreement", 1))
                final_cap, trades = _batch_run_backtest(df_copy, strat["stop_loss"], strat["take_profit"], strat["trailing_stop"])
                if len(trades) >= 5:
                    wins = [t for t in trades if t["pnl"] > 0]
                    roi = (final_cap - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
                    wr = len(wins) / len(trades) * 100
                    pf = sum(t["pnl"] for t in trades if t["pnl"] > 0) / max(abs(sum(t["pnl"] for t in trades if t["pnl"] < 0)), 0.01)
                    score = _compute_score(roi, wr, pf, 0)
                    before_results.append({
                        "name": strat["name"], "roi": round(roi, 2), "win_rate": round(wr, 2),
                        "pf": round(pf, 2), "score": round(score, 2), "trades": len(trades),
                        "sl": strat["stop_loss"], "tp": strat["take_profit"], "ts": strat["trailing_stop"],
                    })
            except Exception:
                pass

        if not before_results:
            self.send_message("No results from default params.")
            return

        before_results.sort(key=lambda x: x["score"], reverse=True)
        best_before = before_results[0]["score"]
        self.send_message(f"_Default best score: {best_before:.1f}. Now optimizing SL/TP/TS..._")

        # Phase 2: optimize SL/TP/TS for each elite strategy
        after_results = []
        for strat in elite_strats:
            try:
                df_copy = apply_strategy(df.copy(), strat["strategies"], strat.get("min_agreement", 1))
                best_score = -999
                best_params = {"sl": strat["stop_loss"], "tp": strat["take_profit"], "ts": strat["trailing_stop"]}
                best_result = None

                for _ in range(_OPT_TRIALS):
                    sl = random.choice(_SL_CANDIDATES)
                    tp = random.choice(_TP_CANDIDATES)
                    ts = random.choice(_TS_CANDIDATES)
                    if tp < sl * 1.5:
                        continue
                    final_cap, trades = _batch_run_backtest(df_copy, sl, tp, ts)
                    if len(trades) >= 5:
                        wins = [t for t in trades if t["pnl"] > 0]
                        roi = (final_cap - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
                        wr = len(wins) / len(trades) * 100
                        pf = sum(t["pnl"] for t in trades if t["pnl"] > 0) / max(abs(sum(t["pnl"] for t in trades if t["pnl"] < 0)), 0.01)
                        score = _compute_score(roi, wr, pf, 0)
                        if score > best_score:
                            best_score = score
                            best_params = {"sl": sl, "tp": tp, "ts": ts}
                            best_result = {
                                "name": strat["name"], "roi": round(roi, 2), "win_rate": round(wr, 2),
                                "pf": round(pf, 2), "score": round(score, 2), "trades": len(trades),
                                "sl": sl, "tp": tp, "ts": ts,
                                "indicators": ", ".join(strat["strategies"]),
                                "min_agreement": strat.get("min_agreement", 1),
                            }

                if best_result:
                    after_results.append(best_result)
            except Exception:
                pass

        if not after_results:
            self.send_message("Optimization produced no results.")
            return

        # Phase 3: re-rank by score — best goes to #1
        after_results.sort(key=lambda x: x["score"], reverse=True)

        # Update ELITE_STRATEGY_NAMES order based on new ranking
        new_order = [r["name"] for r in after_results]
        # Keep any strategies that didn't produce results at the end
        remaining = [n for n in ELITE_STRATEGY_NAMES if n not in new_order]
        ELITE_STRATEGY_NAMES = new_order + remaining

        # Save optimized ranking to disk
        _save_elite_ranking(ELITE_STRATEGY_NAMES, after_results)

        self._last_results = after_results

        # Build comparison message
        msg = (
            "*OPTIMIZATION COMPLETE*\n"
            f"Symbol: `{symbol}`\n"
            f"Trials per strategy: {_OPT_TRIALS}\n\n"
            "*New Elite Ranking (by Score):*\n"
            "```\n"
            f"{'#':<3} {'Strategy':<25} {'Score':<7} {'ROI%':<8} {'WR%':<7} {'PF':<6} {'SL%':<6} {'TP%':<6}\n"
            f"{'-'*68}\n"
        )
        for i, r in enumerate(after_results[:20], 1):
            msg += (
                f"{i:<3} {r['name'][:25]:<25} {r['score']:<7} {r['roi']:<8} "
                f"{r['win_rate']:<7} {r['pf']:<6} "
                f"{r['sl']*100:.1f}  {r['tp']*100:.1f}\n"
            )
        msg += "```"
        self.send_message(msg)

        # Show optimized parameters for each strategy
        param_msg = "OPTIMIZED PARAMETERS:\n\n"
        for i, r in enumerate(after_results[:10], 1):
            param_msg += (
                f"{i}. {r['name']}\n"
                f"   Indicators: {r.get('indicators', 'N/A')}\n"
                f"   Min Agreement: {r.get('min_agreement', 1)}\n"
                f"   SL={r['sl']*100:.1f}% | TP={r['tp']*100:.1f}% | TS={r['ts']*100:.1f}%\n"
                f"   Score={r['score']} | ROI={r['roi']}% | WR={r['win_rate']}% | PF={r['pf']}\n\n"
            )
        self.send_message(param_msg)

        # Save optimization results as downloadable CSV
        import pandas as pd
        opt_csv_data = []
        for i, r in enumerate(after_results, 1):
            opt_csv_data.append({
                "Rank": i,
                "Strategy": r["name"],
                "Indicators": r.get("indicators", "N/A"),
                "Min_Agreement": r.get("min_agreement", 1),
                "Score": r["score"],
                "ROI_Percent": r["roi"],
                "Win_Rate_Percent": r["win_rate"],
                "Profit_Factor": r["pf"],
                "Total_Trades": r["trades"],
                "Stop_Loss_Percent": round(r["sl"] * 100, 1),
                "Take_Profit_Percent": round(r["tp"] * 100, 1),
                "Trailing_Stop_Percent": round(r["ts"] * 100, 1),
                "Symbol": symbol,
            })
        opt_csv_path = os.path.join(_ROOT, "optimization_results.csv")
        pd.DataFrame(opt_csv_data).to_csv(opt_csv_path, index=False)
        self.send_document(opt_csv_path, caption="Optimization results — full parameters")

        # Show improvement
        best_after = after_results[0]["score"]
        improvement = ((best_after - best_before) / max(abs(best_before), 0.01)) * 100
        self.send_message(
            f"*Score Improvement:*\n"
            f"  Before: `{best_before:.1f}`\n"
            f"  After : `{best_after:.1f}`\n"
            f"  Change: `{improvement:+.1f}%`\n\n"
            f"*#1 Strategy:* `{after_results[0]['name']}` "
            f"(ROI={after_results[0]['roi']}%, SL={after_results[0]['sl']*100:.1f}%, TP={after_results[0]['tp']*100:.1f}%)"
        )

        # Per-asset performance breakdown with optimized params
        _parts = symbol.rsplit("_", 1)
        _tf = _parts[1] if len(_parts) == 2 else "4h"
        all_tf_symbols = [k for k in DATA_FILES if k.endswith(f"_{_tf}")]

        if len(all_tf_symbols) > 1:
            self.send_message(f"Testing optimized strategies on all {_tf} assets...")

            # Take top 5 optimized strategies
            top5_opt = after_results[:5]
            asset_breakdown = []

            for sym in sorted(all_tf_symbols):
                if self._should_stop():
                    self.send_message("Stopped by user.")
                    return
                _sym_parts = sym.rsplit("_", 1)
                _asset = _sym_parts[0] if len(_sym_parts) == 2 else sym

                df_asset = load_data(sym)
                if df_asset is None:
                    continue
                df_asset = calculate_indicators(df_asset)

                for opt_r in top5_opt:
                    strat = next((s for s in elite_strats if s["name"] == opt_r["name"]), None)
                    if not strat:
                        continue
                    try:
                        df_copy = apply_strategy(df_asset.copy(), strat["strategies"], strat.get("min_agreement", 1))
                        final_cap, trades = _batch_run_backtest(df_copy, opt_r["sl"], opt_r["tp"], opt_r["ts"])
                        if len(trades) >= 5:
                            wins = [t for t in trades if t["pnl"] > 0]
                            roi = (final_cap - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
                            wr = len(wins) / len(trades) * 100
                            asset_breakdown.append({
                                "Asset": _asset,
                                "Strategy": opt_r["name"],
                                "ROI%": round(roi, 2),
                                "WR%": round(wr, 1),
                                "Trades": len(trades),
                                "SL": f"{opt_r['sl']*100:.1f}%",
                                "TP": f"{opt_r['tp']*100:.1f}%",
                            })
                    except Exception:
                        pass

            if asset_breakdown:
                # Group by strategy
                from collections import defaultdict
                by_strat = defaultdict(list)
                for r in asset_breakdown:
                    by_strat[r["Strategy"]].append(r)

                msg = f"PER-ASSET BREAKDOWN (top 5 strategies on {_tf}):\n\n"
                for strat_name, rows in by_strat.items():
                    avg_roi = sum(r["ROI%"] for r in rows) / len(rows)
                    msg += f"{strat_name} (avg ROI={avg_roi:.1f}%):\n"
                    for r in sorted(rows, key=lambda x: x["ROI%"], reverse=True):
                        status = "+" if r["ROI%"] > 0 else "-"
                        msg += f"  {status} {r['Asset']:<10} ROI={r['ROI%']:>8}% WR={r['WR%']}% ({r['Trades']} trades)\n"
                    msg += "\n"
                self.send_message(msg)

                # Save breakdown CSV
                import pandas as pd
                csv_path = os.path.join(_ROOT, "optimization_asset_breakdown.csv")
                pd.DataFrame(asset_breakdown).to_csv(csv_path, index=False)
                self.send_document(csv_path, caption=f"Optimization breakdown — all assets ({_tf})")

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

            # Check if we have trade data
            if not stats or stats.get('total_trades', 0) == 0:
                # No trades file - try to get stats from CSV files instead
                return self._get_stats_from_csv()

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
    
    def _get_stats_from_csv(self) -> str:
        """Get statistics from CSV result files when no trades file exists."""
        import glob
        import pandas as pd
        
        # Find CSV files
        csv_files = sorted(glob.glob("*_all_results.csv"))
        combined_file = "all_assets_strategies_combined.csv"
        if os.path.exists(combined_file):
            csv_files = [combined_file] + csv_files
        
        if not csv_files:
            return "*No trade data available.*\n\nRun /backtest or /run to generate results first."
        
        # Read and aggregate from CSV files
        all_data = []
        for f in csv_files:
            try:
                df = pd.read_csv(f)
                if len(df) > 0:
                    all_data.append(df)
            except:
                continue
        
        if not all_data:
            return "*No trade data available.*\n\nRun /backtest or /run to generate results first."
        
        combined = pd.concat(all_data, ignore_index=True)
        
        # Calculate statistics
        total_strategies = len(combined)
        winning = len(combined[combined.get('roi', 0) > 0]) if 'roi' in combined.columns else 0
        losing = len(combined[combined.get('roi', 0) <= 0]) if 'roi' in combined.columns else 0
        win_rate = (winning / total_strategies * 100) if total_strategies > 0 else 0
        
        # Get ROI stats
        avg_roi = combined['roi'].mean() if 'roi' in combined.columns else 0
        max_roi = combined['roi'].max() if 'roi' in combined.columns else 0
        min_roi = combined['roi'].min() if 'roi' in combined.columns else 0
        
        # Get drawdown
        avg_dd = combined['drawdown'].mean() if 'drawdown' in combined.columns else 0
        
        # Get win rate from CSV if available
        if 'win_rate' in combined.columns:
            avg_win_rate = combined['win_rate'].mean()
        else:
            avg_win_rate = win_rate
        
        msg = "*Strategy Statistics (from CSV):*\n\n"
        msg += f"Total Strategies : {total_strategies}\n"
        msg += f"Profitable       : {winning}\n"
        msg += f"Losing           : {losing}\n"
        msg += f"Win Rate         : {avg_win_rate:.1f}%\n\n"
        msg += f"*ROI Summary:*\n"
        msg += f"  Average : {avg_roi:.2f}%\n"
        msg += f"  Best    : {max_roi:.2f}%\n"
        msg += f"  Worst   : {min_roi:.2f}%\n"
        msg += f"  Avg DD  : {avg_dd:.1f}%\n\n"
        msg += f"Source: {', '.join([os.path.basename(f) for f in csv_files[:3]])}..."
        return msg

    def _stop_running(self) -> str:
        """Stop all running background jobs."""
        running = [k for k, t in self._running.items() if t.is_alive()]
        if not running:
            return "No jobs running. Sab shaant hai!"

        self._stop_flag.set()

        # Give threads a moment to see the flag
        import time
        time.sleep(1)

        # Clear the flag for future runs
        self._stop_flag.clear()

        # Escape underscores so Telegram doesn't parse as italic
        job_list = "\n".join(f"  - {k.replace('_', ' ')}" for k in running)
        return (
            f"Stop signal sent to {len(running)} running job(s):\n"
            f"{job_list}\n\n"
            f"Jobs will stop at the next checkpoint."
        )

    def _restart_bot(self) -> str:
        """Reset bot state — stop running jobs, clear flags, reload settings."""
        try:
            self._stop_flag.set()
            import time; time.sleep(0.5)
            self._stop_flag.clear()
            self._running.clear()
            if hasattr(self, '_last_results'):
                self._last_results = None
            return "[OK] Bot restarted!\n\nAll jobs stopped. Settings reloaded. Ready for new commands."
        except Exception as e:
            return f"Restart failed: `{e}`"

    def _should_stop(self) -> bool:
        """Check if stop was requested. Workers call this between iterations."""
        return self._stop_flag.is_set()

    # ------------------------------------------------------------------ #
    # Live Trading Controls
    # ------------------------------------------------------------------ #

    def _toggle_kill_switch(self, args: list) -> str:
        from src.manager import activate_kill_switch, deactivate_kill_switch, is_kill_switch_active
        if args and args[0].lower() == "off":
            deactivate_kill_switch()
            return "Kill switch *deactivated*. Trading resumed."
        elif is_kill_switch_active():
            deactivate_kill_switch()
            return "Kill switch *deactivated*. Trading resumed."
        else:
            activate_kill_switch(close_all=True)
            return "🚨 Kill switch *ACTIVATED*. All positions closed, new trades blocked.\nUse `/killswitch off` to resume."

    def _toggle_paper_mode(self, args: list) -> str:
        import src.manager as mgr
        if args and args[0].lower() in ("off", "live"):
            mgr.PAPER_TRADING = False
            mgr._save_state()
            return "⚠️ Paper trading *OFF* — LIVE orders will be placed."
        elif args and args[0].lower() in ("on", "paper"):
            mgr.PAPER_TRADING = True
            mgr._save_state()
            return "Paper trading *ON* — no real orders."
        else:
            current = "ON" if mgr.PAPER_TRADING else "OFF"
            return f"Paper trading is *{current}*.\nUse `/paper on` or `/paper off`."

    def _show_positions(self) -> str:
        from src.manager import get_status
        return f"```\n{get_status()}\n```"

    def _close_all_positions(self) -> str:
        from src.manager import close_all_positions, _active_positions
        if not _active_positions:
            return "No open positions."
        close_all_positions("MANUAL")
        return "All positions closed."

    def _get_bot_status(self) -> str:
        try:
            trades_exist = os.path.exists(TRADES_FILE)
            trades_count = 0
            if trades_exist:
                with open(TRADES_FILE, "r") as f:
                    trades_count = sum(1 for line in f if line.strip())

            running_jobs = [k for k, t in self._running.items() if t.is_alive()]
            jobs_str = ", ".join(running_jobs) if running_jobs else "Idle"
            batch_str = self._format_batches(self._default_batches)
            params_str = "Loaded" if os.path.exists(OPTIMIZED_PARAMS_FILE) else "Not set"

            # Result CSV counts
            result_counts = {}
            for tf in ["15m", "1h", "4h"]:
                csv_path = os.path.join(_ROOT, f"auto_results_{tf}.csv")
                if os.path.exists(csv_path):
                    try:
                        with open(csv_path) as f:
                            result_counts[tf] = sum(1 for _ in f) - 1
                    except Exception:
                        result_counts[tf] = 0

            # Trading system status
            try:
                from src import manager as mgr
                mode = "PAPER" if mgr.PAPER_TRADING else "LIVE"
                kill = "ACTIVE" if mgr.is_kill_switch_active() else "OFF"
                positions = len(mgr._active_positions)
                monitor = "Running" if mgr._monitor_running else "Stopped"
                daily_pnl = mgr._daily_pnl
                weekly_pnl = mgr._weekly_pnl
            except Exception:
                mode = "N/A"
                kill = "N/A"
                positions = 0
                monitor = "N/A"
                daily_pnl = 0
                weekly_pnl = 0

            msg = "*Bot Status*\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"*Config*\n"
            msg += f"Symbol: `{self._default_symbol}`\n"
            msg += f"Batches: `{batch_str}` | Lookback: `{self._opt_lookback_years}yr`\n"
            msg += f"Params: `{params_str}` | AI: `{'ON' if self._brain else 'OFF'}`\n"
            msg += f"Jobs: *{jobs_str}*\n\n"
            msg += f"*Backtest Results*\n"
            for tf in ["15m", "1h", "4h"]:
                count = result_counts.get(tf, 0)
                status = f"`{count}` results" if count > 0 else "not run"
                msg += f"{tf}: {status}\n"
            msg += f"\n*Trading System*\n"
            msg += f"Mode: `{mode}` | Kill Switch: `{kill}`\n"
            msg += f"Positions: `{positions}` | SL/TP Monitor: `{monitor}`\n"
            msg += f"Daily PnL: `${daily_pnl:.2f}` | Weekly PnL: `${weekly_pnl:.2f}`\n"
            msg += f"Trades logged: `{trades_count}`\n\n"
            msg += f"_Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
            return msg

        except Exception as e:
            return f"Error getting status: `{e}`"

    def _run_strategy_analysis(self) -> str:
        """Full strategy analysis across all result CSVs — sent as Telegram messages + file."""
        import pandas as pd

        COL_MAP = {
            "Strategy": "strategy", "name": "strategy",
            "Asset": "asset", "Timeframe": "timeframe", "Candle_Period": "timeframe",
            "ROI_Percent": "roi", "roi": "roi",
            "ROI_per_annum": "roi_yr", "ROI_per_annum_Percent": "roi_yr", "ROI/annum": "roi_yr",
            "Total_Trades": "trades", "Win_Rate_Percent": "win_rate",
            "Profit_Factor": "pf",
            "Gross_DD_Percent": "gross_dd", "Max_Drawdown": "gross_dd", "Max_Drawdown_Percent": "gross_dd",
            "Net_DD_Percent": "net_dd", "Performance_Grade": "grade",
            "Final_Capital_USD": "final_cap", "Parameters": "params",
        }

        RESULT_FILES = {
            "batch_backtest_results.csv": "Backtest",
            "elite_strategies.csv": "Elite",
            "all_assets_strategies_combined.csv": "Combined",
            "auto_optimization_results.csv": "Auto-Optimized",
        }
        asset_map = {"btc":"BTCUSDT","eth":"ETHUSDT","bnb":"BNBUSDT","sol":"SOLUSDT",
                     "xrp":"XRPUSDT","ada":"ADAUSDT","avax":"AVAXUSDT","dot":"DOTUSDT",
                     "link":"LINKUSDT","ltc":"LTCUSDT"}
        for prefix, asset in asset_map.items():
            RESULT_FILES[f"{prefix}_all_results.csv"] = "Backtest"

        ASSETS = list(asset_map.values())
        TIMEFRAMES = ["15m", "1h", "4h"]

        self.send_message("Running full strategy analysis...")

        # Load all CSVs
        frames = []
        for filename, label in RESULT_FILES.items():
            filepath = os.path.join(_ROOT, filename)
            if not os.path.exists(filepath):
                continue
            try:
                df = pd.read_csv(filepath)
                rename = {}
                for old, new in COL_MAP.items():
                    if old in df.columns and new not in df.columns:
                        rename[old] = new
                df = df.rename(columns=rename)
                df["_source"] = label
                if "asset" not in df.columns:
                    prefix = filename.split("_")[0].lower()
                    if prefix in asset_map:
                        df["asset"] = asset_map[prefix]
                if "timeframe" not in df.columns:
                    df["timeframe"] = "unknown"
                frames.append(df.loc[:, ~df.columns.duplicated()].reset_index(drop=True))
            except Exception:
                pass

        if not frames:
            return "No result CSVs found. Run /backtest or /auto first."

        df = pd.concat(frames, ignore_index=True)
        if "asset" in df.columns:
            df["asset"] = df["asset"].astype(str).str.upper()
        if "timeframe" in df.columns:
            df["timeframe"] = df["timeframe"].astype(str).str.lower()
        for col in ["roi", "roi_yr", "trades", "win_rate", "pf", "gross_dd", "net_dd"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Deduplicate
        dedup_cols = [c for c in ["strategy", "asset", "timeframe", "roi_yr", "trades"] if c in df.columns]
        if dedup_cols:
            df = df.sort_values("_source", ascending=False).drop_duplicates(subset=dedup_cols, keep="first")

        total_strats = df["strategy"].nunique() if "strategy" in df.columns else 0
        total_rows = len(df)

        # ── 1. Summary ──
        msg = (
            "*STRATEGY ANALYSIS REPORT*\n"
            "════════════════════════\n"
            f"Strategies: {total_strats} | Results: {total_rows}\n\n"
        )

        # ── 2. Best per Asset × TF ──
        if "roi_yr" in df.columns and "strategy" in df.columns:
            msg += "*Best Strategy per Asset (all timeframes):*\n```\n"
            msg += f"{'Asset':<9} {'TFs':<10} {'Best Strategy':<22} {'ROI/yr':>7} {'GDD':>5} {'NDD':>5}\n"
            msg += "-" * 58 + "\n"
            for asset in ASSETS:
                asset_mask = df["asset"] == asset
                if not asset_mask.any():
                    continue
                # Find which TFs have results for this asset
                tfs_done = sorted(df.loc[asset_mask, "timeframe"].unique())
                tf_str = ",".join(tfs_done)
                # Best across all TFs
                best_idx = df.loc[asset_mask, "roi_yr"].idxmax()
                best = df.loc[best_idx]
                strat = str(best.get("strategy", "?"))[:21]
                roi_yr = best.get("roi_yr", 0)
                gdd = best.get("gross_dd", 0)
                ndd = best.get("net_dd", 0)
                flag = "+" if roi_yr > 0 else "-"
                msg += f"{asset:<9} {tf_str:<10} {strat:<22} {flag}{abs(roi_yr):>5.1f}% {gdd:>4.0f}% {ndd:>4.0f}%\n"
            msg += "```\n"

        self.send_message(msg)

        # ── 3. Top 15 overall ──
        if "roi_yr" in df.columns:
            top = df.nlargest(15, "roi_yr")
            top_msg = "*Top 15 Strategies Overall:*\n```\n"
            top_msg += f"{'#':<3} {'Strategy':<20} {'Asset':<9} {'TF':<4} {'ROI/yr':>7} {'Win%':>5} {'GDD':>5} {'NDD':>5}\n"
            top_msg += "─" * 60 + "\n"
            for i, (_, r) in enumerate(top.iterrows(), 1):
                strat = str(r.get("strategy", "?"))[:19]
                top_msg += (
                    f"{i:<3} {strat:<20} {str(r.get('asset','?')):<9} {str(r.get('timeframe','?')):<4} "
                    f"{r.get('roi_yr',0):>6.1f}% {r.get('win_rate',0):>4.0f}% "
                    f"{r.get('gross_dd',0):>4.0f}% {r.get('net_dd',0):>4.0f}%\n"
                )
            top_msg += "```"
            self.send_message(top_msg)

        # ── 4. Strategy consistency across assets ──
        if "strategy" in df.columns and "roi_yr" in df.columns:
            strat_stats = df.groupby("strategy").agg(
                assets=("asset", "nunique"),
                avg_roi=("roi_yr", "mean"),
                profitable=("roi_yr", lambda x: (x > 0).sum()),
                worst=("roi_yr", "min"),
                best=("roi_yr", "max"),
            ).sort_values("avg_roi", ascending=False).head(15)

            cons_msg = "*Strategy Consistency (top 15 by avg ROI/yr):*\n```\n"
            cons_msg += f"{'Strategy':<22} {'Assets':>6} {'AvgROI':>7} {'Prof':>5} {'Best':>7} {'Worst':>7}\n"
            cons_msg += "─" * 58 + "\n"
            for strat, row in strat_stats.iterrows():
                sname = str(strat)[:21]
                prof = f"{int(row['profitable'])}/{int(row['assets'])}"
                cons_msg += (
                    f"{sname:<22} {int(row['assets']):>6} {row['avg_roi']:>6.1f}% "
                    f"{prof:>5} {row['best']:>6.1f}% {row['worst']:>6.1f}%\n"
                )
            cons_msg += "```"
            self.send_message(cons_msg)

        # ── 5. Drawdown summary ──
        if "gross_dd" in df.columns and "roi_yr" in df.columns:
            profitable = df[df["roi_yr"] > 0]
            safe = len(profitable[profitable["gross_dd"] < 50])
            moderate = len(profitable[(profitable["gross_dd"] >= 50) & (profitable["gross_dd"] < 75)])
            high = len(profitable[profitable["gross_dd"] >= 75])
            dd_msg = (
                "*Drawdown Analysis (profitable strategies):*\n"
                f"  Safe (GrossDD < 50%): {safe}\n"
                f"  Moderate (50-75%): {moderate}\n"
                f"  High risk (> 75%): {high}\n"
            )
            if "net_dd" in df.columns:
                below = len(df[df["net_dd"] > 0])
                severe = len(df[df["net_dd"] > 50])
                dd_msg += (
                    f"  Capital dropped below initial: {below}\n"
                    f"  Lost >50% of capital: {severe}\n"
                )
            self.send_message(dd_msg)

        # ── 6. Pending combos ──
        has_results = set()
        if "asset" in df.columns and "timeframe" in df.columns:
            for _, row in df[["asset", "timeframe"]].drop_duplicates().iterrows():
                has_results.add((row["asset"], row["timeframe"]))
        all_combos = {(a, t) for a in ASSETS for t in TIMEFRAMES}
        pending = sorted(all_combos - has_results)
        if pending:
            pend_msg = f"*Pending ({len(pending)} combos not tested yet):*\n"
            for asset, tf in pending:
                pend_msg += f"  → {asset} {tf}\n"
            self.send_message(pend_msg)

        # ── 7. Elite ranking ──
        elite_path = os.path.join(_ROOT, "storage", "elite_ranking.json")
        if os.path.exists(elite_path):
            try:
                with open(elite_path) as f:
                    data = json.load(f)
                updated = data.get("updated", "unknown")
                results = data.get("results", [])
                elite_msg = f"*Elite Ranking (updated: {updated}):*\n```\n"
                elite_msg += f"{'#':<3} {'Strategy':<24} {'SL':>5} {'TP':>5} {'TS':>5} {'Score':>6}\n"
                elite_msg += "─" * 50 + "\n"
                for i, r in enumerate(results[:10], 1):
                    name = str(r.get("name", "?"))[:23]
                    elite_msg += (
                        f"{i:<3} {name:<24} {r.get('sl',0)*100:>4.1f}% "
                        f"{r.get('tp',0)*100:>4.1f}% {r.get('ts',0)*100:>4.1f}% "
                        f"{r.get('score',0):>6.2f}\n"
                    )
                elite_msg += "```"
                self.send_message(elite_msg)
            except Exception:
                pass

        # ── 8. Save and send full report as file ──
        try:
            report_lines = []
            report_lines.append(f"Strategy Analysis Report — {total_strats} strategies, {total_rows} results")
            report_lines.append("=" * 70)
            if "roi_yr" in df.columns:
                full = df.sort_values("roi_yr", ascending=False)
                for _, r in full.iterrows():
                    report_lines.append(
                        f"{str(r.get('strategy','?')):<25} {str(r.get('asset','?')):<9} "
                        f"{str(r.get('timeframe','?')):<4} ROI/yr={r.get('roi_yr',0):>7.1f}% "
                        f"Win={r.get('win_rate',0):>5.1f}% GDD={r.get('gross_dd',0):>5.1f}% "
                        f"NDD={r.get('net_dd',0):>5.1f}% Grade={r.get('grade','?')}"
                    )
            report_path = os.path.join(_ROOT, "strategy_analysis_report.txt")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("\n".join(report_lines))
            self.send_document(report_path, caption="Full strategy analysis report")
        except Exception as e:
            logger.warning(f"Could not save analysis report: {e}")

        return "Analysis complete."

    def _generate_pine_script(self, args) -> str:
        """Generate TradingView Pine Script for a strategy and send it."""
        SIGNAL_PINE = {
            "EMA_Cross":    "ema8 > ema21",
            "RSI_Oversold": "rsi14 < 30 and rsi14 > rsi14[1]",
            "MACD_Cross":   "ta.crossover(macdLine, signalLine)",
            "BB_Lower":     "close < bbLower",
            "BB_Upper":     "close > bbUpper",
            "Volume_Spike": "volume / volMA > 1.5 and close > close[1]",
            "Breakout_20":  "close > ta.highest(high, 20)[1]",
            "Stochastic":   "stochK < 20 and stochK > stochK[1]",
            "Supertrend":   "close > supertrend",
            "VWAP":         "close > ta.vwap",
            "ADX_Trend":    "adxVal > 25",
            "Trend_MA50":   "close > ema50",
        }
        STRATEGY_SIGNALS = {
            "EMA_Cloud_Strength":      ["EMA_Cross", "Trend_MA50", "ADX_Trend"],
            "EMA_RSI_Momentum":        ["EMA_Cross", "RSI_Oversold", "Trend_MA50"],
            "Supertrend_BB_Entry":     ["Supertrend", "BB_Lower", "EMA_Cross", "MACD_Cross", "RSI_Oversold"],
            "Supertrend_Multi_Entry":  ["Supertrend", "EMA_Cross", "VWAP", "ADX_Trend", "Volume_Spike"],
            "Volume_Breakout_Pro":     ["Volume_Spike", "Breakout_20", "VWAP"],
            "Mean_Reversion_Pro":      ["BB_Lower", "RSI_Oversold", "Stochastic", "VWAP"],
            "RSI_Recovery":            ["RSI_Oversold", "Stochastic", "Trend_MA50"],
            "ADX_Stochastic_VWAP":     ["ADX_Trend", "Stochastic", "VWAP", "BB_Lower", "Volume_Spike"],
            "VWAP_Break_Entry":        ["VWAP", "Breakout_20", "ADX_Trend", "RSI_Oversold"],
            "RSI_Extreme_Reversal":    ["RSI_Oversold", "Stochastic", "BB_Lower", "VWAP"],
            "Breakout_Retest":         ["Breakout_20", "RSI_Oversold", "BB_Lower"],
            "RSI_Stochastic_VWAP_ADX": ["RSI_Oversold", "Stochastic", "VWAP", "ADX_Trend", "MACD_Cross"],
            "RSI_BB_MACD_Stochastic":  ["RSI_Oversold", "BB_Lower", "MACD_Cross", "Stochastic"],
            "Scalp_Trade":             ["RSI_Oversold", "BB_Lower", "VWAP", "Stochastic"],
            "Oversold_Recovery":       ["RSI_Oversold", "Stochastic", "BB_Lower", "VWAP"],
            "Double_Bottom_Formation": ["BB_Lower", "RSI_Oversold", "Stochastic", "VWAP"],
            "BB_Stochastic_Trade":     ["BB_Lower", "Stochastic", "RSI_Oversold", "VWAP"],
            "RSI_Confirmation":        ["RSI_Oversold", "Stochastic", "BB_Lower", "VWAP"],
            "RSI_Stochastic_Pro":      ["RSI_Oversold", "Stochastic", "BB_Lower", "MACD_Cross"],
            "ADX_Stochastic_BB":       ["ADX_Trend", "Stochastic", "BB_Lower", "RSI_Oversold"],
        }

        if not args:
            names = "\n".join(f"  {n}" for n in sorted(STRATEGY_SIGNALS.keys()))
            return (
                "Usage:\n"
                "  /pinescript <name>    - single strategy\n"
                "  /pinescript top 1     - best strategy from elite ranking\n"
                "  /pinescript top 5     - top 5 strategies\n"
                "  /pinescript top       - top 3 (default)\n\n"
                f"Available:\n{names}"
            )

        # ── Handle "top N" ──
        if args[0].lower() == "top":
            n = int(args[1]) if len(args) > 1 and args[1].isdigit() else 3
            elite_path = os.path.join(_ROOT, "storage", "elite_ranking.json")
            if not os.path.exists(elite_path):
                return "elite_ranking.json not found. Run /auto first."
            try:
                with open(elite_path) as f:
                    data = json.load(f)
            except Exception:
                return "Could not read elite_ranking.json"
            results = data.get("results", [])[:n]
            if not results:
                return "No strategies in elite_ranking.json"
            self.send_message(f"Generating Pine Scripts for top {len(results)} strategies...")
            for r in results:
                name = r.get("name", "unknown")
                sl = r.get("sl", 0.03) * 100
                tp = r.get("tp", 0.05) * 100
                ts = r.get("ts", 0.025) * 100
                score = r.get("score", 0)
                # Find signals
                sigs = STRATEGY_SIGNALS.get(name)
                if not sigs:
                    for sname, s in STRATEGY_SIGNALS.items():
                        if name.lower().replace("_", "") in sname.lower().replace("_", ""):
                            sigs = s
                            name = sname
                            break
                if not sigs:
                    self.send_message(f"Skipping {name} - no signal mapping")
                    continue
                pine = self._build_pine(name, sigs, sl, tp, ts, SIGNAL_PINE)
                self.send_message(f"*#{results.index(r)+1} {name}* (Score: {score:.1f})\nSL={sl}% | TP={tp}% | TS={ts}%")
                self.send_message(f"```\n{pine}\n```")
                try:
                    pine_path = os.path.join(_ROOT, f"pine_{name}.txt")
                    with open(pine_path, "w") as f:
                        f.write(pine)
                    self.send_document(pine_path, caption=f"#{results.index(r)+1} {name}")
                except Exception:
                    pass
            return f"Done - {len(results)} Pine Scripts sent."

        strategy_name = args[0]

        # Find strategy (exact or partial match)
        signals = STRATEGY_SIGNALS.get(strategy_name)
        if not signals:
            for name, sigs in STRATEGY_SIGNALS.items():
                if strategy_name.lower().replace("_", "") in name.lower().replace("_", ""):
                    signals = sigs
                    strategy_name = name
                    break
        if not signals:
            return f"Unknown strategy: {strategy_name}\nUse /pinescript to see available strategies."

        # Load SL/TP/TS from elite_ranking.json or use defaults
        sl, tp, ts = 3.0, 5.0, 2.5
        elite_path = os.path.join(_ROOT, "storage", "elite_ranking.json")
        if os.path.exists(elite_path):
            try:
                with open(elite_path) as f:
                    data = json.load(f)
                for r in data.get("results", []):
                    if r.get("name", "").lower().replace("_", "") == strategy_name.lower().replace("_", ""):
                        sl = r.get("sl", 0.03) * 100
                        tp = r.get("tp", 0.05) * 100
                        ts = r.get("ts", 0.025) * 100
                        break
            except Exception:
                pass

        pine = self._build_pine(strategy_name, signals, sl, tp, ts, SIGNAL_PINE)

        self.send_message(f"*Pine Script for {strategy_name}*\nSL={sl}% | TP={tp}% | TS={ts}%\nCopy below into TradingView Pine Editor:")
        self.send_message(f"```\n{pine}\n```")
        try:
            pine_path = os.path.join(_ROOT, f"pine_{strategy_name}.txt")
            with open(pine_path, "w") as f:
                f.write(pine)
            self.send_document(pine_path, caption=f"{strategy_name} - paste into TradingView")
        except Exception:
            pass
        return ""

    @staticmethod
    def _build_pine(strategy_name, signals, sl, tp, ts, signal_pine, min_agreement=None):
        """Build Pine Script v5 string for a strategy."""
        # Look up min_agreement from batch definition if not provided
        if min_agreement is None:
            try:
                strat_def = _find_batch_strategy_by_name(strategy_name)
                min_agreement = strat_def.get("min_agreement", 1) if strat_def else 1
            except Exception:
                min_agreement = 1

        signal_vars = []
        signal_conds = []
        for sig in signals:
            var = f"sig_{sig.lower().replace('_', '')}"
            signal_vars.append(f"{var} = {signal_pine.get(sig, 'false')}")
            signal_conds.append(var)
        exit_sum = " + ".join([f"({s} ? 1 : 0)" for s in signal_conds])

        if min_agreement >= len(signal_conds):
            entry = " and ".join(signal_conds)
            entry_comment = f"// ALL {len(signal_conds)} signals must agree"
        else:
            entry = f"({exit_sum}) >= {min_agreement}"
            entry_comment = f"// ANY {min_agreement} of {len(signal_conds)} signals triggers entry"

        nl = chr(10)
        return f"""//@version=5
strategy("{strategy_name} [Bot Verify]", overlay=true, initial_capital=10000,
         default_qty_type=strategy.cash, default_qty_value=9500,
         commission_type=strategy.commission.percent, commission_value=0.1)

// {strategy_name} | SL={sl}% TP={tp}% TS={ts}%
// Signals: {', '.join(signals)}
{entry_comment}

ema8   = ta.ema(close, 8)
ema21  = ta.ema(close, 21)
ema50  = ta.ema(close, 50)
sma20  = ta.sma(close, 20)
bbUpper = sma20 + 2.0 * ta.stdev(close, 20)
bbLower = sma20 - 2.0 * ta.stdev(close, 20)
rsi14 = ta.rsi(close, 14)
macdLine   = ema21 - ema50
signalLine = ta.ema(macdLine, 9)
stochK = ta.stoch(close, high, low, 14)
volMA = ta.sma(volume, 20)
atr14 = ta.atr(14)
supertrend = (high + low) / 2.0 - 3.0 * atr14
[diPlus, diMinus, adxVal] = ta.dmi(14, 14)

{nl.join(signal_vars)}

signalCount = {exit_sum}
entryCondition = {entry}
exitCondition  = signalCount < 1

sl_pct = {sl} / 100.0
tp_pct = {tp} / 100.0
ts_pct = {ts} / 100.0

canTrade = strategy.equity > 0

if entryCondition and strategy.position_size == 0 and canTrade
    qty = math.max(1, math.floor(strategy.equity * 0.95 / close))
    strategy.entry("Long", strategy.long, qty=qty)
if strategy.position_size > 0
    entryPx = strategy.position_avg_price
    strategy.exit("Exit", "Long", stop=entryPx*(1-sl_pct), limit=entryPx*(1+tp_pct), trail_price=entryPx, trail_offset=entryPx*ts_pct/syminfo.mintick)
if exitCondition and strategy.position_size > 0
    strategy.close("Long", comment="Signal Exit")

plot(ema8, "EMA8", color.blue)
plot(ema21, "EMA21", color.orange)
plot(ema50, "EMA50", color.red, linewidth=2)
plotshape(entryCondition and strategy.position_size == 0 and canTrade, "Entry", shape.triangleup, location.belowbar, color.green, size=size.small)
"""

    def _get_last_results(self, args=None) -> str:
        """Return a summary of the last backtest results from any command.
        Args: optional timeframe filter like '4h', '1h', '15m'
        """
        # Parse timeframe filter from args
        tf_filter = None
        if args:
            tokens = args if isinstance(args, list) else args.split()
            for token in tokens:
                if token.lower() in ("15m", "1h", "4h", "1d"):
                    tf_filter = token.lower()
                    break

        # Try loading from CSV files
        all_records = []
        csv_files = [
            "batch_backtest_results.csv",
            "auto_optimization_results.csv",
            "elite_backtest_results.csv",
            "auto_results_15m.csv",
            "auto_results_1h.csv",
            "auto_results_4h.csv",
        ]
        # Also search reports/ directory for result CSVs
        reports_dir = os.path.join(_ROOT, "reports")
        if os.path.isdir(reports_dir):
            for fname in os.listdir(reports_dir):
                if fname.endswith(".csv") and ("result" in fname.lower() or "combined" in fname.lower() or "elite" in fname.lower()):
                    csv_files.append(os.path.join("reports", fname))
        for csv_file in csv_files:
            csv_path = os.path.join(_ROOT, csv_file)
            if os.path.exists(csv_path):
                try:
                    import pandas as pd
                    df = pd.read_csv(csv_path)
                    records = df.to_dict("records")
                    all_records.extend(records)
                except Exception:
                    pass

        # Also include in-memory results
        if self._last_results:
            all_records.extend(self._last_results)

        # Deduplicate by name+asset+timeframe
        seen = set()
        unique = []
        for r in all_records:
            key = (r.get("name", r.get("Strategy", "")),
                   r.get("asset", r.get("Asset", "")),
                   r.get("timeframe", r.get("Timeframe", r.get("Candle_Period", ""))))
            if key not in seen:
                seen.add(key)
                unique.append(r)
        all_records = unique

        # Apply timeframe filter
        if tf_filter:
            filtered = []
            for r in all_records:
                tf = str(r.get("timeframe", r.get("Timeframe", r.get("Candle_Period", "")))).lower()
                if tf == tf_filter:
                    filtered.append(r)
            all_records = filtered

        if not all_records:
            msg = "No results"
            if tf_filter:
                msg += f" for {tf_filter}"
            return msg + ". Run /backtest, /auto, or /elite first."

        def _norm(r):
            """Normalize result dict to always have consistent keys."""
            out = dict(r)
            # ROI% = per annum (not total period)
            if "roi" not in out or out["roi"] == 0:
                out["roi"] = out.get("ROI_per_annum") or out.get("ROI_per_annum_Percent") or out.get("ROI/annum") or out.get("ROI_Percent") or 0
            if "trades" not in out or out["trades"] == 0:
                out["trades"] = out.get("Total_Trades") or 0
            if "win_rate" not in out or out["win_rate"] == 0:
                out["win_rate"] = out.get("Win_Rate_Percent") or 0
            if "id" not in out:
                out["id"] = out.get("Rank") or "?"
            if "name" not in out:
                out["name"] = out.get("Strategy") or "Unknown"
            if "asset" not in out:
                out["asset"] = out.get("Asset") or "?"
            if "timeframe" not in out:
                out["timeframe"] = out.get("Timeframe") or out.get("Candle_Period") or "?"
            # Drawdown — prefer detailed keys, fall back to Max_Drawdown / Max_Drawdown_Percent
            if "gross_dd" not in out or out["gross_dd"] == 0:
                out["gross_dd"] = out.get("Gross_DD_Percent") or out.get("Max_Drawdown_Percent") or out.get("Max_Drawdown") or 0
            if "net_dd" not in out or out["net_dd"] == 0:
                out["net_dd"] = out.get("Net_DD_Percent") or 0
            # Capital left at worst net drawdown point
            if "capital_at_net_dd" not in out or out["capital_at_net_dd"] == 0:
                cap = out.get("Capital_At_Net_DD")
                if cap and cap > 0:
                    out["capital_at_net_dd"] = cap
                else:
                    initial = float(out.get("Initial_Capital_USD", 10000))
                    out["capital_at_net_dd"] = round(initial * (1 - out["net_dd"] / 100), 2) if out["net_dd"] else initial
            # NDD date
            if "net_dd_date" not in out:
                out["net_dd_date"] = out.get("Net_DD_Date", "")
            return out

        results = sorted(
            [_norm(r) for r in all_records],
            key=lambda x: x.get("roi", 0),
            reverse=True
        )
        profitable = [r for r in results if r.get("roi", 0) >= 20]

        msg = (
            f"*Last Backtest Results*\n"
            f"Strategies tested: {len(results)}\n"
            f"Profitable (ROI>=20%): {len(profitable)}\n\n"
            "*Top 15 by ROI %/yr:*\n"
            "```\n"
            f"{'#':<3} {'Name':<16} {'Asset':<8} {'TF':<3} {'ROI%/yr':<7} {'WR%':<5} {'GDD%':<5} {'Tier'}\n"
            f"{'-'*55}\n"
        )
        for i, r in enumerate(results[:15], 1):
            roi_v = round(r.get("roi", 0), 1)
            daily_v = roi_v / 365
            wr_v = round(r.get("win_rate", 0), 1)
            sh_v = r.get("sharpe", 0)
            gdd_v = round(r.get("gross_dd", 0), 1)

            a_pp = (daily_v >= 0.5 and sh_v >= 3.5 and wr_v >= 45 and gdd_v < 35) or \
                   (daily_v >= 0.6 and sh_v >= 4.0 and wr_v >= 45 and gdd_v < 30) or \
                   (sh_v >= 6.0 and daily_v >= 0.3 and gdd_v < 30)
            a = (daily_v >= 0.25 and sh_v >= 2.5 and wr_v >= 45 and gdd_v < 45) or \
                (daily_v >= 0.3 and sh_v >= 3.0 and wr_v >= 45 and gdd_v < 40) or \
                (sh_v >= 5.0 and daily_v >= 0.2 and gdd_v < 40)
            avg = (daily_v >= 0.1 and sh_v >= 1.5) or daily_v >= 0.05

            if a_pp:
                tier = "ALPHA++"
            elif a:
                tier = "ALPHA"
            elif avg and roi_v > 0:
                tier = "AVERAGE"
            elif roi_v > 0:
                tier = "OK"
            else:
                tier = "REJECT"

            msg += (
                f"{str(i):<3} "
                f"{str(r.get('name',''))[:15]:<16} "
                f"{str(r.get('asset','?'))[:7]:<8} "
                f"{str(r.get('timeframe','?')):<3} "
                f"{str(roi_v):<7} "
                f"{str(wr_v):<5} "
                f"{str(gdd_v):<5} "
                f"{tier}\n"
            )
        msg += "```\n"

        # Benchmark comparison
        if results:
            best = results[0]
            best_roi = round(best.get("roi", 0), 1)
            best_daily = round(best_roi / 365, 3)
            best_name = best.get("name", "?")
            best_asset = best.get("asset", "?")
            safest = min(results[:15], key=lambda x: x.get("net_dd", 100))
            safest_ndd = round(safest.get("net_dd", 0), 1)
            safest_cap = int(safest.get("capital_at_net_dd", 10000))
            safest_name = safest.get("name", "?")
            avg_roi = round(sum(r.get("roi", 0) for r in results[:15]) / min(len(results), 15), 1)
            profitable_pct = round(len(profitable) / len(results) * 100, 0) if results else 0

            msg += (
                f"*Benchmark:*\n"
                f"Best: `{best_name}` on `{best_asset}` = `{best_roi}%/yr` (`{best_daily}%/day`)\n"
                f"Safest: `{safest_name}` NDD=`{safest_ndd}%` Cap=`${safest_cap}`\n"
                f"Avg top 15: `{avg_roi}%/yr` | Profitable: `{profitable_pct:.0f}%`\n"
                f"Cat1 (2%/day): {'YES' if best_daily >= 2.0 else 'NO'} | "
                f"Cat2 (0.5%/day): {'YES' if best_daily >= 0.5 else 'NO'}"
            )
        return msg

    # ------------------------------------------------------------------ #
    # Auto Alpha Hunter (with checkpoints + pause/resume)
    # ------------------------------------------------------------------ #

    _HUNT_CHECKPOINT = os.path.join(_ROOT, "storage", "autohunt_checkpoint.json")
    _HUNT_RESULTS = os.path.join(_ROOT, "storage", "autohunt_results.json")

    def _start_auto_hunt(self, args: list) -> str:
        """Start/stop/resume autonomous strategy hunting."""
        if args and args[0].lower() == "stop":
            self._auto_hunt_running = False
            return "Auto hunt stopped. Progress saved. Use `/autohunt resume` to continue."

        if args and args[0].lower() == "resume":
            if self._auto_hunt_running:
                return "Auto hunt already running."
            self._auto_hunt_running = True
            self._auto_hunt_paused = False
            t = threading.Thread(target=self._auto_hunt_worker, args=(True,), daemon=True)
            t.start()
            return "Auto hunt *RESUMED* from checkpoint."

        if args and args[0].lower() == "status":
            cp = self._load_hunt_checkpoint()
            if cp:
                return (
                    f"*Auto Hunt Status*\n"
                    f"Running: `{self._auto_hunt_running}`\n"
                    f"Paused: `{getattr(self, '_auto_hunt_paused', False)}`\n"
                    f"Tested: `{cp.get('total', 0)}` combos\n"
                    f"Winners: `{cp.get('winners', 0)}`\n"
                    f"Last combo size: `{cp.get('combo_size', '?')}`\n"
                    f"Last combo idx: `{cp.get('combo_idx', '?')}`"
                )
            return "No checkpoint found. Start with `/autohunt`"

        if self._auto_hunt_running:
            return "Auto hunt already running. Use `/autohunt stop` to stop."

        self._auto_hunt_running = True
        self._auto_hunt_paused = False
        t = threading.Thread(target=self._auto_hunt_worker, args=(False,), daemon=True)
        t.start()
        return (
            "*Auto Alpha Hunter STARTED*\n"
            "Testing all signal combinations across assets.\n"
            "Will message you when ALPHA/ALPHA++ found.\n\n"
            "Commands while hunting:\n"
            "  Any command → hunt auto-pauses, runs command, asks to resume\n"
            "  `/autohunt stop` → stop and save checkpoint\n"
            "  `/autohunt resume` → resume from checkpoint\n"
            "  `/autohunt status` → check progress"
        )

    def _save_hunt_checkpoint(self, data):
        os.makedirs(os.path.dirname(self._HUNT_CHECKPOINT), exist_ok=True)
        with open(self._HUNT_CHECKPOINT, "w") as f:
            json.dump(data, f)

    def _load_hunt_checkpoint(self):
        if os.path.exists(self._HUNT_CHECKPOINT):
            with open(self._HUNT_CHECKPOINT) as f:
                return json.load(f)
        return None

    def _save_hunt_result(self, result):
        os.makedirs(os.path.dirname(self._HUNT_RESULTS), exist_ok=True)
        results = []
        if os.path.exists(self._HUNT_RESULTS):
            with open(self._HUNT_RESULTS) as f:
                results = json.load(f)
        results.append(result)
        with open(self._HUNT_RESULTS, "w") as f:
            json.dump(results, f, indent=2)

    def _auto_hunt_worker(self, resume=False):
        """Background worker with checkpoints and pause support."""
        import numpy as np
        from itertools import combinations
        from datetime import datetime as _dt

        self.send_message("Alpha Hunter: Loading data...")

        PERSISTENT = ["EMA_Cross", "Supertrend", "PSAR_Bull", "ADX_Trend", "Trend_MA50",
                       "OBV_Rising", "Ichimoku_Bull", "VWAP"]
        MOMENTARY = ["Volume_Spike", "MACD_Cross", "Breakout_20"]
        all_sigs = PERSISTENT + MOMENTARY

        ASSETS = ["ETHUSDT", "BTCUSDT", "ADAUSDT", "BNBUSDT", "SOLUSDT", "LINKUSDT"]
        TIMEFRAMES = ["1h", "4h"]
        # TF-specific SL/TP/TS params (tighter for shorter TFs)
        PARAMS_BY_TF = {
            "4h": [
                (0.008, 0.03, 0.004), (0.01, 0.04, 0.005),
                (0.01, 0.05, 0.005), (0.012, 0.06, 0.006),
                (0.012, 0.07, 0.006), (0.015, 0.08, 0.007),
                (0.015, 0.09, 0.007), (0.015, 0.10, 0.008),
                (0.02, 0.12, 0.01),
            ],
            "1h": [
                (0.004, 0.012, 0.003), (0.005, 0.015, 0.003),
                (0.005, 0.02, 0.004), (0.006, 0.025, 0.004),
                (0.007, 0.03, 0.005), (0.008, 0.035, 0.005),
                (0.008, 0.04, 0.006), (0.01, 0.05, 0.006),
                (0.01, 0.06, 0.007),
            ],
            "15m": [
                (0.002, 0.006, 0.002), (0.003, 0.008, 0.002),
                (0.003, 0.01, 0.003), (0.004, 0.012, 0.003),
                (0.004, 0.015, 0.003), (0.005, 0.018, 0.004),
                (0.005, 0.02, 0.004), (0.006, 0.025, 0.005),
                (0.007, 0.03, 0.005),
            ],
        }

        # PHASE 0: Test PROVEN combos — includes RELAXED agreement for MORE TRADES
        PROVEN_COMBOS_4H = [
            # Original strict combos (low trades, high PF)
            (["PSAR_Bull", "Volume_Spike", "EMA_Cross", "Supertrend", "Trend_MA50"], 5),
            (["PSAR_Bull", "EMA_Cross", "Volume_Spike", "OBV_Rising"], 4),
            (["Ichimoku_Bull", "PSAR_Bull", "OBV_Rising", "EMA_Cross", "Trend_MA50"], 5),
            (["Ichimoku_Bull", "PSAR_Bull", "EMA_Cross", "Supertrend", "OBV_Rising"], 5),
            (["PSAR_Bull", "EMA_Cross", "Supertrend", "ADX_Trend", "Trend_MA50", "OBV_Rising"], 5),
            # RELAXED agreement — same combos but 3-of-5, 3-of-4 for MORE TRADES
            (["PSAR_Bull", "Volume_Spike", "EMA_Cross", "Supertrend", "Trend_MA50"], 4),
            (["PSAR_Bull", "Volume_Spike", "EMA_Cross", "Supertrend", "Trend_MA50"], 3),
            (["PSAR_Bull", "EMA_Cross", "Volume_Spike", "OBV_Rising"], 3),
            (["Ichimoku_Bull", "PSAR_Bull", "OBV_Rising", "EMA_Cross", "Trend_MA50"], 4),
            (["Ichimoku_Bull", "PSAR_Bull", "OBV_Rising", "EMA_Cross", "Trend_MA50"], 3),
            (["PSAR_Bull", "EMA_Cross", "Supertrend", "ADX_Trend", "Trend_MA50", "OBV_Rising"], 4),
            (["PSAR_Bull", "EMA_Cross", "Supertrend", "ADX_Trend", "Trend_MA50", "OBV_Rising"], 3),
            # Small combos (2-3 signals) — maximum trades
            (["PSAR_Bull", "EMA_Cross", "Supertrend"], 3),
            (["PSAR_Bull", "EMA_Cross", "Supertrend"], 2),
            (["PSAR_Bull", "EMA_Cross", "Trend_MA50"], 2),
            (["EMA_Cross", "Supertrend", "ADX_Trend"], 2),
            (["PSAR_Bull", "OBV_Rising"], 2),
            (["EMA_Cross", "Supertrend"], 2),
            (["PSAR_Bull", "Trend_MA50"], 2),
        ]
        # Shorter TF combos — momentum-based signals that work on 1h/15m
        PROVEN_COMBOS_SHORT = [
            (["EMA_Cross", "MACD_Cross", "Volume_Spike"], 2),
            (["EMA_Cross", "MACD_Cross", "ADX_Trend"], 2),
            (["EMA_Cross", "Supertrend", "MACD_Cross"], 2),
            (["EMA_Cross", "RSI_Oversold", "Volume_Spike"], 2),
            (["PSAR_Bull", "EMA_Cross", "MACD_Cross"], 2),
            (["PSAR_Bull", "EMA_Cross", "MACD_Cross"], 3),
            (["Supertrend", "MACD_Cross", "Volume_Spike"], 2),
            (["Supertrend", "ADX_Trend", "EMA_Cross"], 2),
            (["Supertrend", "ADX_Trend", "EMA_Cross"], 3),
            (["PSAR_Bull", "Supertrend", "EMA_Cross", "MACD_Cross"], 3),
            (["PSAR_Bull", "Supertrend", "EMA_Cross", "MACD_Cross"], 2),
            (["EMA_Cross", "Breakout_20", "Volume_Spike"], 2),
            (["PSAR_Bull", "EMA_Cross", "Stochastic"], 2),
            (["MACD_Cross", "ADX_Trend", "OBV_Rising"], 2),
            (["EMA_Cross", "VWAP", "Volume_Spike"], 2),
        ]
        PROVEN_COMBOS = PROVEN_COMBOS_4H

        data_cache = {}
        for asset in ASSETS:
            for tf in TIMEFRAMES:
                symbol = f"{asset}_{tf}"
                df = load_data(symbol)
                if df is not None:
                    df = calculate_indicators(df)
                    data_cache[symbol] = df

        self.send_message(f"Alpha Hunter: {len(data_cache)} datasets loaded.\nPhase 0: Testing proven combos on ALL timeframes...\nPhase 1: Brute force new combos...")

        # TF-specific tier criteria (relaxed for shorter TFs)
        def get_tier(pf, wr, gdd, tf_str):
            if tf_str == "4h":
                if pf >= 1.8 and wr >= 50 and gdd < 40: return "TIER_1"
                if pf >= 1.6 and wr >= 50 and gdd < 45: return "TIER_2_DEPLOY"
                if pf >= 1.4 and wr >= 50: return "TIER_2_TEST"
                if pf >= 1.2 and wr >= 45: return "PAPER_TRADE"
            elif tf_str == "1h":
                if pf >= 1.6 and wr >= 48 and gdd < 45: return "TIER_1"
                if pf >= 1.4 and wr >= 48 and gdd < 50: return "TIER_2_DEPLOY"
                if pf >= 1.25 and wr >= 46: return "TIER_2_TEST"
                if pf >= 1.15 and wr >= 44: return "PAPER_TRADE"
            else:  # 15m
                if pf >= 1.5 and wr >= 47 and gdd < 50: return "TIER_1"
                if pf >= 1.3 and wr >= 46 and gdd < 55: return "TIER_2_DEPLOY"
                if pf >= 1.2 and wr >= 45: return "TIER_2_TEST"
                if pf >= 1.1 and wr >= 43: return "PAPER_TRADE"
            return None

        def _eval_result(df, combo, min_ag, sl, tp, ts, symbol, yrs, tf_str):
            """Evaluate a single combo — returns result dict or None"""
            nonlocal total, winners
            total += 1
            asset = symbol.split("_")[0]
            min_trades = {"4h": 20, "1h": 50, "15m": 100}.get(tf_str, 20)
            try:
                dc = apply_strategy(df.copy(), list(combo), min_ag)
                cap, trades = run_backtest(dc, sl, tp, ts)
                if len(trades) < min_trades:
                    return None
                roi_a = ((cap / INITIAL_CAPITAL) ** (1 / yrs) - 1) * 100 if cap > 0 else -100
                daily = roi_a / 365
                if daily < 0.005:
                    return None
                w = [t for t in trades if t["pnl"] > 0]
                wr = len(w) / len(trades) * 100
                if wr < 40:
                    return None
                tw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                tl = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                pf = tw / tl if tl > 0 else 0
                if pf < 1.1:
                    return None
                eq = INITIAL_CAPITAL
                pk = eq
                gdd = 0
                for t in trades:
                    eq += t["pnl"]
                    pk = max(pk, eq)
                    dd = (pk - eq) / pk * 100
                    gdd = max(gdd, dd)
                tier = get_tier(pf, wr, gdd, tf_str)
                if tier is not None:
                    winners += 1
                    sig_str = " + ".join(combo)
                    result = {
                        "tier": tier, "signals": list(combo), "min_ag": min_ag,
                        "asset": asset, "tf": tf_str, "sl": sl, "tp": tp, "ts": ts,
                        "roi_a": round(roi_a, 1), "daily": round(daily, 3),
                        "wr": round(wr, 1), "pf": round(pf, 2), "gdd": round(gdd, 1),
                        "trades": len(trades),
                    }
                    self._save_hunt_result(result)
                    self.send_message(
                        f"*{tier} FOUND!*\n\n"
                        f"Signals: `{sig_str}`\n"
                        f"Asset: `{asset}` TF: `{tf_str}` min={min_ag}\n"
                        f"ROI: `{roi_a:.1f}%/yr` PF: `{pf:.2f}` WR: `{wr:.1f}%`\n"
                        f"GDD: `{gdd:.1f}%` Trades: `{len(trades)}`\n"
                        f"Params: SL={sl*100}% TP={tp*100}% TS={ts*100}%"
                    )
                    return result
            except Exception:
                pass
            return None

        # ── PHASE 0: Sweep proven combos on ALL assets + ALL timeframes ──
        for symbol, df in data_cache.items():
            if not self._auto_hunt_running:
                self._save_hunt_checkpoint({"combo_size": 0, "combo_idx": 0, "total": total, "winners": winners})
                self.send_message(f"Alpha Hunter: Paused. {total} tested, {winners} winners.")
                return

            tf_str = symbol.split("_")[1]
            asset = symbol.split("_")[0]
            params = PARAMS_BY_TF.get(tf_str, PARAMS_BY_TF["4h"])
            # Use 4h combos for 4h, short combos for 1h/15m, plus all combos on all TFs
            combos = PROVEN_COMBOS_4H if tf_str == "4h" else PROVEN_COMBOS_SHORT + PROVEN_COMBOS_4H[:5]

            if "timestamp" in df.columns:
                t_s = str(df["timestamp"].iloc[0])[:10]
                t_e = str(df["timestamp"].iloc[-1])[:10]
            else:
                t_s, t_e = "2020-01-01", "2026-03-20"
            try:
                yrs = max((_dt.fromisoformat(t_e) - _dt.fromisoformat(t_s)).days / 365.25, 0.01)
            except Exception:
                yrs = 6.0

            for combo, min_ag in combos:
                for sl, tp, ts in params:
                    _eval_result(df, combo, min_ag, sl, tp, ts, symbol, yrs, tf_str)

        self.send_message(f"Phase 0 done: {total} tested, {winners} winners. Starting Phase 1...")

        # Load checkpoint if resuming
        cp = self._load_hunt_checkpoint() if resume else None
        skip_to_size = cp.get("combo_size", 2) if cp else 2
        skip_to_idx = cp.get("combo_idx", 0) if cp else 0
        if not resume:
            # Keep Phase 0 totals
            pass
        else:
            total = cp.get("total", 0) if cp else 0
            winners = cp.get("winners", 0) if cp else 0

        # Phase 1: combo sizes 2-6 (was 3-6), lower min_agreement
        for combo_size in [2, 3, 4, 5, 6]:
            if combo_size < skip_to_size:
                continue

            combo_list = list(combinations(all_sigs, combo_size))
            start_idx = skip_to_idx if combo_size == skip_to_size else 0

            for cidx, combo in enumerate(combo_list):
                if cidx < start_idx:
                    continue

                # Check pause/stop
                if not self._auto_hunt_running:
                    self._save_hunt_checkpoint({"combo_size": combo_size, "combo_idx": cidx, "total": total, "winners": winners})
                    self.send_message(f"Alpha Hunter: Paused at combo {cidx}/{len(combo_list)} (size {combo_size}). {total} tested, {winners} winners. `/autohunt resume` to continue.")
                    return

                # Pause if another command is being processed
                if getattr(self, '_auto_hunt_paused', False):
                    self._save_hunt_checkpoint({"combo_size": combo_size, "combo_idx": cidx, "total": total, "winners": winners})
                    while self._auto_hunt_paused and self._auto_hunt_running:
                        import time
                        time.sleep(1)
                    if not self._auto_hunt_running:
                        return

                # Test min_agreement from max(combo_size-2, 2) to combo_size
                # This means: 2of2, 2of3, 3of3, 2of4, 3of4, 4of4, etc.
                for min_ag in range(max(combo_size - 2, 2), combo_size + 1):
                    for symbol, df in data_cache.items():
                        tf_str = symbol.split("_")[1]
                        params = PARAMS_BY_TF.get(tf_str, PARAMS_BY_TF["4h"])

                        if "timestamp" in df.columns:
                            t_s = str(df["timestamp"].iloc[0])[:10]
                            t_e = str(df["timestamp"].iloc[-1])[:10]
                        else:
                            t_s, t_e = "2020-01-01", "2026-03-20"
                        try:
                            yrs = max((_dt.fromisoformat(t_e) - _dt.fromisoformat(t_s)).days / 365.25, 0.01)
                        except Exception:
                            yrs = 6.0

                        for sl, tp, ts in params:
                            _eval_result(df, combo, min_ag, sl, tp, ts, symbol, yrs, tf_str)

                # Checkpoint every 50 combos
                if cidx % 50 == 0:
                    self._save_hunt_checkpoint({"combo_size": combo_size, "combo_idx": cidx, "total": total, "winners": winners})

                if total % 10000 == 0 and total > 0:
                    self.send_message(f"Alpha Hunter: `{total}` tested | `{winners}` winners | combo size `{combo_size}` ({cidx}/{len(combo_list)})")

        self._auto_hunt_running = False
        self._save_hunt_checkpoint({"combo_size": 7, "combo_idx": 0, "total": total, "winners": winners, "complete": True})
        self.send_message(
            f"*Alpha Hunter COMPLETE*\n\n"
            f"Total tested: `{total}`\n"
            f"Winners found: `{winners}`\n"
            f"Results saved to storage/autohunt_results.json"
        )

    # ------------------------------------------------------------------ #
    # /generate — New strategy generation engine (5 methods)
    # ------------------------------------------------------------------ #

    def _start_generate(self, args: list) -> str:
        """Launch autonomous strategy generator targeting 1%/day."""
        if args and args[0] == "stop":
            self._generate_running = False
            return "Strategy generator stopped."

        if getattr(self, '_generate_running', False):
            return "Generator already running. `/generate stop` to stop."

        self._generate_running = True
        t = threading.Thread(target=self._generate_worker, daemon=True)
        t.start()
        return (
            "*Strategy Generator Started*\n\n"
            "Target: `1%/day (365%/yr)`\n"
            "Timeframe: `4h`\n\n"
            "Methods:\n"
            "1. ATR-adaptive SL/TP (volatility-based)\n"
            "2. Mean reversion (buy dips)\n"
            "3. Random mutation (genetic-style)\n"
            "4. High-TP hunter (15-40%)\n"
            "5. Trend + dip hybrid\n\n"
            "Will message you when strategies are found.\n"
            "`/generate stop` to stop."
        )

    def _generate_worker(self):
        import random
        import math
        from datetime import datetime as _dt

        ASSETS = ["ETHUSDT", "BTCUSDT", "ADAUSDT", "SOLUSDT", "LINKUSDT", "BNBUSDT"]
        ALL_SIGNALS = list(SIGNAL_FUNCTIONS.keys())
        # Trend signals (persistent — stay on for multiple bars)
        TREND_SIGS = ["EMA_Cross", "Supertrend", "PSAR_Bull", "Trend_MA50",
                      "Ichimoku_Bull", "VWAP", "OBV_Rising", "ADX_Trend"]
        # Dip/mean-reversion signals (momentary — fire on specific conditions)
        DIP_SIGS = ["RSI_Oversold", "BB_Lower", "Stochastic", "CCI_Oversold",
                    "MFI_Oversold", "Keltner_Lower", "Williams_Oversold"]
        # Momentum signals
        MOM_SIGS = ["MACD_Cross", "Volume_Spike", "Breakout_20"]

        results = []
        total = 0
        best_daily = 0

        # Load 4h data
        data_cache = {}
        for asset in ASSETS:
            key = f"{asset}_4h"
            df = load_data(key)
            if df is not None:
                df = calculate_indicators(df)
                data_cache[key] = df

        self.send_message(f"Generator: {len(data_cache)} datasets loaded. Starting 5 methods...")

        def get_years(df):
            if "timestamp" in df.columns:
                t_s = str(df["timestamp"].iloc[0])[:10]
                t_e = str(df["timestamp"].iloc[-1])[:10]
                try:
                    return max((_dt.fromisoformat(t_e) - _dt.fromisoformat(t_s)).days / 365.25, 0.01)
                except:
                    pass
            return 6.0

        def eval_and_report(df, combo, min_ag, sl, tp, ts, asset, yrs, method_name):
            nonlocal total, best_daily, results
            total += 1
            try:
                dc = apply_strategy(df.copy(), list(combo), min_ag)
                cap, trades = run_backtest(dc, sl, tp, ts)
                if len(trades) < 10:
                    return
                roi_a = ((cap / INITIAL_CAPITAL) ** (1 / yrs) - 1) * 100 if cap > 0 else -100
                daily = roi_a / 365
                if daily < 0.2:
                    return
                w = [t for t in trades if t["pnl"] > 0]
                wr = len(w) / len(trades) * 100
                tw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                tl = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                pf = tw / tl if tl > 0 else 0
                eq = INITIAL_CAPITAL
                pk = eq
                gdd = 0
                for t in trades:
                    eq += t["pnl"]
                    pk = max(pk, eq)
                    dd = (pk - eq) / pk * 100
                    gdd = max(gdd, dd)

                sig_str = " + ".join(combo)
                r = {
                    "method": method_name, "signals": sig_str, "min_ag": min_ag,
                    "asset": asset, "sl": sl, "tp": tp, "ts": ts,
                    "roi_day": round(daily, 4), "roi_yr": round(roi_a, 1),
                    "pf": round(pf, 2), "wr": round(wr, 1), "gdd": round(gdd, 1),
                    "trades": len(trades), "final_cap": round(cap, 0),
                }
                results.append(r)

                # Report anything >= 0.5%/day immediately
                if daily >= 0.5 or daily > best_daily:
                    best_daily = max(best_daily, daily)
                    tag = "1%+ TARGET HIT!" if daily >= 1.0 else "NEW BEST" if daily >= best_daily else "0.5%+"
                    self.send_message(
                        f"*{tag}*  `{daily:.3f}%/day` ({roi_a:.1f}%/yr)\n\n"
                        f"Method: `{method_name}`\n"
                        f"Signals: `{sig_str}` (min={min_ag})\n"
                        f"Asset: `{asset}` 4h\n"
                        f"PF: `{pf:.2f}` WR: `{wr:.1f}%` GDD: `{gdd:.1f}%`\n"
                        f"Trades: `{len(trades)}` Final: `${cap:,.0f}`\n"
                        f"Params: SL={sl*100:.1f}% TP={tp*100:.1f}% TS={ts*100:.1f}%"
                    )
            except:
                pass

        # ══════════════════════════════════════════════════════════════
        # METHOD 1: ATR-Adaptive SL/TP
        # Instead of fixed %, use ATR multiples for volatility-adaptive stops
        # ══════════════════════════════════════════════════════════════
        if self._generate_running:
            self.send_message("Method 1/5: ATR-Adaptive SL/TP...")
            combos_m1 = [
                (["PSAR_Bull", "EMA_Cross", "Supertrend"], 2),
                (["PSAR_Bull", "EMA_Cross"], 2),
                (["EMA_Cross", "Supertrend"], 2),
                (["PSAR_Bull", "Trend_MA50"], 2),
                (["Ichimoku_Bull", "PSAR_Bull", "EMA_Cross"], 2),
                (["PSAR_Bull", "MACD_Cross", "EMA_Cross"], 2),
                (["EMA_Cross", "Supertrend", "ADX_Trend"], 2),
                (["PSAR_Bull", "Supertrend", "MACD_Cross", "EMA_Cross"], 2),
            ]
            for key, df in data_cache.items():
                if not self._generate_running:
                    break
                asset = key.split("_")[0]
                yrs = get_years(df)
                # Use ATR to set dynamic SL/TP per asset
                avg_atr_pct = (df["atr"] / df["close"]).mean() * 100  # avg ATR as % of price
                for combo, min_ag in combos_m1:
                    # SL = 1-3x ATR, TP = 3-12x ATR, TS = 0.5-2x ATR
                    for sl_mult in [1.0, 1.5, 2.0, 2.5, 3.0]:
                        for tp_mult in [3, 5, 8, 10, 12, 15, 20]:
                            for ts_mult in [0.5, 1.0, 1.5]:
                                sl = avg_atr_pct * sl_mult / 100
                                tp = avg_atr_pct * tp_mult / 100
                                ts = avg_atr_pct * ts_mult / 100
                                if tp <= sl or tp < 0.02:
                                    continue
                                eval_and_report(df, combo, min_ag, sl, tp, ts, asset, yrs, "ATR_Adaptive")

        # ══════════════════════════════════════════════════════════════
        # METHOD 2: Mean Reversion (Buy the Dip)
        # Use oversold signals — completely different from trend-following
        # ══════════════════════════════════════════════════════════════
        if self._generate_running:
            self.send_message("Method 2/5: Mean Reversion (buy dips)...")
            dip_combos = [
                (["RSI_Oversold"], 1), (["BB_Lower"], 1), (["CCI_Oversold"], 1),
                (["MFI_Oversold"], 1), (["Stochastic"], 1), (["Keltner_Lower"], 1),
                (["Williams_Oversold"], 1),
                (["RSI_Oversold", "BB_Lower"], 1), (["RSI_Oversold", "CCI_Oversold"], 1),
                (["BB_Lower", "Stochastic"], 1), (["MFI_Oversold", "RSI_Oversold"], 1),
                (["Keltner_Lower", "Williams_Oversold"], 1),
                (["RSI_Oversold", "Volume_Spike"], 1), (["BB_Lower", "Volume_Spike"], 1),
                (["CCI_Oversold", "MFI_Oversold"], 1),
                (["RSI_Oversold", "BB_Lower", "Stochastic"], 1),
                (["RSI_Oversold", "BB_Lower", "Stochastic"], 2),
                (["CCI_Oversold", "MFI_Oversold", "Williams_Oversold"], 1),
                (["CCI_Oversold", "MFI_Oversold", "Williams_Oversold"], 2),
                # Dip + trend filter (buy dip only when overall trend is up)
                (["RSI_Oversold", "Trend_MA50"], 2),
                (["BB_Lower", "EMA_Cross"], 2),
                (["Stochastic", "PSAR_Bull"], 2),
                (["CCI_Oversold", "Supertrend"], 2),
                (["MFI_Oversold", "Trend_MA50"], 2),
            ]
            dip_params = [
                (0.005, 0.015, 0.003), (0.005, 0.02, 0.004), (0.008, 0.03, 0.005),
                (0.008, 0.04, 0.005), (0.01, 0.05, 0.006), (0.01, 0.06, 0.006),
                (0.012, 0.08, 0.007), (0.015, 0.10, 0.008), (0.015, 0.12, 0.008),
                (0.02, 0.15, 0.01), (0.02, 0.20, 0.01),
            ]
            for key, df in data_cache.items():
                if not self._generate_running:
                    break
                asset = key.split("_")[0]
                yrs = get_years(df)
                for combo, min_ag in dip_combos:
                    for sl, tp, ts in dip_params:
                        eval_and_report(df, combo, min_ag, sl, tp, ts, asset, yrs, "Mean_Reversion")

        # ══════════════════════════════════════════════════════════════
        # METHOD 3: Random Mutation (Genetic-style)
        # Randomly combine signals + params, keep winners, mutate them
        # ══════════════════════════════════════════════════════════════
        if self._generate_running:
            self.send_message("Method 3/5: Random Mutation (1000 random strategies)...")
            random.seed(42)
            for _ in range(1000):
                if not self._generate_running:
                    break
                # Random combo: 1-5 signals
                n_sigs = random.randint(1, 5)
                combo = random.sample(ALL_SIGNALS, min(n_sigs, len(ALL_SIGNALS)))
                min_ag = random.randint(1, max(1, len(combo) - 1))
                # Random params
                sl = random.uniform(0.005, 0.03)
                tp = random.uniform(0.02, 0.40)
                ts = random.uniform(0.003, 0.02)
                if tp <= sl:
                    continue
                # Random asset
                key = random.choice(list(data_cache.keys()))
                df = data_cache[key]
                asset = key.split("_")[0]
                yrs = get_years(df)
                eval_and_report(df, combo, min_ag, sl, tp, ts, asset, yrs, "Random_Mutation")

        # ══════════════════════════════════════════════════════════════
        # METHOD 4: High-TP Hunter (15-40%)
        # Specifically target huge TP for maximum ROI per trade
        # ══════════════════════════════════════════════════════════════
        if self._generate_running:
            self.send_message("Method 4/5: High-TP Hunter (15-40%)...")
            high_tp_combos = [
                (["PSAR_Bull", "EMA_Cross", "Supertrend"], 2),
                (["EMA_Cross", "Supertrend"], 2),
                (["PSAR_Bull", "Trend_MA50"], 2),
                (["Ichimoku_Bull", "PSAR_Bull", "EMA_Cross"], 2),
                (["EMA_Cross", "Breakout_20"], 2),
                (["Breakout_20", "Volume_Spike"], 2),
                (["PSAR_Bull", "ADX_Trend", "Volume_Spike"], 2),
                (["EMA_Cross", "ADX_Trend", "MACD_Cross"], 2),
                (["PSAR_Bull", "EMA_Cross", "MACD_Cross"], 2),
                (["Supertrend", "ADX_Trend"], 2),
                (["PSAR_Bull", "Supertrend"], 2),
                (["EMA_Cross", "MACD_Cross", "Volume_Spike"], 2),
            ]
            high_tp_params = [
                (0.01, 0.15, 0.008), (0.012, 0.18, 0.01), (0.015, 0.20, 0.01),
                (0.015, 0.25, 0.012), (0.02, 0.30, 0.015), (0.02, 0.35, 0.015),
                (0.025, 0.40, 0.02), (0.03, 0.45, 0.02), (0.03, 0.50, 0.025),
            ]
            for key, df in data_cache.items():
                if not self._generate_running:
                    break
                asset = key.split("_")[0]
                yrs = get_years(df)
                for combo, min_ag in high_tp_combos:
                    for sl, tp, ts in high_tp_params:
                        eval_and_report(df, combo, min_ag, sl, tp, ts, asset, yrs, "High_TP")

        # ══════════════════════════════════════════════════════════════
        # METHOD 5: Trend + Dip Hybrid
        # Use trend signals as filter, dip signals as entry trigger
        # ══════════════════════════════════════════════════════════════
        if self._generate_running:
            self.send_message("Method 5/5: Trend + Dip Hybrid...")
            # Combine 1 trend filter + 1 dip entry — both must fire (min_ag=2)
            hybrid_combos = []
            for trend_sig in TREND_SIGS:
                for dip_sig in DIP_SIGS:
                    hybrid_combos.append(([trend_sig, dip_sig], 2))
            # Also 1 trend + 2 dips (min_ag=2 — trend + at least 1 dip)
            for trend_sig in ["PSAR_Bull", "EMA_Cross", "Supertrend", "Trend_MA50"]:
                for i in range(len(DIP_SIGS)):
                    for j in range(i + 1, len(DIP_SIGS)):
                        hybrid_combos.append(([trend_sig, DIP_SIGS[i], DIP_SIGS[j]], 2))

            hybrid_params = [
                (0.008, 0.03, 0.004), (0.01, 0.05, 0.005), (0.01, 0.06, 0.006),
                (0.012, 0.08, 0.007), (0.015, 0.10, 0.008), (0.015, 0.12, 0.008),
                (0.02, 0.15, 0.01), (0.02, 0.20, 0.01), (0.025, 0.25, 0.012),
            ]
            for key, df in data_cache.items():
                if not self._generate_running:
                    break
                asset = key.split("_")[0]
                yrs = get_years(df)
                for combo, min_ag in hybrid_combos:
                    for sl, tp, ts in hybrid_params:
                        eval_and_report(df, combo, min_ag, sl, tp, ts, asset, yrs, "Trend_Dip_Hybrid")

        # ══════════════════════════════════════════════════════════════
        # FINAL SUMMARY
        # ══════════════════════════════════════════════════════════════
        self._generate_running = False

        # Sort by ROI/day
        results.sort(key=lambda x: -x["roi_day"])

        # Save to file
        import json
        gen_path = os.path.join(_ROOT, "storage", "generate_results.json")
        with open(gen_path, "w") as f:
            json.dump(results, f, indent=2)

        # Build summary message
        above_1 = [r for r in results if r["roi_day"] >= 1.0]
        above_05 = [r for r in results if r["roi_day"] >= 0.5]
        above_03 = [r for r in results if r["roi_day"] >= 0.3]

        msg = (
            f"*Strategy Generator COMPLETE*\n\n"
            f"Total tested: `{total}`\n"
            f"Total with ROI > 0.2%/day: `{len(results)}`\n\n"
            f"*>= 1.0%/day: `{len(above_1)}`*\n"
            f">= 0.5%/day: `{len(above_05)}`\n"
            f">= 0.3%/day: `{len(above_03)}`\n"
            f"Best: `{results[0]['roi_day']:.3f}%/day` ({results[0]['roi_yr']:.1f}%/yr)\n\n" if results else ""
        )

        # Top 10
        if results:
            msg += "*TOP 10:*\n"
            seen = set()
            n = 0
            for r in results:
                k = (r["asset"], r["signals"], r["min_ag"])
                if k in seen:
                    continue
                seen.add(k)
                n += 1
                if n > 10:
                    break
                tag = "***" if r["roi_day"] >= 1.0 else ""
                msg += (
                    f"\n`{n}. {r['roi_day']:.3f}%/day` ({r['roi_yr']:.1f}%/yr) {tag}\n"
                    f"   {r['method']} | {r['asset']}\n"
                    f"   `{r['signals']}` min={r['min_ag']}\n"
                    f"   PF={r['pf']} WR={r['wr']}% Trades={r['trades']}\n"
                    f"   SL={r['sl']*100:.1f}% TP={r['tp']*100:.1f}%\n"
                )

        msg += f"\nResults saved to storage/generate_results.json"
        self.send_message(msg)

    # ------------------------------------------------------------------ #
    # /ml — Machine Learning strategy scanner
    # ------------------------------------------------------------------ #

    def _start_ml(self, args: list) -> str:
        """Launch ML strategy scanner."""
        if args and args[0] == "stop":
            self._ml_running = False
            return "ML scanner stopped."

        if args and args[0] == "status":
            return self._ml_status()

        if args and args[0] == "results":
            return self._ml_results()

        if getattr(self, '_ml_running', False):
            return "ML scanner already running.\n`/ml status` — check progress\n`/ml results` — see results\n`/ml stop` — stop scanner"

        # Parse args: /ml [assets] [tf]
        assets = ["ETHUSDT", "BTCUSDT", "ADAUSDT", "SOLUSDT", "LINKUSDT", "BNBUSDT"]
        tf_list = ["4h"]
        if args:
            if args[0] in ("1h", "4h", "15m"):
                tf_list = [args[0]]
            elif args[0].upper().endswith("USDT"):
                assets = [a.upper() for a in args]

        self._ml_running = True
        self._ml_progress = {"total": 0, "hits": 0, "current_asset": "", "current_model": "", "started": datetime.now().isoformat()}
        t = threading.Thread(target=self._ml_worker, args=(assets, tf_list), daemon=True)
        t.start()
        return (
            f"*ML Strategy Scanner Started*\n\n"
            f"Models: `Random Forest` + `Gradient Boosting`\n"
            f"Features: `40+ indicators` (EMA, RSI, MACD, BB, ATR, Ichimoku, PSAR, etc.)\n"
            f"Assets: `{', '.join(assets)}`\n"
            f"Timeframe: `{', '.join(tf_list)}`\n"
            f"Validation: `Walk-forward (70% train / 30% OOS test)`\n\n"
            f"Testing 10 TP/SL combos x 2 models per asset...\n"
            f"Results are OUT-OF-SAMPLE only (no overfitting).\n\n"
            f"`/ml stop` to stop.\n"
            f"`/ml status` — check progress\n"
            f"`/ml results` — see completed results"
        )

    def _ml_status(self) -> str:
        """Show ML scanner progress."""
        prog = getattr(self, '_ml_progress', {})
        running = getattr(self, '_ml_running', False)

        if not prog and not running:
            return "ML scanner not running. Start with `/ml`"

        # Load results count
        ml_path = os.path.join(_ROOT, "storage", "ml_results.json")
        results = []
        try:
            with open(ml_path) as f:
                results = json.load(f)
        except:
            pass

        status = "Running" if running else "Completed"
        return (
            f"*ML Scanner Status: {status}*\n\n"
            f"Tests completed: `{prog.get('total', 0)}`\n"
            f"Strategies found: `{prog.get('hits', 0)}`\n"
            f"Current: `{prog.get('current_asset', '—')} {prog.get('current_model', '')}`\n"
            f"Started: `{prog.get('started', '—')}`\n\n"
            f"Saved results: `{len(results)}`\n"
            f"Use `/ml results` to see them."
        )

    def _ml_results(self) -> str:
        """Show ML scanner results."""
        ml_path = os.path.join(_ROOT, "storage", "ml_results.json")
        try:
            with open(ml_path) as f:
                results = json.load(f)
        except:
            return "No ML results yet. Run `/ml` first."

        if not results:
            return "No ML results yet. Run `/ml` first."

        # Sort by ROI/day
        results.sort(key=lambda x: -x.get("roi_day", 0))

        above1 = len([r for r in results if r.get("roi_day", 0) >= 1.0])
        above05 = len([r for r in results if r.get("roi_day", 0) >= 0.5])
        above03 = len([r for r in results if r.get("roi_day", 0) >= 0.3])

        msg = (
            f"*ML Scanner Results*\n\n"
            f"Total found: `{len(results)}`\n"
            f">= 1.0%/day: `{above1}`\n"
            f">= 0.5%/day: `{above05}`\n"
            f">= 0.3%/day: `{above03}`\n\n"
            f"*TOP 10:*\n"
        )

        seen = set()
        n = 0
        for r in results:
            k = (r.get("asset", ""), r.get("model", ""))
            if k in seen:
                continue
            seen.add(k)
            n += 1
            if n > 10:
                break
            tag = " ***" if r.get("roi_day", 0) >= 1.0 else ""
            msg += (
                f"\n`{n}. {r.get('roi_day', 0):.3f}%/day` ({r.get('roi_yr', 0):.0f}%/yr){tag}\n"
                f"   {r.get('model', '').upper()} | {r.get('asset', '')} {r.get('tf', '')}\n"
                f"   PF={r.get('pf', 0)} WR={r.get('wr', 0)}% Trades={r.get('trades', 0)}\n"
                f"   TP={r.get('tp_pct', 0)*100:.0f}% SL={r.get('sl_pct', 0)*100:.0f}%\n"
                f"   Acc={r.get('accuracy', 0)}% Prec={r.get('precision', 0)}%\n"
            )

        return msg

    def _ml_worker(self, assets, tf_list):
        try:
            from src.ml_strategy import train_and_evaluate
        except ImportError:
            try:
                from ml_strategy import train_and_evaluate
            except ImportError:
                self.send_message("ML module not found. Ensure src/ml_strategy.py exists.")
                self._ml_running = False
                return

        param_grid = [
            (0.015, 0.008, 12), (0.02, 0.01, 12), (0.03, 0.015, 12),
            (0.04, 0.02, 12), (0.05, 0.025, 18), (0.06, 0.03, 18),
            (0.08, 0.04, 24), (0.10, 0.05, 24), (0.15, 0.07, 30),
            (0.20, 0.10, 36),
        ]
        models = ["rf", "gbm"]
        results = []
        total = 0
        best_daily = 0

        for asset in assets:
            if not self._ml_running:
                break
            for tf in tf_list:
                for model_type in models:
                    for tp, sl, horizon in param_grid:
                        if not self._ml_running:
                            break
                        total += 1
                        self._ml_progress = {
                            "total": total, "hits": len(results),
                            "current_asset": asset, "current_model": f"{model_type} TP={tp*100:.0f}%",
                            "started": getattr(self, '_ml_progress', {}).get('started', ''),
                        }
                        try:
                            r = train_and_evaluate(asset, tf, tp_pct=tp, sl_pct=sl,
                                                   horizon=horizon, model_type=model_type)
                            if r and r["roi_day"] > 0.1:
                                results.append(r)
                                # Report good ones immediately
                                if r["roi_day"] >= 0.5 or r["roi_day"] > best_daily:
                                    best_daily = max(best_daily, r["roi_day"])
                                    tag = "1%+ TARGET!" if r["roi_day"] >= 1.0 else "NEW BEST" if r["roi_day"] >= best_daily else "0.5%+"
                                    self.send_message(
                                        f"*ML {tag}*  `{r['roi_day']:.3f}%/day` ({r['roi_yr']:.0f}%/yr)\n\n"
                                        f"Model: `{r['model'].upper()}`\n"
                                        f"Asset: `{asset}` TF: `{tf}`\n"
                                        f"PF: `{r['pf']}` WR: `{r['wr']}%` GDD: `{r['gdd']}%`\n"
                                        f"Trades: `{r['trades']}` ({r['trades_per_day']:.1f}/day)\n"
                                        f"TP: `{r['tp_pct']*100}%` SL: `{r['sl_pct']*100}%`\n"
                                        f"Accuracy: `{r['accuracy']}%` Precision: `{r['precision']}%`\n"
                                        f"Final: `${r['final_cap']:,.0f}` | Test: `{r['test_years']:.1f}yr OOS`\n"
                                        f"Top features: `{', '.join(f[0] for f in r['top_features'][:5])}`"
                                    )
                        except Exception as e:
                            pass

                self.send_message(f"ML: `{asset} {tf}` done — {total} tested, {len(results)} hits")

        self._ml_running = False

        # Final summary
        results.sort(key=lambda x: -x["roi_day"])

        # Save
        import json
        gen_path = os.path.join(_ROOT, "storage", "ml_results.json")
        with open(gen_path, "w") as f:
            json.dump([{k: v for k, v in r.items() if k != "top_features"} for r in results], f, indent=2)

        above1 = [r for r in results if r["roi_day"] >= 1.0]
        above05 = [r for r in results if r["roi_day"] >= 0.5]

        msg = (
            f"*ML Scanner COMPLETE*\n\n"
            f"Total tested: `{total}`\n"
            f"Profitable: `{len(results)}`\n\n"
            f"*>= 1.0%/day: `{len(above1)}`*\n"
            f">= 0.5%/day: `{len(above05)}`\n\n"
        )

        if results:
            msg += "*TOP 5 (OUT-OF-SAMPLE):*\n"
            seen = set()
            n = 0
            for r in results:
                k = (r["asset"], r["model"])
                if k in seen:
                    continue
                seen.add(k)
                n += 1
                if n > 5:
                    break
                msg += (
                    f"\n`{n}. {r['roi_day']:.3f}%/day` ({r['roi_yr']:.0f}%/yr)\n"
                    f"   {r['model'].upper()} | {r['asset']} {r['tf']}\n"
                    f"   PF={r['pf']} WR={r['wr']}% Trades={r['trades']}\n"
                    f"   TP={r['tp_pct']*100}% SL={r['sl_pct']*100}%\n"
                    f"   Acc={r['accuracy']}% Prec={r['precision']}%\n"
                )

        msg += f"\nResults saved to storage/ml_results.json"
        self.send_message(msg)

    # ------------------------------------------------------------------ #
    # /evolve — Genetic Algorithm status & control
    # ------------------------------------------------------------------ #

    def _evolve_cmd(self, args: list) -> str:
        """Check genetic evolution status and results."""
        gen_path = os.path.join(_ROOT, "storage", "genetic_results.json")

        if args and args[0] == "start":
            # Start genetic evolution in background
            if getattr(self, '_evolve_running', False):
                return "Evolution already running. `/evolve status` to check."
            self._evolve_running = True
            def run_evolve():
                try:
                    from src.genetic_strategy import evolve
                except ImportError:
                    from genetic_strategy import evolve
                def cb(gen, info, best):
                    if gen % 5 == 0 or info["best_roi_day"] >= 1.0:
                        self.send_message(
                            f"*Gen {gen}* | Best: `{info['best_roi_day']:.3f}%/day`\n"
                            f"All-time: `{best[2]['roi_day']:.3f}%/day`\n"
                            f">= 1%: `{info.get('above_1pct', 0)}` | >= 0.5%: `{info.get('above_05pct', 0)}`\n"
                            f"Total viable: `{info.get('total_viable', 0)}`\n"
                            f"Asset: `{info['best_asset']}` [{info['best_signals'][:40]}]"
                        )
                evolve(pop_size=100, generations=50, target_roi_day=3.0, callback=cb)
                self._evolve_running = False
                self.send_message("*Evolution COMPLETE.* Use `/evolve results` to see all strategies.")
            t = threading.Thread(target=run_evolve, daemon=True)
            t.start()
            return "Genetic evolution started! 100 strategies x 50 generations.\nUpdates every 5 generations. `/evolve status` to check."

        if args and args[0] == "results":
            try:
                with open(gen_path) as f:
                    data = json.load(f)
            except:
                return "No results yet. Start with `/evolve start`"

            strats = data.get("all_strategies", [])
            counts = data.get("counts", {})
            msg = (
                f"*Genetic Evolution Results*\n\n"
                f"Status: `{data.get('status', 'unknown')}`\n"
                f"Generation: `{data.get('generation', 0)}/{data.get('total_generations', 0)}`\n\n"
                f"*Counts:*\n"
                f">= 3%/day: `{counts.get('above_3pct', 0)}`\n"
                f">= 1%/day: `{counts.get('above_1pct', 0)}`\n"
                f">= 0.5%/day: `{counts.get('above_05pct', 0)}`\n"
                f">= 0.3%/day: `{counts.get('above_03pct', 0)}`\n"
                f"Total viable: `{counts.get('total', 0)}`\n\n"
                f"*TOP 10:*\n"
            )
            for i, r in enumerate(strats[:10]):
                tag = " ***" if r.get("roi_day", 0) >= 1.0 else ""
                msg += (
                    f"\n`{i+1}. {r.get('roi_day',0):.3f}%/day` ({r.get('roi_yr',0):.0f}%/yr){tag}\n"
                    f"   {r.get('asset','')} | PF={r.get('pf',0)} WR={r.get('wr',0)}% GDD={r.get('gdd',0)}%\n"
                    f"   `{r.get('signals','')[:50]}`\n"
                    f"   SL={r.get('sl',0)*100:.1f}% TP={r.get('tp',0)*100:.1f}% Trades={r.get('trades',0)}\n"
                )
            return msg

        # Default: status
        try:
            with open(gen_path) as f:
                data = json.load(f)
        except:
            return "No evolution data. Start with `/evolve start`"

        best = data.get("all_time_best", {})
        counts = data.get("counts", {})
        running = getattr(self, '_evolve_running', False)
        return (
            f"*Genetic Evolution Status*\n\n"
            f"Status: `{'Running' if running else data.get('status', 'unknown')}`\n"
            f"Generation: `{data.get('generation', 0)}/{data.get('total_generations', 0)}`\n\n"
            f"*All-time best:* `{best.get('roi_day', 0):.3f}%/day`\n"
            f"Asset: `{best.get('asset', '')}` | PF={best.get('pf', 0)} WR={best.get('wr', 0)}%\n"
            f"Signals: `{best.get('signals', '')[:50]}`\n\n"
            f"*Found so far:*\n"
            f">= 3%/day: `{counts.get('above_3pct', 0)}`\n"
            f">= 1%/day: `{counts.get('above_1pct', 0)}`\n"
            f">= 0.5%/day: `{counts.get('above_05pct', 0)}`\n"
            f"Total: `{counts.get('total', 0)}`\n\n"
            f"`/evolve results` — see top strategies\n"
            f"`/evolve start` — start new evolution"
        )

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

                    # Check if user is pasting a Pine Script
                    _is_pine = (
                        str(chat_id) in self._pine_pending
                        and (
                            "//@version" in text
                            or "strategy(" in text
                            or "ta." in text
                            or "indicator(" in text
                            or not command.startswith("/")
                        )
                    )
                    if _is_pine:
                        logger.info("Received Pine Script paste")
                        self.send_typing_action()
                        response = self._handle_pine_script(text)
                        if response:
                            self.send_message(response)
                        continue

                    # Handle greetings without "/" prefix
                    _GREETINGS = ("hello", "hi", "suno", "namaste", "hui",
                                    "stop", "pause", "ruko", "bas")
                    if command.lower() in _GREETINGS:
                        logger.info(f"Greeting: {command}")
                        self.send_typing_action()
                        response = self.process_command(command, args)
                        self.send_message(response)
                        self._post_command_hook()
                    elif command.startswith("/"):
                        logger.info(f"Command: {command} {args}")
                        self.send_typing_action()
                        response = self.process_command(command, args)
                        self.send_message(response)
                        self._post_command_hook()

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
