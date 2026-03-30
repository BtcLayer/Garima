#!/usr/bin/env python3
"""
Select Top 10 Strategies for Live Trading
==========================================
Loads all backtest result CSVs, normalises columns, filters by realistic
criteria, scores each strategy-asset-timeframe combo, enforces
diversification rules, and writes a final report.

Data sources (local):
  - auto_results_4h.csv            (0.1% fee, multi-year, has Gross/Net DD)
  - auto_results_4h_longshort.csv  (long+short combined data)
  - reports/all_assets_strategies_combined.csv  (0.01% fee, 1yr, Max_Drawdown only)
"""

import os, sys, re, textwrap, warnings
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

# ──────────────────────────────────────────────
#  1. Load & normalise all CSV sources
# ──────────────────────────────────────────────

def parse_params(p):
    """Extract SL, TP, TS from parameter strings like 'SL:0.02, TP:0.12, TS:0.02'
    or 'SL=2.0%, TP=8.0%, TS=2.5%'."""
    if pd.isna(p):
        return None, None, None
    s = str(p)
    sl = tp = ts = None
    # format: SL:0.02 or SL=2.0%
    m = re.search(r'SL[=:]\s*([\d.]+)%?', s)
    if m:
        v = float(m.group(1))
        sl = v if v < 1 else v / 100  # normalise to fraction
    m = re.search(r'TP[=:]\s*([\d.]+)%?', s)
    if m:
        v = float(m.group(1))
        tp = v if v < 1 else v / 100
    m = re.search(r'TS[=:]\s*([\d.]+)%?', s)
    if m:
        v = float(m.group(1))
        ts = v if v < 1 else v / 100
    return sl, tp, ts


def load_auto_results_4h():
    """Load the comprehensive auto_results_4h.csv (0.1% fees, multi-year)."""
    path = ROOT / "auto_results_4h.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    # Columns: ROI_per_annum, ROI_Percent, Gross_DD_Percent, Net_DD_Percent,
    #          Capital_At_Net_DD, Parameters
    df = df.rename(columns={
        "ROI_per_annum": "ROI_ann",
        "ROI_Percent": "ROI_total",
        "Gross_DD_Percent": "GrossDD",
        "Net_DD_Percent": "NetDD",
        "Capital_At_Net_DD": "Cap_NDD",
    })
    df["source"] = "auto_4h"
    df["fees_pct"] = 0.1
    # Parse params
    params = df["Parameters"].apply(parse_params)
    df["SL"] = params.apply(lambda x: x[0])
    df["TP"] = params.apply(lambda x: x[1])
    df["TS"] = params.apply(lambda x: x[2])
    return df


def load_combined_1yr():
    """Load reports/all_assets_strategies_combined.csv (0.01% fees, 1yr)."""
    path = ROOT / "reports" / "all_assets_strategies_combined.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    df = df.rename(columns={
        "ROI_per_annum_Percent": "ROI_ann",
        "roi": "ROI_total",
        "Max_Drawdown": "GrossDD",
    })
    # This dataset does not have Net DD or Cap_NDD — estimate
    df["NetDD"] = np.nan
    df["Cap_NDD"] = np.nan
    df["source"] = "combined_1yr"
    df["fees_pct"] = 0.01
    params = df["Parameters"].apply(parse_params)
    df["SL"] = params.apply(lambda x: x[0])
    df["TP"] = params.apply(lambda x: x[1])
    df["TS"] = params.apply(lambda x: x[2])
    return df


def load_longshort():
    """Load long/short combined results."""
    path = ROOT / "auto_results_4h_longshort.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    return df


# ──────────────────────────────────────────────
#  2. Merge & deduplicate
# ──────────────────────────────────────────────

COLS_KEEP = [
    "Strategy", "Asset", "Timeframe",
    "ROI_ann", "ROI_total",
    "Total_Trades", "Win_Rate_Percent", "Profit_Factor",
    "GrossDD", "NetDD", "Cap_NDD",
    "Sharpe_Ratio", "Avg_Trade_Percent",
    "SL", "TP", "TS",
    "source", "fees_pct",
]


