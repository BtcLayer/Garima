"""Hunt for Category 1 strategies: 2%/day (730%/yr), accepts high NDD."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from run_strategies_batch import load_data, calculate_indicators, apply_strategy, run_backtest
from datetime import datetime as _dt

INITIAL = 10000
assets = ['BNBUSDT', 'ETHUSDT', 'SOLUSDT', 'LINKUSDT', 'BTCUSDT']

strats = [
    {"name": "Ultra_Aggro_v1", "strategies": ["Breakout_20", "Volume_Spike", "MACD_Cross", "ADX_Trend"], "min_agreement": 1, "stop_loss": 0.03, "take_profit": 0.20, "trailing_stop": 0.01},
    {"name": "Ultra_Aggro_v2", "strategies": ["EMA_Cross", "MACD_Cross", "Volume_Spike", "Breakout_20"], "min_agreement": 1, "stop_loss": 0.02, "take_profit": 0.25, "trailing_stop": 0.01},
    {"name": "Ultra_Aggro_v3", "strategies": ["PSAR_Bull", "MACD_Cross", "Breakout_20", "Volume_Spike"], "min_agreement": 1, "stop_loss": 0.03, "take_profit": 0.30, "trailing_stop": 0.015},
    {"name": "Max_TP_Runner", "strategies": ["Breakout_20", "Volume_Spike", "ADX_Trend", "EMA_Cross"], "min_agreement": 1, "stop_loss": 0.05, "take_profit": 0.50, "trailing_stop": 0.02},
    {"name": "Trend_Rider_Max", "strategies": ["Ichimoku_Bull", "PSAR_Bull", "EMA_Cross", "ADX_Trend"], "min_agreement": 1, "stop_loss": 0.04, "take_profit": 0.40, "trailing_stop": 0.02},
    {"name": "Scalp_Wide_v1", "strategies": ["Breakout_20", "Volume_Spike", "MACD_Cross"], "min_agreement": 1, "stop_loss": 0.01, "take_profit": 0.15, "trailing_stop": 0.005},
    {"name": "Scalp_Wide_v2", "strategies": ["EMA_Cross", "Volume_Spike", "ADX_Trend"], "min_agreement": 1, "stop_loss": 0.01, "take_profit": 0.20, "trailing_stop": 0.005},
    {"name": "Ichimoku_Aggro", "strategies": ["Ichimoku_Bull", "MACD_Cross", "Volume_Spike", "Breakout_20"], "min_agreement": 1, "stop_loss": 0.03, "take_profit": 0.25, "trailing_stop": 0.01},
    {"name": "PSAR_Aggro", "strategies": ["PSAR_Bull", "EMA_Cross", "Volume_Spike", "Breakout_20"], "min_agreement": 1, "stop_loss": 0.02, "take_profit": 0.20, "trailing_stop": 0.01},
    {"name": "OBV_Breakout_Aggro", "strategies": ["OBV_Rising", "Breakout_20", "Volume_Spike", "MACD_Cross"], "min_agreement": 1, "stop_loss": 0.03, "take_profit": 0.25, "trailing_stop": 0.01},
    {"name": "Aggro_Entry_m1", "strategies": ["Breakout_20", "Volume_Spike", "MACD_Cross", "ADX_Trend"], "min_agreement": 1, "stop_loss": 0.04, "take_profit": 0.15, "trailing_stop": 0.005},
    {"name": "MACD_Break_m1", "strategies": ["MACD_Cross", "Breakout_20", "Volume_Spike", "ADX_Trend"], "min_agreement": 1, "stop_loss": 0.04, "take_profit": 0.15, "trailing_stop": 0.015},
    {"name": "EMA_Break_m1", "strategies": ["EMA_Cross", "Breakout_20", "MACD_Cross", "ADX_Trend"], "min_agreement": 1, "stop_loss": 0.02, "take_profit": 0.15, "trailing_stop": 0.025},
    {"name": "Pure_SLTP_Wide", "strategies": ["Breakout_20", "Volume_Spike", "MACD_Cross", "EMA_Cross"], "min_agreement": 1, "stop_loss": 0.03, "take_profit": 0.30, "trailing_stop": 0.0},
    {"name": "Pure_SLTP_Tight", "strategies": ["Breakout_20", "Volume_Spike", "MACD_Cross", "EMA_Cross"], "min_agreement": 1, "stop_loss": 0.015, "take_profit": 0.10, "trailing_stop": 0.0},
]

results = []
for asset_name in assets:
    symbol = f"{asset_name}_4h"
    df = load_data(symbol)
    if df is None:
        continue
    df = calculate_indicators(df)

    if "timestamp" in df.columns:
        ts = str(df["timestamp"].iloc[0])[:10]
        te = str(df["timestamp"].iloc[-1])[:10]
    else:
        ts, te = "2020-01-01", "2026-03-20"
    try:
        _years = max((_dt.fromisoformat(te) - _dt.fromisoformat(ts)).days / 365.25, 0.01)
    except:
        _years = 1.0

    for strat in strats:
        try:
            df_copy = apply_strategy(df.copy(), strat["strategies"], strat["min_agreement"])
            final_cap, trades = run_backtest(df_copy, strat["stop_loss"], strat["take_profit"], strat["trailing_stop"])
            if len(trades) >= 10:
                roi_a = ((final_cap / INITIAL) ** (1 / _years) - 1) * 100
                daily = roi_a / 365
                wins = [t for t in trades if t["pnl"] > 0]
                wr = len(wins) / len(trades) * 100
                tw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                tl = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                pf = tw / tl if tl > 0 else 0
                eq = INITIAL; pk = eq; gdd = 0; mn = INITIAL
                for t in trades:
                    eq += t["pnl"]; pk = max(pk, eq)
                    dd = (pk - eq) / pk * 100; gdd = max(gdd, dd)
                    mn = min(mn, eq)
                ndd = max(0, (INITIAL - mn) / INITIAL * 100)
                results.append({
                    "name": strat["name"], "asset": asset_name, "roi_a": roi_a, "daily": daily,
                    "trades": len(trades), "wr": wr, "pf": pf, "gdd": gdd, "ndd": ndd,
                    "cap_ndd": round(mn, 2), "final": round(final_cap, 2),
                    "params": f"SL={strat['stop_loss']*100}% TP={strat['take_profit']*100}% TS={strat['trailing_stop']*100}%"
                })
        except Exception as e:
            pass

results.sort(key=lambda x: x["roi_a"], reverse=True)

print("=" * 120)
print("  CATEGORY 1 HUNT: Target 2%/day (730%/yr) -- High NDD accepted")
print("=" * 120)
print(f"{'#':<3} {'Strategy':<22} {'Asset':<10} {'ROI%/yr':<9} {'Daily%':<7} {'Trades':<7} {'Win%':<6} {'PF':<5} {'GDD%':<7} {'NDD%':<7} {'Cap@NDD':<10} {'Params'}")
print("-" * 120)

cat1 = []
for i, r in enumerate(results, 1):
    if r["roi_a"] > 30:
        tag = " <<<< CAT1!" if r["daily"] >= 1.5 else (" << CLOSE" if r["daily"] >= 0.8 else "")
        print(f"{i:<3} {r['name']:<22} {r['asset']:<10} {r['roi_a']:<9.1f} {r['daily']:<7.3f} {r['trades']:<7} {r['wr']:<6.1f} {r['pf']:<5.2f} {r['gdd']:<7.1f} {r['ndd']:<7.1f} ${r['cap_ndd']:<9} {r['params']}{tag}")
        if r["daily"] >= 1.0:
            cat1.append(r)

print()
if cat1:
    print(f"CAT 1 STRATEGIES FOUND: {len(cat1)}")
    for r in cat1:
        print(f"  {r['name']} on {r['asset']} -- {r['daily']:.2f}%/day ({r['roi_a']:.0f}%/yr) NDD={r['ndd']:.1f}%")
else:
    best = results[0] if results else None
    if best:
        print(f"Best daily: {best['daily']:.3f}%/day ({best['roi_a']:.1f}%/yr) -- {best['name']} on {best['asset']}")
        print(f"Gap to 2%/day: {(2 - best['daily']) / 2 * 100:.0f}% short")
        print()
        print("To reach 2%/day without leverage:")
        needed = int(2 / best["daily"]) if best["daily"] > 0 else 999
        print(f"  - Stack {needed} strategies simultaneously")
        print(f"  - Or use {2 / best['daily']:.1f}x leverage on best strategy")
