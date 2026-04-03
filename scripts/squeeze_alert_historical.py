#!/usr/bin/env python3
"""
BB Squeeze Alert System — uses our downloaded 4h data.
Scans all assets, finds where squeeze is currently active or just released.
No external API needed — works with stored parquet files.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd, numpy as np
from run_strategies_batch import load_data, calculate_indicators
from datetime import datetime

ASSETS = ["ETHUSDT", "BTCUSDT", "ADAUSDT", "SOLUSDT", "LINKUSDT",
          "BNBUSDT", "XRPUSDT", "AVAXUSDT", "DOTUSDT", "LTCUSDT"]

BEST_PARAMS = {
    "LDOUSDT": {"tp": 14, "sl": 1.5, "bb": 14, "roi_yr": 74.53, "tier": "TIER_2"},
    "SUIUSDT": {"tp": 15, "sl": 1.5, "bb": 14, "roi_yr": 63.54, "tier": "TIER_2"},
    "ETHUSDT": {"tp": 10, "sl": 1.5, "bb": 14, "roi_yr": 51.76, "tier": "TIER_2"},
    "DOTUSDT": {"tp": 10, "sl": 1.5, "bb": 14, "roi_yr": 35.70, "tier": "PAPER"},
    "BTCUSDT": {"tp": 10, "sl": 1.5, "bb": 14, "roi_yr": 19.47, "tier": "PAPER"},
    "LTCUSDT": {"tp": 10, "sl": 1.5, "bb": 20, "roi_yr": 22.38, "tier": "PAPER"},
    "SOLUSDT": {"tp": 10, "sl": 1.5, "bb": 14, "roi_yr": 9.80, "tier": "REJECT"},
    "ADAUSDT": {"tp": 10, "sl": 1.5, "bb": 14, "roi_yr": 8.46, "tier": "REJECT"},
    "BNBUSDT": {"tp": 10, "sl": 1.5, "bb": 14, "roi_yr": 9.93, "tier": "REJECT"},
    "XRPUSDT": {"tp": 10, "sl": 1.5, "bb": 14, "roi_yr": 10.18, "tier": "REJECT"},
    "AVAXUSDT": {"tp": 10, "sl": 1.5, "bb": 14, "roi_yr": -15.43, "tier": "REJECT"},
    "LINKUSDT": {"tp": 10, "sl": 1.5, "bb": 14, "roi_yr": -28.15, "tier": "REJECT"},
}
DEFAULT = {"tp": 10, "sl": 1.5, "bb": 14, "roi_yr": 0, "tier": "UNKNOWN"}


def detect_squeeze_state(df, bb_len=14, bb_mult=2.0, kc_mult=1.5):
    """Detect squeeze state for last N bars."""
    c = df["close"]
    bb_basis = c.rolling(bb_len).mean()
    bb_dev = c.rolling(bb_len).std() * bb_mult
    bb_upper = bb_basis + bb_dev
    bb_lower = bb_basis - bb_dev

    kc_basis = c.ewm(span=bb_len).mean()
    kc_range = (df["high"] - df["low"]).rolling(bb_len).mean()
    kc_upper = kc_basis + kc_mult * kc_range
    kc_lower = kc_basis - kc_mult * kc_range

    squeeze = (bb_upper < kc_upper) & (bb_lower > kc_lower)
    release = ~squeeze & squeeze.shift(1).fillna(False)

    # Momentum
    highest = df["high"].rolling(bb_len).max()
    lowest = df["low"].rolling(bb_len).min()
    delta = c - ((highest + lowest) / 2 + bb_basis) / 2
    # Simple momentum approximation
    mom = c.pct_change(bb_len)

    return squeeze, release, mom


def scan_all():
    print("=" * 70, flush=True)
    print("  BB SQUEEZE SCANNER — Historical Data (4h)", flush=True)
    print("=" * 70, flush=True)

    results = {
        "squeezing": [],      # Currently in squeeze (about to break)
        "just_released": [],   # Released in last 3 bars
        "recent_entry": [],    # Good entry in last 5 bars
        "no_squeeze": [],      # Not in squeeze
    }

    for asset in ASSETS:
        df = load_data(f"{asset}_4h")
        if df is None:
            continue
        df = calculate_indicators(df)

        params = BEST_PARAMS.get(asset, DEFAULT)
        bb_len = params["bb"]

        squeeze, release, mom = detect_squeeze_state(df, bb_len=bb_len)

        last_bar = len(df) - 1
        last_date = str(df["timestamp"].iloc[-1])[:19] if "timestamp" in df.columns else "N/A"
        price = df["close"].iloc[-1]
        rsi = df["rsi"].iloc[-1] if "rsi" in df.columns else 50
        adx = df["adx"].iloc[-1] if "adx" in df.columns else 0
        ema50 = df["ema50"].iloc[-1] if "ema50" in df.columns else price

        # Squeeze duration (how many bars in squeeze)
        sq_duration = 0
        for i in range(last_bar, max(0, last_bar - 50), -1):
            if squeeze.iloc[i]:
                sq_duration += 1
            else:
                break

        # Check states
        is_squeezing = squeeze.iloc[-1]
        just_released = any(release.iloc[-3:]) if last_bar >= 2 else False
        mom_direction = "LONG" if mom.iloc[-1] > 0 else "SHORT"
        trend_up = price > ema50

        info = {
            "asset": asset,
            "price": round(price, 4),
            "rsi": round(rsi, 1),
            "adx": round(adx, 1),
            "momentum": mom_direction,
            "trend": "UP" if trend_up else "DOWN",
            "sq_duration": sq_duration,
            "last_bar": last_date,
            "tp": params["tp"],
            "sl": params["sl"],
            "tier": params["tier"],
            "roi_yr": params["roi_yr"],
        }

        if is_squeezing:
            results["squeezing"].append(info)
        elif just_released:
            results["just_released"].append(info)
        else:
            results["no_squeeze"].append(info)

    # Print results
    print(f"\n  SQUEEZING NOW (ready to break out):", flush=True)
    if results["squeezing"]:
        for s in results["squeezing"]:
            print(f"    {s['asset']:<12} Price=${s['price']:<10} RSI={s['rsi']:<5} ADX={s['adx']:<5} "
                  f"Duration={s['sq_duration']} bars | {s['tier']} {s['roi_yr']}%/yr", flush=True)
    else:
        print(f"    None currently", flush=True)

    print(f"\n  JUST RELEASED (last 3 bars — potential entry):", flush=True)
    if results["just_released"]:
        for s in results["just_released"]:
            print(f"    {s['asset']:<12} {s['momentum']:<6} Price=${s['price']:<10} RSI={s['rsi']:<5} ADX={s['adx']:<5} "
                  f"Trend={s['trend']} | Use TP={s['tp']}% SL={s['sl']}% | {s['tier']} {s['roi_yr']}%/yr", flush=True)
    else:
        print(f"    None recently", flush=True)

    print(f"\n  NO SQUEEZE (wait for setup):", flush=True)
    for s in results["no_squeeze"][:5]:
        print(f"    {s['asset']:<12} RSI={s['rsi']:<5} ADX={s['adx']:<5} | {s['tier']}", flush=True)

    # Save
    save_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "storage", "squeeze_scan.json")
    json.dump(results, open(save_path, "w"), indent=2, default=str)
    print(f"\n  Saved to storage/squeeze_scan.json", flush=True)

    return results


if __name__ == "__main__":
    scan_all()
