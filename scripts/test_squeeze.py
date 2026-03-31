#!/usr/bin/env python3
"""Test BB Squeeze Break strategy — matching the Pine Script."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from run_strategies_batch import load_data, calculate_indicators, INITIAL_CAPITAL
import pandas as pd
import numpy as np
from datetime import datetime

FEE = 0.0003


def bb_squeeze_strategy(df, bb_len=20, bb_mult=2.0, kc_len=20, kc_mult=1.5):
    d = df.copy()

    # Bollinger Bands
    d["bb_basis"] = d["close"].rolling(bb_len).mean()
    d["bb_std"] = d["close"].rolling(bb_len).std()
    d["bb_upper"] = d["bb_basis"] + bb_mult * d["bb_std"]
    d["bb_lower"] = d["bb_basis"] - bb_mult * d["bb_std"]

    # Keltner Channel
    d["kc_basis"] = d["close"].ewm(span=kc_len).mean()
    high_low = d["high"] - d["low"]
    high_close = abs(d["high"] - d["close"].shift())
    low_close = abs(d["low"] - d["close"].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    d["kc_atr"] = tr.rolling(kc_len).mean()
    d["kc_upper"] = d["kc_basis"] + kc_mult * d["kc_atr"]
    d["kc_lower"] = d["kc_basis"] - kc_mult * d["kc_atr"]

    # Squeeze
    d["squeeze_on"] = ((d["bb_upper"] < d["kc_upper"]) & (d["bb_lower"] > d["kc_lower"])).astype(int)
    d["squeeze_release"] = ((d["squeeze_on"] == 0) & (d["squeeze_on"].shift(1) == 1)).astype(int)

    # Momentum (linear regression of delta)
    highest = d["high"].rolling(bb_len).max()
    lowest = d["low"].rolling(bb_len).min()
    delta = d["close"] - ((highest + lowest) / 2 + d["bb_basis"]) / 2
    # Simple linreg approximation
    momentum = delta.rolling(bb_len).apply(
        lambda x: np.polyfit(range(len(x)), x, 1)[0] * (len(x) - 1) + x.mean() if len(x) == bb_len else 0,
        raw=False
    )
    d["momentum"] = momentum

    # ADX filter
    plus_dm = d["high"].diff().clip(lower=0)
    minus_dm = (-d["low"].diff()).clip(lower=0)
    atr14 = tr.rolling(14).mean()
    plus_di = 100 * plus_dm.rolling(14).mean() / atr14
    minus_di = 100 * minus_dm.rolling(14).mean() / atr14
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)
    d["adx"] = dx.rolling(14).mean()
    d["adx_ok"] = (d["adx"] > 20).astype(int)

    # ATR vol filter
    d["atr14"] = atr14
    d["atr_ma100"] = atr14.rolling(100).mean()
    d["vol_ok"] = (d["atr14"] < d["atr_ma100"] * 2).astype(int)

    # Signals
    d["long_signal"] = ((d["squeeze_release"] == 1) & (d["momentum"] > 0) & (d["adx_ok"] == 1) & (d["vol_ok"] == 1)).astype(int)
    d["short_signal"] = ((d["squeeze_release"] == 1) & (d["momentum"] < 0) & (d["adx_ok"] == 1) & (d["vol_ok"] == 1)).astype(int)

    return d


def backtest_squeeze(df, sl_pct=0.01, tp_pct=0.03, ts_pct=0.02):
    capital = INITIAL_CAPITAL
    trades = []
    i = 0
    while i < len(df) - 2:
        row = df.iloc[i]
        if row["long_signal"] == 1 or row["short_signal"] == 1:
            side = "long" if row["long_signal"] == 1 else "short"
            entry_price = df.iloc[i + 1]["open"] * (1 + FEE if side == "long" else 1 - FEE)
            qty = capital * 0.95 / entry_price
            peak = entry_price
            exit_price = None
            reason = "timeout"

            for j in range(i + 2, min(i + 200, len(df))):
                bar = df.iloc[j]
                if side == "long":
                    peak = max(peak, bar["high"])
                    trail_stop = peak * (1 - ts_pct)
                    if bar["low"] <= entry_price * (1 - sl_pct):
                        exit_price = entry_price * (1 - sl_pct) * (1 - FEE)
                        reason = "SL"
                        break
                    elif bar["high"] >= entry_price * (1 + tp_pct):
                        exit_price = entry_price * (1 + tp_pct) * (1 - FEE)
                        reason = "TP"
                        break
                    elif peak > entry_price * 1.005 and bar["low"] <= trail_stop:
                        exit_price = trail_stop * (1 - FEE)
                        reason = "TS"
                        break
                else:
                    peak = min(peak, bar["low"])
                    trail_stop = peak * (1 + ts_pct)
                    if bar["high"] >= entry_price * (1 + sl_pct):
                        exit_price = entry_price * (1 + sl_pct) * (1 + FEE)
                        reason = "SL"
                        break
                    elif bar["low"] <= entry_price * (1 - tp_pct):
                        exit_price = entry_price * (1 - tp_pct) * (1 + FEE)
                        reason = "TP"
                        break
                    elif peak < entry_price * 0.995 and bar["high"] >= trail_stop:
                        exit_price = trail_stop * (1 + FEE)
                        reason = "TS"
                        break

            if exit_price is None:
                j_end = min(i + 200, len(df) - 1)
                exit_price = df.iloc[j_end]["close"] * (1 - FEE if side == "long" else 1 + FEE)
                j = j_end

            if side == "long":
                pnl = (exit_price - entry_price) * qty
            else:
                pnl = (entry_price - exit_price) * qty

            capital += pnl
            trades.append({"side": side, "pnl": round(pnl, 2), "reason": reason})
            i = j + 1
        else:
            i += 1

    return capital, trades


if __name__ == "__main__":
    ASSETS = ["ETHUSDT", "BTCUSDT", "ADAUSDT", "SOLUSDT", "LINKUSDT", "BNBUSDT"]
    TFS = ["4h", "1h"]
    PARAMS = [
        (0.01, 0.03, 0.02),   # Pine Script original
        (0.008, 0.025, 0.015),
        (0.01, 0.04, 0.02),
        (0.015, 0.05, 0.025),
        (0.01, 0.02, 0.015),
        (0.008, 0.02, 0.01),
        (0.005, 0.015, 0.01),
    ]

    print("=" * 100, flush=True)
    print("  BB SQUEEZE BREAK — Long + Short (2024+ data)", flush=True)
    print("=" * 100, flush=True)

    results = []
    for tf in TFS:
        for asset in ASSETS:
            df = load_data(f"{asset}_{tf}")
            if df is None:
                continue
            if "timestamp" in df.columns:
                df = df[df["timestamp"] >= "2024-01-01"].copy()
            if len(df) < 200:
                continue

            df_sq = bb_squeeze_strategy(df)
            if "timestamp" in df.columns:
                yrs = max((datetime.fromisoformat(str(df["timestamp"].iloc[-1])[:10]) - datetime.fromisoformat(str(df["timestamp"].iloc[0])[:10])).days / 365.25, 0.01)
            else:
                yrs = 2.0

            n_long = int(df_sq["long_signal"].sum())
            n_short = int(df_sq["short_signal"].sum())

            for sl, tp, ts in PARAMS:
                cap, trades = backtest_squeeze(df_sq, sl, tp, ts)
                if len(trades) < 3:
                    continue
                roi_a = ((cap / INITIAL_CAPITAL) ** (1 / yrs) - 1) * 100 if cap > 0 else -100
                daily = roi_a / 365
                if daily < -1:
                    continue
                w = [t for t in trades if t["pnl"] > 0]
                wr = len(w) / len(trades) * 100
                tw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                tl = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                pf = tw / tl if tl > 0 else 0
                longs = len([t for t in trades if t["side"] == "long"])
                shorts = len([t for t in trades if t["side"] == "short"])
                tp_hits = len([t for t in trades if t["reason"] == "TP"])
                sl_hits = len([t for t in trades if t["reason"] == "SL"])
                ts_hits = len([t for t in trades if t["reason"] == "TS"])
                results.append((daily, roi_a, asset, tf, pf, wr, len(trades), longs, shorts,
                               tp_hits, sl_hits, ts_hits, sl * 100, tp * 100, ts * 100, cap))

            print(f"  {asset} {tf}: {n_long} longs, {n_short} shorts, {len(df)} bars", flush=True)

    results.sort(key=lambda x: -x[0])
    seen = set()
    n = 0
    print(f"\nTOP 20 BB SQUEEZE RESULTS:", flush=True)
    print(f"  # ROI/d   ROI/yr  Asset      TF   PF    WR%  Trades  L    S   TP   SL   TS  SL%  TP%  TS%   Final$", flush=True)
    print(f"  {'-' * 105}", flush=True)
    for r in results:
        k = (r[2], r[3])
        if k in seen:
            continue
        seen.add(k)
        n += 1
        if n > 20:
            break
        daily, roi, asset, tf, pf, wr, tr, l, s, tp_h, sl_h, ts_h, sl, tp, ts, cap = r
        tag = " *** 1%+ ***" if daily >= 1.0 else (" ** 0.5%+ **" if daily >= 0.5 else "")
        print(f"  {n:<2} {daily:>6.3f}% {roi:>7.1f}% {asset:<10} {tf:<4} {pf:>5.2f} {wr:>5.1f} {tr:>6} {l:>4} {s:>4} {tp_h:>4} {sl_h:>4} {ts_h:>4} {sl:>4} {tp:>4} {ts:>4}  ${cap:>9,.0f}{tag}", flush=True)

    above1 = len(set((r[2], r[3]) for r in results if r[0] >= 1.0))
    above05 = len(set((r[2], r[3]) for r in results if r[0] >= 0.5))
    print(f"\n>= 1%/day: {above1} | >= 0.5%/day: {above05}", flush=True)
    print("DONE", flush=True)
