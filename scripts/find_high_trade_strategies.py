#!/usr/bin/env python3
"""Find strategies with HIGH trade counts on 4h and 1h timeframes.
Relaxed min_agreement (2-of-5, 3-of-5) = more trades.
TF-specific SL/TP params for 1h."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run_strategies_batch import load_data, calculate_indicators, apply_strategy, run_backtest, INITIAL_CAPITAL
from itertools import combinations
from datetime import datetime
import csv

# ── SIGNAL POOLS ──
# 4h: trend-following signals (proven)
SIGNALS_4H = ["PSAR_Bull", "EMA_Cross", "Supertrend", "Trend_MA50", "OBV_Rising",
              "ADX_Trend", "Volume_Spike", "Ichimoku_Bull", "VWAP", "MACD_Cross", "Breakout_20"]

# 1h: momentum + mean-reversion signals (work on shorter TF)
SIGNALS_1H = ["EMA_Cross", "MACD_Cross", "Supertrend", "PSAR_Bull", "ADX_Trend",
              "Volume_Spike", "Breakout_20", "VWAP", "OBV_Rising", "Stochastic",
              "RSI_Oversold", "CCI_Oversold", "MFI_Oversold", "Trend_MA50"]

ASSETS = ["ETHUSDT", "BTCUSDT", "ADAUSDT", "BNBUSDT", "SOLUSDT", "LINKUSDT"]

# TF-specific params
PARAMS_4H = [
    (0.008, 0.03, 0.004), (0.01, 0.04, 0.005),
    (0.01, 0.05, 0.005), (0.012, 0.06, 0.006),
    (0.012, 0.07, 0.006), (0.015, 0.08, 0.007),
    (0.015, 0.09, 0.007), (0.015, 0.10, 0.008),
    (0.02, 0.12, 0.01),
]

PARAMS_1H = [
    (0.004, 0.012, 0.003), (0.005, 0.015, 0.003),
    (0.005, 0.02, 0.004), (0.006, 0.025, 0.004),
    (0.007, 0.03, 0.005), (0.008, 0.035, 0.005),
    (0.008, 0.04, 0.006), (0.01, 0.05, 0.006),
    (0.01, 0.06, 0.007),
]

# TF-specific tier criteria (relaxed for 1h)
def get_tier(pf, wr, gdd, tf):
    if tf == "4h":
        if pf >= 1.8 and wr >= 50 and gdd < 40: return "TIER_1"
        if pf >= 1.6 and wr >= 50 and gdd < 45: return "TIER_2_DEPLOY"
        if pf >= 1.4 and wr >= 50: return "TIER_2_TEST"
        if pf >= 1.2 and wr >= 45: return "PAPER_TRADE"
    elif tf == "1h":
        if pf >= 1.5 and wr >= 48 and gdd < 45: return "TIER_1"
        if pf >= 1.35 and wr >= 47 and gdd < 50: return "TIER_2_DEPLOY"
        if pf >= 1.2 and wr >= 45: return "TIER_2_TEST"
        if pf >= 1.1 and wr >= 43: return "PAPER_TRADE"
    return None

def run_sweep(tf, signals, params, assets, output_file):
    results = []
    tested = 0
    winners = 0

    # Load data
    data_cache = {}
    for asset in assets:
        key = f"{asset}_{tf}"
        df = load_data(key)
        if df is not None:
            df = calculate_indicators(df)
            data_cache[key] = df
            print(f"  Loaded {key}: {len(df)} candles")

    if not data_cache:
        print(f"  No data for {tf}!")
        return results

    # Get years from data
    def get_years(df):
        if "timestamp" in df.columns:
            t_s = str(df["timestamp"].iloc[0])[:10]
            t_e = str(df["timestamp"].iloc[-1])[:10]
        else:
            return 6.0
        try:
            return max((datetime.fromisoformat(t_e) - datetime.fromisoformat(t_s)).days / 365.25, 0.01)
        except:
            return 6.0

    min_trades = 50 if tf == "1h" else 20

    # Test combo sizes 2, 3, 4, 5
    for combo_size in [2, 3, 4, 5]:
        combo_list = list(combinations(signals, combo_size))
        print(f"  Combo size {combo_size}: {len(combo_list)} combos")

        for combo in combo_list:
            # Test different min_agreement values: from 2 to combo_size
            for min_ag in range(max(combo_size - 2, 2), combo_size + 1):
                for key, df in data_cache.items():
                    asset = key.split("_")[0]
                    yrs = get_years(df)

                    for sl, tp, ts in params:
                        tested += 1
                        if tested % 5000 == 0:
                            print(f"  [{tf}] {tested} tested, {winners} found...")

                        try:
                            dc = apply_strategy(df.copy(), list(combo), min_ag)
                            cap, trades = run_backtest(dc, sl, tp, ts)

                            if len(trades) < min_trades:
                                continue

                            roi_a = ((cap / INITIAL_CAPITAL) ** (1/yrs) - 1) * 100 if cap > 0 else -100
                            if roi_a < 2:
                                continue

                            w = [t for t in trades if t["pnl"] > 0]
                            wr = len(w) / len(trades) * 100
                            if wr < 40:
                                continue

                            tw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                            tl = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                            pf = tw / tl if tl > 0 else 0
                            if pf < 1.1:
                                continue

                            # Drawdown
                            eq = INITIAL_CAPITAL
                            pk = eq
                            gdd = 0
                            for t in trades:
                                eq += t["pnl"]
                                pk = max(pk, eq)
                                dd = (pk - eq) / pk * 100
                                gdd = max(gdd, dd)

                            tier = get_tier(pf, wr, gdd, tf)
                            if tier is None:
                                continue

                            winners += 1
                            sig_str = " + ".join(combo)
                            r = {
                                "tier": tier, "signals": sig_str, "min_ag": min_ag,
                                "asset": asset, "tf": tf,
                                "sl": round(sl*100, 1), "tp": round(tp*100, 1), "ts": round(ts*100, 1),
                                "roi_pct_yr": round(roi_a, 1),
                                "wr": round(wr, 1), "pf": round(pf, 2),
                                "gdd": round(gdd, 1), "trades": len(trades),
                                "final_cap": round(cap, 0),
                            }
                            results.append(r)
                            print(f"  ** {tier} | {asset} {tf} | {sig_str} (min={min_ag}) | PF={pf:.2f} WR={wr:.1f}% ROI={roi_a:.1f}%/yr | {len(trades)} trades | SL={sl*100}% TP={tp*100}% **")

                        except Exception:
                            continue

    # Sort by tier priority then trades descending
    tier_order = {"TIER_1": 0, "TIER_2_DEPLOY": 1, "TIER_2_TEST": 2, "PAPER_TRADE": 3}
    results.sort(key=lambda x: (tier_order.get(x["tier"], 9), -x["trades"]))

    # Save CSV
    if results:
        with open(output_file, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader()
            w.writerows(results)
        print(f"\n  Saved {len(results)} results to {output_file}")

    print(f"\n  [{tf}] DONE: {tested} tested, {winners} winners")
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--tf", default="4h", choices=["1h", "4h", "both"])
    args = parser.parse_args()

    timeframes = ["1h", "4h"] if args.tf == "both" else [args.tf]

    for tf in timeframes:
        print(f"\n{'='*60}")
        print(f"  SCANNING {tf} — high trade count strategies")
        print(f"{'='*60}")

        sigs = SIGNALS_1H if tf == "1h" else SIGNALS_4H
        params = PARAMS_1H if tf == "1h" else PARAMS_4H
        outfile = f"reports/high_trade_strategies_{tf}.csv"

        results = run_sweep(tf, sigs, params, ASSETS, outfile)

        # Print summary
        if results:
            print(f"\n  TOP 20 by trades ({tf}):")
            print(f"  {'Tier':<15} {'Asset':<8} {'Signals':<45} {'min':>3} {'PF':>5} {'WR%':>5} {'ROI%':>7} {'GDD%':>5} {'Trades':>6}")
            print(f"  {'-'*100}")
            by_trades = sorted(results, key=lambda x: -x["trades"])[:20]
            for r in by_trades:
                print(f"  {r['tier']:<15} {r['asset']:<8} {r['signals'][:44]:<45} {r['min_ag']:>3} {r['pf']:>5.2f} {r['wr']:>5.1f} {r['roi_pct_yr']:>7.1f} {r['gdd']:>5.1f} {r['trades']:>6}")
        else:
            print(f"\n  No results for {tf}")
