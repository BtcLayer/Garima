#!/usr/bin/env python3
"""
ML + Generate Hybrid — combines /generate's 5 methods with ML filtering.
1. ATR-adaptive SL/TP (volatility-based, not fixed %)
2. High-TP hunter (15-40% TP for big moves)
3. Trend+Dip hybrid entries (trend filter + dip entry)
4. Mean reversion entries with ML filter
5. Random mutation with ML quality scoring
"""
import sys, os, json, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd, numpy as np
from run_strategies_batch import load_data, calculate_indicators, INITIAL_CAPITAL
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.preprocessing import StandardScaler

FEE = 0.001
STORAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage")

ASSETS = ["ETHUSDT", "BTCUSDT", "ADAUSDT", "SOLUSDT", "LINKUSDT",
          "BNBUSDT", "XRPUSDT", "AVAXUSDT", "DOTUSDT", "LTCUSDT"]


def get_atr_params(df):
    """ATR-adaptive SL/TP — from generate method 1."""
    avg_atr_pct = (df["atr"] / df["close"]).mean()
    params = []
    for sl_mult in [1.0, 1.5, 2.0, 3.0]:
        for tp_mult in [3, 5, 8, 12, 15, 20]:
            sl = avg_atr_pct * sl_mult
            tp = avg_atr_pct * tp_mult
            if tp > sl * 1.5 and tp > 0.01 and sl > 0.003:
                params.append((round(tp, 4), round(sl, 4)))
    return params


def entry_trend_dip(df):
    """Trend+Dip hybrid — from generate method 5.
    Trend filter (EMA/Supertrend) + dip entry (RSI/BB/Stoch)."""
    trends = {
        "ema_trend": df["close"] > df["ema50"],
        "supertrend": df["close"] > df["supertrend"],
        "psar": df["close"] > df["psar"],
        "ichimoku": (df["close"] > df["senkou_span_a"]) & (df["close"] > df["senkou_span_b"]),
    }
    dips = {
        "rsi_dip": (df["rsi"] < 35) & (df["rsi"] > df["rsi"].shift(1)),
        "bb_dip": df["close"] < df["bb_lower"],
        "stoch_dip": (df["stoch_k"] < 25) & (df["stoch_k"] > df["stoch_k"].shift(1)),
        "cci_dip": (df["cci"] < -80) & (df["cci"] > df["cci"].shift(1)),
        "mfi_dip": (df["mfi"] < 25) & (df["mfi"] > df["mfi"].shift(1)),
        "keltner_dip": df["close"] < df["keltner_lower"],
        "williams_dip": (df["williams_r"] < -75) & (df["williams_r"] > df["williams_r"].shift(1)),
    }
    combos = []
    for t_name, t_sig in trends.items():
        for d_name, d_sig in dips.items():
            bull = (t_sig & d_sig).astype(int)
            bear_trend = ~t_sig
            bear_dip = {
                "rsi_dip": (df["rsi"] > 65) & (df["rsi"] < df["rsi"].shift(1)),
                "bb_dip": df["close"] > df["bb_upper"],
                "stoch_dip": (df["stoch_k"] > 75) & (df["stoch_k"] < df["stoch_k"].shift(1)),
            }.get(d_name, pd.Series(0, index=df.index))
            bear = (bear_trend & bear_dip).astype(int) if isinstance(bear_dip, pd.Series) else pd.Series(0, index=df.index)
            combos.append((f"{t_name}+{d_name}", bull, bear))
    return combos


def entry_mean_reversion(df):
    """Mean reversion entries — from generate method 4."""
    combos = []
    # Single dip signals
    dips = {
        "RSI_bounce": ((df["rsi"] < 30) & (df["rsi"] > df["rsi"].shift(1))).astype(int),
        "BB_bounce": ((df["close"] < df["bb_lower"]) & (df["close"] > df["close"].shift(1))).astype(int),
        "Stoch_bounce": ((df["stoch_k"] < 20) & (df["stoch_k"] > df["stoch_k"].shift(1))).astype(int),
        "Multi_dip": (
            ((df["rsi"] < 35).astype(int) + (df["stoch_k"] < 25).astype(int) + (df["cci"] < -80).astype(int)) >= 2
        ).astype(int),
    }
    for name, bull in dips.items():
        bear = pd.Series(0, index=df.index)  # mean reversion = long only primarily
        combos.append((name, bull, bear))
    return combos