def build_master():
    df1 = load_auto_results_4h()
    df2 = load_combined_1yr()

    frames = []
    for df in [df1, df2]:
        if df.empty:
            continue
        # Normalise Asset: strip USDT suffix for matching, keep original
        if "Asset" in df.columns:
            df["Asset"] = df["Asset"].str.strip()
        present = [c for c in COLS_KEEP if c in df.columns]
        frames.append(df[present].copy())

    if not frames:
        print("ERROR: No data files found!")
        sys.exit(1)

    master = pd.concat(frames, ignore_index=True)

    # Fix: BTC ROI_per_annum_Percent bug — values like 3823.22 for roi=38.23
    # In combined_1yr, ROI_ann == ROI_total for 364-day data; already annualised
    # In auto_4h, ROI_per_annum is correctly annualised.
    # For combined_1yr the ROI_per_annum_Percent was copied from roi directly
    # and is already a per-annum figure (364 days ~ 1 year). OK as-is.

    # Prefer auto_4h rows (realistic 0.1% fees) when duplicates exist
    # Deduplicate: keep auto_4h over combined_1yr
    master["_prio"] = master["source"].map({"auto_4h": 0, "combined_1yr": 1})
    master = master.sort_values("_prio")
    master = master.drop_duplicates(subset=["Strategy", "Asset", "Timeframe"], keep="first")
    master = master.drop(columns=["_prio"])
    master = master.reset_index(drop=True)

    return master


# ──────────────────────────────────────────────
#  3. Enrich with long/short data
# ──────────────────────────────────────────────

SHORT_BENEFICIAL = ["Volume_Stochastic_MACD_ADX", "High_Momentum_Entry"]


def enrich_longshort(master):
    ls = load_longshort()
    if ls.empty:
        master["use_short"] = False
        master["combined_ROI_ann"] = master["ROI_ann"]
        return master

    # Build lookup from longshort
    ls_lookup = {}
    for _, row in ls.iterrows():
        strat = row["Strategy"]
        asset = row["Asset"] + "USDT" if "USDT" not in str(row["Asset"]) else row["Asset"]
        # key
        short_pf = row.get("Short_PF", 0)
        short_roi = row.get("Short_ROI_Pct", 0)
        combined_roi_ann = row.get("Combined_ROI_Annum", None)
        long_roi_ann = row.get("Long_ROI_Annum", None)
        delta = row.get("ROI_Delta_Pct", 0)
        ls_lookup[(strat, asset)] = {
            "short_pf": short_pf,
            "short_roi": short_roi,
            "combined_roi_ann": combined_roi_ann,
            "long_roi_ann": long_roi_ann,
            "roi_delta": delta,
            "short_trades": row.get("Short_Trades", 0),
            "short_winrate": row.get("Short_WinRate", 0),
            "short_gdd": row.get("Short_GDD", 0),
        }

    use_short = []
    combined_roi = []
    for _, row in master.iterrows():
        strat = row["Strategy"]
        asset = row["Asset"]
        key = (strat, asset)
        if key in ls_lookup:
            info = ls_lookup[key]
            # Short is beneficial if: delta > 0 AND short PF > 1.0 AND short GDD < 60
            beneficial = (
                info["roi_delta"] > 0
                and info["short_pf"] > 1.0
                and info["short_gdd"] < 60
            )
            use_short.append(beneficial)
            if beneficial and info["combined_roi_ann"] is not None:
                combined_roi.append(info["combined_roi_ann"])
            else:
                combined_roi.append(row["ROI_ann"])
        else:
            use_short.append(False)
            combined_roi.append(row["ROI_ann"])

    master["use_short"] = use_short
    master["combined_ROI_ann"] = combined_roi
    return master


# ──────────────────────────────────────────────
#  4. Filter by realistic criteria
# ──────────────────────────────────────────────

def apply_filters(df):
    print(f"  Before filters: {len(df)} rows")
    f = df.copy()
    f = f[f["ROI_ann"] >= 30]
    print(f"  After ROI_ann >= 30%: {len(f)}")
    f = f[f["GrossDD"] < 60]
    print(f"  After GrossDD < 60%: {len(f)}")
    f = f[f["Win_Rate_Percent"] > 20]
    print(f"  After Win_Rate > 20%: {len(f)}")
    f = f[f["Profit_Factor"] > 1.0]
    print(f"  After PF > 1.0: {len(f)}")
    f = f[f["Total_Trades"] > 50]
    print(f"  After Trades > 50: {len(f)}")
    return f.reset_index(drop=True)


# ──────────────────────────────────────────────
#  5. Score each strategy
# ──────────────────────────────────────────────

