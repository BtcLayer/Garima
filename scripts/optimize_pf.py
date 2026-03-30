"""
Optimize SL/TP/TS to maximize Profit Factor for top-10 strategy-asset combos.

Sweeps 910 param sets per combo (13 SL x 10 TP x 7 TS) across 60 combos.
Filters, classifies tiers, and saves all passing results.

Usage:
    .tbenv/Scripts/python scripts/optimize_pf.py
"""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from itertools import product
from run_strategies_batch import (
    load_data, calculate_indicators, apply_strategy, run_backtest,
    INITIAL_CAPITAL, FEE,
)

# ── Configuration ───────────────────────────────────────────────────

STRATEGIES = [
    {"name": "S01_PSAR_Vol_EMA_ST_MA50",
     "combo": ['PSAR_Bull','Volume_Spike','EMA_Cross','Supertrend','Trend_MA50'], "min": 5},
    {"name": "S02_Ichi_OBV_Vol_PSAR_MA50",
     "combo": ['Ichimoku_Bull','OBV_Rising','Volume_Spike','PSAR_Bull','Trend_MA50'], "min": 5},
    {"name": "S03_PSAR_Vol_EMA_ST_MA50_ADX",
     "combo": ['PSAR_Bull','Volume_Spike','EMA_Cross','Supertrend','Trend_MA50','ADX_Trend'], "min": 6},
    {"name": "S04_PSAR_Vol_EMA_ST_MA50_ADX_OBV",
     "combo": ['PSAR_Bull','Volume_Spike','EMA_Cross','Supertrend','Trend_MA50','ADX_Trend','OBV_Rising'], "min": 5},
    {"name": "S05_Break_Vol_EMA_ADX_PSAR_MA50_OBV",
     "combo": ['Breakout_20','Volume_Spike','EMA_Cross','ADX_Trend','PSAR_Bull','Trend_MA50','OBV_Rising'], "min": 5},
    {"name": "S06_Ichi_PSAR_ADX_OBV_EMA_ST",
     "combo": ['Ichimoku_Bull','PSAR_Bull','ADX_Trend','OBV_Rising','EMA_Cross','Supertrend'], "min": 5},
    {"name": "S07_EMA_MA50_Ichi_PSAR_ST_ADX_OBV_m7",
     "combo": ['EMA_Cross','Trend_MA50','Ichimoku_Bull','PSAR_Bull','Supertrend','ADX_Trend','OBV_Rising'], "min": 7},
    {"name": "S08_EMA_MA50_Ichi_PSAR_ST_ADX_OBV_m6",
     "combo": ['EMA_Cross','Trend_MA50','Ichimoku_Bull','PSAR_Bull','Supertrend','ADX_Trend','OBV_Rising'], "min": 6},
    {"name": "S09_MACD_Break_Vol_ADX",
     "combo": ['MACD_Cross','Breakout_20','Volume_Spike','ADX_Trend'], "min": 2},
    {"name": "S10_PSAR_EMA_ST_ADX_MA50_OBV",
     "combo": ['PSAR_Bull','EMA_Cross','Supertrend','ADX_Trend','Trend_MA50','OBV_Rising'], "min": 5},
]

ASSETS = [
    "ETHUSDT_4h", "BNBUSDT_4h", "BTCUSDT_4h",
    "SOLUSDT_4h", "LINKUSDT_4h", "ADAUSDT_4h",
]

SL_RANGE = [0.003, 0.004, 0.005, 0.006, 0.007, 0.008, 0.009, 0.01, 0.012, 0.015, 0.02, 0.025, 0.03]
TP_RANGE = [0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.05, 0.06, 0.08]
TS_RANGE = [0.002, 0.003, 0.004, 0.005, 0.006, 0.008, 0.01]

PARAM_GRID = list(product(SL_RANGE, TP_RANGE, TS_RANGE))
print(f"Param grid size: {len(PARAM_GRID)} per combo")
print(f"Total combos: {len(STRATEGIES) * len(ASSETS)} = {len(STRATEGIES) * len(ASSETS) * len(PARAM_GRID)} backtests")

# ── Helpers ─────────────────────────────────────────────────────────

