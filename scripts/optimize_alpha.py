"""Optimize strategies to meet ALPHA tier criteria."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from run_strategies_batch import load_data, calculate_indicators, apply_strategy, run_backtest
from datetime import datetime as _dt
import numpy as np

INITIAL = 10000

all_strats = [
    ("MACD_Breakout", "ETHUSDT_4h", ["MACD_Cross","Breakout_20","Volume_Spike","ADX_Trend"]),
    ("Full_Momentum", "BNBUSDT_4h", ["PSAR_Bull","Ichimoku_Bull","MACD_Cross","ADX_Trend","OBV_Rising"]),
    ("EMA_Break_Momentum", "BNBUSDT_4h", ["EMA_Cross","Breakout_20","MACD_Cross","ADX_Trend"]),
    ("Ichimoku_MACD_Pro", "BTCUSDT_4h", ["Ichimoku_Bull","MACD_Cross","OBV_Rising","Volume_Spike"]),
    ("MACD_Breakout", "BNBUSDT_4h", ["MACD_Cross","Breakout_20","Volume_Spike","ADX_Trend"]),
    ("Aggressive_Entry", "ETHUSDT_4h", ["Breakout_20","Volume_Spike","MACD_Cross","ADX_Trend"]),
    ("Aggressive_Entry", "BNBUSDT_4h", ["Breakout_20","Volume_Spike","MACD_Cross","ADX_Trend"]),
    ("Aggressive_Entry", "SOLUSDT_4h", ["Breakout_20","Volume_Spike","MACD_Cross","ADX_Trend"]),
    ("Aggressive_Entry", "LINKUSDT_4h", ["Breakout_20","Volume_Spike","MACD_Cross","ADX_Trend"]),
    ("Aggressive_Entry", "BTCUSDT_4h", ["Breakout_20","Volume_Spike","MACD_Cross","ADX_Trend"]),
    ("Ichimoku_Trend_Pro", "BNBUSDT_4h", ["Ichimoku_Bull","EMA_Cross","ADX_Trend","OBV_Rising"]),
    ("Ichimoku_Trend_Pro", "ETHUSDT_4h", ["Ichimoku_Bull","EMA_Cross","ADX_Trend","OBV_Rising"]),
    ("Ichimoku_Trend_Pro", "BTCUSDT_4h", ["Ichimoku_Bull","EMA_Cross","ADX_Trend","OBV_Rising"]),
    ("Full_Momentum", "ETHUSDT_4h", ["PSAR_Bull","Ichimoku_Bull","MACD_Cross","ADX_Trend","OBV_Rising"]),
    ("Full_Momentum", "BTCUSDT_4h", ["PSAR_Bull","Ichimoku_Bull","MACD_Cross","ADX_Trend","OBV_Rising"]),
    ("MACD_Breakout", "LINKUSDT_4h", ["MACD_Cross","Breakout_20","Volume_Spike","ADX_Trend"]),
    ("EMA_Break_Momentum", "ETHUSDT_4h", ["EMA_Cross","Breakout_20","MACD_Cross","ADX_Trend"]),
    ("Ichimoku_MACD_Pro", "BNBUSDT_4h", ["Ichimoku_Bull","MACD_Cross","OBV_Rising","Volume_Spike"]),
    ("Ichimoku_MACD_Pro", "ETHUSDT_4h", ["Ichimoku_Bull","MACD_Cross","OBV_Rising","Volume_Spike"]),
    ("EMA_Break_Momentum", "SOLUSDT_4h", ["EMA_Cross","Breakout_20","MACD_Cross","ADX_Trend"]),
]

param_grid = [
    (1, 0.01, 0.05, 0.005), (1, 0.015, 0.08, 0.005), (1, 0.02, 0.10, 0.01),
    (1, 0.02, 0.15, 0.01), (1, 0.03, 0.15, 0.015),
    (2, 0.01, 0.05, 0.005), (2, 0.015, 0.08, 0.01), (2, 0.02, 0.10, 0.01),
    (2, 0.02, 0.12, 0.015), (2, 0.03, 0.15, 0.015), (2, 0.04, 0.15, 0.005),
    (2, 0.04, 0.20, 0.02),
    (3, 0.015, 0.08, 0.01), (3, 0.02, 0.10, 0.015), (3, 0.02, 0.12, 0.02),
    (3, 0.03, 0.15, 0.02), (3, 0.04, 0.20, 0.025),
]

data_cache = {}
results = []
done = 0

for name, symbol, signals in all_strats:
    if symbol not in data_cache:
        df = load_data(symbol)
        if df is None:
            continue
        df = calculate_indicators(df)
        data_cache[symbol] = df
        print(f"Loaded {symbol}: {len(df)} candles")
    df = data_cache[symbol]

    if "timestamp" in df.columns:
        t_s = str(df["timestamp"].iloc[0])[:10]
        t_e = str(df["timestamp"].iloc[-1])[:10]
    else:
        t_s, t_e = "2020-01-01", "2026-03-20"
    try:
        _years = max((_dt.fromisoformat(t_e) - _dt.fromisoformat(t_s)).days / 365.25, 0.01)
    except Exception:
        _years = 6.0

    best = None

    for min_ag, sl, tp, ts_val in param_grid:
        if min_ag > len(signals):
            continue
        done += 1
        try:
            df_copy = apply_strategy(df.copy(), signals, min_ag)
            final_cap, trades = run_backtest(df_copy, sl, tp, ts_val)
            if len(trades) < 20:
                continue

            roi_a = ((final_cap / INITIAL) ** (1 / _years) - 1) * 100 if final_cap > 0 else -100
            daily_roi = roi_a / 365
            wins = [t for t in trades if t["pnl"] > 0]
            wr = len(wins) / len(trades) * 100
            tw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
            tl = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
            pf = tw / tl if tl > 0 else 0

            rets = [t.get("return_pct", t["pnl"] / INITIAL * 100) for t in trades]
            avg_r = np.mean(rets)
            std_r = np.std(rets) if len(rets) > 1 else 1
            sharpe = (avg_r / std_r) * np.sqrt(len(trades) / _years) if std_r > 0 else 0

            eq = INITIAL
            pk = eq
            gdd = 0
            mn = INITIAL
            for t in trades:
                eq += t["pnl"]
                pk = max(pk, eq)
                dd = (pk - eq) / pk * 100
                gdd = max(gdd, dd)
                mn = min(mn, eq)
            ndd = max(0, (INITIAL - mn) / INITIAL * 100)

            # Tier check
            alpha_pp = daily_roi >= 0.6 and sharpe >= 4.0 and wr >= 45 and gdd < 30
            alpha_pp2 = daily_roi >= 0.5 and sharpe >= 3.5 and wr >= 45 and gdd < 35
            alpha1 = daily_roi >= 0.3 and sharpe >= 3.0 and wr >= 45 and gdd < 40
            alpha2 = daily_roi >= 0.25 and sharpe >= 2.5 and wr >= 48 and gdd < 45
            bonus1 = sharpe >= 6.0 and daily_roi >= 0.3 and gdd < 30
            bonus2 = sharpe >= 5.0 and daily_roi >= 0.2 and gdd < 40
            average1 = daily_roi >= 0.1 and sharpe >= 1.5
            average2 = daily_roi >= 0.05

            if alpha_pp or alpha_pp2 or bonus1:
                tier = "ALPHA++"
            elif alpha1 or alpha2 or bonus2:
                tier = "ALPHA"
            elif average1 or average2:
                tier = "AVERAGE"
            else:
                tier = "REJECT"

            if tier != "REJECT" and roi_a > 0:
                entry = {
                    "name": name, "asset": symbol.replace("_4h", ""), "min_ag": min_ag,
                    "sl": sl, "tp": tp, "ts": ts_val, "roi_a": roi_a, "daily": daily_roi,
                    "trades": len(trades), "wr": wr, "pf": pf, "sharpe": sharpe,
                    "gdd": gdd, "ndd": ndd, "cap_ndd": round(mn, 2), "tier": tier,
                }
                tier_order = {"ALPHA++": 0, "ALPHA": 1, "AVERAGE": 2}
                if best is None or tier_order.get(entry["tier"], 3) < tier_order.get(best["tier"], 3) or \
                   (entry["tier"] == best["tier"] and entry["sharpe"] > best["sharpe"]):
                    best = entry
                results.append(entry)
        except Exception:
            pass

    if best:
        print(f"  {name} {symbol}: {best['tier']} ROI={best['roi_a']:.1f}%/yr Sharpe={best['sharpe']:.2f} WR={best['wr']:.1f}% min={best['min_ag']} SL={best['sl']*100}% TP={best['tp']*100}% TS={best['ts']*100}%")

# Deduplicate
tier_order = {"ALPHA++": 0, "ALPHA": 1, "AVERAGE": 2}
seen = {}
for r in results:
    key = (r["name"], r["asset"])
    if key not in seen or tier_order.get(r["tier"], 3) < tier_order.get(seen[key]["tier"], 3) or \
       (r["tier"] == seen[key]["tier"] and r["sharpe"] > seen[key]["sharpe"]):
        seen[key] = r

unique = sorted(seen.values(), key=lambda x: (tier_order.get(x["tier"], 3), -x["sharpe"]))

print()
print("=" * 140)
print("  ALPHA OPTIMIZATION RESULTS")
print("  ALPHA: Daily>=0.25%, Sharpe>=2.5, WR>=45%, GDD<45%")
print("=" * 140)
print(f"{'#':<3} {'Tier':<10} {'Strategy':<22} {'Asset':<10} {'ROI%/yr':<8} {'Daily%':<7} {'Sharpe':<7} {'WR%':<6} {'PF':<5} {'GDD%':<6} {'NDD%':<6} {'Trades':<7} Params")
print("-" * 140)
for i, r in enumerate(unique, 1):
    print(f"{i:<3} {r['tier']:<10} {r['name']:<22} {r['asset']:<10} {r['roi_a']:<8.1f} {r['daily']:<7.3f} {r['sharpe']:<7.2f} {r['wr']:<6.1f} {r['pf']:<5.2f} {r['gdd']:<6.1f} {r['ndd']:<6.1f} {r['trades']:<7} min={r['min_ag']} SL={r['sl']*100}% TP={r['tp']*100}% TS={r['ts']*100}%")

a_pp = len([r for r in unique if r["tier"] == "ALPHA++"])
a = len([r for r in unique if r["tier"] == "ALPHA"])
avg = len([r for r in unique if r["tier"] == "AVERAGE"])
print(f"\nALPHA++: {a_pp} | ALPHA: {a} | AVERAGE: {avg} | Total combos tested: {done}")
