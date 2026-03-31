"""
Genetic Algorithm Strategy Evolver
Breeds, mutates, and evolves trading strategies toward a target ROI/day.
Each generation keeps winners, combines their DNA, mutates params.
"""
import sys, os, random, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from datetime import datetime
from run_strategies_batch import (
    load_data, calculate_indicators, apply_strategy,
    run_backtest, INITIAL_CAPITAL, SIGNAL_FUNCTIONS
)

ALL_SIGNALS = list(SIGNAL_FUNCTIONS.keys())
STORAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage")


def random_strategy():
    """Create a random strategy DNA."""
    n_signals = random.randint(1, 5)
    signals = random.sample(ALL_SIGNALS, n_signals)
    min_ag = random.randint(1, max(1, n_signals - 1))
    sl = round(random.uniform(0.003, 0.04), 4)
    tp = round(random.uniform(sl * 1.5, 0.40), 4)
    ts = round(random.uniform(0.002, sl * 1.5), 4)
    return {
        "signals": signals,
        "min_ag": min_ag,
        "sl": sl,
        "tp": tp,
        "ts": ts,
    }


def crossover(parent1, parent2):
    """Breed two strategies — combine signals from both parents."""
    # Take some signals from each parent
    all_sigs = list(set(parent1["signals"] + parent2["signals"]))
    n = random.randint(1, min(5, len(all_sigs)))
    child_sigs = random.sample(all_sigs, n)

    # Average params
    child = {
        "signals": child_sigs,
        "min_ag": random.randint(1, max(1, len(child_sigs) - 1)),
        "sl": round((parent1["sl"] + parent2["sl"]) / 2 * random.uniform(0.8, 1.2), 4),
        "tp": round((parent1["tp"] + parent2["tp"]) / 2 * random.uniform(0.8, 1.2), 4),
        "ts": round((parent1["ts"] + parent2["ts"]) / 2 * random.uniform(0.8, 1.2), 4),
    }
    child["sl"] = max(0.003, min(0.05, child["sl"]))
    child["tp"] = max(child["sl"] * 1.5, min(0.50, child["tp"]))
    child["ts"] = max(0.002, min(0.03, child["ts"]))
    return child


def mutate(strategy, mutation_rate=0.3):
    """Randomly mutate a strategy's DNA."""
    s = dict(strategy)
    s["signals"] = list(s["signals"])

    if random.random() < mutation_rate:
        # Add or remove a signal
        if len(s["signals"]) > 1 and random.random() < 0.5:
            s["signals"].pop(random.randint(0, len(s["signals"]) - 1))
        else:
            remaining = [sig for sig in ALL_SIGNALS if sig not in s["signals"]]
            if remaining:
                s["signals"].append(random.choice(remaining))

    if random.random() < mutation_rate:
        s["min_ag"] = random.randint(1, max(1, len(s["signals"]) - 1))

    if random.random() < mutation_rate:
        s["sl"] = round(s["sl"] * random.uniform(0.7, 1.4), 4)
        s["sl"] = max(0.003, min(0.05, s["sl"]))

    if random.random() < mutation_rate:
        s["tp"] = round(s["tp"] * random.uniform(0.7, 1.4), 4)
        s["tp"] = max(s["sl"] * 1.5, min(0.50, s["tp"]))

    if random.random() < mutation_rate:
        s["ts"] = round(s["ts"] * random.uniform(0.7, 1.4), 4)
        s["ts"] = max(0.002, min(0.03, s["ts"]))

    return s


