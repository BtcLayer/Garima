"""
Phase 3 — Daily Profit Framework
Answers: "Which strategy combination achieves 2% daily profit consistently?"

How it works:
  1. Loads elite_strategies.csv (run find_elite_strategies.py first)
  2. Models daily P&L distribution per strategy
  3. Simulates portfolio of top N strategies running simultaneously
  4. Optimises SL/TP on top candidates via grid search
  5. Prints actionable deployment plan

Output files:
  daily_profit_report.txt    → human-readable report
  portfolio_candidates.csv   → strategies ready for live execution
"""

import pandas as pd
import numpy as np
import os
import json
from itertools import product

ELITE_CSV       = "elite_strategies.csv"
PORTFOLIO_CSV   = "portfolio_candidates.csv"
REPORT_TXT      = "daily_profit_report.txt"

DAILY_TARGET    = 2.0   # % per day target
CAPITAL         = 10000 # USD
MAX_DRAWDOWN_LIMIT = 25.0  # % — hard limit for live deployment

# ── Optimised SL/TP grid ─────────────────────────────────────────────────────
SL_GRID = [0.010, 0.015, 0.020, 0.025, 0.030]
TP_GRID = [0.030, 0.040, 0.050, 0.060, 0.080, 0.100]
TS_GRID = [0.010, 0.015, 0.020]

def load_elite():
    if not os.path.exists(ELITE_CSV):
        raise FileNotFoundError(
            f"{ELITE_CSV} not found. Run: python find_elite_strategies.py first."
        )
    df = pd.read_csv(ELITE_CSV)
    print(f"Loaded {len(df)} elite strategies from {ELITE_CSV}")
    return df

def parse_params(param_str):
    """Parse 'SL:0.015, TP:0.09, TS:0.015' into dict."""
    params = {"sl": 0.015, "tp": 0.05, "ts": 0.015}
    try:
        for part in str(param_str).split(","):
            part = part.strip()
            if ":" in part:
                k, v = part.split(":")
                key = k.strip().lower()
                if key in ("sl", "tp", "ts"):
                    params[key] = float(v.strip())
    except Exception:
        pass
    return params

def model_daily_returns(row):
    """
    Estimate daily P&L distribution using backtest metrics.
    Returns: (mean_daily_pct, std_daily_pct, sharpe_daily)
    """
    period_days  = max(int(str(row.get("period_days", 365)).split()[0]), 1)
    total_trades = max(row.get("Total_Trades", 1), 1)
    win_rate     = row.get("Win_Rate_Percent", 50) / 100
    avg_trade    = row.get("Avg_Trade_Percent", 0)
    roi          = row.get("roi", 0)
    pf           = row.get("Profit_Factor", 1)
    max_dd       = row.get("Max_Drawdown", 10)

    trades_per_day = total_trades / period_days

    # Mean daily return (conservative: use ROI-based estimate)
    mean_daily = roi / period_days

    # Estimated std: assume avg losing trade is avg_win / pf
    avg_win = avg_trade / win_rate if win_rate > 0 else avg_trade
    avg_loss = abs(avg_win / pf) if pf > 0 else abs(avg_win)
    daily_std = np.sqrt(trades_per_day) * (
        win_rate * avg_win**2 + (1 - win_rate) * avg_loss**2
    ) ** 0.5

    sharpe_daily = mean_daily / daily_std if daily_std > 0 else 0

    return round(mean_daily, 4), round(daily_std, 4), round(sharpe_daily, 4)

