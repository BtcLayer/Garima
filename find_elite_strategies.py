"""
Phase 2 — Elite Strategy Shortlist
Filters all results using strict quant criteria and outputs:
  - elite_strategies.csv      → top strategies meeting all thresholds
  - elite_strategies.json     → same, JSON format for bot use
  - daily_profit_model.csv    → expected daily return per combo

Criteria:
  ROI          > 50%       (strong annual return)
  Win Rate     > 25%       (at least 1 in 4 trades wins)
  Profit Factor> 1.5       (gross wins 1.5x gross losses)
  Max Drawdown < 30%       (risk control)
  Total Trades >= 20       (statistically meaningful)

Daily profit model:
  Trades per day = Total_Trades / period_days
  Expected daily = Avg_Trade_Percent * Win_Rate * Trades_per_day / 100
"""

import pandas as pd
import numpy as np
import json
import glob
import os

# ── Configuration ─────────────────────────────────────────────────────────────
MIN_ROI          = 50.0    # %
MIN_WIN_RATE     = 25.0    # %
MIN_PROFIT_FACTOR= 1.5
MAX_DRAWDOWN     = 30.0    # %
MIN_TRADES       = 20
DAILY_TARGET_PCT = 2.0     # % — strategies are flagged if they can hit this

OUTPUT_ELITE_CSV  = "elite_strategies.csv"
OUTPUT_ELITE_JSON = "elite_strategies.json"
OUTPUT_DAILY_CSV  = "daily_profit_model.csv"

# ── Load all result CSVs ───────────────────────────────────────────────────────
def load_all_results():
    csv_files = glob.glob("*_all_results.csv")
    if not csv_files:
        raise FileNotFoundError("No *_all_results.csv files found. Run the strategy runners first.")

    frames = []
    for f in csv_files:
        try:
            df = pd.read_csv(f)
            df["source_file"] = os.path.basename(f)
            frames.append(df)
            print(f"  Loaded {f}: {len(df)} rows")
        except Exception as e:
            print(f"  Warning — could not load {f}: {e}")

    combined = pd.concat(frames, ignore_index=True)
    print(f"\nTotal rows loaded: {len(combined)}")
    return combined

