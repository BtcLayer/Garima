"""
Optimize near-ALPHA strategies to push Win Rate above 45%.

Targets:
  1. Cloud_Momentum (ETH) — Sharpe 4.01, WR 41.9%
  2. PSAR_Volume_Surge (ETH) — Sharpe 3.68, WR 41.4%
  3. Cloud_Break_Volume (ETH) — Sharpe 3.18, WR 42.6%
  + 3 new high-selectivity combos (A, B, C)

Grid search over TP, SL, TS, min_agreement + extra filter signals.
Filter: WR >= 45%, Sharpe >= 2.5, GDD < 45%, daily ROI > 0.
"""

import sys
import os
import itertools
import time

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pandas as pd
from run_strategies_batch import (
    load_data, calculate_indicators, apply_strategy, run_backtest,
    SIGNAL_FUNCTIONS, INITIAL_CAPITAL,
)

# ── Param grid ──────────────────────────────────────────────────
TP_GRID = [0.015, 0.02, 0.025, 0.03, 0.035, 0.04]
SL_GRID = [0.01, 0.015, 0.02, 0.025, 0.03]
TS_GRID = [0.003, 0.004, 0.005, 0.006, 0.008, 0.01]

# ── Strategy definitions ────────────────────────────────────────
BASE_STRATEGIES = {
    "Cloud_Momentum": {
        "base_signals": ["Ichimoku_Bull", "OBV_Rising", "Volume_Spike", "PSAR_Bull", "Trend_MA50"],
        "extra_pool": ["EMA_Cross", "Supertrend", "ADX_Trend"],
    },
    "PSAR_Volume_Surge": {
        "base_signals": ["PSAR_Bull", "Volume_Spike", "EMA_Cross", "Supertrend"],
        "extra_pool": ["Trend_MA50", "ADX_Trend", "Ichimoku_Bull", "OBV_Rising"],
    },
    "Cloud_Break_Volume": {
        "base_signals": ["Ichimoku_Bull", "Volume_Spike", "ADX_Trend", "PSAR_Bull", "OBV_Rising"],
        "extra_pool": ["EMA_Cross", "Supertrend", "Trend_MA50"],
    },
}

NEW_COMBOS = {
    "Combo_A": {
        "signals": ["Ichimoku_Bull", "PSAR_Bull", "Supertrend", "Trend_MA50", "OBV_Rising"],
        "min_agreement_fixed": 5,
    },
    "Combo_B": {
        "signals": ["EMA_Cross", "Supertrend", "PSAR_Bull", "ADX_Trend", "Trend_MA50", "OBV_Rising"],
        "min_agreement_fixed": 6,
    },
    "Combo_C": {
        "signals": ["Ichimoku_Bull", "PSAR_Bull", "Supertrend", "ADX_Trend", "EMA_Cross", "Trend_MA50", "OBV_Rising"],
        "min_agreement_fixed": 7,
    },
}

ASSETS = ["ETHUSDT_4h", "BNBUSDT_4h", "BTCUSDT_4h"]

# ── Metric helpers ──────────────────────────────────────────────

