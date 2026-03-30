#!/usr/bin/env python3
"""
Test script for batch-21 strategies (new indicators) on 4h data.
Runs all 12 new strategies + 3 baseline strategies on 5 assets.
"""
import sys, os
import numpy as np
import pandas as pd
from datetime import datetime as _dt

# Project root on sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from run_strategies_batch import (
    load_data,
    calculate_indicators,
    apply_strategy,
    run_backtest,
    INITIAL_CAPITAL,
    FEE,
    DATA_FILES,
)
from strategies.batch_21 import STRATEGY_COMBINATIONS as NEW_STRATEGIES

# ── Config ──────────────────────────────────────────────────────────
TIMEFRAME = "4h"
ASSETS = ["BNBUSDT", "ETHUSDT", "SOLUSDT", "LINKUSDT", "BTCUSDT"]

# Baseline strategies (current top 3) for comparison
BASELINE_STRATEGIES = [
    {"id": 223, "name": "Aggressive_Entry",
     "strategies": ["Breakout_20", "Volume_Spike", "MACD_Cross", "ADX_Trend"],
     "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 2},
    {"id": 173, "name": "MACD_Breakout",
     "strategies": ["MACD_Cross", "Breakout_20", "Volume_Spike", "ADX_Trend"],
     "stop_loss": 0.02, "take_profit": 0.12, "trailing_stop": 0.02, "min_agreement": 2},
    {"id": 161, "name": "EMA_Break_Momentum",
     "strategies": ["EMA_Cross", "Breakout_20", "MACD_Cross", "ADX_Trend"],
     "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 2},
]

ALL_STRATEGIES = NEW_STRATEGIES + BASELINE_STRATEGIES


def _metrics(strategy, final_capital, trades, years, asset, timeframe):
    """Compute a result row dict."""
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    win_rate = len(wins) / len(trades) * 100 if trades else 0
    roi = (final_capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    roi_pa = ((final_capital / INITIAL_CAPITAL) ** (1 / max(years, 0.01)) - 1) * 100

    total_wins = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    total_losses = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
    pf = total_wins / total_losses if total_losses > 0 else 0

    # Drawdown
    equity = INITIAL_CAPITAL
    peak = equity
    max_dd = 0
    min_cap = equity
    for t in trades:
        equity += t["pnl"]
        peak = max(peak, equity)
        dd = (peak - equity) / peak * 100
        max_dd = max(max_dd, dd)
        min_cap = min(min_cap, equity)
    net_dd = max(0, (INITIAL_CAPITAL - min_cap) / INITIAL_CAPITAL * 100)

    # Capital at max net DD
    cap_at_ndd = round(min_cap, 2)

    return {
        "Strategy": strategy["name"],
        "Asset": asset,
        "ROI%/yr": round(roi_pa, 2),
        "Trades": len(trades),
        "Win%": round(win_rate, 2),
        "PF": round(pf, 2),
        "Gross_DD%": round(max_dd, 2),
        "Net_DD%": round(net_dd, 2),
        "Cap@NDD": cap_at_ndd,
        "Final_Cap": round(final_capital, 2),
        "ROI%": round(roi, 2),
        "is_new": strategy["id"] >= 231,
    }


def main():
    results = []

    for asset in ASSETS:
        key = f"{asset}_{TIMEFRAME}"
        if key not in DATA_FILES:
            print(f"[SKIP] No data for {key}")
            continue

        df_raw = load_data(key)
        if df_raw is None:
            continue

        print(f"Calculating indicators for {key} ...")
        df = calculate_indicators(df_raw)

        # Determine time span
        if "timestamp" in df.columns:
            t0 = pd.Timestamp(str(df["timestamp"].min()))
            t1 = pd.Timestamp(str(df["timestamp"].max()))
            years = max((t1 - t0).days / 365.25, 0.01)
        else:
            years = 1.0

        for strat in ALL_STRATEGIES:
            try:
                df_copy = apply_strategy(
                    df.copy(),
                    strat["strategies"],
                    strat.get("min_agreement", 1),
                )
                final_cap, trades = run_backtest(
                    df_copy,
                    strat["stop_loss"],
                    strat["take_profit"],
                    strat["trailing_stop"],
                )
                if len(trades) >= 3:
                    row = _metrics(strat, final_cap, trades, years, asset, TIMEFRAME)
                    results.append(row)
            except Exception as e:
                print(f"  [ERR] {strat['name']} on {asset}: {e}")

    if not results:
        print("\nNo results produced. Check data files exist under storage/historical_data/")
        return

    # Build DataFrame and sort
    df_res = pd.DataFrame(results)
    df_res.sort_values("ROI%/yr", ascending=False, inplace=True)

    # Print header
    sep = "=" * 115
    print(f"\n{sep}")
    print(f"{'STRATEGY':<24} {'ASSET':<10} {'ROI%/yr':>8} {'Trades':>7} {'Win%':>6} {'PF':>6} {'GrossDD%':>9} {'NetDD%':>7} {'Cap@NDD':>10} {'NEW?':>5}")
    print(sep)
    for _, r in df_res.iterrows():
        tag = " *" if r["is_new"] else ""
        print(
            f"{r['Strategy']:<24} {r['Asset']:<10} {r['ROI%/yr']:>8} {r['Trades']:>7} "
            f"{r['Win%']:>6} {r['PF']:>6} {r['Gross_DD%']:>9} {r['Net_DD%']:>7} "
            f"{r['Cap@NDD']:>10}{tag}"
        )
    print(sep)

    # Summary
    new_res = df_res[df_res["is_new"]]
    old_res = df_res[~df_res["is_new"]]
    print(f"\nNew strategies tested : {len(new_res)}")
    print(f"Baseline strategies   : {len(old_res)}")
    if len(new_res):
        print(f"Best new ROI%/yr      : {new_res['ROI%/yr'].max():.2f}  ({new_res.loc[new_res['ROI%/yr'].idxmax(), 'Strategy']} on {new_res.loc[new_res['ROI%/yr'].idxmax(), 'Asset']})")
    if len(old_res):
        print(f"Best baseline ROI%/yr : {old_res['ROI%/yr'].max():.2f}  ({old_res.loc[old_res['ROI%/yr'].idxmax(), 'Strategy']} on {old_res.loc[old_res['ROI%/yr'].idxmax(), 'Asset']})")

    # Save CSV
    out_path = os.path.join(_ROOT, "reports", "batch21_test_results.csv")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df_res.to_csv(out_path, index=False)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
