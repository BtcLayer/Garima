#!/usr/bin/env python3
"""Standalone auto-optimization for 4h timeframe. Run directly on server via SSH."""
import sys, os, json, random, time
import numpy as np
import pandas as pd
from datetime import datetime as _dt
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from run_strategies_batch import (
    load_data, calculate_indicators, apply_strategy,
    run_backtest as _batch_run_backtest, DATA_FILES, INITIAL_CAPITAL, FEE,
)
from strategies import get_all_strategies

# ── Config ───────────────────────────────────────────────────────────
TIMEFRAME = "15m"
_MAX_PHASE1 = 50
_OPT_TRIALS = 20
_SL_CANDIDATES = [0.010, 0.015, 0.020, 0.025, 0.030, 0.040, 0.050]
_TP_CANDIDATES = [0.020, 0.030, 0.040, 0.050, 0.060, 0.080, 0.100, 0.150]
_TS_CANDIDATES = [0.005, 0.010, 0.015, 0.020, 0.025, 0.030]

# Build symbol list for 4h
symbols = [k for k in DATA_FILES if k.endswith(f"_{TIMEFRAME}")]
print(f"Assets: {len(symbols)} — {symbols}")


def _compute_score(roi, wr, pf, dd):
    score = roi * 0.4 + wr * 0.3 + pf * 10 + max(0, 50 - dd) * 0.2
    return round(score, 2)


def _grade_performance(roi_pct, win_rate, profit_factor):
    if roi_pct >= 100 and win_rate >= 0.55 and profit_factor >= 2.0:
        return "A+"
    elif roi_pct >= 50 and win_rate >= 0.50 and profit_factor >= 1.5:
        return "A"
    elif roi_pct >= 20 and win_rate >= 0.45 and profit_factor >= 1.2:
        return "B+"
    elif roi_pct >= 10:
        return "B"
    elif roi_pct >= 0:
        return "C"
    else:
        return "D"


def _deployment_status(grade, total_trades, max_dd):
    if grade in ("A+", "A") and total_trades >= 20 and max_dd < 50:
        return "Ready"
    elif grade in ("B+", "B") and total_trades >= 10:
        return "Active"
    else:
        return "Monitor"


# Load elite ranking
_elite_path = os.path.join(_ROOT, "storage", "elite_ranking.json")
ELITE_NAMES = []
if os.path.exists(_elite_path):
    try:
        with open(_elite_path) as f:
            ELITE_NAMES = json.load(f).get("ranking", [])
    except Exception:
        pass


def save_elite_ranking(names, results):
    data = {"updated": _dt.now().isoformat(), "ranking": names, "results": results}
    os.makedirs(os.path.dirname(_elite_path), exist_ok=True)
    with open(_elite_path, "w") as f:
        json.dump(data, f, indent=2)


# ── PHASE 1: Run strategies on each asset ────────────────────────────
print(f"\n{'='*60}")
print(f"PHASE 1: Testing strategies on {len(symbols)} assets...")
print(f"{'='*60}\n")

all_strats = get_all_strategies()
if ELITE_NAMES and len(ELITE_NAMES) >= _MAX_PHASE1:
    elite_set = set(ELITE_NAMES[:_MAX_PHASE1])
    elite_strats = [s for s in all_strats if s["name"] in elite_set]
    if len(elite_strats) < _MAX_PHASE1:
        used = {s["name"] for s in elite_strats}
        for s in all_strats:
            if s["name"] not in used:
                elite_strats.append(s)
                used.add(s["name"])
            if len(elite_strats) >= _MAX_PHASE1:
                break
else:
    elite_strats = all_strats[:_MAX_PHASE1]

print(f"Testing {len(elite_strats)} strategies per asset.\n")

top10_per_asset = {}
all_phase1 = []