# ── Parse period_days from "365 days" string ──────────────────────────────────
def extract_days(period_str):
    try:
        return int(str(period_str).split()[0])
    except Exception:
        return 365

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("ELITE STRATEGY FILTER")
    print("=" * 65)

    # Load
    df = load_all_results()

    # Normalise column names (lowercase strip)
    df.columns = [c.strip() for c in df.columns]

    # Required columns check
    required = ["roi", "Win_Rate_Percent", "Profit_Factor", "Max_Drawdown", "Total_Trades"]
    missing  = [c for c in required if c not in df.columns]
    if missing:
        print(f"\n⚠️  Missing columns: {missing}")
        print(f"Available: {list(df.columns)}")
        return

    # ── Apply elite filters ───────────────────────────────────────────────────
    elite = df[
        (df["roi"]              > MIN_ROI)          &
        (df["Win_Rate_Percent"] > MIN_WIN_RATE)      &
        (df["Profit_Factor"]    > MIN_PROFIT_FACTOR) &
        (df["Max_Drawdown"]     < MAX_DRAWDOWN)      &
        (df["Total_Trades"]     >= MIN_TRADES)
    ].copy()

    print(f"\nFiltered {len(df)} → {len(elite)} elite strategies")
    print(f"  ROI > {MIN_ROI}%  |  Win Rate > {MIN_WIN_RATE}%  |  "
          f"PF > {MIN_PROFIT_FACTOR}  |  MaxDD < {MAX_DRAWDOWN}%  |  Trades ≥ {MIN_TRADES}")

    if elite.empty:
        print("\n⚠️  No strategies passed all filters. Loosening to ROI > 30% ...")
        elite = df[
            (df["roi"]              > 30.0) &
            (df["Win_Rate_Percent"] > 20.0) &
            (df["Profit_Factor"]    > 1.2)  &
            (df["Max_Drawdown"]     < 40.0) &
            (df["Total_Trades"]     >= 15)
        ].copy()
        print(f"  Found {len(elite)} with relaxed criteria")

    # ── Daily profit model ────────────────────────────────────────────────────
    elite["period_days"] = elite["Time_period_checked"].apply(extract_days)
    elite["trades_per_day"] = elite["Total_Trades"] / elite["period_days"]

    avg_pct_col = "Avg_Trade_Percent"
    if avg_pct_col in elite.columns:
        elite["expected_daily_pct"] = (
            elite[avg_pct_col] * (elite["Win_Rate_Percent"] / 100) * elite["trades_per_day"]
        ).round(4)
    else:
        # Estimate from ROI
        elite["expected_daily_pct"] = (elite["roi"] / elite["period_days"]).round(4)

    elite["hits_2pct_daily"] = elite["expected_daily_pct"] >= DAILY_TARGET_PCT

    # ── Score for ranking (composite) ────────────────────────────────────────
    elite["composite_score"] = (
        (elite["roi"]              / 100) * 0.35 +
        (elite["Win_Rate_Percent"] / 100) * 0.20 +
        (elite["Profit_Factor"]    / 5  ) * 0.20 +
        (1 - elite["Max_Drawdown"] / 100) * 0.15 +
        (elite["expected_daily_pct"] / DAILY_TARGET_PCT) * 0.10
    ).round(4)

    elite = elite.sort_values("composite_score", ascending=False).reset_index(drop=True)
    elite["Elite_Rank"] = range(1, len(elite) + 1)

    # ── Save CSV ──────────────────────────────────────────────────────────────
    elite.to_csv(OUTPUT_ELITE_CSV, index=False)
    print(f"\n✅ Saved {OUTPUT_ELITE_CSV}  ({len(elite)} strategies)")

    # ── Save JSON for bot use ─────────────────────────────────────────────────
    json_cols = ["Elite_Rank", "Strategy", "Asset", "Timeframe", "roi",
                 "Win_Rate_Percent", "Profit_Factor", "Max_Drawdown",
                 "Total_Trades", "Avg_Trade_Percent", "expected_daily_pct",
                 "hits_2pct_daily", "composite_score", "Parameters"]
    json_cols = [c for c in json_cols if c in elite.columns]
    elite[json_cols].to_json(OUTPUT_ELITE_JSON, orient="records", indent=2)
    print(f"✅ Saved {OUTPUT_ELITE_JSON}")

    # ── Daily profit model report ─────────────────────────────────────────────
    daily_cols = ["Elite_Rank", "Strategy", "Asset", "Timeframe",
                  "trades_per_day", "Win_Rate_Percent", "Avg_Trade_Percent",
                  "expected_daily_pct", "hits_2pct_daily", "roi"]
    daily_cols = [c for c in daily_cols if c in elite.columns]
    elite[daily_cols].to_csv(OUTPUT_DAILY_CSV, index=False)
    print(f"✅ Saved {OUTPUT_DAILY_CSV}")

    # ── Print summary ─────────────────────────────────────────────────────────
    print(f"\n{'='*65}")
    print(f"TOP 20 ELITE STRATEGIES (ranked by composite score)")
    print(f"{'='*65}")
    display_cols = ["Elite_Rank", "Strategy", "Asset", "Timeframe",
                    "roi", "Win_Rate_Percent", "Profit_Factor",
                    "Max_Drawdown", "expected_daily_pct", "hits_2pct_daily"]
    display_cols = [c for c in display_cols if c in elite.columns]
    print(elite[display_cols].head(20).to_string(index=False))

    # ── Asset breakdown ───────────────────────────────────────────────────────
    print(f"\n{'='*65}")
    print("ELITE STRATEGIES BY ASSET")
    print(f"{'='*65}")
    asset_summary = elite.groupby("Asset").agg(
        count=("roi", "count"),
        avg_roi=("roi", "mean"),
        best_roi=("roi", "max"),
        avg_daily=("expected_daily_pct", "mean"),
    ).sort_values("best_roi", ascending=False)
    print(asset_summary.round(2).to_string())

    # ── 2% daily hits ─────────────────────────────────────────────────────────
    hits = elite[elite["hits_2pct_daily"]]
    print(f"\n{'='*65}")
    print(f"STRATEGIES THAT CAN HIT {DAILY_TARGET_PCT}% DAILY: {len(hits)}")
    print(f"{'='*65}")
    if not hits.empty:
        print(hits[display_cols].head(10).to_string(index=False))
    else:
        print("None hit the 2% daily target outright.")
        print("Best candidates (top 5 by expected daily):")
        print(elite[display_cols].head(5).to_string(index=False))

    # ── Recommended parameters ────────────────────────────────────────────────
    print(f"\n{'='*65}")
    print("RECOMMENDED PARAMETERS FOR TOP 10 ELITE STRATEGIES")
    print(f"{'='*65}")
    if "Parameters" in elite.columns:
        for _, row in elite.head(10).iterrows():
            print(f"  #{int(row['Elite_Rank']):2d}  {row['Strategy']:<35} "
                  f"{row['Asset']} {row['Timeframe']}  →  {row['Parameters']}")

    print(f"\n✅ Elite filter complete. {len(elite)} strategies shortlisted.")
    return elite

if __name__ == "__main__":
    main()
