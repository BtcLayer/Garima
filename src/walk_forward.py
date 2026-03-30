"""
Walk-Forward Validation (P2 #11)

Splits historical data into rolling train/test windows and validates
that strategies perform on unseen data, not just in-sample.

Walk-forward approach:
  - Split 6yr data into N windows (default: 6 x 1yr)
  - For each window: train on previous windows, test on current
  - Report in-sample vs out-of-sample performance
  - Flag strategies that degrade out-of-sample (overfitting signal)

Usage:
    from src.walk_forward import walk_forward_validate
    results = walk_forward_validate("BTCUSDT_4h", strategy_dict, n_windows=6)
"""

import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run_strategies_batch import (
    load_data, calculate_indicators, apply_strategy, run_backtest,
    INITIAL_CAPITAL
)


def _split_windows(df, n_windows: int = 6) -> list:
    """Split dataframe into N equal-sized windows. Returns list of (train_df, test_df)."""
    total = len(df)
    window_size = total // n_windows
    splits = []

    for i in range(1, n_windows):
        train_end = i * window_size
        test_end = min((i + 1) * window_size, total)
        train_df = df.iloc[:train_end].copy()
        test_df = df.iloc[train_end:test_end].copy()
        splits.append((train_df, test_df))

    return splits


def _run_single(df, strategies: list, min_agreement: int,
                sl: float, tp: float, ts: float) -> dict:
    """Run backtest on a dataframe, return metrics."""
    df_copy = apply_strategy(df.copy(), strategies, min_agreement)
    final_cap, trades = run_backtest(df_copy, sl, tp, ts)

    if len(trades) < 3:
        return {"roi": 0, "trades": len(trades), "win_rate": 0, "final_cap": final_cap}

    wins = [t for t in trades if t["pnl"] > 0]
    roi = (final_cap - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    wr = len(wins) / len(trades) * 100

    return {
        "roi": round(roi, 2),
        "trades": len(trades),
        "win_rate": round(wr, 2),
        "final_cap": round(final_cap, 2),
    }


def walk_forward_validate(
    symbol_key: str,
    strat: dict,
    n_windows: int = 6,
) -> dict:
    """
    Run walk-forward validation for a single strategy on a single asset.

    Args:
        symbol_key: e.g. "BTCUSDT_4h"
        strat: dict with keys: name, strategies, min_agreement, stop_loss, take_profit, trailing_stop
        n_windows: number of time windows (default 6 for ~1yr each)

    Returns:
        dict with per-window results and overall verdict
    """
    df = load_data(symbol_key)
    if df is None:
        return {"error": f"No data for {symbol_key}"}

    df = calculate_indicators(df)
    splits = _split_windows(df, n_windows)

    strategies = strat["strategies"]
    min_ag = strat.get("min_agreement", 1)
    sl = strat["stop_loss"]
    tp = strat["take_profit"]
    ts = strat["trailing_stop"]

    windows = []
    for i, (train_df, test_df) in enumerate(splits):
        train_result = _run_single(train_df, strategies, min_ag, sl, tp, ts)
        test_result = _run_single(test_df, strategies, min_ag, sl, tp, ts)

        windows.append({
            "window": i + 1,
            "train_rows": len(train_df),
            "test_rows": len(test_df),
            "train_roi": train_result["roi"],
            "test_roi": test_result["roi"],
            "train_trades": train_result["trades"],
            "test_trades": test_result["trades"],
            "train_wr": train_result["win_rate"],
            "test_wr": test_result["win_rate"],
        })

    # Aggregate
    train_rois = [w["train_roi"] for w in windows]
    test_rois = [w["test_roi"] for w in windows]

    avg_train = np.mean(train_rois) if train_rois else 0
    avg_test = np.mean(test_rois) if test_rois else 0
    degradation = avg_train - avg_test
    consistency = sum(1 for r in test_rois if r > 0) / len(test_rois) if test_rois else 0

    # Verdict
    if avg_test <= 0:
        verdict = "FAIL — negative out-of-sample returns"
    elif degradation > avg_train * 0.5 and avg_train > 0:
        verdict = "OVERFIT — >50% degradation out-of-sample"
    elif consistency < 0.5:
        verdict = "UNSTABLE — profitable in <50% of test windows"
    elif avg_test > 20:
        verdict = "STRONG — consistent out-of-sample performance"
    elif avg_test > 0:
        verdict = "PASS — positive but modest out-of-sample"
    else:
        verdict = "MARGINAL"

    return {
        "strategy": strat["name"],
        "symbol": symbol_key,
        "n_windows": n_windows,
        "windows": windows,
        "avg_train_roi": round(avg_train, 2),
        "avg_test_roi": round(avg_test, 2),
        "degradation_pct": round(degradation, 2),
        "consistency": round(consistency, 2),
        "verdict": verdict,
    }


def walk_forward_batch(
    symbol_key: str,
    strats: list,
    n_windows: int = 6,
) -> list:
    """Run walk-forward on multiple strategies. Returns sorted results."""
    results = []
    for strat in strats:
        result = walk_forward_validate(symbol_key, strat, n_windows)
        results.append(result)

    results.sort(key=lambda x: x.get("avg_test_roi", 0), reverse=True)
    return results
