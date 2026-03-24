"""
Strategy Analysis & Asset Status Tracker
=========================================
Analyzes all strategies across all assets × timeframes.
Shows: performance matrix, best/worst per combo, DD analysis,
       pending combinations, and IST last-modified timestamps.

Run:    python asset_status.py
Output: asset_status_report.txt
"""

import os
import json
import pandas as pd
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
IST = timezone(timedelta(hours=5, minutes=30))

ASSETS     = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
               "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT"]
TIMEFRAMES = ["15m", "1h", "4h"]

# ── All result files → (label, bot_command) ──────────────────────────────
RESULT_CSVS = {
    "batch_backtest_results.csv":          ("Backtest",       "/backtest"),
    "elite_strategies.csv":                ("Elite",          "/elite"),
    "all_assets_strategies_combined.csv":  ("Combined",       "combine_all_results.py"),
    "auto_optimization_results.csv":       ("Auto-Optimized", "/auto"),
}
# Per-asset CSVs
for _prefix, _asset in [("btc","BTCUSDT"),("eth","ETHUSDT"),("bnb","BNBUSDT"),
                         ("sol","SOLUSDT"),("xrp","XRPUSDT"),("ada","ADAUSDT"),
                         ("avax","AVAXUSDT"),("dot","DOTUSDT"),("link","LINKUSDT"),
                         ("ltc","LTCUSDT")]:
    RESULT_CSVS[f"{_prefix}_all_results.csv"] = ("Backtest", f"/backtest {_prefix}")

ELITE_JSON = os.path.join(ROOT, "storage", "elite_ranking.json")

# ── Column name normalization ────────────────────────────────────────────
COL_MAP = {
    "Strategy": "strategy", "name": "strategy",
    "Asset": "asset",
    "Timeframe": "timeframe", "Candle_Period": "timeframe",
    "ROI_Percent": "roi", "roi": "roi",
    "ROI_per_annum": "roi_yr", "ROI_per_annum_Percent": "roi_yr", "ROI/annum": "roi_yr",
    "Total_Trades": "trades",
    "Win_Rate_Percent": "win_rate",
    "Profit_Factor": "pf",
    "Gross_DD_Percent": "gross_dd", "Max_Drawdown": "gross_dd", "Max_Drawdown_Percent": "gross_dd",
    "Net_DD_Percent": "net_dd",
    "Performance_Grade": "grade",
    "Final_Capital_USD": "final_cap",
    "Initial_Capital_USD": "init_cap",
    "Parameters": "params",
    "Sharpe_Ratio": "sharpe",
}


def _norm_columns(df):
    """Rename columns to standard names."""
    rename = {}
    for old, new in COL_MAP.items():
        if old in df.columns and new not in df.columns:
            rename[old] = new
    return df.rename(columns=rename)


def _asset_from_symbol(sym):
    s = str(sym).upper()
    for a in ASSETS:
        if s.startswith(a):
            return a
    return None


def _tf_from_symbol(sym):
    s = str(sym)
    for tf in TIMEFRAMES:
        if s.endswith(tf):
            return tf
    return None


def _mtime_ist(filepath):
    try:
        ts = os.path.getmtime(filepath)
        return datetime.fromtimestamp(ts, tz=IST).strftime("%Y-%m-%d %H:%M IST")
    except Exception:
        return None


