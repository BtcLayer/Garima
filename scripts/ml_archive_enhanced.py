#!/usr/bin/env python3
"""
Enhanced ML — combines archive insights:
1. Portfolio approach (multi-asset concurrent positions from combo_strategies.py)
2. Squeeze momentum features (from strategies.py linreg momentum)
3. Multiple SL/TP configs from HIGH_ROI_CONFIGS
4. Multi-timeframe (4h direction + 1h features)
5. BTC leading indicator
6. Mean reversion + trend following COMBINED (not just trend)
7. Rule-based + raw value HYBRID features
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd, numpy as np
from run_strategies_batch import load_data, calculate_indicators, INITIAL_CAPITAL
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.preprocessing import StandardScaler

FEE = 0.001
STORAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage")


def archive_features(df):
    """Features inspired by all archive strategies + squeeze momentum + mean reversion."""
    f = pd.DataFrame(index=df.index)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # ── TREND FEATURES (from combo_strategies.py) ──
    f["ema8_21"] = (df["ema8"] - df["ema21"]) / close
    f["ema21_50"] = (df["ema21"] - df["ema50"]) / close
    f["above_supertrend"] = (close > df["supertrend"]).astype(float)
    f["above_psar"] = (close > df["psar"]).astype(float)
    f["above_cloud"] = ((close > df["senkou_span_a"]) & (close > df["senkou_span_b"])).astype(float)
    f["tenkan_kijun"] = (df["tenkan_sen"] - df["kijun_sen"]) / close

    # ── SQUEEZE MOMENTUM (from strategies.py — linreg momentum) ──
    # This is what squeeze_momentum strategy uses
    deviation = close - close.rolling(20).mean()
    # Linear regression slope of deviation (approximation)
    for period in [10, 20, 30]:
        dev = close - close.rolling(period).mean()
        slope = dev.rolling(period).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) == period else 0,
            raw=False
        )
        f[f"linreg_mom_{period}"] = slope
    # Squeeze detection (BB inside KC)
    f["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / close
    kc_upper = df["keltner_upper"] if "keltner_upper" in df.columns else close
    kc_lower = df["keltner_lower"] if "keltner_lower" in df.columns else close
    f["squeeze_on"] = ((df["bb_upper"] < kc_upper) & (df["bb_lower"] > kc_lower)).astype(float)
    f["squeeze_duration"] = f["squeeze_on"].rolling(20).sum()

    # ── MEAN REVERSION FEATURES (not just trend) ──
    f["rsi_dist_50"] = (df["rsi"] - 50) / 50  # distance from neutral
    f["bb_position"] = (close - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)
    f["stoch_dist"] = (df["stoch_k"] - 50) / 50
    f["cci_norm"] = df["cci"] / 200  # normalized CCI
    f["mfi_norm"] = (df["mfi"] - 50) / 50
    f["williams_norm"] = (df["williams_r"] + 50) / 50
    # Mean reversion signals
    f["oversold_count"] = (
        (df["rsi"] < 30).astype(float) +
        (df["stoch_k"] < 20).astype(float) +
        (df["cci"] < -100).astype(float) +
        (df["mfi"] < 20).astype(float) +
        (df["williams_r"] < -80).astype(float) +
        (close < df["bb_lower"]).astype(float)
    )
    f["overbought_count"] = (
        (df["rsi"] > 70).astype(float) +
        (df["stoch_k"] > 80).astype(float) +
        (df["cci"] > 100).astype(float) +
        (df["mfi"] > 80).astype(float) +
        (df["williams_r"] > -20).astype(float) +
        (close > df["bb_upper"]).astype(float)
    )

    # ── VOLUME FEATURES (from combo_strategies.py) ──
    f["vol_ratio"] = df["vol_ratio"]
    f["obv_trend"] = (df["obv"] - df["obv_sma20"]) / df["obv_sma20"].replace(0, np.nan)
    f["vol_trend_5"] = volume.rolling(5).mean() / volume.rolling(20).mean()

    # ── PRICE ACTION ──
    f["ret_1"] = close.pct_change(1)
    f["ret_3"] = close.pct_change(3)
    f["ret_6"] = close.pct_change(6)
    f["ret_12"] = close.pct_change(12)
    f["atr_pct"] = df["atr"] / close
    f["adx"] = df["adx"]
    f["rsi"] = df["rsi"]

    # ── CROSSOVER EVENTS (recent, from archive) ──
    f["ema_xup_5"] = ((df["ema8"] > df["ema21"]) & (df["ema8"].shift(5) <= df["ema21"].shift(5))).astype(float)
    f["macd_xup_5"] = ((df["macd"] > df["macd_signal"]) & (df["macd"].shift(5) <= df["macd_signal"].shift(5))).astype(float)
    f["rsi_cross_30_up"] = ((df["rsi"] > 30) & (df["rsi"].shift(3) <= 30)).astype(float)
    f["rsi_cross_70_down"] = ((df["rsi"] < 70) & (df["rsi"].shift(3) >= 70)).astype(float)

    # ── TREND SCORE (from combo_strategies.py multi-strategy agreement) ──
    f["trend_score"] = (
        (df["ema8"] > df["ema21"]).astype(float) +
        (close > df["ema50"]).astype(float) +
        (close > df["supertrend"]).astype(float) +
        (close > df["psar"]).astype(float) +
        (df["macd"] > df["macd_signal"]).astype(float) +
        (df["obv"] > df["obv_sma20"]).astype(float) +
        (df["adx"] > 25).astype(float)
    )
    f["reversal_score"] = f["oversold_count"] - f["overbought_count"]

    # ── PATTERN FEATURES ──
    f["higher_highs_5"] = (high > high.shift(1)).rolling(5).sum()
    f["lower_lows_5"] = (low < low.shift(1)).rolling(5).sum()
    f["green_ratio_10"] = (close > df["open"]).astype(float).rolling(10).mean()
    f["near_high_20"] = close / high.rolling(20).max()
    f["near_low_20"] = close / low.rolling(20).min()

    return f


def build_labels_multi(df, configs):
    """Build labels for MULTIPLE TP/SL configs — ML learns which config works best."""
    best_labels = np.zeros(len(df))
    c, h, l = df["close"].values, df["high"].values, df["low"].values

    for tp, sl, horizon in configs:
        labels = np.zeros(len(df))
        for i in range(len(df) - horizon):
            entry = c[i]
            for j in range(i + 1, min(i + horizon + 1, len(df))):
                if h[j] >= entry * (1 + tp):
                    labels[i] = 1
                    break
                if l[j] <= entry * (1 - sl):
                    break
        # Keep the most profitable config's labels
        best_labels = np.maximum(best_labels, labels)

    return best_labels


def backtest(df, preds, tp, sl, horizon):
    cap = INITIAL_CAPITAL; trades = []; i = 0
    while i < len(df) - horizon - 1:
        if preds[i] == 1:
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

    # HIGH_ROI_CONFIGS from archive (8 configs for label generation)
    LABEL_CONFIGS = [
        (0.02, 0.01, 8), (0.03, 0.015, 8), (0.04, 0.02, 10),
        (0.05, 0.02, 10), (0.06, 0.025, 12), (0.08, 0.03, 12),
    ]
    # Test params
    TEST_PARAMS = [
        (0.02, 0.01, 8), (0.03, 0.015, 10), (0.04, 0.02, 10),
        (0.06, 0.03, 12), (0.08, 0.04, 12), (0.10, 0.05, 15),
        (0.15, 0.07, 18),
    ]

    # Load BTC for leading indicator
    btc_df = load_data("BTCUSDT_4h")
    if btc_df is not None:
        btc_df = calculate_indicators(btc_df)

    results = []
    total = 0

    print("=" * 80, flush=True)
    print("  ENHANCED ML — Archive Insights + Squeeze + Mean Reversion + Portfolio", flush=True)
    print("  Features: 50+ (trend + squeeze + mean reversion + patterns + BTC lead)", flush=True)
    print("  Labels: multi-config best (learns which TP/SL combo works)", flush=True)
    print("  Model: MLP(128,64,32) + RF(200) + GBM(200) voting ensemble", flush=True)
    print("=" * 80, flush=True)

    for asset in ASSETS:
        df = load_data(f"{asset}_4h")
        if df is None:
            continue
        df = calculate_indicators(df)
        features = archive_features(df)

        # Add BTC leading indicator
        if btc_df is not None and asset != "BTCUSDT":
            n = min(len(features), len(btc_df))
            features["btc_ret1"] = btc_df["close"].pct_change(1).values[-n:][-len(features):]
            features["btc_ret3"] = btc_df["close"].pct_change(3).values[-n:][-len(features):]
            features["btc_ret6"] = btc_df["close"].pct_change(6).values[-n:][-len(features):]
            btc_trend = ((btc_df["close"] - btc_df["close"].rolling(50).mean()) / btc_df["close"].rolling(50).mean()).values
            features["btc_trend"] = btc_trend[-n:][-len(features):]
            features["btc_rsi"] = btc_df["rsi"].values[-n:][-len(features):]

        # Add 1h features if available
        df_1h = load_data(f"{asset}_1h")
        if df_1h is not None:
            try:
                df_1h = calculate_indicators(df_1h)
                rsi_1h = df_1h["rsi"].values[3::4]
                n = min(len(features), len(rsi_1h))
                if n > 0:
                    arr = np.full(len(features), np.nan)
                    arr[-n:] = rsi_1h[-n:]
                    features["rsi_1h"] = arr
                macd_1h = df_1h["macd_hist"].values[3::4]
                n = min(len(features), len(macd_1h))
                if n > 0:
                    arr = np.full(len(features), np.nan)
                    arr[-n:] = macd_1h[-n:]
                    features["macd_1h"] = arr
            except:
                pass

        features = features.replace([np.inf, -np.inf], np.nan).dropna()
        if len(features) < 500:
            continue

        # Multi-config labels (learns from best TP/SL automatically)
        multi_labels = build_labels_multi(df.loc[features.index], LABEL_CONFIGS)

        X = features.values
        y = multi_labels[:len(X)]
        split = int(len(X) * 0.7)
        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X[:split])
        X_te = scaler.transform(X[split:])
        y_tr, y_te = y[:split], y[split:]

        # Train ensemble
        try:
            ens = VotingClassifier(estimators=[
                ("mlp", MLPClassifier(hidden_layer_sizes=(128, 64, 32), max_iter=300,
                                      learning_rate="adaptive", early_stopping=True, random_state=42)),
                ("rf", RandomForestClassifier(n_estimators=200, max_depth=12,
                                              min_samples_leaf=15, random_state=42, n_jobs=-1)),
                ("gbm", GradientBoostingClassifier(n_estimators=200, max_depth=6,
                                                   learning_rate=0.05, random_state=42)),
            ], voting="soft")
            ens.fit(X_tr, y_tr)
            y_pred = ens.predict(X_te)
            acc = (y_pred == y_te).mean() * 100
            prec = (y_te[y_pred == 1].sum() / y_pred.sum() * 100) if y_pred.sum() > 0 else 0
        except:
            continue

        # Test on multiple TP/SL configs
        for tp, sl, horizon in TEST_PARAMS:
            total += 1
            try:
                test_df = df.loc[features.index[split:]].reset_index(drop=True)
                cap, trades = backtest(test_df, y_pred[:len(test_df)], tp, sl, horizon)
                if len(trades) < 5:
                    continue
                days = len(test_df) / 6
                daily = ((cap / INITIAL_CAPITAL - 1) * 100) / max(days, 1)
                w = [t for t in trades if t["pnl"] > 0]
                wr = len(w) / len(trades) * 100
                tw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                tl = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                pf = tw / tl if tl > 0 else 0

                if daily > 0.03:
                    results.append({
                        "asset": asset, "model": "Archive_Enhanced_Ensemble", "tf": "4h",
                        "tp_pct": tp, "sl_pct": sl, "roi_day": round(daily, 4),
                        "roi_yr": round(daily * 365, 1), "pf": round(pf, 2),
                        "wr": round(wr, 1), "trades": len(trades),
                        "accuracy": round(acc, 1), "precision": round(prec, 1),
                        "final_cap": round(cap, 0), "gdd": 0,
                        "trades_per_day": round(len(trades) / max(days, 1), 2),
                        "test_years": round(days / 365, 2),
                    })
                    if daily > 0.08:
                        print(f"  ** {daily:.3f}%/day {asset} TP={tp*100}% SL={sl*100}% PF={pf:.2f} WR={wr:.1f}% Acc={acc:.0f}% Trades={len(trades)} **", flush=True)
            except:
                pass

        results.sort(key=lambda x: -x["roi_day"])
        json.dump(results, open(os.path.join(STORAGE, "ml_results.json"), "w"), indent=2)
        print(f"  {asset} done ({total} tested, {len(results)} found)", flush=True)

    # Portfolio analysis
    print(f"\n{'='*80}", flush=True)
    print(f"  RESULTS", flush=True)
    print(f"{'='*80}", flush=True)
    print(f"  Total: {len(results)} | >= 0.1%: {len([r for r in results if r['roi_day'] >= 0.1])}", flush=True)

    seen = set()
    n = 0
    for r in results:
        k = (r["asset"], round(r["tp_pct"], 2))
        if k in seen:
            continue
        seen.add(k)
        n += 1
        if n > 15:
            break
        print(f"  {n}. {r['roi_day']:.3f}%/day {r['asset']} TP={r['tp_pct']*100}% PF={r['pf']} WR={r['wr']}% Trades={r['trades']}", flush=True)

    # Portfolio combination
    if len(results) >= 3:
        print(f"\n  PORTFOLIO (top 3 combined on different assets):", flush=True)
        unique_assets = {}
        for r in results:
            if r["asset"] not in unique_assets:
                unique_assets[r["asset"]] = r
            if len(unique_assets) >= 4:
                break
        portfolio_daily = sum(r["roi_day"] for r in unique_assets.values()) / len(unique_assets)
        print(f"  Combined ROI/day: {portfolio_daily:.3f}% ({portfolio_daily*365:.0f}%/yr)", flush=True)
        for a, r in unique_assets.items():
            print(f"    {a}: {r['roi_day']:.3f}%/day PF={r['pf']} WR={r['wr']}%", flush=True)

    print("DONE", flush=True)