def optimal_params_for_target(row, target_daily=2.0):
    """
    Grid search for SL/TP/TS combo that maximises expected daily return
    while keeping risk bounded.
    """
    win_rate   = row.get("Win_Rate_Percent", 50) / 100
    period_days = max(row.get("period_days", 365), 1)
    total_trades = max(row.get("Total_Trades", 1), 1)
    trades_per_day = total_trades / period_days

    best = {"score": -999, "sl": 0.020, "tp": 0.050, "ts": 0.015}

    for sl, tp, ts in product(SL_GRID, TP_GRID, TS_GRID):
        if tp < sl * 1.5:
            continue  # enforce minimum R:R of 1.5

        # Expected per-trade return with these params
        expected_per_trade = win_rate * tp * 100 - (1 - win_rate) * sl * 100
        expected_daily = expected_per_trade * trades_per_day

        # Penalty for high SL (max drawdown risk proxy)
        risk_penalty = sl * 50  # 2% sl → 100% penalty factor

        score = expected_daily - risk_penalty

        if score > best["score"]:
            best = {"score": round(score, 4), "sl": sl, "tp": tp, "ts": ts,
                    "expected_per_trade": round(expected_per_trade, 4),
                    "expected_daily": round(expected_daily, 4)}

    return best

def portfolio_simulation(strategies_df, n=5):
    """
    Simulate running top N strategies simultaneously.
    Assumes independent returns (conservative).
    """
    top = strategies_df.head(n).copy()

    portfolio_daily = top["mean_daily"].sum()      # combined mean
    portfolio_std   = np.sqrt((top["std_daily"]**2).sum())  # quadrature sum
    portfolio_sharpe = portfolio_daily / portfolio_std if portfolio_std > 0 else 0

    return {
        "n_strategies": n,
        "portfolio_daily_pct": round(portfolio_daily, 4),
        "portfolio_std_pct":   round(portfolio_std, 4),
        "portfolio_sharpe":    round(portfolio_sharpe, 4),
        "annualised_pct":      round(portfolio_daily * 365, 2),
        "hits_2pct_target":    portfolio_daily >= DAILY_TARGET,
    }

def generate_report(elite, portfolio_results, report_lines):
    with open(REPORT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"\n✅ Report saved to {REPORT_TXT}")