def load_all_results():
    """Load and merge all result CSVs into one DataFrame with standard columns."""
    frames = []
    file_meta = {}  # (asset, tf) -> (label, bot_cmd, mtime_ist)

    for filename, (label, bot_cmd) in RESULT_CSVS.items():
        filepath = os.path.join(ROOT, filename)
        if not os.path.exists(filepath):
            continue
        mtime = os.path.getmtime(filepath)
        mtime_str = datetime.fromtimestamp(mtime, tz=IST).strftime("%Y-%m-%d %H:%M IST")
        try:
            df = pd.read_csv(filepath)
            df = _norm_columns(df)
            df["_source"] = label
            df["_bot_cmd"] = bot_cmd
            df["_mtime"] = mtime

            # Fix asset column if missing
            if "asset" not in df.columns:
                prefix = filename.split("_")[0].lower()
                asset_map = {"btc":"BTCUSDT","eth":"ETHUSDT","bnb":"BNBUSDT",
                             "sol":"SOLUSDT","xrp":"XRPUSDT","ada":"ADAUSDT",
                             "avax":"AVAXUSDT","dot":"DOTUSDT","link":"LINKUSDT",
                             "ltc":"LTCUSDT"}
                if prefix in asset_map:
                    df["asset"] = asset_map[prefix]

            # Fix timeframe column if missing
            if "timeframe" not in df.columns and "asset" in df.columns:
                df["timeframe"] = "unknown"

            if "asset" in df.columns and "timeframe" in df.columns:
                for _, row in df[["asset", "timeframe"]].drop_duplicates().iterrows():
                    a, t = str(row["asset"]).upper(), str(row["timeframe"]).lower()
                    key = (a, t)
                    prev = file_meta.get(key)
                    if prev is None or mtime > prev[2]:
                        file_meta[key] = (label, bot_cmd, mtime, mtime_str)

                # Reset index to avoid duplicates before concat
                frames.append(df.reset_index(drop=True))
        except Exception as e:
            print(f"  Warning: {filename}: {e}")

    if not frames:
        return pd.DataFrame(), file_meta

    # Drop duplicate columns in each frame before concat
    clean_frames = []
    for f in frames:
        f = f.loc[:, ~f.columns.duplicated()]
        clean_frames.append(f)

    combined = pd.concat(clean_frames, ignore_index=True)

    # De-duplicate: keep the row from the most recent file per strategy+asset+tf
    dedup_cols = [c for c in ["strategy", "asset", "timeframe", "roi_yr", "trades"] if c in combined.columns]
    if dedup_cols:
        combined = combined.sort_values("_mtime", ascending=False).drop_duplicates(subset=dedup_cols, keep="first")

    # Normalize asset/tf values
    if "asset" in combined.columns:
        combined["asset"] = combined["asset"].astype(str).str.upper()
    if "timeframe" in combined.columns:
        combined["timeframe"] = combined["timeframe"].astype(str).str.lower()

    # Ensure numeric columns
    for col in ["roi", "roi_yr", "trades", "win_rate", "pf", "gross_dd", "net_dd", "sharpe", "final_cap"]:
        if col in combined.columns:
            combined[col] = pd.to_numeric(combined[col], errors="coerce")

    return combined, file_meta


def check_data_files():
    """Returns set of (asset, tf) that have parquet data."""
    data_dir = os.path.join(ROOT, "storage", "historical_data")
    available = set()
    if not os.path.exists(data_dir):
        return available
    for f in os.listdir(data_dir):
        if not f.endswith(".parquet"):
            continue
        a = _asset_from_symbol(f)
        t = _tf_from_symbol(f.replace(".parquet", ""))
        if a and t:
            available.add((a.upper(), t.lower()))
    return available


