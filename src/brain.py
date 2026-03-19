"""
Trading Bot Brain — Claude-powered AI analysis layer.

Provides two capabilities:
1. Auto-analysis: after every backtest, generate an expert summary of results.
2. Free Q&A:  answer any natural-language question about the bot, strategies, or market.

Requires ANTHROPIC_API_KEY in .env
"""

import os
import logging
from typing import List, Dict, Any

import anthropic
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_MODEL = "claude-opus-4-6"

_SYSTEM_PROMPT = """You are an expert algorithmic cryptocurrency trading analyst and quantitative researcher.
You have deep knowledge of:
- Technical indicators: RSI, MACD, Bollinger Bands, EMA/SMA crossovers, VWAP, ATR, Stochastic, ADX, Supertrend
- Backtesting methodology: walk-forward validation, overfitting risks, look-ahead bias
- Risk management: stop-loss, take-profit, trailing stops, position sizing, drawdown control
- Strategy evaluation: Sharpe ratio, Sortino ratio, Calmar ratio, profit factor, win rate
- Crypto market structure: BTC/ETH/BNB/SOL/XRP characteristics, volatility regimes, timeframe selection

When analysing backtest results:
- Be direct and specific. Point out what the numbers actually mean.
- Highlight the best and worst strategies with reasons.
- Flag any risk concerns (high drawdown, low trade count, overfitting signals).
- Give 2-3 concrete, actionable recommendations.

Keep responses concise and structured. Use bullet points. Avoid generic advice."""


class TradingBrain:
    """AI brain that wraps the Claude API for trading analysis."""

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found in environment. "
                "Add it to your .env file to enable the AI brain."
            )
        self.client = anthropic.Anthropic(api_key=api_key)

    # ------------------------------------------------------------------ #
    # Core streaming helper
    # ------------------------------------------------------------------ #

    def _ask(self, messages: List[Dict[str, str]], max_tokens: int = 1024) -> str:
        """Send messages to Claude and return the full response text via streaming."""
        full_text = ""
        with self.client.messages.stream(
            model=_MODEL,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            system=_SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                full_text += text
        return full_text.strip()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def analyze_backtest(self, results: List[Dict[str, Any]], symbol: str, batches: list) -> str:
        """
        Analyse a batch backtest result list and return an expert summary.

        Parameters
        ----------
        results : list of dicts, each with keys:
            id, name, strategies, trades, wins, losses, win_rate, roi, final_capital
        symbol  : e.g. "BTCUSDT_15m"
        batches : e.g. [1, 2, 3]
        """
        if not results:
            return "No backtest results to analyse."

        results_sorted = sorted(results, key=lambda r: r.get("roi", 0), reverse=True)
        profitable = [r for r in results_sorted if r.get("roi", 0) > 0]
        top5 = results_sorted[:5]
        bottom5 = results_sorted[-5:]

        def fmt(r: dict) -> str:
            return (
                f"  • {r['name']}: ROI={r.get('roi', 0):.2f}%, "
                f"Win%={r.get('win_rate', 0):.1f}%, Trades={r.get('trades', 0)}"
            )

        context = (
            f"Backtest completed on {symbol}, batches {batches}.\n"
            f"Total strategies tested: {len(results)}\n"
            f"Profitable strategies: {len(profitable)} ({len(profitable)/len(results)*100:.0f}%)\n"
            f"Best ROI: {results_sorted[0].get('roi', 0):.2f}%\n"
            f"Worst ROI: {results_sorted[-1].get('roi', 0):.2f}%\n\n"
            f"Top 5 strategies:\n" + "\n".join(fmt(r) for r in top5) + "\n\n"
            f"Bottom 5 strategies:\n" + "\n".join(fmt(r) for r in bottom5)
        )

        messages = [{"role": "user", "content": (
            f"Here are the backtest results:\n\n{context}\n\n"
            "Please provide:\n"
            "1. A brief assessment of overall performance\n"
            "2. What makes the top strategies successful\n"
            "3. Why the bottom strategies are underperforming\n"
            "4. 2-3 concrete next steps to improve results"
        )}]

        return self._ask(messages, max_tokens=800)

    def analyze_optimization(
        self,
        original_results: List[Dict[str, Any]],
        optimized_results: List[Dict[str, Any]],
        best_params: Dict[str, float],
    ) -> str:
        """Compare pre/post optimization results and explain the improvement."""
        if not optimized_results:
            return "No optimized results to analyse."

        def summary(results: List[Dict[str, Any]]) -> str:
            if not results:
                return "N/A"
            profitable = [r for r in results if r.get("roi", 0) > 0]
            best = max(results, key=lambda r: r.get("roi", 0))
            return (
                f"profitable={len(profitable)}/{len(results)}, "
                f"best_roi={best.get('roi', 0):.2f}%, "
                f"avg_roi={sum(r.get('roi',0) for r in results)/len(results):.2f}%"
            )

        param_str = ", ".join(
            f"{k}={v*100:.1f}%" for k, v in best_params.items()
        )

        context = (
            f"Before optimization: {summary(original_results)}\n"
            f"After  optimization: {summary(optimized_results)}\n"
            f"Optimized parameters: {param_str}"
        )

        messages = [{"role": "user", "content": (
            f"Auto-optimization just ran on the trading strategies.\n\n{context}\n\n"
            "Explain: did the optimization help? Why or why not? "
            "Are the new parameters sensible for crypto trading? "
            "What should the trader watch out for?"
        )}]

        return self._ask(messages, max_tokens=600)

    def answer_question(self, question: str, bot_context: Dict[str, Any] = None) -> str:
        """
        Answer any free-form question the user sends via /ask.

        Parameters
        ----------
        question    : the user's message
        bot_context : optional dict with current bot state (default symbol, last results, etc.)
        """
        context_block = ""
        if bot_context:
            parts = []
            if "default_symbol" in bot_context:
                parts.append(f"Current default symbol: {bot_context['default_symbol']}")
            if "opt_years" in bot_context:
                parts.append(f"Optimization lookback: {bot_context['opt_years']} year(s)")
            if "last_results" in bot_context and bot_context["last_results"]:
                r = bot_context["last_results"]
                profitable = [x for x in r if x.get("roi", 0) > 0]
                best = max(r, key=lambda x: x.get("roi", 0))
                parts.append(
                    f"Last backtest: {len(r)} strategies, "
                    f"{len(profitable)} profitable, "
                    f"best ROI={best.get('roi', 0):.2f}%"
                )
            if parts:
                context_block = "Bot context:\n" + "\n".join(f"  - {p}" for p in parts) + "\n\n"

        messages = [{"role": "user", "content": context_block + question}]
        return self._ask(messages, max_tokens=1000)