def compute_metrics(trades, years):
    """Compute all metrics from a trades list."""
    if not trades or len(trades) < 1:
        return None

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    n_trades = len(trades)
    win_rate = len(wins) / n_trades * 100

    total_win_pnl = sum(t["pnl"] for t in wins)
    total_loss_pnl = abs(sum(t["pnl"] for t in losses))
    pf = total_win_pnl / total_loss_pnl if total_loss_pnl > 0 else 999.0

    final_capital = trades[-1]["capital_after"]
    net_profit = final_capital - INITIAL_CAPITAL
    roi = net_profit / INITIAL_CAPITAL * 100
    roi_annual = ((final_capital / INITIAL_CAPITAL) ** (1 / max(years, 0.01)) - 1) * 100

    # Gross drawdown (peak-to-trough of equity curve)
    equity = INITIAL_CAPITAL
    peak = equity
    max_dd = 0.0
    for t in trades:
        equity += t["pnl"]
        peak = max(peak, equity)
        dd = (peak - equity) / peak * 100
        max_dd = max(max_dd, dd)

    # Daily Sharpe (TV-style): build daily PnL array including 0 for non-trading days
    daily_pnl = {}
    for t in trades:
        d = t["exit_date"]
        daily_pnl[d] = daily_pnl.get(d, 0.0) + t["return_pct"]

    # Fill all calendar days in range
    try:
        all_dates = sorted(daily_pnl.keys())
        if len(all_dates) >= 2:
            start = pd.Timestamp(all_dates[0])
            end = pd.Timestamp(all_dates[-1])
            date_range = pd.date_range(start, end, freq="D")
            daily_returns = np.array([daily_pnl.get(str(d.date()), 0.0) for d in date_range])
        else:
            daily_returns = np.array(list(daily_pnl.values()))
    except Exception:
        daily_returns = np.array(list(daily_pnl.values()))

    if len(daily_returns) > 1:
        std = np.std(daily_returns, ddof=1)
        sharpe = (np.mean(daily_returns) / std) * np.sqrt(252) if std > 0 else 0.0
    else:
        sharpe = 0.0

    avg_trade = np.mean([t["return_pct"] for t in trades])
    daily_pct = roi_annual / 365.0

    return {
        "roi_annual": round(roi_annual, 2),
        "daily_pct": round(daily_pct, 4),
        "win_rate": round(win_rate, 2),
        "pf": round(pf, 2),
        "gdd": round(max_dd, 2),
        "trades": n_trades,
        "sharpe": round(sharpe, 2),
        "roi": round(roi, 2),
        "avg_trade": round(avg_trade, 4),
        "final_capital": round(final_capital, 2),
    }


def classify_tier(pf, wr, gdd):
    if pf >= 2.0 and wr >= 50 and gdd < 30:
        return "TIER_1"
    if pf >= 1.6 and wr >= 50 and gdd < 35:
        return "TIER_2_DEPLOY"
    if pf >= 1.4 and wr >= 50:
        return "TIER_2_TEST"
    if pf >= 1.2 and wr >= 45:
        return "PAPER_TRADE"
    return "NONE"


# ── Main ────────────────────────────────────────────────────────────

