#!/usr/bin/env python3
"""Continuous strategy search — runs until 3%/day found or stopped.
Uses tournament-style risk filters: ADX, ATR, cooldown, circuit breaker.
Tests all assets, all param combos, saves every result."""
import sys, os, json, random, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import numpy as np
from datetime import datetime
from itertools import combinations

INITIAL_CAPITAL = 10000
FEE = 0.001
TARGET = 3.0  # %/day
STORAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage")
TOURNAMENT_DIR = "/home/ubuntu/tradingview_webhook_bot/storage/backtest_data"
DATA_DIR = "storage/historical_data"


def load_data(symbol):
    csv_path = os.path.join(TOURNAMENT_DIR, f"{symbol}_3y_15m.csv")
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    for f in sorted(os.listdir(DATA_DIR), reverse=True):
        if f.startswith(f"{symbol}_15m") and f.endswith(".parquet"):
            try:
                return pd.read_parquet(os.path.join(DATA_DIR, f))
            except:
                continue
    return None


def calc_indicators(df, mult=2.0, length=14):
    d = df.copy()
    d["ema9"] = d["close"].ewm(span=9).mean()
    d["ema21"] = d["close"].ewm(span=21).mean()
    d["ema20"] = d["close"].ewm(span=20).mean()
    d["ema50"] = d["close"].ewm(span=50).mean()
    delta = d["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    d["rsi"] = 100 - (100 / (1 + rs))
    d["vol_sma"] = d["volume"].rolling(20).mean()
    high_low = d["high"] - d["low"]
    high_close = abs(d["high"] - d["close"].shift())
    low_close = abs(d["low"] - d["close"].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    d["atr14"] = tr.rolling(14).mean()
    d["atr10"] = tr.rolling(10).mean()
    d["atr_ma100"] = d["atr14"].rolling(100).mean()
    # Keltner
    d["kc_upper"] = d["ema20"] + mult * d["atr10"]
    d["kc_lower"] = d["ema20"] - mult * d["atr10"]
    # Ichimoku
    d["tenkan"] = (d["high"].rolling(9).max() + d["low"].rolling(9).min()) / 2
    d["kijun"] = (d["high"].rolling(26).max() + d["low"].rolling(26).min()) / 2
    d["senkou_a"] = ((d["tenkan"] + d["kijun"]) / 2).shift(26)
    d["senkou_b"] = ((d["high"].rolling(52).max() + d["low"].rolling(52).min()) / 2).shift(26)
    d["cloud_top"] = d[["senkou_a", "senkou_b"]].max(axis=1)
    d["cloud_bottom"] = d[["senkou_a", "senkou_b"]].min(axis=1)
    d["chikou_past"] = d["close"].shift(26)
    # MACD
    d["macd"] = d["close"].ewm(span=12).mean() - d["close"].ewm(span=26).mean()
    d["macd_signal"] = d["macd"].ewm(span=9).mean()
    # Supertrend
    hl_avg = (d["high"] + d["low"]) / 2
    d["supertrend"] = hl_avg - mult * d["atr14"]
    # Bollinger
    d["bb_mid"] = d["close"].rolling(20).mean()
    d["bb_upper"] = d["bb_mid"] + 2 * d["close"].rolling(20).std()
    d["bb_lower"] = d["bb_mid"] - 2 * d["close"].rolling(20).std()
    # ADX
    plus_dm = d["high"].diff().clip(lower=0)
    minus_dm = (-d["low"].diff()).clip(lower=0)
    plus_di = 100 * plus_dm.rolling(length).mean() / d["atr14"]
    minus_di = 100 * minus_dm.rolling(length).mean() / d["atr14"]
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)
    d["adx"] = dx.rolling(length).mean()
    # Stochastic
    low14 = d["low"].rolling(14).min()
    high14 = d["high"].rolling(14).max()
    d["stoch_k"] = 100 * (d["close"] - low14) / (high14 - low14)
    return d


def backtest_with_filters(df, long_entry, short_entry, long_exit, short_exit,
                          sl_pct=0.01, tp_pct=0.03, use_adx=True, use_atr=True,
                          cooldown_losses=3, cooldown_bars=4, circuit_breaker_pct=0.03):
    """Backtest with tournament-style risk management."""
    capital = INITIAL_CAPITAL
    position = 0
    entry_price = 0
    position_size = 0
    trades = []
    consecutive_losses = 0
    cooldown_remaining = 0
    daily_pnl = 0
    current_day = None
    circuit_breaker_active = False

    for i in range(1, len(df)):
        bar = df.iloc[i]
        price = bar["close"]
        high = bar["high"]
        low = bar["low"]

        # Daily reset
        if "timestamp" in df.columns:
            day = str(bar["timestamp"])[:10]
        else:
            day = str(i // 96)
        if day != current_day:
            current_day = day
            daily_pnl = 0
            circuit_breaker_active = False

        # Cooldown
        if cooldown_remaining > 0:
            cooldown_remaining -= 1
            continue

        # Circuit breaker
        if circuit_breaker_active:
            continue

        # Filters
        adx_ok = bar.get("adx", 25) > 20 if use_adx else True
        atr_ok = bar.get("atr14", 0) < bar.get("atr_ma100", float("inf")) * 2 if use_atr else True

        if position == 1:
            exit_price = None
            # SL/TP caps
            if sl_pct > 0 and low <= entry_price * (1 - sl_pct):
                exit_price = entry_price * (1 - sl_pct) * (1 - FEE)
                reason = "SL"
            elif tp_pct > 0 and high >= entry_price * (1 + tp_pct):
                exit_price = entry_price * (1 + tp_pct) * (1 - FEE)
                reason = "TP"
            elif long_exit.iloc[i] or (short_entry.iloc[i] and adx_ok and atr_ok):
                exit_price = price * (1 - FEE)
                reason = "SIGNAL"

            if exit_price:
                pnl = (exit_price - entry_price) * position_size
                capital += pnl
                daily_pnl += pnl / INITIAL_CAPITAL * 100
                trades.append({"pnl": pnl, "return_pct": (exit_price / entry_price - 1) * 100, "side": "long", "reason": reason})
                position = 0
                if pnl < 0:
                    consecutive_losses += 1
                    if consecutive_losses >= cooldown_losses:
                        cooldown_remaining = cooldown_bars
                        consecutive_losses = 0
                else:
                    consecutive_losses = 0
                if daily_pnl < -circuit_breaker_pct * 100:
                    circuit_breaker_active = True
                # Flip to short
                if short_entry.iloc[i] and adx_ok and atr_ok and not circuit_breaker_active and reason == "SIGNAL":
                    entry_price = price * (1 - FEE)
                    position_size = capital / entry_price
                    position = -1

        elif position == -1:
            exit_price = None
            if sl_pct > 0 and high >= entry_price * (1 + sl_pct):
                exit_price = entry_price * (1 + sl_pct) * (1 + FEE)
                reason = "SL"
            elif tp_pct > 0 and low <= entry_price * (1 - tp_pct):
                exit_price = entry_price * (1 - tp_pct) * (1 + FEE)
                reason = "TP"
            elif short_exit.iloc[i] or (long_entry.iloc[i] and adx_ok and atr_ok):
                exit_price = price * (1 + FEE)
                reason = "SIGNAL"

            if exit_price:
                pnl = (entry_price - exit_price) * position_size
                capital += pnl
                daily_pnl += pnl / INITIAL_CAPITAL * 100
                trades.append({"pnl": pnl, "return_pct": (entry_price / exit_price - 1) * 100, "side": "short", "reason": reason})
                position = 0
                if pnl < 0:
                    consecutive_losses += 1
                    if consecutive_losses >= cooldown_losses:
                        cooldown_remaining = cooldown_bars
                        consecutive_losses = 0
                else:
                    consecutive_losses = 0
                if daily_pnl < -circuit_breaker_pct * 100:
                    circuit_breaker_active = True
                if long_entry.iloc[i] and adx_ok and atr_ok and not circuit_breaker_active and reason == "SIGNAL":
                    entry_price = price * (1 + FEE)
                    position_size = capital / entry_price
                    position = 1

        elif position == 0:
            if not circuit_breaker_active and adx_ok and atr_ok:
                if long_entry.iloc[i]:
                    entry_price = price * (1 + FEE)
                    position_size = capital / entry_price
                    position = 1
                elif short_entry.iloc[i]:
                    entry_price = price * (1 - FEE)
                    position_size = capital / entry_price
                    position = -1

    return capital, trades


# ── Strategy definitions ──

def strat_ichimoku(d):
    le = (d["close"] > d["cloud_top"]) & (d["tenkan"] > d["kijun"]) & (d["close"] > d["chikou_past"])
    se = (d["close"] < d["cloud_bottom"]) & (d["tenkan"] < d["kijun"])
    le = le & ~le.shift(1).fillna(False)
    se = se & ~se.shift(1).fillna(False)
    lx = ((d["tenkan"] < d["kijun"]) & (d["tenkan"].shift(1) >= d["kijun"].shift(1))) | (d["close"] < d["cloud_bottom"])
    sx = ((d["tenkan"] > d["kijun"]) & (d["tenkan"].shift(1) <= d["kijun"].shift(1))) | (d["close"] > d["cloud_top"])
    return le, se, lx, sx

def strat_keltner(d):
    le = ((d["close"] > d["kc_upper"]) & (d["close"].shift(1) <= d["kc_upper"].shift(1))) & (d["rsi"] > 55)
    se = ((d["close"] < d["kc_lower"]) & (d["close"].shift(1) >= d["kc_lower"].shift(1))) & (d["rsi"] < 45)
    lx = (d["close"] < d["ema20"]) | ((d["close"] < d["kc_lower"]) & (d["close"].shift(1) >= d["kc_lower"].shift(1)))
    sx = (d["close"] > d["ema20"]) | ((d["close"] > d["kc_upper"]) & (d["close"].shift(1) <= d["kc_upper"].shift(1)))
    return le, se, lx, sx

def strat_aggressive(d):
    eu = (d["ema9"] > d["ema21"]) & (d["ema9"].shift(1) <= d["ema21"].shift(1))
    ed = (d["ema9"] < d["ema21"]) & (d["ema9"].shift(1) >= d["ema21"].shift(1))
    vs = d["volume"] > d["vol_sma"] * 1.2
    le = eu & (d["rsi"] > 50) & vs
    se = ed & (d["rsi"] < 50) & vs
    lx = ed | ((d["rsi"] < 50) & (d["rsi"].shift(1) >= 50))
    sx = eu | ((d["rsi"] > 50) & (d["rsi"].shift(1) <= 50))
    return le, se, lx, sx

def strat_macd_breakout(d):
    le = ((d["macd"] > d["macd_signal"]) & (d["macd"].shift(1) <= d["macd_signal"].shift(1))) & (d["close"] > d["ema20"])
    se = ((d["macd"] < d["macd_signal"]) & (d["macd"].shift(1) >= d["macd_signal"].shift(1))) & (d["close"] < d["ema20"])
    lx = (d["macd"] < d["macd_signal"]) & (d["macd"].shift(1) >= d["macd_signal"].shift(1))
    sx = (d["macd"] > d["macd_signal"]) & (d["macd"].shift(1) <= d["macd_signal"].shift(1))
    return le, se, lx, sx

def strat_supertrend_rsi(d):
    st_bull = d["close"] > d["supertrend"]
    le = (st_bull & ~st_bull.shift(1).fillna(False)) & (d["rsi"] > 50)
    se = (~st_bull & st_bull.shift(1).fillna(True)) & (d["rsi"] < 50)
    lx = ~st_bull & st_bull.shift(1).fillna(True)
    sx = st_bull & ~st_bull.shift(1).fillna(False)
    return le, se, lx, sx

def strat_bb_squeeze(d):
    squeeze = (d["bb_upper"] < d["kc_upper"]) & (d["bb_lower"] > d["kc_lower"])
    release = ~squeeze & squeeze.shift(1).fillna(False)
    mom = d["close"] - d["close"].shift(20)
    le = release & (mom > 0) & (d["adx"] > 20)
    se = release & (mom < 0) & (d["adx"] > 20)
    lx = (d["close"] < d["bb_mid"]) | ((d["close"] < d["kc_lower"]) & (d["close"].shift(1) >= d["kc_lower"].shift(1)))
    sx = (d["close"] > d["bb_mid"]) | ((d["close"] > d["kc_upper"]) & (d["close"].shift(1) <= d["kc_upper"].shift(1)))
    return le, se, lx, sx

def strat_stoch_ema(d):
    le = ((d["stoch_k"] > 20) & (d["stoch_k"].shift(1) <= 20)) & (d["ema9"] > d["ema21"])
    se = ((d["stoch_k"] < 80) & (d["stoch_k"].shift(1) >= 80)) & (d["ema9"] < d["ema21"])
    lx = (d["stoch_k"] > 80) | ((d["ema9"] < d["ema21"]) & (d["ema9"].shift(1) >= d["ema21"].shift(1)))
    sx = (d["stoch_k"] < 20) | ((d["ema9"] > d["ema21"]) & (d["ema9"].shift(1) <= d["ema21"].shift(1)))
    return le, se, lx, sx


STRATEGIES = {
    "Ichimoku_Trend_Pro": strat_ichimoku,
    "Keltner_Breakout": strat_keltner,
    "Aggressive_Entry": strat_aggressive,
    "MACD_Breakout": strat_macd_breakout,
    "SuperTrend_RSI": strat_supertrend_rsi,
    "BB_Squeeze_Break": strat_bb_squeeze,
    "Stoch_EMA": strat_stoch_ema,
}

PARAM_GRID = [
    {"mult": 1.5, "len": 7, "sl": 0.01, "tp": 0.03},
    {"mult": 1.8, "len": 9, "sl": 0.01, "tp": 0.03},
    {"mult": 2.0, "len": 11, "sl": 0.01, "tp": 0.03},
    {"mult": 2.5, "len": 14, "sl": 0.01, "tp": 0.03},
    {"mult": 3.0, "len": 18, "sl": 0.015, "tp": 0.04},
    {"mult": 3.5, "len": 21, "sl": 0.015, "tp": 0.05},
    {"mult": 4.0, "len": 26, "sl": 0.02, "tp": 0.06},
    {"mult": 2.0, "len": 14, "sl": 0.008, "tp": 0.025},
    {"mult": 2.5, "len": 14, "sl": 0.012, "tp": 0.035},
    {"mult": 2.0, "len": 11, "sl": 0, "tp": 0},  # signal-only exits
]

ASSETS = [
    "FILUSDT", "LDOUSDT", "SUIUSDT", "OPUSDT", "INJUSDT",
    "DOGEUSDT", "SOLUSDT", "AVAXUSDT", "ARBUSDT", "APTUSDT",
    "LINKUSDT", "NEARUSDT", "ADAUSDT", "ETHUSDT", "BTCUSDT",
    "BNBUSDT", "XRPUSDT", "ATOMUSDT", "AAVEUSDT", "UNIUSDT",
]


if __name__ == "__main__":
    print(f"{'='*100}", flush=True)
    print(f"  CONTINUOUS SEARCH — Target {TARGET}%/day", flush=True)
    print(f"  7 strategies x 10 params x 20 assets = 1400 tests", flush=True)
    print(f"  Risk filters: ADX>20, ATR<2x, Cooldown(3L,4bars), Circuit(-3%/day)", flush=True)
    print(f"{'='*100}\n", flush=True)

    all_results = []
    total = 0
    best_daily = 0

    for asset in ASSETS:
        df_raw = load_data(asset)
        if df_raw is None:
            print(f"  {asset}: NO DATA", flush=True)
            continue

        if "timestamp" in df_raw.columns:
            yrs = max((datetime.fromisoformat(str(df_raw["timestamp"].iloc[-1])[:10]) -
                       datetime.fromisoformat(str(df_raw["timestamp"].iloc[0])[:10])).days / 365.25, 0.01)
        else:
            yrs = 3.0

        for params in PARAM_GRID:
            d = calc_indicators(df_raw, mult=params["mult"], length=params["len"])

            for strat_name, strat_func in STRATEGIES.items():
                total += 1
                try:
                    le, se, lx, sx = strat_func(d)
                    cap, trades = backtest_with_filters(
                        d, le, se, lx, sx,
                        sl_pct=params["sl"], tp_pct=params["tp"],
                    )
                    if len(trades) < 20:
                        continue
                    roi_a = ((cap / INITIAL_CAPITAL) ** (1 / yrs) - 1) * 100 if cap > 0 else -100
                    daily = roi_a / 365
                    if daily < 0.05:
                        continue
                    wins = [t for t in trades if t["pnl"] > 0]
                    wr = len(wins) / len(trades) * 100
                    tw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                    tl = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                    pf = tw / tl if tl > 0 else 0
                    eq = INITIAL_CAPITAL; pk = eq; gdd = 0
                    for t in trades:
                        eq += t["pnl"]; pk = max(pk, eq)
                        dd = (pk - eq) / pk * 100; gdd = max(gdd, dd)

                    r = {
                        "asset": asset, "strategy": strat_name,
                        "roi_day": round(daily, 4), "roi_yr": round(roi_a, 1),
                        "pf": round(pf, 2), "wr": round(wr, 1), "gdd": round(gdd, 1),
                        "trades": len(trades), "final_cap": round(cap, 0),
                        "mult": params["mult"], "len": params["len"],
                        "sl": params["sl"], "tp": params["tp"],
                    }
                    all_results.append(r)

                    if daily > best_daily:
                        best_daily = daily
                        print(f"  ** NEW BEST: {daily:.3f}%/day | {asset} | {strat_name} | PF={pf:.2f} WR={wr:.1f}% GDD={gdd:.1f}% Trades={len(trades)} | mult={params['mult']} len={params['len']} **", flush=True)
                    elif daily >= 0.25:
                        print(f"  {daily:.3f}%/day | {asset} | {strat_name} | PF={pf:.2f} WR={wr:.1f}% Trades={len(trades)}", flush=True)

                except Exception:
                    continue

        # Save after each asset
        all_results.sort(key=lambda x: -x["roi_day"])
        save_path = os.path.join(STORAGE, "continuous_search_results.json")
        with open(save_path, "w") as f:
            json.dump({
                "status": "running",
                "total_tested": total,
                "total_found": len(all_results),
                "best_daily": round(best_daily, 4),
                "target": TARGET,
                "above_3": len([r for r in all_results if r["roi_day"] >= 3.0]),
                "above_1": len([r for r in all_results if r["roi_day"] >= 1.0]),
                "above_05": len([r for r in all_results if r["roi_day"] >= 0.5]),
                "above_025": len([r for r in all_results if r["roi_day"] >= 0.25]),
                "strategies": all_results[:100],
            }, f, indent=2)
        print(f"  {asset}: {total} tested, {len(all_results)} found, best={best_daily:.3f}%/day", flush=True)

    # Final summary
    print(f"\n{'='*100}", flush=True)
    print(f"  SEARCH COMPLETE", flush=True)
    print(f"  Tested: {total} | Found: {len(all_results)} | Best: {best_daily:.3f}%/day", flush=True)
    print(f"  >= 3%: {len([r for r in all_results if r['roi_day'] >= 3.0])}", flush=True)
    print(f"  >= 1%: {len([r for r in all_results if r['roi_day'] >= 1.0])}", flush=True)
    print(f"  >= 0.5%: {len([r for r in all_results if r['roi_day'] >= 0.5])}", flush=True)
    print(f"  >= 0.25%: {len([r for r in all_results if r['roi_day'] >= 0.25])}", flush=True)
    print(f"{'='*100}", flush=True)

    # Print top 20
    seen = set()
    n = 0
    for r in all_results:
        k = (r["asset"], r["strategy"])
        if k in seen: continue
        seen.add(k)
        n += 1
        if n > 20: break
        print(f"  {n}. {r['roi_day']:.3f}%/day | {r['asset']} | {r['strategy']} | PF={r['pf']} WR={r['wr']}% GDD={r['gdd']}% Trades={r['trades']} | m={r['mult']} l={r['len']}", flush=True)
    print("DONE", flush=True)