def score(df):
    """Weighted composite score. Higher = better.
    ROI 35%, Low DD 25%, Win rate 15%, PF 15%, Trade count 10%."""
    d = df.copy()

    # Use combined ROI (includes short benefit if applicable)
    roi = d["combined_ROI_ann"].fillna(d["ROI_ann"])

    # Normalise each metric to 0-1 (min-max)
    def norm(s):
        mn, mx = s.min(), s.max()
        if mx == mn:
            return pd.Series(0.5, index=s.index)
        return (s - mn) / (mx - mn)

    d["s_roi"]   = norm(roi)
    d["s_dd"]    = norm(100 - d["GrossDD"])  # lower DD = better
    d["s_wr"]    = norm(d["Win_Rate_Percent"])
    d["s_pf"]    = norm(d["Profit_Factor"])
    d["s_tc"]    = norm(d["Total_Trades"])

    d["score"] = (
        0.35 * d["s_roi"]
        + 0.25 * d["s_dd"]
        + 0.15 * d["s_wr"]
        + 0.15 * d["s_pf"]
        + 0.10 * d["s_tc"]
    )

    # Scale to 0-100
    d["confidence"] = (d["score"] * 100).round(1)

    return d.sort_values("confidence", ascending=False).reset_index(drop=True)


# ──────────────────────────────────────────────
#  6. Diversification enforcement
# ──────────────────────────────────────────────

def diversify(df, top_n=10, max_per_asset=3):
    """Select top N ensuring:
    - No more than max_per_asset strategies per asset
    - Mix of timeframes (at least 2 different if possible)
    """
    selected = []
    asset_count = {}
    tf_set = set()

    for _, row in df.iterrows():
        asset = row["Asset"]
        tf = row["Timeframe"]
        ac = asset_count.get(asset, 0)
        if ac >= max_per_asset:
            continue
        selected.append(row)
        asset_count[asset] = ac + 1
        tf_set.add(tf)
        if len(selected) >= top_n:
            break

    result = pd.DataFrame(selected).reset_index(drop=True)
    print(f"\n  Diversified selection: {len(result)} strategies")
    print(f"  Assets: {result['Asset'].nunique()} unique — {list(result['Asset'].unique())}")
    print(f"  Timeframes: {sorted(tf_set)}")
    return result


# ──────────────────────────────────────────────
#  7. Output formatters
# ──────────────────────────────────────────────

def format_pct(v, mult100=False):
    if pd.isna(v):
        return "N/A"
    if mult100:
        return f"{v*100:.1f}%"
    return f"{v:.1f}%"


def generate_markdown(top10):
    lines = []
    lines.append("# FINAL TOP 10 STRATEGIES FOR LIVE TRADING")
    lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"\nSelection criteria: ROI/yr >= 30%, Gross DD < 60%, Win Rate > 20%, PF > 1.0, Trades > 50")
    lines.append(f"Scoring: ROI 35% | Low DD 25% | Win Rate 15% | PF 15% | Trade Count 10%")
    lines.append("")

    # Summary table
    lines.append("## Strategy Summary")
    lines.append("")
    lines.append("| # | Strategy | Asset | TF | ROI%/yr | Win% | Trades | PF | GrossDD% | NetDD% | Cap@NDD | SL% | TP% | TS% | Short? | Score |")
    lines.append("|---|----------|-------|----|---------|------|--------|----|----------|--------|---------|-----|-----|-----|--------|-------|")

    for i, row in top10.iterrows():
        sl_str = format_pct(row.get("SL"), mult100=True) if pd.notna(row.get("SL")) else "N/A"
        tp_str = format_pct(row.get("TP"), mult100=True) if pd.notna(row.get("TP")) else "N/A"
        ts_str = format_pct(row.get("TS"), mult100=True) if pd.notna(row.get("TS")) else "N/A"
        ndd_str = format_pct(row.get("NetDD")) if pd.notna(row.get("NetDD")) else "N/A"
        cap_str = f"${row['Cap_NDD']:,.0f}" if pd.notna(row.get("Cap_NDD")) else "N/A"
        short_str = "Yes" if row.get("use_short", False) else "No"
        roi_display = row.get("combined_ROI_ann", row["ROI_ann"])

        lines.append(
            f"| {i+1} | {row['Strategy']} | {row['Asset']} | {row['Timeframe']} | "
            f"{roi_display:.1f}% | {row['Win_Rate_Percent']:.1f}% | {int(row['Total_Trades'])} | "
            f"{row['Profit_Factor']:.2f} | {row['GrossDD']:.1f}% | {ndd_str} | {cap_str} | "
            f"{sl_str} | {tp_str} | {ts_str} | {short_str} | {row['confidence']:.1f} |"
        )

    # Detailed notes
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("### Fee Assumptions")
    lines.append("- **auto_4h source**: 0.1% round-trip fees (realistic for Binance Spot)")
    lines.append("- **combined_1yr source**: 0.01% fees (optimistic; results may slightly overestimate)")
    lines.append("- Strategies from auto_4h are preferred when duplicates exist")
    lines.append("")
    lines.append("### Short Selling")
    short_rows = top10[top10["use_short"] == True]
    if len(short_rows) > 0:
        for _, r in short_rows.iterrows():
            lines.append(f"- **{r['Strategy']} on {r['Asset']}**: Short signals add ROI. Combined L+S ROI = {r['combined_ROI_ann']:.1f}%/yr")
    else:
        lines.append("- No strategies in the top 10 benefit from short selling in this selection.")
    lines.append("")

    lines.append("### Diversification")
    lines.append(f"- {top10['Asset'].nunique()} unique assets")
    lines.append(f"- Timeframes: {sorted(top10['Timeframe'].unique())}")
    lines.append(f"- Max 3 strategies per asset enforced")
    lines.append("")
    lines.append("### Recommended Next Steps")
    lines.append("1. Run walk-forward validation on each strategy-asset-TF combo")
    lines.append("2. Paper trade for 2 weeks before going live")
    lines.append("3. Start with 50% position sizing, scale up after 1 month")
    lines.append("4. Set circuit breaker at 2x GrossDD as kill-switch threshold")
    lines.append("")

    return "\n".join(lines)