def compute_metrics(final_capital, trades, years):
    """Return dict with win_rate, sharpe, gdd, daily_roi, roi, trades_count."""
    if not trades or len(trades) < 5:
        return None

    wins = [t for t in trades if t["pnl"] > 0]
    win_rate = len(wins) / len(trades) * 100

    returns = [t["return_pct"] for t in trades]
    avg_trade = np.mean(returns)
    std = np.std(returns) if len(returns) > 1 else 1
    sharpe = (avg_trade / std) * np.sqrt(len(trades)) if std > 0 else 0

    equity = INITIAL_CAPITAL
    peak = equity
    max_dd = 0
    for t in trades:
        equity += t["pnl"]
        peak = max(peak, equity)
        dd = (peak - equity) / peak * 100
        max_dd = max(max_dd, dd)

    roi = (final_capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    total_days = years * 365.25
    daily_roi = roi / total_days if total_days > 0 else 0

    total_wins_usd = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    total_losses_usd = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
    profit_factor = total_wins_usd / total_losses_usd if total_losses_usd > 0 else 0

    return {
        "win_rate": round(win_rate, 2),
        "sharpe": round(sharpe, 2),
        "gdd": round(max_dd, 2),
        "daily_roi": round(daily_roi, 4),
        "roi": round(roi, 2),
        "trades_count": len(trades),
        "profit_factor": round(profit_factor, 2),
        "avg_trade": round(avg_trade, 4),
    }


def passes_filter(m):
    return (
        m["win_rate"] >= 45
        and m["sharpe"] >= 2.5
        and m["gdd"] < 45
        and m["daily_roi"] > 0
    )


def score(m):
    return m["sharpe"] * 10 + m["win_rate"] + m["daily_roi"] * 100


def classify(m):
    """Return ALPHA++ / ALPHA / near-ALPHA / ---"""
    if m["win_rate"] >= 50 and m["sharpe"] >= 3.0 and m["gdd"] < 30 and m["profit_factor"] >= 2.0:
        return "ALPHA++"
    if m["win_rate"] >= 45 and m["sharpe"] >= 2.5 and m["gdd"] < 45 and m["daily_roi"] > 0:
        return "ALPHA"
    if m["win_rate"] >= 42 and m["sharpe"] >= 2.0:
        return "near-ALPHA"
    return "---"


# ── Main ────────────────────────────────────────────────────────

def main():
    t0 = time.time()

    # Pre-load and cache indicator data per asset
    print("=" * 70)
    print("NEAR-ALPHA STRATEGY OPTIMIZER")
    print("Target: WR >= 45%, Sharpe >= 2.5, GDD < 45%, dailyROI > 0")
    print("=" * 70)

    asset_data = {}
    asset_years = {}
    for asset_key in ASSETS:
        df = load_data(asset_key)
        if df is None:
            print(f"  SKIP {asset_key} — no data")
            continue
        df = calculate_indicators(df)
        asset_data[asset_key] = df

        # Compute data span in years
        if "timestamp" in df.columns:
            t_start = pd.Timestamp(df["timestamp"].min())
            t_end = pd.Timestamp(df["timestamp"].max())
            years = max((t_end - t_start).days / 365.25, 0.01)
        else:
            years = 1.0
        asset_years[asset_key] = years

    if not asset_data:
        print("No data loaded. Exiting.")
        return

    results = []
    total_combos = 0
    passed = 0

    # ── Part 1: Grid search on base strategies + optional extras ──
    for strat_name, strat_def in BASE_STRATEGIES.items():
        base_sigs = strat_def["base_signals"]
        extra_pool = strat_def["extra_pool"]

        # Build signal sets: base only + base with each extra + base with pairs of extras
        signal_variants = [base_sigs]
        for extra in extra_pool:
            if extra not in base_sigs:
                signal_variants.append(base_sigs + [extra])
        for combo in itertools.combinations(extra_pool, 2):
            augmented = base_sigs + [e for e in combo if e not in base_sigs]
            if augmented not in signal_variants:
                signal_variants.append(augmented)

        for signals in signal_variants:
            n_signals = len(signals)
            # min_agreement range: from n_signals-1 down to max(2, n_signals-2), plus n_signals
            min_agreements = sorted(set(
                [n_signals] +
                list(range(max(2, n_signals - 2), n_signals + 1))
            ))

            for min_ag in min_agreements:
                for tp in TP_GRID:
                    for sl in SL_GRID:
                        for ts in TS_GRID:
                            total_combos += len(asset_data)
                            for asset_key, df in asset_data.items():
                                df_copy = apply_strategy(df.copy(), signals, min_ag)
                                final_cap, trades = run_backtest(df_copy, sl, tp, ts)
                                m = compute_metrics(final_cap, trades, asset_years[asset_key])
                                if m is None:
                                    continue
                                if passes_filter(m):
                                    passed += 1
                                    results.append({
                                        "strategy": strat_name,
                                        "signals": "+".join(signals),
                                        "n_signals": n_signals,
                                        "min_agreement": min_ag,
                                        "tp": tp,
                                        "sl": sl,
                                        "ts": ts,
                                        "asset": asset_key,
                                        "score": score(m),
                                        "class": classify(m),
                                        **m,
                                    })

    # ── Part 2: New combos (fixed min_agreement, grid over TP/SL/TS) ──
    for combo_name, combo_def in NEW_COMBOS.items():
        signals = combo_def["signals"]
        min_ag = combo_def["min_agreement_fixed"]
        # Also try min_ag - 1 if > 2
        min_ags = [min_ag]
        if min_ag - 1 >= 2:
            min_ags.append(min_ag - 1)

        for ma in min_ags:
            for tp in TP_GRID:
                for sl in SL_GRID:
                    for ts in TS_GRID:
                        total_combos += len(asset_data)
                        for asset_key, df in asset_data.items():
                            df_copy = apply_strategy(df.copy(), signals, ma)
                            final_cap, trades = run_backtest(df_copy, sl, tp, ts)
                            m = compute_metrics(final_cap, trades, asset_years[asset_key])
                            if m is None:
                                continue
                            if passes_filter(m):
                                passed += 1
                                results.append({
                                    "strategy": combo_name,
                                    "signals": "+".join(signals),
                                    "n_signals": len(signals),
                                    "min_agreement": ma,
                                    "tp": tp,
                                    "sl": sl,
                                    "ts": ts,
                                    "asset": asset_key,
                                    "score": score(m),
                                    "class": classify(m),
                                    **m,
                                })

    elapsed = time.time() - t0
    print(f"\n{'=' * 70}")
    print(f"GRID SEARCH COMPLETE  |  {total_combos:,} backtests  |  {elapsed:.1f}s")
    print(f"Passed filter: {passed}")
    print(f"{'=' * 70}")

    if not results:
        print("\nNo combinations passed the ALPHA filter (WR>=45, Sharpe>=2.5, GDD<45, dROI>0).")
        print("Showing top 20 near-misses would require relaxing filters.")
        return

    # Sort by score descending
    results.sort(key=lambda r: r["score"], reverse=True)

    # Print top 20
    print(f"\n{'=' * 70}")
    print("TOP 20 RESULTS  (sorted by score = Sharpe*10 + WR + daily*100)")
    print(f"{'=' * 70}")
    header = (
        f"{'#':<3} {'Strategy':<22} {'Asset':<14} {'Signals':<8} "
        f"{'MinAg':<6} {'TP%':<6} {'SL%':<6} {'TS%':<6} "
        f"{'WR%':<7} {'Sharpe':<7} {'GDD%':<7} {'dROI':<7} "
        f"{'ROI%':<8} {'PF':<6} {'Trades':<7} {'Score':<7} {'Class'}"
    )
    print(header)
    print("-" * len(header))

    for i, r in enumerate(results[:20], 1):
        print(
            f"{i:<3} {r['strategy']:<22} {r['asset']:<14} {r['n_signals']:<8} "
            f"{r['min_agreement']:<6} {r['tp']*100:<6.1f} {r['sl']*100:<6.1f} {r['ts']*100:<6.1f} "
            f"{r['win_rate']:<7.1f} {r['sharpe']:<7.2f} {r['gdd']:<7.1f} {r['daily_roi']:<7.4f} "
            f"{r['roi']:<8.1f} {r['profit_factor']:<6.2f} {r['trades_count']:<7} {r['score']:<7.1f} {r['class']}"
        )

    # Summary: ALPHA and ALPHA++ counts
    alpha_pp = [r for r in results if r["class"] == "ALPHA++"]
    alpha = [r for r in results if r["class"] == "ALPHA"]
    print(f"\n{'=' * 70}")
    print(f"ALPHA++ combos: {len(alpha_pp)}")
    print(f"ALPHA combos:   {len(alpha)}")
    print(f"Total passing:  {len(results)}")
    print(f"{'=' * 70}")

    if alpha_pp:
        print(f"\n--- ALPHA++ DETAILS (top 10) ---")
        for i, r in enumerate(alpha_pp[:10], 1):
            print(
                f"  {i}. {r['strategy']} on {r['asset']}  "
                f"Signals: {r['signals']}  min={r['min_agreement']}  "
                f"TP={r['tp']*100:.1f}% SL={r['sl']*100:.1f}% TS={r['ts']*100:.1f}%  "
                f"WR={r['win_rate']}% Sharpe={r['sharpe']} GDD={r['gdd']}% "
                f"ROI={r['roi']}% PF={r['profit_factor']}"
            )

    # Save to CSV
    out_path = os.path.join(os.path.dirname(__file__), "..", "reports", "near_alpha_optimized.csv")
    df_out = pd.DataFrame(results)
    df_out.to_csv(out_path, index=False)
    print(f"\nAll {len(results)} passing results saved to {out_path}")


if __name__ == "__main__":
    main()
