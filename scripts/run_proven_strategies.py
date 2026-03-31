#!/usr/bin/env python3
"""Run the 3 PROVEN strategies (from tournament system) on all assets.
These strategies have real OOS results on FILUSDT.
Implements exact TV Pine Script logic."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import numpy as np
from datetime import datetime

INITIAL_CAPITAL = 10000
FEE = 0.001  # 0.1% matching working strategies

DATA_DIR = "storage/historical_data"
TOURNAMENT_DIR = "/home/ubuntu/tradingview_webhook_bot/storage/backtest_data"


def load_any_data(symbol, tf="15m"):
    """Load data from either tournament store or our store."""
    # Try tournament CSV first (15m data)
    csv_path = os.path.join(TOURNAMENT_DIR, f"{symbol}_3y_15m.csv")
    if os.path.exists(csv_path) and tf == "15m":
        return pd.read_csv(csv_path)
    # Try our parquet files
    for f in sorted(os.listdir(DATA_DIR), reverse=True):
        if f.startswith(f"{symbol}_{tf}") and f.endswith(".parquet"):
            try:
                return pd.read_parquet(os.path.join(DATA_DIR, f))
            except:
                continue
    # Try our CSVs
    for f in sorted(os.listdir(DATA_DIR), reverse=True):
        if f.startswith(f"{symbol}_{tf}") and f.endswith(".csv"):
            return pd.read_csv(os.path.join(DATA_DIR, f))
    return None


def calc_indicators(df):
    """Calculate all needed indicators."""
    d = df.copy()
    # EMAs
    d["ema9"] = d["close"].ewm(span=9).mean()
    d["ema21"] = d["close"].ewm(span=21).mean()
    d["ema20"] = d["close"].ewm(span=20).mean()
    d["ema50"] = d["close"].ewm(span=50).mean()
    # RSI
    delta = d["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    d["rsi"] = 100 - (100 / (1 + rs))
    # Volume
    d["vol_sma"] = d["volume"].rolling(20).mean()
    # ATR
    high_low = d["high"] - d["low"]
    high_close = abs(d["high"] - d["close"].shift())
    low_close = abs(d["low"] - d["close"].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    d["atr10"] = tr.rolling(10).mean()
    # Keltner
    d["kc_upper"] = d["ema20"] + 2.0 * d["atr10"]
    d["kc_lower"] = d["ema20"] - 2.0 * d["atr10"]
    # Ichimoku
    d["tenkan"] = (d["high"].rolling(9).max() + d["low"].rolling(9).min()) / 2
    d["kijun"] = (d["high"].rolling(26).max() + d["low"].rolling(26).min()) / 2
    d["senkou_a"] = ((d["tenkan"] + d["kijun"]) / 2).shift(26)
    d["senkou_b"] = ((d["high"].rolling(52).max() + d["low"].rolling(52).min()) / 2).shift(26)
    d["cloud_top"] = d[["senkou_a", "senkou_b"]].max(axis=1)
    d["cloud_bottom"] = d[["senkou_a", "senkou_b"]].min(axis=1)
    d["chikou_past"] = d["close"].shift(26)
    return d


def backtest_strategy(df, long_entry, short_entry, long_exit, short_exit):
    """Backtest with long+short, signal-based exits, position flipping."""
    capital = INITIAL_CAPITAL
    position = 0  # 0=flat, 1=long, -1=short
    entry_price = 0
    position_size = 0
    trades = []

    for i in range(1, len(df)):
        bar = df.iloc[i]
        prev = df.iloc[i - 1]
        price = bar["close"]

        if position == 1:  # LONG
            if long_exit.iloc[i] or short_entry.iloc[i]:
                exit_price = price * (1 - FEE)
                pnl = (exit_price - entry_price) * position_size
                capital += pnl
                trades.append({"pnl": pnl, "return_pct": (exit_price / entry_price - 1) * 100,
                               "side": "long", "exit_reason": "FLIP" if short_entry.iloc[i] else "SIGNAL"})
                position = 0
                if short_entry.iloc[i]:
                    entry_price = price * (1 - FEE)
                    position_size = capital / entry_price
                    position = -1

        elif position == -1:  # SHORT
            if short_exit.iloc[i] or long_entry.iloc[i]:
                exit_price = price * (1 + FEE)
                pnl = (entry_price - exit_price) * position_size
                capital += pnl
                trades.append({"pnl": pnl, "return_pct": (entry_price / exit_price - 1) * 100,
                               "side": "short", "exit_reason": "FLIP" if long_entry.iloc[i] else "SIGNAL"})
                position = 0
                if long_entry.iloc[i]:
                    entry_price = price * (1 + FEE)
                    position_size = capital / entry_price
                    position = 1

        elif position == 0:  # FLAT
            if long_entry.iloc[i]:
                entry_price = price * (1 + FEE)
                position_size = capital / entry_price
                position = 1
            elif short_entry.iloc[i]:
                entry_price = price * (1 - FEE)
                position_size = capital / entry_price
                position = -1

    return capital, trades


def strategy_ichimoku_trend_pro(df):
    """22 Ichimoku Trend Pro — exact match to Pine Script."""
    d = calc_indicators(df)
    long_entry = (d["close"] > d["cloud_top"]) & (d["tenkan"] > d["kijun"]) & (d["close"] > d["chikou_past"])
    short_entry = (d["close"] < d["cloud_bottom"]) & (d["tenkan"] < d["kijun"])
    # Crossover versions
    le = long_entry & ~long_entry.shift(1).fillna(False)
    se = short_entry & ~short_entry.shift(1).fillna(False)
    long_exit = ((d["tenkan"] < d["kijun"]) & (d["tenkan"].shift(1) >= d["kijun"].shift(1))) | (d["close"] < d["cloud_bottom"])
    short_exit = ((d["tenkan"] > d["kijun"]) & (d["tenkan"].shift(1) <= d["kijun"].shift(1))) | (d["close"] > d["cloud_top"])
    return backtest_strategy(d, le, se, long_exit, short_exit)


def strategy_keltner_breakout(df):
    """24 Keltner Breakout — exact match to Pine Script."""
    d = calc_indicators(df)
    long_break = (d["close"] > d["kc_upper"]) & (d["close"].shift(1) <= d["kc_upper"].shift(1))
    short_break = (d["close"] < d["kc_lower"]) & (d["close"].shift(1) >= d["kc_lower"].shift(1))
    le = long_break & (d["rsi"] > 55)
    se = short_break & (d["rsi"] < 45)
    long_exit = (d["close"] < d["ema20"]) | ((d["close"] < d["kc_lower"]) & (d["close"].shift(1) >= d["kc_lower"].shift(1)))
    short_exit = (d["close"] > d["ema20"]) | ((d["close"] > d["kc_upper"]) & (d["close"].shift(1) <= d["kc_upper"].shift(1)))
    return backtest_strategy(d, le, se, long_exit, short_exit)


def strategy_aggressive_entry(df):
    """10 Aggressive Entry — exact match to Pine Script."""
    d = calc_indicators(df)
    ema_cross_up = (d["ema9"] > d["ema21"]) & (d["ema9"].shift(1) <= d["ema21"].shift(1))
    ema_cross_down = (d["ema9"] < d["ema21"]) & (d["ema9"].shift(1) >= d["ema21"].shift(1))
    vol_spike = d["volume"] > d["vol_sma"] * 1.2
    rsi_above = d["rsi"] > 50
    rsi_below = d["rsi"] < 50
    le = ema_cross_up & rsi_above & vol_spike
    se = ema_cross_down & rsi_below & vol_spike
    rsi_cross_below = (d["rsi"] < 50) & (d["rsi"].shift(1) >= 50)
    rsi_cross_above = (d["rsi"] > 50) & (d["rsi"].shift(1) <= 50)
    long_exit = ema_cross_down | rsi_cross_below
    short_exit = ema_cross_up | rsi_cross_above
    return backtest_strategy(d, le, se, long_exit, short_exit)


STRATEGIES = {
    "Ichimoku_Trend_Pro": strategy_ichimoku_trend_pro,
    "Keltner_Breakout": strategy_keltner_breakout,
    "Aggressive_Entry": strategy_aggressive_entry,
}

if __name__ == "__main__":
    # All assets from tournament system
    ASSETS = [
        "FILUSDT", "LDOUSDT", "SUIUSDT", "OPUSDT", "INJUSDT",
        "DOGEUSDT", "SOLUSDT", "AVAXUSDT", "ARBUSDT", "APTUSDT",
        "LINKUSDT", "NEARUSDT", "ADAUSDT", "ETHUSDT", "BTCUSDT",
        "BNBUSDT", "XRPUSDT", "ATOMUSDT", "AAVEUSDT",
    ]

    print("=" * 100, flush=True)
    print("  PROVEN STRATEGIES — Ichimoku + Keltner + Aggressive", flush=True)
    print("  Matching exact Pine Script logic | 15m data | Long + Short", flush=True)
    print("=" * 100, flush=True)

    results = []
    for asset in ASSETS:
        df = load_any_data(asset, "15m")
        if df is None:
            continue
        if "timestamp" in df.columns:
            try:
                yrs = max((datetime.fromisoformat(str(df["timestamp"].iloc[-1])[:10]) -
                           datetime.fromisoformat(str(df["timestamp"].iloc[0])[:10])).days / 365.25, 0.01)
            except:
                yrs = 3.0
        else:
            yrs = 3.0
        n_bars = len(df)

        for strat_name, strat_func in STRATEGIES.items():
            try:
                cap, trades = strat_func(df)
                if len(trades) < 10:
                    continue
                roi_a = ((cap / INITIAL_CAPITAL) ** (1 / yrs) - 1) * 100 if cap > 0 else -100
                daily = roi_a / 365
                wins = [t for t in trades if t["pnl"] > 0]
                wr = len(wins) / len(trades) * 100
                tw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                tl = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                pf = tw / tl if tl > 0 else 0
                longs = len([t for t in trades if t["side"] == "long"])
                shorts = len([t for t in trades if t["side"] == "short"])
                eq = INITIAL_CAPITAL; pk = eq; gdd = 0
                for t in trades:
                    eq += t["pnl"]; pk = max(pk, eq)
                    dd = (pk - eq) / pk * 100; gdd = max(gdd, dd)
                results.append((daily, roi_a, asset, strat_name, pf, wr, len(trades), longs, shorts, gdd, cap, n_bars))
            except Exception as e:
                print(f"  ERROR: {asset} {strat_name}: {e}", flush=True)

        print(f"  {asset}: {n_bars} bars, {len([r for r in results if r[2]==asset])} results", flush=True)

    results.sort(key=lambda x: -x[0])
    print(f"\n{'='*100}", flush=True)
    print(f"  TOP 20 RESULTS", flush=True)
    print(f"{'='*100}", flush=True)
    print(f"  # {'ROI/d':>7} {'ROI/yr':>7} {'Asset':<12} {'Strategy':<22} {'PF':>5} {'WR%':>5} {'Trd':>5} {'L':>4} {'S':>4} {'GDD':>5} {'Final$':>10}", flush=True)
    print(f"  {'-'*100}", flush=True)

    seen = set()
    n = 0
    for r in results:
        k = (r[2], r[3])
        if k in seen:
            continue
        seen.add(k)
        n += 1
        if n > 20:
            break
        daily, roi, asset, strat, pf, wr, tr, l, s, gdd, cap, _ = r
        tag = " <<<" if daily >= 0.25 else ""
        print(f"  {n:<2} {daily:>6.3f}% {roi:>6.1f}% {asset:<12} {strat:<22} {pf:>5.2f} {wr:>5.1f} {tr:>5} {l:>4} {s:>4} {gdd:>5.1f}  ${cap:>9,.0f}{tag}", flush=True)

    above_025 = len(set((r[2], r[3]) for r in results if r[0] >= 0.25))
    above_01 = len(set((r[2], r[3]) for r in results if r[0] >= 0.1))
    print(f"\n  >= 0.25%/day: {above_025} | >= 0.1%/day: {above_01} | Total: {len(set((r[2],r[3]) for r in results))}", flush=True)
    print("DONE", flush=True)