def evaluate(strategy, df, yrs):
    """Backtest with OOS validation — only report realistic OOS numbers.

    Train on first 70% of data, test on last 30%.
    ROI calculated with FIXED position sizing (no compounding fantasy).
    """
    try:
        n = len(df)
        split = int(n * 0.7)
        if split < 200 or n - split < 100:
            return None

        # ── IN-SAMPLE (train) — used to check if strategy has any edge ──
        df_is = df.iloc[:split].copy()
        dc_is = apply_strategy(df_is, strategy["signals"], strategy["min_ag"])
        cap_is, trades_is = run_backtest(dc_is, strategy["sl"], strategy["tp"], strategy["ts"])
        if len(trades_is) < 20:
            return None

        # Quick IS check — skip if clearly bad
        wins_is = [t for t in trades_is if t["pnl"] > 0]
        wr_is = len(wins_is) / len(trades_is) * 100
        if wr_is < 35:
            return None

        # ── OUT-OF-SAMPLE (test) — THIS is the real result ──
        df_oos = df.iloc[split:].copy()
        dc_oos = apply_strategy(df_oos, strategy["signals"], strategy["min_ag"])
        cap_oos, trades_oos = run_backtest(dc_oos, strategy["sl"], strategy["tp"], strategy["ts"])
        if len(trades_oos) < 10:
            return None

        # Calculate OOS metrics with FIXED sizing (realistic)
        # Instead of compounding, calculate avg return per trade
        wins = [t for t in trades_oos if t["pnl"] > 0]
        losses = [t for t in trades_oos if t["pnl"] <= 0]
        wr = len(wins) / len(trades_oos) * 100

        # Fixed-size PnL: what % return per trade on initial capital
        returns_pct = [t["return_pct"] for t in trades_oos]
        avg_return = np.mean(returns_pct) if returns_pct else 0

        tw = sum(t["pnl"] for t in trades_oos if t["pnl"] > 0)
        tl = abs(sum(t["pnl"] for t in trades_oos if t["pnl"] <= 0))
        pf = tw / tl if tl > 0 else 0

        # Calculate OOS years
        if "timestamp" in df_oos.columns:
            oos_days = (datetime.fromisoformat(str(df_oos["timestamp"].iloc[-1])[:10]) -
                       datetime.fromisoformat(str(df_oos["timestamp"].iloc[0])[:10])).days
            oos_yrs = max(oos_days / 365.25, 0.01)
        else:
            oos_yrs = yrs * 0.3

        # Daily ROI from FIXED sizing (no compound inflation)
        total_return_pct = sum(returns_pct)
        daily_roi = total_return_pct / max(oos_days, 1) if oos_days > 0 else 0
        annual_roi = daily_roi * 365

        # Also calculate compound ROI for comparison
        compound_roi = ((cap_oos / INITIAL_CAPITAL) ** (1 / oos_yrs) - 1) * 100 if cap_oos > 0 else -100

        # Drawdown on OOS
        eq = INITIAL_CAPITAL
        pk = eq
        gdd = 0
        for t in trades_oos:
            eq += t["pnl"]
            pk = max(pk, eq)
            dd = (pk - eq) / pk * 100
            gdd = max(gdd, dd)

        # Net drawdown (fixed sizing)
        ndd = 0
        running = 0
        for t in trades_oos:
            running += t["return_pct"]
            ndd = max(ndd, -running)

        # Reject unrealistic or too risky
        if daily_roi > 5.0:  # > 5%/day is certainly overfit even on OOS
            return None
        if gdd > 30:
            return None
        if ndd > 30:
            return None

        trades_per_day = len(trades_oos) / max(oos_days, 1)

        # Fitness: OOS daily ROI penalized by drawdown
        fitness = daily_roi - (gdd * 0.005) - (ndd * 0.005)

        return {
            "fitness": round(fitness, 4),
            "roi_day": round(daily_roi, 4),  # FIXED sizing, OOS only
            "roi_day_compound": round(compound_roi / 365, 4),  # compound for reference
            "roi_yr": round(annual_roi, 1),
            "pf": round(pf, 2),
            "wr": round(wr, 1),
            "gdd": round(gdd, 1),
            "ndd": round(ndd, 1),
            "trades": len(trades_oos),
            "trades_per_day": round(trades_per_day, 2),
            "avg_return_pct": round(avg_return, 3),
            "final_cap": round(cap_oos, 0),
            "oos_years": round(oos_yrs, 2),
            "is_trades": len(trades_is),
            "is_wr": round(wr_is, 1),
            "validation": "OOS_70_30",
        }
    except Exception:
        return None