for si, symbol in enumerate(sorted(symbols), 1):
    _asset = symbol.rsplit("_", 1)[0] if "_" in symbol else symbol
    t0 = time.time()

    df = load_data(symbol)
    if df is None:
        print(f"  [{si}/{len(symbols)}] {_asset}: NO DATA — skipped")
        continue
    df = calculate_indicators(df)

    if "timestamp" in df.columns:
        time_start = str(df["timestamp"].iloc[0])[:10]
        time_end = str(df["timestamp"].iloc[-1])[:10]
    else:
        time_start, time_end = "unknown", "unknown"
    try:
        _years = max((_dt.fromisoformat(time_end) - _dt.fromisoformat(time_start)).days / 365.25, 0.01)
    except Exception:
        _years = 1.0

    asset_results = []
    for strat in elite_strats:
        try:
            df_copy = apply_strategy(df.copy(), strat["strategies"], strat.get("min_agreement", 1))
            final_cap, trades = _batch_run_backtest(df_copy, strat["stop_loss"], strat["take_profit"], strat["trailing_stop"])
            if len(trades) >= 5:
                wins = [t for t in trades if t["pnl"] > 0]
                roi = (final_cap - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
                roi_a = ((final_cap / INITIAL_CAPITAL) ** (1 / _years) - 1) * 100 if _years > 0 else 0
                wr = len(wins) / len(trades) * 100
                total_w = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                total_l = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                pf = total_w / total_l if total_l > 0 else 0
                score = _compute_score(roi, wr, pf, 0)
                asset_results.append({
                    "name": strat["name"], "asset": _asset,
                    "roi_annum": round(roi_a, 2), "roi": round(roi, 2),
                    "win_rate": round(wr, 2), "pf": round(pf, 2),
                    "score": round(score, 2), "trades": len(trades),
                })
        except Exception:
            pass

    asset_results.sort(key=lambda x: x["score"], reverse=True)
    top10 = asset_results[:10]
    top10_per_asset[_asset] = top10
    all_phase1.extend(asset_results)

    elapsed = time.time() - t0
    best = top10[0] if top10 else None
    best_str = f"best={best['name']}({best['roi_annum']}%/yr)" if best else "no results"
    print(f"  [{si}/{len(symbols)}] {_asset}: {len(asset_results)} results in {elapsed:.0f}s — {best_str}")

if not all_phase1:
    print("Phase 1 produced no results. Exiting.")
    sys.exit(1)


# ── PHASE 2: Find universal winners ──────────────────────────────────
print(f"\n{'='*60}")
print("PHASE 2: Finding universal winners...")
print(f"{'='*60}\n")

strat_counter = Counter()
strat_scores = {}
for asset, top10 in top10_per_asset.items():
    for r in top10:
        strat_counter[r["name"]] += 1
        strat_scores.setdefault(r["name"], []).append(r["score"])

universal = []
for name, count in strat_counter.most_common():
    if count >= 2:
        avg_score = sum(strat_scores[name]) / len(strat_scores[name])
        universal.append({"name": name, "assets": count, "avg_score": round(avg_score, 2)})

if not universal:
    for name in strat_scores:
        avg_score = sum(strat_scores[name]) / len(strat_scores[name])
        universal.append({"name": name, "assets": len(strat_scores[name]), "avg_score": round(avg_score, 2)})

universal.sort(key=lambda x: x["avg_score"], reverse=True)
universal = universal[:20]

for i, u in enumerate(universal, 1):
    print(f"  {i}. {u['name']} — {u['assets']} assets, avg_score={u['avg_score']}")


# ── PHASE 3: Optimize SL/TP/TS ──────────────────────────────────────
print(f"\n{'='*60}")
print("PHASE 3: Optimizing SL/TP/TS for universal winners...")
print(f"{'='*60}\n")

universal_names = {u["name"] for u in universal}
universal_strats = [s for s in elite_strats if s["name"] in universal_names]
optimized_results = []

for idx, strat in enumerate(universal_strats, 1):
    t0 = time.time()
    best_avg_score = -999
    best_params = {"sl": strat["stop_loss"], "tp": strat["take_profit"], "ts": strat["trailing_stop"]}

    for _ in range(_OPT_TRIALS):
        sl = random.choice(_SL_CANDIDATES)
        tp = random.choice(_TP_CANDIDATES)
        ts = random.choice(_TS_CANDIDATES)
        if tp < sl * 1.5:
            continue

        trial_scores = []
        for symbol in symbols:
            df = load_data(symbol)
            if df is None:
                continue
            df = calculate_indicators(df)
            try:
                df_copy = apply_strategy(df.copy(), strat["strategies"], strat.get("min_agreement", 1))
                final_cap, trades = _batch_run_backtest(df_copy, sl, tp, ts)
                if len(trades) >= 5:
                    wins = [t for t in trades if t["pnl"] > 0]
                    roi = (final_cap - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
                    wr = len(wins) / len(trades) * 100
                    total_w = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                    total_l = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                    pf = total_w / total_l if total_l > 0 else 0
                    trial_scores.append(_compute_score(roi, wr, pf, 0))
            except Exception:
                pass

        if trial_scores:
            avg = sum(trial_scores) / len(trial_scores)
            if avg > best_avg_score:
                best_avg_score = avg
                best_params = {"sl": sl, "tp": tp, "ts": ts}

    optimized_results.append({
        "name": strat["name"],
        "score": round(best_avg_score, 2),
        "sl": best_params["sl"],
        "tp": best_params["tp"],
        "ts": best_params["ts"],
    })
    elapsed = time.time() - t0
    print(f"  [{idx}/{len(universal_strats)}] {strat['name']}: score={best_avg_score:.1f} SL={best_params['sl']*100:.1f}% TP={best_params['tp']*100:.1f}% TS={best_params['ts']*100:.1f}% ({elapsed:.0f}s)")

optimized_results.sort(key=lambda x: x["score"], reverse=True)


# ── PHASE 4: Final validation & save ─────────────────────────────────
print(f"\n{'='*60}")
print("PHASE 4: Final validation with optimized params...")
print(f"{'='*60}\n")

# Update elite ranking
new_order = [r["name"] for r in optimized_results]
remaining = [n for n in ELITE_NAMES if n not in new_order]
ELITE_NAMES = new_order + remaining
save_elite_ranking(ELITE_NAMES, optimized_results)

final_results = []
for si, symbol in enumerate(sorted(symbols), 1):
    _asset = symbol.rsplit("_", 1)[0] if "_" in symbol else symbol
    df = load_data(symbol)
    if df is None:
        continue
    df = calculate_indicators(df)

    if "timestamp" in df.columns:
        time_start = str(df["timestamp"].iloc[0])[:10]
        time_end = str(df["timestamp"].iloc[-1])[:10]
    else:
        time_start, time_end = "unknown", "unknown"
    try:
        _years = max((_dt.fromisoformat(time_end) - _dt.fromisoformat(time_start)).days / 365.25, 0.01)
    except Exception:
        _years = 1.0

    for opt_r in optimized_results:
        strat = next((s for s in elite_strats if s["name"] == opt_r["name"]), None)
        if not strat:
            continue
        try:
            df_copy = apply_strategy(df.copy(), strat["strategies"], strat.get("min_agreement", 1))
            final_cap, trades = _batch_run_backtest(df_copy, opt_r["sl"], opt_r["tp"], opt_r["ts"])
            if len(trades) >= 5:
                wins = [t for t in trades if t["pnl"] > 0]
                losses_list = [t for t in trades if t["pnl"] <= 0]
                roi = (final_cap - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
                roi_a = ((final_cap / INITIAL_CAPITAL) ** (1 / _years) - 1) * 100 if _years > 0 else 0
                wr = len(wins) / len(trades) * 100
                net = final_cap - INITIAL_CAPITAL
                total_w = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                total_l = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                pf = total_w / total_l if total_l > 0 else 0
                returns = [t.get("return_pct", t["pnl"] / INITIAL_CAPITAL * 100) for t in trades]
                avg_trade = sum(returns) / len(returns) if returns else 0
                std = np.std(returns) if len(returns) > 1 else 1
                sharpe = (avg_trade / std) * np.sqrt(len(trades)) if std > 0 else 0

                equity = INITIAL_CAPITAL
                peak = equity
                gross_dd = 0
                min_capital = INITIAL_CAPITAL
                for t in trades:
                    equity += t["pnl"]
                    peak = max(peak, equity)
                    dd = (peak - equity) / peak * 100
                    gross_dd = max(gross_dd, dd)
                    min_capital = min(min_capital, equity)
                net_dd = max(0, (INITIAL_CAPITAL - min_capital) / INITIAL_CAPITAL * 100)

                grade = _grade_performance(roi, wr / 100, pf)
                deploy = _deployment_status(grade, len(trades), gross_dd)
                score = _compute_score(roi, wr, pf, gross_dd)

                final_results.append({
                    "Rank": 0,
                    "name": opt_r["name"],
                    "Strategy": ", ".join(strat["strategies"]),
                    "Asset": _asset,
                    "Timeframe": TIMEFRAME,
                    "Initial_Capital_USD": INITIAL_CAPITAL,
                    "Final_Capital_USD": round(final_cap, 2),
                    "Net_Profit_USD": round(net, 2),
                    "ROI_per_annum": round(roi_a, 2),
                    "ROI_Percent": round(roi, 2),
                    "Total_Trades": len(trades),
                    "Winning_Trades": len(wins),
                    "Losing_Trades": len(losses_list),
                    "Win_Rate_Percent": round(wr, 2),
                    "Profit_Factor": round(pf, 2),
                    "Sharpe_Ratio": round(sharpe, 2),
                    "Avg_Trade_Percent": round(avg_trade, 4),
                    "Gross_DD_Percent": round(gross_dd, 2),
                    "Net_DD_Percent": round(net_dd, 2),
                    "Capital_At_Net_DD": round(INITIAL_CAPITAL * (1 - net_dd / 100), 2),
                    "Performance_Grade": grade,
                    "Deployment_Status": deploy,
                    "Score": round(score, 2),
                    "Data_Source": "Binance Spot",
                    "Time_Period": f"{time_start} to {time_end}",
                    "Time_Start": time_start,
                    "Time_End": time_end,
                    "Fees_Exchange": f"{FEE*100}%",
                    "Candle_Period": TIMEFRAME,
                    "Parameters": f"SL={opt_r['sl']*100:.1f}%, TP={opt_r['tp']*100:.1f}%, TS={opt_r['ts']*100:.1f}%",
                })
        except Exception:
            pass

    print(f"  [{si}/{len(symbols)}] {_asset}: done")

if final_results:
    final_results.sort(key=lambda x: x["ROI_per_annum"], reverse=True)
    for i, r in enumerate(final_results, 1):
        r["Rank"] = i

    # Save CSVs
    csv1 = os.path.join(_ROOT, f"auto_results_{TIMEFRAME}.csv")
    csv2 = os.path.join(_ROOT, "auto_optimization_results.csv")
    pd.DataFrame(final_results).to_csv(csv1, index=False)
    pd.DataFrame(final_results).to_csv(csv2, index=False)

    print(f"\n{'='*60}")
    print(f"DONE — {len(final_results)} results saved to:")
    print(f"  {csv1}")
    print(f"  {csv2}")
    print(f"{'='*60}\n")

    # Print top 10
    print("TOP 10 by ROI%/yr:")
    print(f"{'#':<3} {'Name':<22} {'Asset':<10} {'ROI%/yr':<10} {'Trades':<7} {'Win%':<7} {'GDD%':<7} {'NDD%':<7} {'Cap@NDD'}")
    print("-" * 85)
    for i, r in enumerate(final_results[:10], 1):
        cap_ndd = r.get("Capital_At_Net_DD", INITIAL_CAPITAL)
        print(f"{i:<3} {r['name'][:22]:<22} {r['Asset']:<10} {r['ROI_per_annum']:<10.2f} {r['Total_Trades']:<7} {r['Win_Rate_Percent']:<7.1f} {r['Gross_DD_Percent']:<7.1f} {r['Net_DD_Percent']:<7.1f} ${cap_ndd}")
else:
    print("No results produced!")
    sys.exit(1)