def entry_high_tp(df):
    """High-TP entries — from generate method 4. Strong trend signals for big moves."""
    combos = []
    entries = {
        "Breakout_Volume": ((df["close"] > df["high_20"]) & (df["vol_ratio"] > 1.5)).astype(int),
        "MACD_ADX_strong": (
            ((df["macd"] > df["macd_signal"]) & (df["macd"].shift(1) <= df["macd_signal"].shift(1))) &
            (df["adx"] > 30)
        ).astype(int),
        "Supertrend_Volume": (
            ((df["close"] > df["supertrend"]) & (df["close"].shift(1) <= df["supertrend"].shift(1))) &
            (df["vol_ratio"] > 1.3)
        ).astype(int),
    }
    for name, bull in entries.items():
        bear = pd.Series(0, index=df.index)
        combos.append((name, bull, bear))
    return combos


def collect_and_train(df, bull, bear, tp, sl, horizon=12):
    """Collect trades, extract features at entry, train ML filter."""
    trades = []
    i = 0
    while i < len(df) - horizon - 1:
        side = None
        if bull.iloc[i] == 1: side = "long"
        elif bear.iloc[i] == 1: side = "short"
        if side:
            entry = df.iloc[i+1]["open"] * (1 + FEE if side == "long" else 1 - FEE)
            tp_p = entry * (1 + tp) if side == "long" else entry * (1 - tp)
            sl_p = entry * (1 - sl) if side == "long" else entry * (1 + sl)
            result = 0
            for j in range(i+2, min(i+horizon+2, len(df))):
                if side == "long":
                    if df.iloc[j]["low"] <= sl_p: break
                    if df.iloc[j]["high"] >= tp_p: result = 1; break
                else:
                    if df.iloc[j]["high"] >= sl_p: break
                    if df.iloc[j]["low"] <= tp_p: result = 1; break
            row = df.iloc[i]
            close = row["close"]
            feat = {
                "rsi": row.get("rsi", 50), "adx": row.get("adx", 0),
                "macd_hist": row.get("macd_hist", 0), "vol_ratio": row.get("vol_ratio", 1),
                "stoch": row.get("stoch_k", 50), "atr_pct": row.get("atr", 0) / close if close > 0 else 0,
                "bb_pos": (close - row.get("bb_lower", close)) / max(row.get("bb_upper", close) - row.get("bb_lower", close), 0.001),
                "ema_dist": (row.get("ema8", close) - row.get("ema21", close)) / close,
                "trend_score": float(row.get("ema8",0)>row.get("ema21",0)) + float(close>row.get("ema50",0)) + float(close>row.get("supertrend",0)) + float(close>row.get("psar",0)),
                "ret1": df["close"].pct_change(1).iloc[i],
                "ret3": df["close"].pct_change(3).iloc[i],
                "obv_trend": float(row.get("obv",0) > row.get("obv_sma20",0)),
                "cci": row.get("cci", 0) / 200,
                "mfi": row.get("mfi", 50),
            }
            trades.append({"feat": feat, "result": result})
            i = j + 1 if j > i else i + 2
        else:
            i += 1

    if len(trades) < 30:
        return None

    X = pd.DataFrame([t["feat"] for t in trades]).fillna(0).values
    y = np.array([t["result"] for t in trades])
    split = int(len(X) * 0.7)
    if split < 15 or len(X) - split < 10:
        return None

    scaler = StandardScaler()
    X_tr = scaler.fit_transform(X[:split])
    X_te = scaler.transform(X[split:])
    y_tr, y_te = y[:split], y[split:]
    orig_wr = y_te.mean() * 100

    try:
        ens = VotingClassifier(estimators=[
            ("rf", RandomForestClassifier(n_estimators=150, max_depth=8, min_samples_leaf=10, random_state=42, n_jobs=-1)),
            ("gbm", GradientBoostingClassifier(n_estimators=150, max_depth=5, learning_rate=0.05, random_state=42)),
        ], voting="soft")
        ens.fit(X_tr, y_tr)
        proba = ens.predict_proba(X_te)[:, 1]
    except:
        return None

    best = None
    for conf in [0.5, 0.55, 0.6, 0.65, 0.7]:
        filtered = y_te[proba >= conf]
        if len(filtered) < 5: continue
        fwr = filtered.mean() * 100
        wins = filtered.sum()
        losses = len(filtered) - wins
        pf = (wins * tp) / (losses * sl) if losses * sl > 0 else 0
        net_ret = (wins * tp - losses * sl) * 100
        oos_days = (len(df) * 0.3) / 6
        daily = net_ret / max(oos_days, 1)
        if daily > 0.03 and fwr > orig_wr:
            if best is None or daily > best["roi_day"]:
                best = {
                    "roi_day": round(daily, 4), "pf": round(pf, 2), "wr": round(fwr, 1),
                    "trades": len(filtered), "orig_wr": round(orig_wr, 1),
                    "improvement": round(fwr - orig_wr, 1), "confidence": conf,
                    "tp_pct": tp, "sl_pct": sl,
                }
    return best


