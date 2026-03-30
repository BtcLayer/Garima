#!/usr/bin/env python3
"""
Run top-5 strategies with long+short on selected assets (4h timeframe).
Compares long-only vs long+short ROI and saves results.
"""
import sys, os, time
import numpy as np
import pandas as pd
from datetime import datetime as _dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from run_strategies_batch import (
    load_data, calculate_indicators, apply_strategy, apply_strategy_short,
    run_backtest, DATA_FILES, INITIAL_CAPITAL, FEE,
)
from strategies import get_all_strategies

# ── Config ───────────────────────────────────────────────────────────
TIMEFRAME = "4h"
ASSETS = ["BNBUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "LINKUSDT"]
TOP5_NAMES = [
    "EMA_Break_Momentum",
    "MACD_Breakout",
    "Volume_Stochastic_MACD_ADX",
    "Breakout_Cluster",
    "High_Momentum_Entry",
]
OUTPUT_CSV = os.path.join(_ROOT, "auto_results_4h_longshort.csv")


def _metrics(final_cap, trades, years):
    """Compute standard metrics from backtest output."""
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    roi = (final_cap - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    roi_a = ((final_cap / INITIAL_CAPITAL) ** (1 / years) - 1) * 100 if years > 0 else 0
    wr = len(wins) / len(trades) * 100 if trades else 0
    total_w = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    total_l = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
    pf = total_w / total_l if total_l > 0 else 0

    returns = [t["return_pct"] for t in trades]
    avg_trade = sum(returns) / len(returns) if returns else 0
    std = np.std(returns) if len(returns) > 1 else 1
    sharpe = (avg_trade / std) * np.sqrt(len(trades)) if std > 0 else 0

    equity = INITIAL_CAPITAL
    peak = equity
    gross_dd = 0
    for t in trades:
        equity += t["pnl"]
        peak = max(peak, equity)
        dd = (peak - equity) / peak * 100
        gross_dd = max(gross_dd, dd)

    return {
        "final_cap": round(final_cap, 2),
        "roi": round(roi, 2),
        "roi_annum": round(roi_a, 2),
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(wr, 2),
        "profit_factor": round(pf, 2),
        "sharpe": round(sharpe, 2),
        "avg_trade_pct": round(avg_trade, 4),
        "gross_dd": round(gross_dd, 2),
    }


# ── Resolve strategy objects ────────────────────────────────────────
all_strats = get_all_strategies()
strat_map = {s["name"]: s for s in all_strats}
top5 = [strat_map[n] for n in TOP5_NAMES if n in strat_map]
missing = [n for n in TOP5_NAMES if n not in strat_map]
if missing:
    print(f"WARNING: strategies not found: {missing}")
if not top5:
    print("No matching strategies found. Exiting.")
    sys.exit(1)

print(f"Strategies: {[s['name'] for s in top5]}")
print(f"Assets:     {ASSETS}")
print(f"Timeframe:  {TIMEFRAME}\n")

# ── Run backtests ───────────────────────────────────────────────────
rows = []

for asset_name in ASSETS:
    symbol_key = f"{asset_name}_{TIMEFRAME}"
    if symbol_key not in DATA_FILES:
        print(f"  {asset_name}: no data file for {TIMEFRAME} — skipped")
        continue

    df_raw = load_data(symbol_key)
    if df_raw is None:
        continue
    df_ind = calculate_indicators(df_raw)

    # Time range
    if "timestamp" in df_ind.columns:
        t0_str = str(df_ind["timestamp"].iloc[0])[:10]
        t1_str = str(df_ind["timestamp"].iloc[-1])[:10]
    else:
        t0_str, t1_str = "unknown", "unknown"
    try:
        _years = max((_dt.fromisoformat(t1_str) - _dt.fromisoformat(t0_str)).days / 365.25, 0.01)
    except Exception:
        _years = 1.0

    for strat in top5:
        name = strat["name"]
        sl, tp, ts = strat["stop_loss"], strat["take_profit"], strat["trailing_stop"]
        min_ag = strat.get("min_agreement", 1)

        # ── Long only ──
        df_long = apply_strategy(df_ind.copy(), strat["strategies"], min_ag)
        long_cap, long_trades = run_backtest(df_long, sl, tp, ts, side="long")
        m_long = _metrics(long_cap, long_trades, _years)

        # ── Short only ──
        df_short = apply_strategy_short(df_ind.copy(), strat["strategies"], min_ag)
        short_cap, short_trades = run_backtest(df_short, sl, tp, ts, side="short")
        m_short = _metrics(short_cap, short_trades, _years)

        # ── Long+Short combined ──
        # Run both independently, combine final PnL
        combined_net = (long_cap - INITIAL_CAPITAL) + (short_cap - INITIAL_CAPITAL)
        combined_cap = INITIAL_CAPITAL + combined_net
        combined_roi = combined_net / INITIAL_CAPITAL * 100
        combined_roi_a = ((combined_cap / INITIAL_CAPITAL) ** (1 / _years) - 1) * 100 if _years > 0 and combined_cap > 0 else 0
        combined_trades = len(long_trades) + len(short_trades)

        row = {
            "Strategy": name,
            "Asset": asset_name.replace("USDT", ""),
            "Timeframe": TIMEFRAME,
            "Long_ROI_Pct": m_long["roi"],
            "Long_ROI_Annum": m_long["roi_annum"],
            "Long_Trades": m_long["trades"],
            "Long_WinRate": m_long["win_rate"],
            "Long_PF": m_long["profit_factor"],
            "Long_GDD": m_long["gross_dd"],
            "Short_ROI_Pct": m_short["roi"],
            "Short_ROI_Annum": m_short["roi_annum"],
            "Short_Trades": m_short["trades"],
            "Short_WinRate": m_short["win_rate"],
            "Short_PF": m_short["profit_factor"],
            "Short_GDD": m_short["gross_dd"],
            "Combined_ROI_Pct": round(combined_roi, 2),
            "Combined_ROI_Annum": round(combined_roi_a, 2),
            "Combined_Trades": combined_trades,
            "ROI_Delta_Pct": round(combined_roi - m_long["roi"], 2),
            "Time_Period": f"{t0_str} to {t1_str}",
        }
        rows.append(row)

        tag = "+" if row["ROI_Delta_Pct"] >= 0 else ""
        print(f"  {name:30s} {asset_name:10s}  L={m_long['roi']:>8.2f}%  S={m_short['roi']:>8.2f}%  L+S={combined_roi:>8.2f}%  delta={tag}{row['ROI_Delta_Pct']:.2f}%")

# ── Save results ────────────────────────────────────────────────────
if not rows:
    print("\nNo results produced.")
    sys.exit(1)

df_out = pd.DataFrame(rows)
df_out.to_csv(OUTPUT_CSV, index=False)
print(f"\nResults saved to {OUTPUT_CSV}")

# ── Comparison table ────────────────────────────────────────────────
print(f"\n{'='*110}")
print("LONG-ONLY vs LONG+SHORT COMPARISON")
print(f"{'='*110}")
print(f"{'Strategy':<30} {'Asset':<8} {'Long ROI%':<12} {'Short ROI%':<12} {'L+S ROI%':<12} {'Delta':<10} {'L Trades':<10} {'S Trades':<10}")
print("-" * 110)

for r in rows:
    tag = "+" if r["ROI_Delta_Pct"] >= 0 else ""
    print(f"{r['Strategy']:<30} {r['Asset']:<8} {r['Long_ROI_Pct']:<12.2f} {r['Short_ROI_Pct']:<12.2f} {r['Combined_ROI_Pct']:<12.2f} {tag}{r['ROI_Delta_Pct']:<9.2f} {r['Long_Trades']:<10} {r['Short_Trades']:<10}")

# ── Summary by strategy ────────────────────────────────────────────
print(f"\n{'='*80}")
print("AVERAGE ACROSS ASSETS (by strategy)")
print(f"{'='*80}")
print(f"{'Strategy':<30} {'Avg Long ROI%':<15} {'Avg L+S ROI%':<15} {'Avg Delta':<12}")
print("-" * 80)

for name in TOP5_NAMES:
    strat_rows = [r for r in rows if r["Strategy"] == name]
    if strat_rows:
        avg_long = sum(r["Long_ROI_Pct"] for r in strat_rows) / len(strat_rows)
        avg_combined = sum(r["Combined_ROI_Pct"] for r in strat_rows) / len(strat_rows)
        avg_delta = sum(r["ROI_Delta_Pct"] for r in strat_rows) / len(strat_rows)
        tag = "+" if avg_delta >= 0 else ""
        print(f"{name:<30} {avg_long:<15.2f} {avg_combined:<15.2f} {tag}{avg_delta:<11.2f}")

print(f"\nDone.")