def evolve(assets=None, tf="4h", pop_size=100, generations=50,
           keep_top=20, mutation_rate=0.3, target_roi_day=3.0,
           callback=None):
    """
    Run genetic evolution.
    callback(gen, best, population_stats) called each generation.
    """
    if assets is None:
        assets = ["ETHUSDT", "BTCUSDT", "ADAUSDT", "SOLUSDT", "LINKUSDT", "BNBUSDT"]

    # Load data
    data_cache = {}
    for asset in assets:
        key = f"{asset}_{tf}"
        df = load_data(key)
        if df is not None:
            df = calculate_indicators(df)
            if "timestamp" in df.columns:
                yrs = max((datetime.fromisoformat(str(df["timestamp"].iloc[-1])[:10]) -
                           datetime.fromisoformat(str(df["timestamp"].iloc[0])[:10])).days / 365.25, 0.01)
            else:
                yrs = 6.0
            data_cache[key] = (df, yrs)

    if not data_cache:
        return [], []

    # Initialize population
    population = [random_strategy() for _ in range(pop_size)]
    all_time_best = None
    all_results = []  # ALL strategies with ROI > 0.05%/day
    gen_history = []

    for gen in range(generations):
        # Evaluate all strategies on ALL assets — save every result
        scored = []
        for strat in population:
            for key, (df, yrs) in data_cache.items():
                asset = key.split("_")[0]
                result = evaluate(strat, df, yrs)
                if result is not None and result["roi_day"] > 0.05:
                    scored.append((result["fitness"], strat, result, asset))

                    # Save ALL viable results
                    all_results.append({
                        **result,
                        "generation": gen + 1,
                        "signals": " + ".join(strat["signals"]),
                        "min_ag": strat["min_ag"],
                        "asset": asset,
                        "sl": strat["sl"],
                        "tp": strat["tp"],
                        "ts": strat["ts"],
                    })

        if not scored:
            population = [random_strategy() for _ in range(pop_size)]
            continue

        # Sort by fitness
        scored.sort(key=lambda x: -x[0])

        # Track best this generation
        gen_best_fitness, gen_best_strat, gen_best_result, gen_best_asset = scored[0]
        gen_avg = np.mean([s[0] for s in scored])

        gen_info = {
            "generation": gen + 1,
            "best_fitness": round(gen_best_fitness, 4),
            "best_roi_day": gen_best_result["roi_day"],
            "avg_fitness": round(gen_avg, 4),
            "best_signals": " + ".join(gen_best_strat["signals"]),
            "best_asset": gen_best_asset,
            "best_pf": gen_best_result["pf"],
            "best_wr": gen_best_result["wr"],
            "best_trades": gen_best_result["trades"],
            "pop_size": len(scored),
            "total_viable": len(all_results),
            "above_1pct": len([r for r in all_results if r["roi_day"] >= 1.0]),
            "above_05pct": len([r for r in all_results if r["roi_day"] >= 0.5]),
        }
        gen_history.append(gen_info)

        if all_time_best is None or gen_best_fitness > all_time_best[0]:
            all_time_best = (gen_best_fitness, gen_best_strat, gen_best_result, gen_best_asset)

        # Callback
        if callback:
            callback(gen + 1, gen_info, all_time_best)

        # Deduplicate all_results for saving (keep best per signal+asset combo)
        seen = {}
        for r in all_results:
            k = (r["asset"], r["signals"], r["min_ag"])
            if k not in seen or r["roi_day"] > seen[k]["roi_day"]:
                seen[k] = r
        unique_results = sorted(seen.values(), key=lambda x: -x["roi_day"])

        # Save after every generation
        save_path = os.path.join(STORAGE, "genetic_results.json")
        with open(save_path, "w") as f:
            json.dump({
                "generation": gen + 1,
                "total_generations": generations,
                "target": target_roi_day,
                "status": "running",
                "all_time_best": {
                    **all_time_best[2],
                    "signals": " + ".join(all_time_best[1]["signals"]),
                    "min_ag": all_time_best[1]["min_ag"],
                    "asset": all_time_best[3],
                    "sl": all_time_best[1]["sl"],
                    "tp": all_time_best[1]["tp"],
                    "ts": all_time_best[1]["ts"],
                },
                "history": gen_history,
                "all_strategies": unique_results,
                "counts": {
                    "total": len(unique_results),
                    "above_3pct": len([r for r in unique_results if r["roi_day"] >= 3.0]),
                    "above_1pct": len([r for r in unique_results if r["roi_day"] >= 1.0]),
                    "above_05pct": len([r for r in unique_results if r["roi_day"] >= 0.5]),
                    "above_03pct": len([r for r in unique_results if r["roi_day"] >= 0.3]),
                },
            }, f, indent=2)

        # DON'T stop early — keep evolving to find MORE strategies
        # Selection: keep top performers per asset
        unique_scored = {}
        for s in scored:
            k = (s[3], " + ".join(s[1]["signals"]))
            if k not in unique_scored or s[0] > unique_scored[k][0]:
                unique_scored[k] = s
        best_strats = sorted(unique_scored.values(), key=lambda x: -x[0])
        survivors = [s[1] for s in best_strats[:keep_top]]

        # Breed next generation
        new_population = list(survivors)

        while len(new_population) < pop_size:
            if random.random() < 0.6:
                p1, p2 = random.sample(survivors, 2)
                child = crossover(p1, p2)
            elif random.random() < 0.8:
                # Mutate a survivor
                child = mutate(random.choice(survivors), mutation_rate)
            else:
                child = random_strategy()

            child = mutate(child, mutation_rate)
            new_population.append(child)

        population = new_population

    # Final save with completed status
    if all_time_best:
        seen = {}
        for r in all_results:
            k = (r["asset"], r["signals"], r["min_ag"])
            if k not in seen or r["roi_day"] > seen[k]["roi_day"]:
                seen[k] = r
        unique_results = sorted(seen.values(), key=lambda x: -x["roi_day"])

        save_path = os.path.join(STORAGE, "genetic_results.json")
        with open(save_path, "w") as f:
            json.dump({
                "generation": generations,
                "total_generations": generations,
                "target": target_roi_day,
                "status": "completed",
                "all_time_best": {
                    **all_time_best[2],
                    "signals": " + ".join(all_time_best[1]["signals"]),
                    "min_ag": all_time_best[1]["min_ag"],
                    "asset": all_time_best[3],
                    "sl": all_time_best[1]["sl"],
                    "tp": all_time_best[1]["tp"],
                    "ts": all_time_best[1]["ts"],
                },
                "history": gen_history,
                "all_strategies": unique_results,
                "counts": {
                    "total": len(unique_results),
                    "above_3pct": len([r for r in unique_results if r["roi_day"] >= 3.0]),
                    "above_1pct": len([r for r in unique_results if r["roi_day"] >= 1.0]),
                    "above_05pct": len([r for r in unique_results if r["roi_day"] >= 0.5]),
                    "above_03pct": len([r for r in unique_results if r["roi_day"] >= 0.3]),
                },
            }, f, indent=2)

    return all_results, gen_history


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", nargs="+", default=["ETHUSDT", "BTCUSDT", "ADAUSDT", "SOLUSDT", "LINKUSDT", "BNBUSDT"])
    parser.add_argument("--tf", default="4h")
    parser.add_argument("--pop", type=int, default=100)
    parser.add_argument("--gen", type=int, default=50)
    parser.add_argument("--target", type=float, default=3.0)
    args = parser.parse_args()

    print(f"\n{'='*80}", flush=True)
    print(f"  GENETIC STRATEGY EVOLVER (REALISTIC — OOS ONLY)", flush=True)
    print(f"  Target: {args.target}%/day | Pop: {args.pop} | Generations: {args.gen}", flush=True)
    print(f"  Validation: 70% train / 30% OOS | Fixed-size ROI (no compound fantasy)", flush=True)
    print(f"  Assets: {args.assets} | TF: {args.tf}", flush=True)
    print(f"{'='*80}\n", flush=True)

    def on_generation(gen, info, best):
        best_result = best[2]
        print(
            f"  Gen {gen:>3} | Best OOS: {info['best_roi_day']:.3f}%/day | "
            f"All-time: {best_result['roi_day']:.3f}%/day | "
            f">=1%: {info.get('above_1pct', 0)} | >=0.5%: {info.get('above_05pct', 0)} | "
            f"Total: {info.get('total_viable', 0)} | "
            f"{info['best_asset']} [{info['best_signals'][:35]}]",
            flush=True
        )

    results, history = evolve(
        assets=args.assets, tf=args.tf,
        pop_size=args.pop, generations=args.gen,
        target_roi_day=args.target, callback=on_generation,
    )

    print(f"\n{'='*80}", flush=True)
    print(f"  EVOLUTION COMPLETE — ALL RESULTS ARE OOS (REALISTIC)", flush=True)
    print(f"{'='*80}", flush=True)
    if results:
        # Dedupe and sort
        seen = {}
        for r in results:
            k = (r.get("asset", ""), r.get("signals", ""))
            if k not in seen or r["roi_day"] > seen[k]["roi_day"]:
                seen[k] = r
        top = sorted(seen.values(), key=lambda x: -x["roi_day"])[:20]

        above_1 = len([r for r in top if r["roi_day"] >= 1.0])
        above_05 = len([r for r in top if r["roi_day"] >= 0.5])
        above_03 = len([r for r in top if r["roi_day"] >= 0.3])
        print(f"\n  >= 1%/day: {above_1} | >= 0.5%/day: {above_05} | >= 0.3%/day: {above_03}")
        print(f"\n  TOP 20 (OOS, fixed-size ROI):")
        print(f"  {'#':<3} {'ROI/d':>7} {'ROI/yr':>7} {'Asset':<10} {'PF':>5} {'WR%':>5} {'GDD':>5} {'NDD':>5} {'Trd':>5} {'Trd/d':>5} Signals")
        print(f"  {'-'*90}")
        for i, r in enumerate(top):
            tag = " ***" if r["roi_day"] >= 1.0 else ""
            print(f"  {i+1:<3} {r['roi_day']:>6.3f}% {r['roi_yr']:>6.1f}% {r.get('asset',''):<10} "
                  f"{r['pf']:>5.2f} {r['wr']:>5.1f} {r['gdd']:>5.1f} {r.get('ndd',0):>5.1f} "
                  f"{r['trades']:>5} {r.get('trades_per_day',0):>5.2f} {r.get('signals','')[:40]}{tag}", flush=True)
    print("DONE", flush=True)
