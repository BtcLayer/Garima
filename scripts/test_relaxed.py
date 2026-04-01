#!/usr/bin/env python3
"""Test tournament-matched backtester on all assets 15m — full scan."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from run_strategies_batch import run_tournament_backtest

TOURNAMENT_DATA = "/home/ubuntu/tradingview_webhook_bot/storage/backtest_data"
ASSETS = ["FILUSDT", "LDOUSDT", "SUIUSDT", "OPUSDT", "INJUSDT", "DOGEUSDT",
          "SOLUSDT", "AVAXUSDT", "ARBUSDT", "APTUSDT", "LINKUSDT", "NEARUSDT",
          "ADAUSDT", "ETHUSDT", "BTCUSDT", "BNBUSDT", "XRPUSDT", "ATOMUSDT",
          "AAVEUSDT", "UNIUSDT"]
STRATS = ["Ichimoku_Trend_Pro", "Keltner_Breakout", "Aggressive_Entry",
          "MACD_Breakout", "Full_Momentum", "Hybrid_SMC"]
PARAMS = [(1.5, 7), (1.8, 9), (2.0, 11), (2.5, 14), (3.0, 18), (3.5, 21), (4.0, 26)]

results = []
for asset in ASSETS:
    path = os.path.join(TOURNAMENT_DATA, f"{asset}_3y_15m.csv")
    if not os.path.exists(path):
        continue
    df = pd.read_csv(path)
    print(f"{asset}: {len(df)} bars", flush=True)

    for strat in STRATS:
        for mult, ln in PARAMS:
            try:
                is_m, oos_m = run_tournament_backtest(df, strat, mult=mult, length=ln, oos_split=0.2)
                if oos_m["daily_roi"] > 0.05:
                    results.append({
                        "asset": asset, "strategy": strat, "mult": mult, "len": ln,
                        "is_roi": is_m["daily_roi"], "oos_roi": oos_m["daily_roi"],
                        "wr": oos_m["win_rate"], "pf": oos_m["pf"],
                        "sharpe": oos_m["sharpe"], "gdd": oos_m["gross_dd"],
                        "trades": oos_m["total_trades"],
                    })
            except:
                continue

results.sort(key=lambda x: -x["oos_roi"])
print(f"\nTOP 30 (OOS, tournament-matched):")
print(f"{'#':<3} {'Asset':<12} {'Strategy':<22} {'m':>4} {'l':>3} {'IS%':>7} {'OOS%':>7} {'WR':>5} {'PF':>5} {'Sharpe':>7} {'GDD':>6} {'Trd':>6}")
print("-" * 95)
seen = set()
n = 0
for r in results:
    k = (r["asset"], r["strategy"])
    if k in seen:
        continue
    seen.add(k)
    n += 1
    if n > 30:
        break
    print(f"{n:<3} {r['asset']:<12} {r['strategy']:<22} {r['mult']:>4} {r['len']:>3} {r['is_roi']:>6.3f}% {r['oos_roi']:>6.3f}% {r['wr']:>5.1f} {r['pf']:>5.2f} {r['sharpe']:>7.2f} {r['gdd']:>5.1f}% {r['trades']:>6}")

above_1 = len(set((r["asset"], r["strategy"]) for r in results if r["oos_roi"] >= 1.0))
above_05 = len(set((r["asset"], r["strategy"]) for r in results if r["oos_roi"] >= 0.5))
above_025 = len(set((r["asset"], r["strategy"]) for r in results if r["oos_roi"] >= 0.25))
print(f"\n>= 1%: {above_1} | >= 0.5%: {above_05} | >= 0.25%: {above_025} | Total: {len(set((r['asset'],r['strategy']) for r in results))}")
print("DONE", flush=True)