def main():
    t0 = time.time()

    # Cache loaded+indicator data per asset
    data_cache = {}
    for asset in ASSETS:
        print(f"\nLoading {asset}...")
        df = load_data(asset)
        if df is None:
            print(f"  SKIP - no data for {asset}")
            continue
        df = calculate_indicators(df)
        data_cache[asset] = df
        print(f"  {len(df)} candles loaded")

    # Detect years from first loaded asset
    sample_df = next(iter(data_cache.values()))
    if "timestamp" in sample_df.columns:
        t_start = pd.Timestamp(str(sample_df["timestamp"].min())[:10])
        t_end = pd.Timestamp(str(sample_df["timestamp"].max())[:10])
        years = max((t_end - t_start).days / 365.25, 0.01)
    else:
        years = 1.0
    print(f"\nData span: ~{years:.1f} years")

    all_results = []
    total_combos = len(STRATEGIES) * len(ASSETS)
    combo_i = 0

    for strat in STRATEGIES:
        for asset in ASSETS:
            combo_i += 1
            if asset not in data_cache:
                continue

            df_base = data_cache[asset]
            # Apply strategy signals once (shared across all param sets)
            df_sig = apply_strategy(
                df_base.copy(), strat["combo"], strat["min"]
            )

            best_pf = 0
            best_result = None
            combo_passing = 0

            for sl, tp, ts in PARAM_GRID:
                final_capital, trades = run_backtest(df_sig.copy(), sl, tp, ts)

                if len(trades) < 50:
                    continue

                m = compute_metrics(trades, years)
                if m is None:
                    continue

                # Filter
                if m["pf"] < 1.2 or m["win_rate"] < 40 or m["trades"] < 50 or m["roi"] <= 0:
                    continue

                tier = classify_tier(m["pf"], m["win_rate"], m["gdd"])
                if tier == "NONE":
                    continue

                row = {
                    "strategy": strat["name"],
                    "combo": "+".join(strat["combo"]),
                    "min_agree": strat["min"],
                    "asset": asset,
                    "sl_pct": round(sl * 100, 1),
                    "tp_pct": round(tp * 100, 1),
                    "ts_pct": round(ts * 100, 1),
                    "tier": tier,
                    **m,
                }
                all_results.append(row)
                combo_passing += 1

                if m["pf"] > best_pf:
                    best_pf = m["pf"]
                    best_result = row

            tag = f"  PF={best_result['pf']} WR={best_result['win_rate']}% GDD={best_result['gdd']}% [{best_result['tier']}]" if best_result else "  no passing"
            print(f"[{combo_i:3d}/{total_combos}] {strat['name']:40s} {asset:14s} pass={combo_passing:4d}{tag}")

    elapsed = time.time() - t0
    print(f"\n{'='*80}")
    print(f"OPTIMIZATION COMPLETE  ({elapsed/60:.1f} min, {len(all_results)} passing results)")
    print(f"{'='*80}")

    if not all_results:
        print("No results passed filters.")
        return

    df_all = pd.DataFrame(all_results)

    # ── Sort by PF desc ─────────────────────────────────────────────
    df_all.sort_values("pf", ascending=False, inplace=True)

    # ── Tier counts ─────────────────────────────────────────────────
    tier_counts = df_all["tier"].value_counts()
    print("\n--- TIER SUMMARY ---")
    for tier in ["TIER_1", "TIER_2_DEPLOY", "TIER_2_TEST", "PAPER_TRADE"]:
        print(f"  {tier:20s}: {tier_counts.get(tier, 0)}")
    print(f"  {'TOTAL':20s}: {len(df_all)}")

    # ── Print TIER_1 and TIER_2_DEPLOY (all) ────────────────────────
    deploy = df_all[df_all["tier"].isin(["TIER_1", "TIER_2_DEPLOY"])]
    if len(deploy):
        print(f"\n{'='*100}")
        print(f"ALL TIER_1 + TIER_2_DEPLOY  ({len(deploy)} results)")
        print(f"{'='*100}")
        _print_table(deploy)
    else:
        print("\nNo TIER_1 or TIER_2_DEPLOY results found.")

    # ── Print top-20 TIER_2_TEST ────────────────────────────────────
    t2test = df_all[df_all["tier"] == "TIER_2_TEST"].head(20)
    if len(t2test):
        print(f"\n{'='*100}")
        print(f"TOP 20 TIER_2_TEST")
        print(f"{'='*100}")
        _print_table(t2test)

    # ── Pine Script params for TIER_2_DEPLOY+ ───────────────────────
    if len(deploy):
        print(f"\n{'='*100}")
        print("PINE SCRIPT PARAMS (TIER_2_DEPLOY+)")
        print(f"{'='*100}")
        for _, r in deploy.iterrows():
            print(f"  {r['strategy']} on {r['asset']}: "
                  f"SL={r['sl_pct']}% TP={r['tp_pct']}% TS={r['ts_pct']}% "
                  f"-> PF={r['pf']} WR={r['win_rate']}% GDD={r['gdd']}%")

    # ── Save CSV ────────────────────────────────────────────────────
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "reports", "optimize_pf_results.csv")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df_all.to_csv(out_path, index=False)
    print(f"\nSaved {len(df_all)} results to {out_path}")


def _print_table(df_sub):
    """Pretty-print a results DataFrame."""
    header = (f"{'Strategy':40s} {'Asset':14s} {'SL%':>5s} {'TP%':>5s} {'TS%':>5s} "
              f"{'PF':>6s} {'WR%':>6s} {'GDD%':>6s} {'ROI/yr':>8s} {'Sharpe':>7s} "
              f"{'Trades':>6s} {'Tier':16s}")
    print(header)
    print("-" * len(header))
    for _, r in df_sub.iterrows():
        print(f"{r['strategy']:40s} {r['asset']:14s} {r['sl_pct']:5.1f} {r['tp_pct']:5.1f} {r['ts_pct']:5.1f} "
              f"{r['pf']:6.2f} {r['win_rate']:6.1f} {r['gdd']:6.1f} {r['roi_annual']:8.1f} {r['sharpe']:7.2f} "
              f"{r['trades']:6d} {r['tier']:16s}")


if __name__ == "__main__":
    main()
