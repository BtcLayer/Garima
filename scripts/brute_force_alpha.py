"""Brute force every signal combination to find ALPHA-tier strategies."""
import sys, os, numpy as np
from itertools import combinations
from datetime import datetime as _dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from run_strategies_batch import load_data, calculate_indicators, apply_strategy, run_backtest, SIGNAL_FUNCTIONS

INITIAL = 10000
assets = ["BNBUSDT_4h", "ETHUSDT_4h", "BTCUSDT_4h", "SOLUSDT_4h", "LINKUSDT_4h"]

data = {}
for a in assets:
    df = load_data(a)
    if df is not None:
        df = calculate_indicators(df)
        data[a] = df

all_signals = list(SIGNAL_FUNCTIONS.keys())
print(f"Signals ({len(all_signals)}): {all_signals}")

param_sets = [
    (0.008, 0.04, 0.004),
    (0.01, 0.05, 0.005),
    (0.012, 0.06, 0.006),
    (0.015, 0.08, 0.008),
    (0.02, 0.08, 0.01),
    (0.02, 0.10, 0.01),
]

best_results = []
total = 0

for asset_name, df in data.items():
    asset_short = asset_name.replace("_4h", "")
    if "timestamp" in df.columns:
        t_s = str(df["timestamp"].iloc[0])[:10]
        t_e = str(df["timestamp"].iloc[-1])[:10]
    else:
        t_s, t_e = "2020-01-01", "2026-03-20"
    try:
        _years = max((_dt.fromisoformat(t_e) - _dt.fromisoformat(t_s)).days / 365.25, 0.01)
    except Exception:
        _years = 6.0

    def test_combo(combo, min_ag):
        global total
        for sl, tp, ts_val in param_sets:
            total += 1
            try:
                df_copy = apply_strategy(df.copy(), list(combo), min_ag)
                final_cap, trades = run_backtest(df_copy, sl, tp, ts_val)
                if len(trades) < 20:
                    continue
                roi_a = ((final_cap / INITIAL) ** (1 / _years) - 1) * 100 if final_cap > 0 else -100
                daily = roi_a / 365
                if daily < 0.05:
                    continue
                wins = [t for t in trades if t["pnl"] > 0]
                wr = len(wins) / len(trades) * 100
                if wr < 38:
                    continue
                tw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                tl = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                pf = tw / tl if tl > 0 else 0
                rets = [t["pnl"] / INITIAL * 100 for t in trades]
                sharpe = (np.mean(rets) / np.std(rets)) * np.sqrt(len(trades) / _years) if np.std(rets) > 0 else 0
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

                is_alpha_pp = (daily >= 0.5 and sharpe >= 3.5 and wr >= 45 and gdd < 35) or \
                              (daily >= 0.6 and sharpe >= 4.0 and wr >= 45 and gdd < 30) or \
                              (sharpe >= 6.0 and daily >= 0.3 and gdd < 30)
                is_alpha = (daily >= 0.25 and sharpe >= 2.5 and wr >= 45 and gdd < 45) or \
                           (daily >= 0.3 and sharpe >= 3.0 and wr >= 45 and gdd < 40) or \
                           (sharpe >= 5.0 and daily >= 0.2 and gdd < 40)
                is_near = daily >= 0.1 and sharpe >= 1.5 and wr >= 42

                if is_alpha_pp or is_alpha or is_near:
                    tier = "ALPHA++" if is_alpha_pp else ("ALPHA" if is_alpha else "NEAR-ALPHA")
                    best_results.append({
                        "signals": list(combo), "min_ag": min_ag, "asset": asset_short,
                        "sl": sl, "tp": tp, "ts": ts_val, "roi_a": roi_a, "daily": daily,
                        "trades": len(trades), "wr": wr, "pf": pf, "sharpe": sharpe,
                        "gdd": gdd, "ndd": ndd, "tier": tier,
                    })
            except Exception:
                pass

    # 2-signal combos, min_agreement=2
    for combo in combinations(all_signals, 2):
        test_combo(combo, 2)

    # 3-signal combos, min_agreement=3
    for combo in combinations(all_signals, 3):
        test_combo(combo, 3)

    # 3-signal combos, min_agreement=2
    for combo in combinations(all_signals, 3):
        test_combo(combo, 2)

    found = len([r for r in best_results if r["asset"] == asset_short])
    alphas = len([r for r in best_results if r["asset"] == asset_short and r["tier"] in ("ALPHA++", "ALPHA")])
    print(f"{asset_short}: {found} candidates ({alphas} ALPHA/ALPHA++) — tested {total} combos so far")

# Deduplicate: best tier+sharpe per signal-combo+asset
seen = {}
for r in best_results:
    key = (tuple(sorted(r["signals"])), r["asset"])
    tier_ord = {"ALPHA++": 0, "ALPHA": 1, "NEAR-ALPHA": 2}
    if key not in seen or tier_ord.get(r["tier"], 3) < tier_ord.get(seen[key]["tier"], 3) or \
       (r["tier"] == seen[key]["tier"] and r["sharpe"] > seen[key]["sharpe"]):
        seen[key] = r

unique = sorted(seen.values(), key=lambda x: ({"ALPHA++": 0, "ALPHA": 1, "NEAR-ALPHA": 2}.get(x["tier"], 3), -x["sharpe"]))

print()
print("=" * 160)
print(f"  BRUTE FORCE RESULTS — {total} combinations tested")
print("=" * 160)
hdr = f"{'#':<3} {'Tier':<12} {'Signals':<50} {'Asset':<10} {'ROI%/yr':<8} {'Daily%':<7} {'Sharpe':<7} {'WR%':<6} {'PF':<5} {'GDD%':<6} {'Tr':<5} Params"
print(hdr)
print("-" * 160)
for i, r in enumerate(unique[:40], 1):
    sigs = " + ".join(r["signals"])
    params = f"min={r['min_ag']} SL={r['sl']*100}% TP={r['tp']*100}% TS={r['ts']*100}%"
    print(f"{i:<3} {r['tier']:<12} {sigs:<50} {r['asset']:<10} {r['roi_a']:<8.1f} {r['daily']:<7.3f} {r['sharpe']:<7.2f} {r['wr']:<6.1f} {r['pf']:<5.2f} {r['gdd']:<6.1f} {r['trades']:<5} {params}")

a_pp = len([r for r in unique if r["tier"] == "ALPHA++"])
a = len([r for r in unique if r["tier"] == "ALPHA"])
na = len([r for r in unique if r["tier"] == "NEAR-ALPHA"])
print(f"\nALPHA++: {a_pp} | ALPHA: {a} | NEAR-ALPHA: {na} | Total combos tested: {total}")