def main():
    lines = []
    def log(s=""):
        print(s)
        lines.append(s)

    log("=" * 70)
    log("DAILY PROFIT FRAMEWORK — 2% Daily Target Analysis")
    log(f"Capital: ${CAPITAL:,}  |  Target: {DAILY_TARGET}%/day  |  Max Drawdown: {MAX_DRAWDOWN_LIMIT}%")
    log("=" * 70)

    elite = load_elite()

    # ── Model daily returns for every elite strategy ──────────────────────────
    if "period_days" not in elite.columns:
        elite["period_days"] = elite["Time_period_checked"].apply(
            lambda x: int(str(x).split()[0]) if pd.notna(x) else 365
        )

    modelled = []
    for _, row in elite.iterrows():
        mean_d, std_d, sharpe_d = model_daily_returns(row)
        opt = optimal_params_for_target(row)
        modelled.append({
            **row.to_dict(),
            "mean_daily": mean_d,
            "std_daily":  std_d,
            "sharpe_daily": sharpe_d,
            "opt_sl": opt["sl"],
            "opt_tp": opt["tp"],
            "opt_ts": opt["ts"],
            "opt_expected_daily": opt.get("expected_daily", mean_d),
            "opt_expected_per_trade": opt.get("expected_per_trade", 0),
        })

    modelled_df = pd.DataFrame(modelled).sort_values("opt_expected_daily", ascending=False).reset_index(drop=True)
    modelled_df["Portfolio_Rank"] = range(1, len(modelled_df) + 1)

    # Filter to deployable (max drawdown under hard limit)
    deployable = modelled_df[modelled_df["Max_Drawdown"] < MAX_DRAWDOWN_LIMIT].copy()

    log(f"\nElite strategies analysed   : {len(modelled_df)}")
    log(f"Deployable (DrawDown < {MAX_DRAWDOWN_LIMIT}%) : {len(deployable)}")

    # ── Portfolio simulation ──────────────────────────────────────────────────
    log(f"\n{'='*70}")
    log("PORTFOLIO SIMULATION (top N strategies combined)")
    log(f"{'='*70}")

    portfolio_results = {}
    for n in [1, 3, 5, 10]:
        if n > len(deployable):
            continue
        pr = portfolio_simulation(deployable, n)
        portfolio_results[n] = pr
        status = "✅ HITS TARGET" if pr["hits_2pct_target"] else "❌ below target"
        log(f"  Top {n:2d} strategies  →  Daily: {pr['portfolio_daily_pct']:+.3f}%  "
            f"Annualised: {pr['annualised_pct']:+.1f}%  {status}")

    # ── Top 20 deployable strategies ─────────────────────────────────────────
    log(f"\n{'='*70}")
    log("TOP 20 DEPLOYABLE STRATEGIES (optimised for 2%/day)")
    log(f"{'='*70}")
    log(f"{'Rank':<5} {'Strategy':<35} {'Asset':<10} {'TF':<5} "
        f"{'ROI%':>7} {'WR%':>7} {'DD%':>7} {'E.Daily':>9} {'OptSL':>6} {'OptTP':>6}")
    log("-" * 90)

    display = deployable.head(20)
    for _, row in display.iterrows():
        log(f"  {int(row['Portfolio_Rank']):<3}  {str(row.get('Strategy','')):<35} "
            f"{str(row.get('Asset','')):<10} {str(row.get('Timeframe','')):<5} "
            f"{row.get('roi',0):>7.1f}% "
            f"{row.get('Win_Rate_Percent',0):>6.1f}% "
            f"{row.get('Max_Drawdown',0):>6.1f}% "
            f"{row.get('opt_expected_daily',0):>8.3f}% "
            f"{row.get('opt_sl',0)*100:>5.1f}% "
            f"{row.get('opt_tp',0)*100:>5.1f}%")

    # ── Recommended deployment plan ───────────────────────────────────────────
    log(f"\n{'='*70}")
    log("DEPLOYMENT PLAN — RECOMMENDED PARAMETER SETTINGS")
    log(f"{'='*70}")

    top5 = deployable.head(5)
    capital_per_strategy = CAPITAL / max(len(top5), 1)

    for i, (_, row) in enumerate(top5.iterrows(), 1):
        log(f"\n  Strategy {i}: {row.get('Strategy','')} — {row.get('Asset','')} {row.get('Timeframe','')}")
        log(f"    Current params  : {row.get('Parameters','N/A')}")
        log(f"    Optimised SL    : {row.get('opt_sl',0)*100:.1f}%")
        log(f"    Optimised TP    : {row.get('opt_tp',0)*100:.1f}%")
        log(f"    Optimised TS    : {row.get('opt_ts',0)*100:.1f}%")
        log(f"    Expected/trade  : {row.get('opt_expected_per_trade',0):+.3f}%")
        log(f"    Expected/day    : {row.get('opt_expected_daily',0):+.4f}%")
        log(f"    Allocated capital: ${capital_per_strategy:,.0f}")

    # ── Risk warnings ─────────────────────────────────────────────────────────
    log(f"\n{'='*70}")
    log("RISK NOTES")
    log(f"{'='*70}")
    log("  1. Daily returns are estimates from backtest averages — live results vary.")
    log("  2. Strategies optimised on historical data may overfit — validate on fresh data.")
    log("  3. Max Drawdown shown is backtest max — live DD can exceed this in tail events.")
    log("  4. 2% daily = ~600% annualised — realistic only with low-drawdown high-PF strategies.")
    log("  5. Start with paper trading before committing real capital.")
    log(f"  6. Hard stop: exit if total portfolio drawdown exceeds {MAX_DRAWDOWN_LIMIT}%.")

    # ── Save portfolio CSV ────────────────────────────────────────────────────
    save_cols = [c for c in ["Portfolio_Rank", "Strategy", "Asset", "Timeframe",
                              "roi", "Win_Rate_Percent", "Profit_Factor", "Max_Drawdown",
                              "Total_Trades", "mean_daily", "opt_expected_daily",
                              "opt_sl", "opt_tp", "opt_ts", "Parameters"] if c in deployable.columns]
    deployable[save_cols].to_csv(PORTFOLIO_CSV, index=False)
    log(f"\n✅ Portfolio candidates saved to {PORTFOLIO_CSV}")

    generate_report(elite, portfolio_results, lines)

if __name__ == "__main__":
    main()
