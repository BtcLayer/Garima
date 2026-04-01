#!/usr/bin/env python3
"""
ML with SCORED labels — not binary yes/no but HOW GOOD is each trade opportunity.

Score = weighted combination of:
  - Max favorable excursion (how far price went in your favor)
  - Risk-reward ratio achieved
  - Speed to profit (faster = better)
  - Trend alignment at entry
  - Volume confirmation
  - Mean reversion bounce quality

ML learns to predict the SCORE, trades only when score > threshold.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd, numpy as np
from run_strategies_batch import load_data, calculate_indicators, INITIAL_CAPITAL
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, VotingRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

FEE = 0.001
STORAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage")


def build_scored_labels(df, horizon=12):
    """Score each bar 0-100 based on how good a long entry it would be."""
    scores = np.zeros(len(df))
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    volume = df["volume"].values
    vol_ma = pd.Series(volume).rolling(20).mean().values

    for i in range(len(df) - horizon):
        entry = close[i]
        if entry <= 0:
            continue

        # 1. Max Favorable Excursion (0-30 pts)
        # How far did price go UP from entry within horizon?
        max_high = max(high[i+1:i+horizon+1])
        mfe_pct = (max_high - entry) / entry * 100
        mfe_score = min(mfe_pct * 5, 30)  # 6% move = 30 pts

        # 2. Max Adverse Excursion (0-20 pts, inverted — less drawdown = more points)
        # How far did price go DOWN before going up?
        min_low = min(low[i+1:i+horizon+1])
        mae_pct = (entry - min_low) / entry * 100
        mae_score = max(20 - mae_pct * 5, 0)  # 0% drawdown = 20 pts, 4% = 0 pts

        # 3. Final return (0-20 pts)
        final = close[min(i + horizon, len(df) - 1)]
        ret_pct = (final - entry) / entry * 100
        ret_score = min(max(ret_pct * 4, 0), 20)  # 5% return = 20 pts

        # 4. Speed to profit (0-15 pts)
        # How quickly did price reach 1% profit?
        speed_score = 0
        for j in range(i + 1, min(i + horizon + 1, len(df))):
            if high[j] >= entry * 1.01:
                bars_to_profit = j - i
                speed_score = max(15 - bars_to_profit, 0)  # 1 bar = 15 pts, 15 bars = 0
                break

        # 5. Volume confirmation (0-15 pts)
        # Was there volume support?
        if i < len(vol_ma) and vol_ma[i] > 0:
            vol_ratio = volume[i] / vol_ma[i]
            vol_score = min(vol_ratio * 5, 15)  # 3x volume = 15 pts
        else:
            vol_score = 5

        total = mfe_score + mae_score + ret_score + speed_score + vol_score
        scores[i] = total

    return scores


def build_features(df):
    """Compact but powerful feature set."""
    f = pd.DataFrame(index=df.index)
    close = df["close"]

    # Trend
    f["ema8_21"] = (df["ema8"] - df["ema21"]) / close
    f["ema21_50"] = (df["ema21"] - df["ema50"]) / close
    f["above_st"] = (close > df["supertrend"]).astype(float)
    f["above_psar"] = (close > df["psar"]).astype(float)
    f["above_cloud"] = ((close > df["senkou_span_a"]) & (close > df["senkou_span_b"])).astype(float)
    f["obv_trend"] = (df["obv"] - df["obv_sma20"]) / df["obv_sma20"].replace(0, np.nan)

    # Momentum
    f["rsi"] = df["rsi"]
    f["rsi_dist50"] = (df["rsi"] - 50) / 50
    f["macd_hist"] = df["macd_hist"]
    f["stoch"] = df["stoch_k"]
    f["adx"] = df["adx"]
    f["cci_norm"] = df["cci"] / 200
    f["mfi"] = df["mfi"]
    f["williams"] = df["williams_r"]

    # Volume
    f["vol_ratio"] = df["vol_ratio"]

    # Volatility
    f["atr_pct"] = df["atr"] / close
    f["bb_pos"] = (close - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)
    f["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / close

    # Squeeze
    if "keltner_upper" in df.columns:
        f["squeeze"] = ((df["bb_upper"] < df["keltner_upper"]) & (df["bb_lower"] > df["keltner_lower"])).astype(float)

    # Price action
    f["ret1"] = close.pct_change(1)
    f["ret3"] = close.pct_change(3)
    f["ret6"] = close.pct_change(6)
    f["ret12"] = close.pct_change(12)
    f["near_high20"] = close / df["high"].rolling(20).max()
    f["near_low20"] = close / df["low"].rolling(20).min()

    # Patterns
    f["green5"] = (close > df["open"]).astype(float).rolling(5).mean()
    f["hh5"] = (df["high"] > df["high"].shift(1)).astype(float).rolling(5).sum()

    # Scores
    f["trend_score"] = (
        (df["ema8"] > df["ema21"]).astype(float) +
        (close > df["ema50"]).astype(float) +
        (close > df["supertrend"]).astype(float) +
        (close > df["psar"]).astype(float) +
        (df["macd"] > df["macd_signal"]).astype(float) +
        (df["adx"] > 25).astype(float)
    )
    f["reversal_score"] = (
        (df["rsi"] < 30).astype(float) +
        (df["stoch_k"] < 20).astype(float) +
        (df["cci"] < -100).astype(float) +
        (close < df["bb_lower"]).astype(float)
    )

    return f


def backtest_scored(df, predictions, threshold=50, tp=0.04, sl=0.02, horizon=12):
    """Trade when predicted score > threshold."""
    cap = INITIAL_CAPITAL; trades = []; i = 0
    while i < len(df) - horizon - 1:
        if predictions[i] >= threshold:
            entry = df.iloc[i + 1]["open"] * (1 + FEE)
            qty = cap * 0.95 / entry
            tp_p, sl_p = entry * (1 + tp), entry * (1 - sl)
            ex = None
            for j in range(i + 2, min(i + horizon + 2, len(df))):
                if df.iloc[j]["low"] <= sl_p: ex = sl_p * (1 - FEE); break
                if df.iloc[j]["high"] >= tp_p: ex = tp_p * (1 - FEE); break
            if ex is None:
                ex = df.iloc[min(i + horizon + 1, len(df) - 1)]["close"] * (1 - FEE)
                j = min(i + horizon + 1, len(df) - 1)
            pnl = (ex - entry) * qty; cap += pnl
            trades.append({"pnl": pnl})
            i = j + 1
        else:
            i += 1
    return cap, trades


if __name__ == "__main__":
    ASSETS = ["ETHUSDT", "BTCUSDT", "ADAUSDT", "SOLUSDT", "LINKUSDT",
              "BNBUSDT", "XRPUSDT", "AVAXUSDT", "DOTUSDT", "LTCUSDT"]
    THRESHOLDS = [40, 50, 60, 70]
    TP_SL = [(0.02, 0.01), (0.03, 0.015), (0.04, 0.02), (0.06, 0.03), (0.08, 0.04), (0.10, 0.05)]

    btc_df = load_data("BTCUSDT_4h")
    if btc_df is not None: btc_df = calculate_indicators(btc_df)

    results = []; total = 0
    print("=" * 80, flush=True)
    print("  SCORED ML — quality score 0-100 per trade opportunity", flush=True)
    print("  Model: RF + GBM + MLP regression ensemble", flush=True)
    print("  Score = MFE + MAE + Return + Speed + Volume (0-100)", flush=True)
    print("=" * 80, flush=True)

    for asset in ASSETS:
        df = load_data(f"{asset}_4h")
        if df is None: continue
        df = calculate_indicators(df)
        features = build_features(df)

        # BTC leading
        if btc_df is not None and asset != "BTCUSDT":
            n = min(len(features), len(btc_df))
            features["btc_ret1"] = btc_df["close"].pct_change(1).values[-n:][-len(features):]
            features["btc_ret3"] = btc_df["close"].pct_change(3).values[-n:][-len(features):]
            btc_trend = ((btc_df["close"] - btc_df["close"].rolling(50).mean()) / btc_df["close"].rolling(50).mean()).values
            features["btc_trend"] = btc_trend[-n:][-len(features):]

        features = features.replace([np.inf, -np.inf], np.nan).dropna()
        if len(features) < 500: continue

        scores = build_scored_labels(df.loc[features.index])
        X = features.values; y = scores[:len(X)]
        split = int(len(X) * 0.7)

        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X[:split])
        X_te = scaler.transform(X[split:])
        y_tr, y_te = y[:split], y[split:]

        try:
            ens = VotingRegressor(estimators=[
                ("mlp", MLPRegressor(hidden_layer_sizes=(128, 64, 32), max_iter=300,
                                     learning_rate="adaptive", early_stopping=True, random_state=42)),
                ("rf", RandomForestRegressor(n_estimators=200, max_depth=12,
                                             min_samples_leaf=15, random_state=42, n_jobs=-1)),
                ("gbm", GradientBoostingRegressor(n_estimators=200, max_depth=6,
                                                   learning_rate=0.05, random_state=42)),
            ])
            ens.fit(X_tr, y_tr)
            y_pred = ens.predict(X_te)

            # Score distribution
            mean_pred = np.mean(y_pred)
            max_pred = np.max(y_pred)
            above_50 = (y_pred >= 50).sum()
            above_60 = (y_pred >= 60).sum()
        except:
            continue

        test_df = df.loc[features.index[split:]].reset_index(drop=True)

        for threshold in THRESHOLDS:
            for tp, sl in TP_SL:
                total += 1
                try:
                    cap, trades = backtest_scored(test_df, y_pred[:len(test_df)],
                                                  threshold=threshold, tp=tp, sl=sl, horizon=12)
                    if len(trades) < 5: continue
                    days = len(test_df) / 6
                    daily = ((cap / INITIAL_CAPITAL - 1) * 100) / max(days, 1)
                    w = [t for t in trades if t["pnl"] > 0]
                    wr = len(w) / len(trades) * 100
                    tw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                    tl = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                    pf = tw / tl if tl > 0 else 0

                    if daily > 0.03:
                        results.append({
                            "asset": asset, "model": f"Scored_T{threshold}", "tf": "4h",
                            "tp_pct": tp, "sl_pct": sl, "roi_day": round(daily, 4),
                            "roi_yr": round(daily * 365, 1), "pf": round(pf, 2),
                            "wr": round(wr, 1), "trades": len(trades),
                            "accuracy": round(mean_pred, 1), "precision": round(max_pred, 1),
                            "final_cap": round(cap, 0), "gdd": 0,
                            "trades_per_day": round(len(trades) / max(days, 1), 2),
                            "test_years": round(days / 365, 2),
                        })
                        if daily > 0.08:
                            print(f"  ** {daily:.3f}%/day {asset} T={threshold} TP={tp*100}% SL={sl*100}% PF={pf:.2f} WR={wr:.1f}% Trades={len(trades)} **", flush=True)
                except:
                    pass

        results.sort(key=lambda x: -x["roi_day"])
        json.dump(results, open(os.path.join(STORAGE, "ml_results.json"), "w"), indent=2)
        print(f"  {asset} done ({total} tested, {len(results)} found) | Score range: {mean_pred:.0f}-{max_pred:.0f} | >50: {above_50} | >60: {above_60}", flush=True)

    print(f"\n{'='*80}", flush=True)
    print(f"  COMPLETE: {len(results)} strategies found", flush=True)
    print(f"{'='*80}", flush=True)
    seen = set(); n = 0
    for r in results:
        k = (r["asset"], r["model"])
        if k in seen: continue
        seen.add(k); n += 1
        if n > 15: break
        print(f"  {n}. {r['roi_day']:.3f}%/day {r['asset']} {r['model']} TP={r['tp_pct']*100}% PF={r['pf']} WR={r['wr']}% Trades={r['trades']}", flush=True)

    if len(results) >= 3:
        unique = {}
        for r in results:
            if r["asset"] not in unique: unique[r["asset"]] = r
            if len(unique) >= 4: break
        port = sum(r["roi_day"] for r in unique.values()) / len(unique)
        print(f"\n  PORTFOLIO (top {len(unique)} assets): {port:.3f}%/day ({port*365:.0f}%/yr)", flush=True)

    print("DONE", flush=True)