if __name__ == "__main__":
    print("=" * 80, flush=True)
    print("  ML + GENERATE HYBRID", flush=True)
    print("  ATR-adaptive + High-TP + Trend+Dip + Mean Reversion + ML filter", flush=True)
    print("=" * 80, flush=True)

    all_results = []
    total = 0

    for asset in ASSETS:
        df = load_data(f"{asset}_4h")
        if df is None: continue
        df = calculate_indicators(df)
        atr_params = get_atr_params(df)

        # Collect all entry methods
        all_entries = []
        all_entries.extend(entry_trend_dip(df))
        all_entries.extend(entry_mean_reversion(df))
        all_entries.extend(entry_high_tp(df))

        for entry_name, bull, bear in all_entries:
            # Test with ATR-adaptive params
            for tp, sl in atr_params[:8]:  # top 8 ATR params
                total += 1
                result = collect_and_train(df, bull, bear, tp, sl)
                if result:
                    result["asset"] = asset
                    result["signal"] = entry_name
                    result["model"] = "GenerateHybrid"
                    result["tf"] = "4h"
                    result["roi_yr"] = round(result["roi_day"] * 365, 1)
                    result["gdd"] = 0
                    result["trades_per_day"] = round(result["trades"] / ((len(df) * 0.3) / 6 / 365), 2) if result["trades"] > 0 else 0
                    result["test_years"] = round((len(df) * 0.3) / 6 / 365, 2)
                    result["accuracy"] = 0
                    result["precision"] = 0
                    result["final_cap"] = 0
                    all_results.append(result)
                    if result["roi_day"] > 0.1:
                        print(f"  ** {result['roi_day']:.3f}%/day {asset} {entry_name} TP={tp*100:.1f}% WR:{result['orig_wr']:.0f}→{result['wr']:.0f}% PF={result['pf']:.2f} Trades={result['trades']} **", flush=True)

            # Also test with fixed high-TP params
            for tp, sl in [(0.15, 0.05), (0.20, 0.07), (0.25, 0.08), (0.30, 0.10), (0.40, 0.12)]:
                total += 1
                result = collect_and_train(df, bull, bear, tp, sl, horizon=18)
                if result:
                    result["asset"] = asset
                    result["signal"] = entry_name + "_highTP"
                    result["model"] = "GenerateHybrid"
                    result["tf"] = "4h"
                    result["roi_yr"] = round(result["roi_day"] * 365, 1)
                    result["gdd"] = 0
                    result["trades_per_day"] = 0
                    result["test_years"] = round((len(df) * 0.3) / 6 / 365, 2)
                    result["accuracy"] = 0
                    result["precision"] = 0
                    result["final_cap"] = 0
                    all_results.append(result)
                    if result["roi_day"] > 0.1:
                        print(f"  ** {result['roi_day']:.3f}%/day {asset} {entry_name}_highTP TP={tp*100:.0f}% WR:{result['orig_wr']:.0f}→{result['wr']:.0f}% PF={result['pf']:.2f} **", flush=True)

        all_results.sort(key=lambda x: -x["roi_day"])
        # Merge with existing results
        try:
            existing = json.load(open(os.path.join(STORAGE, "ml_results.json")))
        except:
            existing = []
        combined = existing + [r for r in all_results if r not in existing]
        combined.sort(key=lambda x: -x.get("roi_day", 0))
        json.dump(combined, open(os.path.join(STORAGE, "ml_results.json"), "w"), indent=2)
        print(f"  {asset} done ({total} tested, {len(all_results)} found)", flush=True)

    print(f"\n{'='*80}", flush=True)
    print(f"  COMPLETE: {len(all_results)} strategies from generate hybrid", flush=True)
    print(f"{'='*80}", flush=True)
    seen = set(); n = 0
    for r in all_results:
        k = (r["asset"], r["signal"])
        if k in seen: continue
        seen.add(k); n += 1
        if n > 15: break
        print(f"  {n}. {r['roi_day']:.3f}%/day {r['asset']} {r['signal']} WR:{r['orig_wr']}→{r['wr']}% PF={r['pf']} Trades={r['trades']}", flush=True)
    print("DONE", flush=True)
