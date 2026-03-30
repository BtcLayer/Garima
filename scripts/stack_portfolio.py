"""
Portfolio Stacking Model
========================
Runs 5 top strategies on their best assets (4h) simultaneously,
combines all trades into a unified timeline, and reports combined
daily PnL, drawdown, monthly breakdown, and whether Cat 1/Cat 2
targets are achievable.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import numpy as np
from collections import defaultdict

from run_strategies_batch import (
    load_data,
    calculate_indicators,
    apply_strategy,
    SIGNAL_FUNCTIONS,
    FEE,
)

# ── Configuration ──────────────────────────────────────────────────
CAPITAL_PER_STRATEGY = 2_000
NUM_STRATEGIES = 5
TOTAL_CAPITAL = CAPITAL_PER_STRATEGY * NUM_STRATEGIES  # $10,000

STRATEGIES = [
    {
        "name": "Aggressive_Entry / SOLUSDT_4h",
        "data_key": "SOLUSDT_4h",
        "signals": ["Breakout_20", "Volume_Spike", "MACD_Cross", "ADX_Trend"],
        "min_agreement": 2,
        "stop_loss": 0.04,
        "take_profit": 0.15,
        "trailing_stop": 0.005,
    },
    {
        "name": "Aggressive_Entry / BNBUSDT_4h",
        "data_key": "BNBUSDT_4h",
        "signals": ["Breakout_20", "Volume_Spike", "MACD_Cross", "ADX_Trend"],
        "min_agreement": 2,
        "stop_loss": 0.04,
        "take_profit": 0.15,
        "trailing_stop": 0.005,
    },
    {
        "name": "MACD_Breakout / SOLUSDT_4h",
        "data_key": "SOLUSDT_4h",
        "signals": ["MACD_Cross", "Breakout_20", "Volume_Spike", "ADX_Trend"],
        "min_agreement": 2,
        "stop_loss": 0.04,
        "take_profit": 0.15,
        "trailing_stop": 0.015,
    },
    {
        "name": "Ichimoku_Trend_Pro / BNBUSDT_4h",
        "data_key": "BNBUSDT_4h",
        "signals": ["Ichimoku_Bull", "EMA_Cross", "ADX_Trend", "OBV_Rising"],
        "min_agreement": 3,
        "stop_loss": 0.02,
        "take_profit": 0.12,
        "trailing_stop": 0.02,
    },
    {
        "name": "EMA_Break_Momentum / SOLUSDT_4h",
        "data_key": "SOLUSDT_4h",
        "signals": ["EMA_Cross", "Breakout_20", "MACD_Cross", "ADX_Trend"],
        "min_agreement": 2,
        "stop_loss": 0.02,
        "take_profit": 0.15,
        "trailing_stop": 0.025,
    },
]


# ── Backtest engine (per-strategy, with $2k capital) ──────────────
def run_backtest_with_dates(df, stop_loss, take_profit, trailing_stop, capital):
    """Run backtest and return (final_capital, trades) where each trade
    carries an exit_date string (YYYY-MM-DD)."""
    position = 0
    position_size = 0
    entry_price = 0.0
    peak_price = 0.0
    trades = []

    for _idx, row in df.iterrows():
        if row["entry_signal"] == 1 and position == 0:
            entry_price = row["close"]
            position_size = capital * 0.95 / entry_price
            position = 1
            peak_price = entry_price

        elif position == 1:
            current_price = row["close"]
            high = row.get("high", current_price)
            low = row.get("low", current_price)

            if current_price > peak_price:
                peak_price = current_price
            trailing_stop_price = peak_price * (1 - trailing_stop)

            should_exit = False
            if row["exit_signal"] == 1:
                should_exit = True
            if low <= entry_price * (1 - stop_loss):
                should_exit = True
            if high >= entry_price * (1 + take_profit):
                should_exit = True
            if current_price <= trailing_stop_price and trailing_stop > 0:
                should_exit = True

            if should_exit:
                exit_price = current_price
                pnl = position_size * exit_price * (1 - FEE) - position_size * entry_price * (1 + FEE)
                capital += pnl
                ret_pct = (exit_price - entry_price) / entry_price * 100
                exit_date = str(row.get("timestamp", row.get("open_time", _idx)))[:10]
                trades.append({
                    "entry": entry_price,
                    "exit": exit_price,
                    "pnl": pnl,
                    "return_pct": ret_pct,
                    "exit_date": exit_date,
                    "capital_after": round(capital, 2),
                })
                position = 0
                peak_price = 0.0

    return capital, trades


# ── Run all strategies ─────────────────────────────────────────────
def run_all():
    # Cache loaded & indicator-enriched dataframes
    data_cache = {}
    all_results = []

    for strat in STRATEGIES:
        key = strat["data_key"]
        if key not in data_cache:
            df = load_data(key)
            if df is None:
                print(f"  SKIP {strat['name']} -- no data for {key}")
                continue
            data_cache[key] = calculate_indicators(df)

        df = data_cache[key].copy()
        df = apply_strategy(df, strat["signals"], strat["min_agreement"])
        final_cap, trades = run_backtest_with_dates(
            df, strat["stop_loss"], strat["take_profit"],
            strat["trailing_stop"], CAPITAL_PER_STRATEGY,
        )
        all_results.append({
            "name": strat["name"],
            "final_capital": final_cap,
            "trades": trades,
        })

    if not all_results:
        print("No strategies produced results. Exiting.")
        return

    # ── Detect data time range ─────────────────────────────────────
    first_key = STRATEGIES[0]["data_key"]
    df0 = data_cache[first_key]
    time_start = str(df0["timestamp"].min())[:10] if "timestamp" in df0.columns else "2020-01-01"
    time_end = str(df0["timestamp"].max())[:10] if "timestamp" in df0.columns else "2026-03-21"
    from datetime import datetime
    dt_start = datetime.fromisoformat(time_start)
    dt_end = datetime.fromisoformat(time_end)
    total_days = max((dt_end - dt_start).days, 1)
    total_years = total_days / 365.25

    # ── Individual strategy summaries ──────────────────────────────
    print("\n" + "=" * 80)
    print("INDIVIDUAL STRATEGY PERFORMANCE  (each starting with $2,000)")
    print("=" * 80)
    for r in all_results:
        trades = r["trades"]
        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] <= 0]
        wr = len(wins) / len(trades) * 100 if trades else 0
        net = r["final_capital"] - CAPITAL_PER_STRATEGY
        roi = net / CAPITAL_PER_STRATEGY * 100
        roi_yr = ((r["final_capital"] / CAPITAL_PER_STRATEGY) ** (1 / total_years) - 1) * 100 if total_years > 0 else 0
        avg_ret = np.mean([t["return_pct"] for t in trades]) if trades else 0
        # Max drawdown
        eq = CAPITAL_PER_STRATEGY
        peak = eq
        max_dd = 0
        for t in trades:
            eq += t["pnl"]
            peak = max(peak, eq)
            dd = (peak - eq) / peak * 100
            max_dd = max(max_dd, dd)

        print(f"\n  {r['name']}")
        print(f"    Trades: {len(trades)}  |  Win rate: {wr:.1f}%")
        print(f"    Final capital: ${r['final_capital']:,.2f}  |  Net P&L: ${net:,.2f}")
        print(f"    ROI: {roi:.1f}%  |  ROI/yr: {roi_yr:.1f}%  |  Avg trade: {avg_ret:.2f}%")
        print(f"    Max drawdown: {max_dd:.1f}%")

    # ── Combine into daily PnL timeline ────────────────────────────
    daily_pnl = defaultdict(float)  # date -> combined PnL ($)
    trades_per_day = defaultdict(int)
    strats_per_day = defaultdict(set)

    for r in all_results:
        for t in r["trades"]:
            d = t["exit_date"]
            daily_pnl[d] += t["pnl"]
            trades_per_day[d] += 1
            strats_per_day[d].add(r["name"])

    if not daily_pnl:
        print("No trades at all -- nothing to combine.")
        return

    sorted_dates = sorted(daily_pnl.keys())

    # Equity curve on the combined portfolio
    equity = TOTAL_CAPITAL
    peak_eq = equity
    max_dd_combined = 0
    equity_series = []
    for d in sorted_dates:
        equity += daily_pnl[d]
        peak_eq = max(peak_eq, equity)
        dd = (peak_eq - equity) / peak_eq * 100
        max_dd_combined = max(max_dd_combined, dd)
        equity_series.append({"date": d, "equity": equity})

    combined_final = equity
    combined_net = combined_final - TOTAL_CAPITAL
    combined_roi = combined_net / TOTAL_CAPITAL * 100
    combined_roi_yr = ((combined_final / TOTAL_CAPITAL) ** (1 / total_years) - 1) * 100 if total_years > 0 else 0
    total_trade_days = len(sorted_dates)
    combined_daily_pct_avg = (combined_net / TOTAL_CAPITAL * 100) / total_days if total_days > 0 else 0

    # ── Overlap analysis ───────────────────────────────────────────
    overlap_counts = defaultdict(int)  # how many strategies traded that day
    for d, strats in strats_per_day.items():
        overlap_counts[len(strats)] += 1

    # ── Monthly breakdown ──────────────────────────────────────────
    monthly_pnl = defaultdict(float)
    for d, pnl in daily_pnl.items():
        month_key = d[:7]  # YYYY-MM
        monthly_pnl[month_key] += pnl

    sorted_months = sorted(monthly_pnl.keys())
    monthly_roi = {m: monthly_pnl[m] / TOTAL_CAPITAL * 100 for m in sorted_months}
    best_month = max(sorted_months, key=lambda m: monthly_pnl[m])
    worst_month = min(sorted_months, key=lambda m: monthly_pnl[m])

    # ── Print combined summary ─────────────────────────────────────
    print("\n" + "=" * 80)
    print("COMBINED PORTFOLIO PERFORMANCE  ($2,000 x 5 = $10,000 total)")
    print("=" * 80)
    print(f"  Data range        : {time_start} to {time_end} ({total_days} days, {total_years:.1f} years)")
    print(f"  Starting capital  : ${TOTAL_CAPITAL:,}")
    print(f"  Final capital     : ${combined_final:,.2f}")
    print(f"  Net P&L           : ${combined_net:,.2f}")
    print(f"  Combined ROI      : {combined_roi:.1f}%")
    print(f"  Combined ROI/yr   : {combined_roi_yr:.1f}%")
    print(f"  Avg daily %       : {combined_daily_pct_avg:.4f}%  (over {total_days} calendar days)")
    print(f"  Trading days      : {total_trade_days}")
    print(f"  Max drawdown      : {max_dd_combined:.1f}%")

    print(f"\n  Best month        : {best_month}  ${monthly_pnl[best_month]:+,.2f} ({monthly_roi[best_month]:+.2f}%)")
    print(f"  Worst month       : {worst_month}  ${monthly_pnl[worst_month]:+,.2f} ({monthly_roi[worst_month]:+.2f}%)")

    # ── Overlap analysis ───────────────────────────────────────────
    print(f"\n  Overlap analysis (strategies trading same day):")
    for n_strats in sorted(overlap_counts.keys()):
        count = overlap_counts[n_strats]
        pct = count / total_trade_days * 100 if total_trade_days else 0
        print(f"    {n_strats} strategy(ies) active : {count} days ({pct:.1f}%)")

    # ── Monthly returns table ──────────────────────────────────────
    print(f"\n  {'MONTH':>7}  {'P&L ($)':>12}  {'ROI %':>8}  {'Cum. ROI %':>11}")
    print(f"  {'-'*7}  {'-'*12}  {'-'*8}  {'-'*11}")
    cum_pnl = 0
    for m in sorted_months:
        cum_pnl += monthly_pnl[m]
        cum_roi = cum_pnl / TOTAL_CAPITAL * 100
        print(f"  {m:>7}  {monthly_pnl[m]:>+12,.2f}  {monthly_roi[m]:>+8.2f}  {cum_roi:>+11.2f}")

    # ── Cat 1 / Cat 2 assessment ───────────────────────────────────
    cat2_target = 0.5   # %/day
    cat1_target = 2.0   # %/day
    avg_daily = combined_daily_pct_avg

    print("\n" + "=" * 80)
    print("CAT TARGET ASSESSMENT")
    print("=" * 80)
    print(f"  Average daily return on $10k portfolio: {avg_daily:.4f}%")
    print(f"  Cat 2 target (0.5%/day = {0.5*TOTAL_CAPITAL/100:.0f}$/day):")
    if avg_daily >= cat2_target:
        print(f"    >>> ACHIEVABLE  (avg {avg_daily:.4f}% >= {cat2_target}%)")
    else:
        needed_mult = cat2_target / avg_daily if avg_daily > 0 else float("inf")
        print(f"    >>> NOT achievable  (need {needed_mult:.1f}x more return or more strategies)")
    print(f"  Cat 1 target (2.0%/day = {2.0*TOTAL_CAPITAL/100:.0f}$/day):")
    if avg_daily >= cat1_target:
        print(f"    >>> ACHIEVABLE  (avg {avg_daily:.4f}% >= {cat1_target}%)")
    else:
        needed_mult = cat1_target / avg_daily if avg_daily > 0 else float("inf")
        print(f"    >>> NOT achievable  (need {needed_mult:.1f}x more return or more strategies)")

    # Quick sanity: what daily% would we need per strategy?
    print(f"\n  To hit Cat 2 via stacking 5 strategies, each needs avg {cat2_target/1:.2f}%/day on its $2k slice.")
    print(f"  To hit Cat 1 via stacking 5 strategies, each needs avg {cat1_target/1:.2f}%/day on its $2k slice.")
    print(f"  (Or add more strategies / increase leverage.)")
    print("=" * 80)


if __name__ == "__main__":
    run_all()