def generate_report():
    df, file_meta = load_all_results()
    available = check_data_files()
    now_ist = datetime.now(tz=IST).strftime("%Y-%m-%d %H:%M IST")

    lines = []
    W = 90

    # ═══════════════════════════════════════════════════════════════════════
    lines.append("=" * W)
    lines.append("  STRATEGY ANALYSIS & ASSET STATUS REPORT")
    lines.append(f"  Generated: {now_ist}")
    lines.append("=" * W)

    if df.empty:
        lines.append("\n  No result CSVs found. Run /backtest or /auto first.")
        _write_report(lines, W)
        return

    # ── 1. OVERALL SUMMARY ────────────────────────────────────────────────
    has_results = set()
    if "asset" in df.columns and "timeframe" in df.columns:
        for _, row in df[["asset", "timeframe"]].drop_duplicates().iterrows():
            has_results.add((row["asset"], row["timeframe"]))

    total = len(ASSETS) * len(TIMEFRAMES)
    touched = len(has_results & available)
    pending = len(available - has_results)

    lines.append(f"\n  Total combinations : {total}")
    lines.append(f"  Data available     : {len(available)}")
    lines.append(f"  Results exist      : {touched}")
    lines.append(f"  Pending            : {pending}")

    if "strategy" in df.columns:
        lines.append(f"  Unique strategies  : {df['strategy'].nunique()}")
    lines.append(f"  Total result rows  : {len(df)}")

    # ── 2. ASSET × TIMEFRAME STATUS GRID ──────────────────────────────────
    lines.append(f"\n{'─' * W}")
    lines.append("  ASSET × TIMEFRAME STATUS")
    lines.append(f"{'─' * W}")
    lines.append(f"  {'ASSET':<12} {'15m':<22} {'1h':<22} {'4h':<22}")
    lines.append(f"{'─' * W}")

    for asset in ASSETS:
        row = f"  {asset:<12}"
        for tf in TIMEFRAMES:
            key = (asset, tf)
            has_data = key in available
            has_res = key in has_results
            if not has_data:
                cell = "NO DATA"
            elif has_res:
                # Count strategies tested on this combo
                mask = (df["asset"] == asset) & (df["timeframe"] == tf)
                n = mask.sum()
                # Best ROI/yr
                if "roi_yr" in df.columns:
                    best = df.loc[mask, "roi_yr"].max()
                    cell = f"✅ {n}strats best:{best:.1f}%"
                else:
                    cell = f"✅ {n} strategies"
            else:
                cell = "⏳ PENDING"
            row += f" {cell:<22}"
        lines.append(row)
    lines.append(f"{'─' * W}")

    # ── 3. BEST STRATEGY PER ASSET × TIMEFRAME ───────────────────────────
    if "roi_yr" in df.columns and "strategy" in df.columns:
        lines.append(f"\n{'─' * W}")
        lines.append("  BEST STRATEGY PER ASSET (by ROI/yr)")
        lines.append(f"{'─' * W}")
        lines.append(f"  {'Asset':<10} {'TFs':<12} {'Strategy':<28} {'ROI/yr':>8} {'Win%':>6} {'Trades':>7} {'GrossDD':>8} {'NetDD':>7} {'Grade':<6}")
        lines.append(f"{'─' * W}")

        for asset in ASSETS:
            asset_mask = df["asset"] == asset
            if not asset_mask.any():
                continue
            tfs_done = sorted(df.loc[asset_mask, "timeframe"].unique())
            tf_str = ",".join(tfs_done)
            best_idx = df.loc[asset_mask, "roi_yr"].idxmax()
            r = df.loc[best_idx]
            strat = str(r.get("strategy", "?"))[:27]
            roi_yr = r.get("roi_yr", 0)
            wr = r.get("win_rate", 0)
            tr = int(r.get("trades", 0))
            gdd = r.get("gross_dd", 0)
            ndd = r.get("net_dd", 0)
            gr = r.get("grade", "?")
            marker = "+" if roi_yr > 20 else "=" if roi_yr > 0 else "-"
            lines.append(
                f"  {asset:<10} {tf_str:<12} {strat:<28} {roi_yr:>7.1f}% {wr:>5.1f}% {tr:>7} {gdd:>7.1f}% {ndd:>6.1f}% {gr:<3} {marker}"
            )
        lines.append(f"{'─' * W}")

    # ── 4. TOP 15 OVERALL STRATEGIES ──────────────────────────────────────
    if "roi_yr" in df.columns:
        lines.append(f"\n{'─' * W}")
        lines.append("  TOP 15 STRATEGIES OVERALL (by ROI/yr)")
        lines.append(f"{'─' * W}")
        lines.append(f"  {'#':<3} {'Strategy':<25} {'Asset':<10} {'TF':<5} {'ROI/yr':>8} {'Win%':>6} {'GrossDD':>8} {'NetDD':>7} {'Grade':<6}")
        lines.append(f"{'─' * W}")

        top = df.nlargest(15, "roi_yr")
        for i, (_, r) in enumerate(top.iterrows(), 1):
            strat = str(r.get("strategy", "?"))[:24]
            lines.append(
                f"  {i:<3} {strat:<25} {str(r.get('asset','?')):<10} {str(r.get('timeframe','?')):<5} "
                f"{r.get('roi_yr',0):>7.1f}% {r.get('win_rate',0):>5.1f}% "
                f"{r.get('gross_dd',0):>7.1f}% {r.get('net_dd',0):>6.1f}% {r.get('grade','?'):<3}"
            )
        lines.append(f"{'─' * W}")

    # ── 5. WORST 10 (LOSING MONEY) ───────────────────────────────────────
    if "roi_yr" in df.columns:
        losers = df[df["roi_yr"] < 0].nsmallest(10, "roi_yr")
        if not losers.empty:
            lines.append(f"\n{'─' * W}")
            lines.append("  BOTTOM 10 STRATEGIES (worst ROI/yr)")
            lines.append(f"{'─' * W}")
            lines.append(f"  {'#':<3} {'Strategy':<25} {'Asset':<10} {'TF':<5} {'ROI/yr':>8} {'NetDD':>7} {'Grade':<6}")
            lines.append(f"{'─' * W}")
            for i, (_, r) in enumerate(losers.iterrows(), 1):
                strat = str(r.get("strategy", "?"))[:24]
                lines.append(
                    f"  {i:<3} {strat:<25} {str(r.get('asset','?')):<10} {str(r.get('timeframe','?')):<5} "
                    f"{r.get('roi_yr',0):>7.1f}% {r.get('net_dd',0):>6.1f}% {r.get('grade','?'):<3}"
                )
            lines.append(f"{'─' * W}")

    # ── 6. DRAWDOWN ANALYSIS ─────────────────────────────────────────────
    if "gross_dd" in df.columns:
        lines.append(f"\n{'─' * W}")
        lines.append("  DRAWDOWN ANALYSIS")
        lines.append(f"{'─' * W}")

        profitable = df[df.get("roi_yr", df.get("roi", pd.Series())) > 0] if "roi_yr" in df.columns else df

        if not profitable.empty and "gross_dd" in profitable.columns:
            safe = profitable[profitable["gross_dd"] < 50]
            moderate = profitable[(profitable["gross_dd"] >= 50) & (profitable["gross_dd"] < 75)]
            high = profitable[profitable["gross_dd"] >= 75]
            lines.append(f"  Among profitable strategies:")
            lines.append(f"    ✅ Safe (GrossDD < 50%)     : {len(safe)}")
            lines.append(f"    🟡 Moderate (50-75%)        : {len(moderate)}")
            lines.append(f"    🔴 High risk (> 75%)        : {len(high)}")

        if "net_dd" in df.columns:
            below_capital = df[df["net_dd"] > 0]
            severe = df[df["net_dd"] > 50]
            lines.append(f"    Capital went below initial  : {len(below_capital)} strategies")
            lines.append(f"    Lost >50% of capital        : {len(severe)} strategies")

        lines.append(f"{'─' * W}")

    # ── 7. STRATEGY CONSISTENCY (same strategy across assets) ─────────────
    if "strategy" in df.columns and "roi_yr" in df.columns and "asset" in df.columns:
        lines.append(f"\n{'─' * W}")
        lines.append("  STRATEGY CONSISTENCY ACROSS ASSETS")
        lines.append(f"{'─' * W}")
        lines.append(f"  {'Strategy':<28} {'Assets':>6} {'Avg ROI/yr':>10} {'Profitable':>10} {'Worst':>10}")
        lines.append(f"{'─' * W}")

        strat_stats = df.groupby("strategy").agg(
            assets=("asset", "nunique"),
            avg_roi=("roi_yr", "mean"),
            profitable=("roi_yr", lambda x: (x > 0).sum()),
            worst=("roi_yr", "min"),
        ).sort_values("avg_roi", ascending=False)

        for strat, row in strat_stats.head(20).iterrows():
            sname = str(strat)[:27]
            prof_str = f"{int(row['profitable'])}/{int(row['assets'])}"
            lines.append(
                f"  {sname:<28} {int(row['assets']):>6} {row['avg_roi']:>9.1f}% {prof_str:>10} {row['worst']:>9.1f}%"
            )
        lines.append(f"{'─' * W}")

    # ── 8. LAST MODIFIED (IST) ───────────────────────────────────────────
    lines.append(f"\n{'─' * W}")
    lines.append("  LAST MODIFIED (IST)")
    lines.append(f"{'─' * W}")
    lines.append(f"  {'ASSET':<10} {'TF':<5} {'Command':<16} {'Bot Command':<24} {'Timestamp'}")
    lines.append(f"{'─' * W}")

    for asset in ASSETS:
        for tf in TIMEFRAMES:
            key = (asset, tf)
            if key not in available:
                continue
            if key in file_meta:
                label, bot_cmd, _, mtime_str = file_meta[key]
                lines.append(f"  {asset:<10} {tf:<5} {label:<16} {bot_cmd:<24} {mtime_str}")
            else:
                lines.append(f"  {asset:<10} {tf:<5} {'PENDING':<16} {'—':<24} —")
    lines.append(f"{'─' * W}")

    # ── 9. PENDING COMBINATIONS ──────────────────────────────────────────
    pending_list = sorted(available - has_results)
    if pending_list:
        lines.append(f"\n  PENDING ({len(pending_list)} combinations):")
        for asset, tf in pending_list:
            lines.append(f"    → {asset} {tf}")
    else:
        lines.append("\n  ✅ All available data has been processed.")

    # ── 10. ELITE RANKING STATUS ─────────────────────────────────────────
    if os.path.exists(ELITE_JSON):
        try:
            with open(ELITE_JSON) as f:
                data = json.load(f)
            updated = data.get("updated", _mtime_ist(ELITE_JSON) or "unknown")
            results = data.get("results", [])
            lines.append(f"\n{'─' * W}")
            lines.append(f"  ELITE RANKING (elite_ranking.json) — last updated: {updated}")
            lines.append(f"{'─' * W}")
            lines.append(f"  {'#':<3} {'Strategy':<28} {'SL':>6} {'TP':>6} {'TS':>6} {'Score':>7}")
            lines.append(f"{'─' * W}")
            for i, r in enumerate(results[:10], 1):
                name = str(r.get("name", "?"))[:27]
                sl = r.get("sl", 0)
                tp = r.get("tp", 0)
                ts = r.get("ts", 0)
                score = r.get("score", 0)
                lines.append(
                    f"  {i:<3} {name:<28} {sl*100:>5.1f}% {tp*100:>5.1f}% {ts*100:>5.1f}% {score:>7.2f}"
                )
            lines.append(f"{'─' * W}")
        except Exception:
            pass

    lines.append(f"\n{'=' * W}")
    _write_report(lines, W)


def _write_report(lines, W):
    report = "\n".join(lines)
    try:
        print(report)
    except UnicodeEncodeError:
        print(report.encode("ascii", errors="replace").decode("ascii"))
    out_path = os.path.join(ROOT, "asset_status_report.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n  Saved to: asset_status_report.txt")


if __name__ == "__main__":
    generate_report()
