#!/usr/bin/env python3
"""FAST targeted sweep — only proven combos, skip brute force."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from run_strategies_batch import load_data, calculate_indicators, apply_strategy, run_backtest, INITIAL_CAPITAL
from datetime import datetime

COMBOS = [
    (["PSAR_Bull", "EMA_Cross", "Supertrend"], 2),
    (["PSAR_Bull", "EMA_Cross", "Supertrend"], 3),
    (["PSAR_Bull", "EMA_Cross", "Trend_MA50"], 2),
    (["EMA_Cross", "Supertrend"], 2),
    (["PSAR_Bull", "Trend_MA50"], 2),
    (["EMA_Cross", "Supertrend", "ADX_Trend"], 2),
    (["EMA_Cross", "MACD_Cross", "ADX_Trend"], 2),
    (["PSAR_Bull", "EMA_Cross", "MACD_Cross"], 2),
    (["PSAR_Bull", "Supertrend", "MACD_Cross", "EMA_Cross"], 2),
    (["PSAR_Bull", "Supertrend", "MACD_Cross", "EMA_Cross"], 3),
    (["EMA_Cross", "Breakout_20", "Volume_Spike"], 2),
    (["Ichimoku_Bull", "PSAR_Bull", "EMA_Cross"], 2),
    (["PSAR_Bull", "Volume_Spike", "EMA_Cross", "Supertrend", "Trend_MA50"], 3),
    (["PSAR_Bull", "Volume_Spike", "EMA_Cross", "Supertrend", "Trend_MA50"], 4),
    (["PSAR_Bull", "EMA_Cross", "Volume_Spike", "OBV_Rising"], 3),
    (["Ichimoku_Bull", "PSAR_Bull", "OBV_Rising", "EMA_Cross", "Trend_MA50"], 3),
    (["EMA_Cross", "MACD_Cross", "Volume_Spike"], 2),
    (["Supertrend", "MACD_Cross", "Volume_Spike"], 2),
    (["Supertrend", "ADX_Trend", "EMA_Cross"], 2),
    (["PSAR_Bull", "EMA_Cross", "Stochastic"], 2),
    (["EMA_Cross", "VWAP", "Volume_Spike"], 2),
    (["EMA_Cross", "RSI_Oversold", "Volume_Spike"], 2),
    (["CCI_Oversold", "EMA_Cross", "PSAR_Bull"], 2),
    (["MFI_Oversold", "PSAR_Bull", "EMA_Cross"], 2),
]

ASSETS = ["ETHUSDT", "BTCUSDT", "ADAUSDT", "BNBUSDT", "SOLUSDT", "LINKUSDT"]
P4 = [(0.008,0.03,0.004),(0.01,0.05,0.005),(0.012,0.06,0.006),(0.012,0.07,0.006),(0.015,0.08,0.007),(0.015,0.10,0.008),(0.02,0.12,0.01)]
P1 = [(0.005,0.015,0.003),(0.005,0.02,0.004),(0.007,0.03,0.005),(0.008,0.04,0.006),(0.01,0.05,0.006),(0.01,0.06,0.007)]

all_res = []
for tf in ["4h", "1h"]:
    params = P4 if tf == "4h" else P1
    min_t = 20 if tf == "4h" else 50
    print(f"\n=== {tf} SWEEP ===", flush=True)
    for asset in ASSETS:
        df = load_data(f"{asset}_{tf}")
        if df is None:
            continue
        df = calculate_indicators(df)
        if "timestamp" in df.columns:
            yrs = max((datetime.fromisoformat(str(df["timestamp"].iloc[-1])[:10]) - datetime.fromisoformat(str(df["timestamp"].iloc[0])[:10])).days / 365.25, 0.01)
        else:
            yrs = 6.0
        found = 0
        for combo, min_ag in COMBOS:
            for sl, tp, ts in params:
                try:
                    dc = apply_strategy(df.copy(), list(combo), min_ag)
                    cap, trades = run_backtest(dc, sl, tp, ts)
                    if len(trades) < min_t:
                        continue
                    roi_a = ((cap / INITIAL_CAPITAL) ** (1 / yrs) - 1) * 100 if cap > 0 else -100
                    if roi_a < 2:
                        continue
                    w = [t for t in trades if t["pnl"] > 0]
                    wr = len(w) / len(trades) * 100
                    if wr < 40:
                        continue
                    tw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                    tl = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                    pf = tw / tl if tl > 0 else 0
                    if pf < 1.05:
                        continue
                    eq = INITIAL_CAPITAL; pk = eq; gdd = 0
                    for t in trades:
                        eq += t["pnl"]; pk = max(pk, eq)
                        dd = (pk - eq) / pk * 100; gdd = max(gdd, dd)
                    tier = None
                    if tf == "4h":
                        if pf >= 1.8 and wr >= 50 and gdd < 40: tier = "TIER_1"
                        elif pf >= 1.6 and wr >= 50 and gdd < 45: tier = "TIER_2_D"
                        elif pf >= 1.4 and wr >= 50: tier = "TIER_2_T"
                        elif pf >= 1.2 and wr >= 45: tier = "PAPER"
                        elif pf >= 1.1 and wr >= 43: tier = "WATCH"
                    else:
                        if pf >= 1.5 and wr >= 48 and gdd < 45: tier = "TIER_1"
                        elif pf >= 1.35 and wr >= 47 and gdd < 50: tier = "TIER_2_D"
                        elif pf >= 1.2 and wr >= 45: tier = "TIER_2_T"
                        elif pf >= 1.1 and wr >= 43: tier = "PAPER"
                        elif pf >= 1.05 and wr >= 42: tier = "WATCH"
                    if tier:
                        all_res.append((tier, asset, tf, "+".join(combo), min_ag, pf, wr, roi_a, gdd, len(trades), sl * 100, tp * 100))
                        found += 1
                except:
                    continue
        print(f"  {asset} {tf}: {found} hits", flush=True)

# Dedupe: keep best tier+PF per (asset, tf, signals, min_ag)
tier_ord = {"TIER_1": 0, "TIER_2_D": 1, "TIER_2_T": 2, "PAPER": 3, "WATCH": 4}
best = {}
for r in all_res:
    k = (r[1], r[2], r[3], r[4])  # asset, tf, sig, min_ag
    if k not in best or tier_ord.get(r[0], 9) < tier_ord.get(best[k][0], 9) or (r[0] == best[k][0] and r[5] > best[k][5]):
        best[k] = r
final = sorted(best.values(), key=lambda x: (tier_ord.get(x[0], 9), -x[9]))

print(f"\n{'='*100}", flush=True)
print(f"  FINAL STRATEGY LIST", flush=True)
print(f"{'='*100}", flush=True)
n = 0
for tf_label in ["4h", "1h"]:
    subset = [r for r in final if r[2] == tf_label]
    if not subset:
        print(f"\n--- {tf_label}: NO RESULTS ---", flush=True)
        continue
    print(f"\n--- {tf_label} ({len(subset)} strategies) ---", flush=True)
    print(f"  {'#':<4} {'Tier':<10} {'Asset':<10} {'Signals':<48} {'min':>3} {'PF':>5} {'WR%':>5} {'ROI%':>7} {'GDD%':>5} {'Trades':>6} {'SL%':>4} {'TP%':>4}", flush=True)
    print(f"  {'-'*112}", flush=True)
    for r in subset:
        n += 1
        tier, asset, tf, sig, mag, pf, wr, roi, gdd, tr, sl, tp = r
        print(f"  {n:<4} {tier:<10} {asset:<10} {sig[:47]:<48} {mag:>3} {pf:>5.2f} {wr:>5.1f} {roi:>7.1f} {gdd:>5.1f} {tr:>6} {sl:>4} {tp:>4}", flush=True)

print(f"\nTOTAL: {n} unique strategies", flush=True)
print("DONE", flush=True)