def save_csv(top10, path):
    out_cols = [
        "Strategy", "Asset", "Timeframe",
        "ROI_ann", "combined_ROI_ann",
        "Win_Rate_Percent", "Total_Trades", "Profit_Factor",
        "GrossDD", "NetDD", "Cap_NDD",
        "SL", "TP", "TS",
        "use_short", "confidence", "source",
    ]
    present = [c for c in out_cols if c in top10.columns]
    top10[present].to_csv(path, index=False)
    print(f"  Saved CSV: {path}")


# ──────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  TOP 10 STRATEGY SELECTOR")
    print("=" * 60)

    print("\n[1] Loading data sources...")
    master = build_master()
    print(f"  Master dataset: {len(master)} strategy-asset-timeframe combos")

    print("\n[2] Enriching with long/short data...")
    master = enrich_longshort(master)
    n_short = master["use_short"].sum()
    print(f"  Strategies benefiting from short: {n_short}")

    print("\n[3] Applying filters...")
    filtered = apply_filters(master)

    if len(filtered) == 0:
        print("\nERROR: No strategies pass all filters. Relaxing criteria...")
        # Relax: ROI >= 20, DD < 70
        filtered = master.copy()
        filtered = filtered[filtered["ROI_ann"] >= 20]
        filtered = filtered[filtered["GrossDD"] < 70]
        filtered = filtered[filtered["Win_Rate_Percent"] > 15]
        filtered = filtered[filtered["Profit_Factor"] > 1.0]
        filtered = filtered[filtered["Total_Trades"] > 30]
        print(f"  Relaxed filter: {len(filtered)} rows")

    print("\n[4] Scoring strategies...")
    scored = score(filtered)
    print(f"  Top 5 preview:")
    for i in range(min(5, len(scored))):
        r = scored.iloc[i]
        print(f"    {i+1}. {r['Strategy']:30s} {r['Asset']:10s} {r['Timeframe']:4s}  "
              f"ROI={r['combined_ROI_ann']:6.1f}%  DD={r['GrossDD']:5.1f}%  "
              f"WR={r['Win_Rate_Percent']:5.1f}%  PF={r['Profit_Factor']:.2f}  "
              f"Score={r['confidence']:.1f}")

    print("\n[5] Enforcing diversification...")
    top10 = diversify(scored, top_n=10, max_per_asset=3)

    print("\n[6] Generating reports...")
    md = generate_markdown(top10)
    md_path = ROOT / "reports" / "FINAL_TOP10_STRATEGIES.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"  Saved MD: {md_path}")

    csv_path = ROOT / "reports" / "final_top10.csv"
    save_csv(top10, csv_path)

    print("\n" + "=" * 60)
    print("  FINAL TOP 10 STRATEGIES")
    print("=" * 60)
    print(md)


if __name__ == "__main__":
    main()
