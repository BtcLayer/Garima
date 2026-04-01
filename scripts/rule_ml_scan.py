#!/usr/bin/env python3
"""Rule-Based ML: use indicator rules as binary features for neural network."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd, numpy as np
from run_strategies_batch import load_data, calculate_indicators, INITIAL_CAPITAL
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.preprocessing import StandardScaler

FEE = 0.001
STORAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage")

def rule_features(df):
    f = pd.DataFrame(index=df.index)
    # Trend rules (binary: is condition true?)
    f["ema8>21"] = (df["ema8"] > df["ema21"]).astype(float)
    f["ema21>50"] = (df["ema21"] > df["ema50"]).astype(float)
    f["above_ema50"] = (df["close"] > df["ema50"]).astype(float)
    f["above_supertrend"] = (df["close"] > df["supertrend"]).astype(float)
    f["above_psar"] = (df["close"] > df["psar"]).astype(float)
    f["above_vwap"] = (df["close"] > df["vwap"]).astype(float)
    f["above_cloud"] = ((df["close"] > df["senkou_span_a"]) & (df["close"] > df["senkou_span_b"])).astype(float)
    f["tenkan>kijun"] = (df["tenkan_sen"] > df["kijun_sen"]).astype(float)
    f["obv>sma"] = (df["obv"] > df["obv_sma20"]).astype(float)
    # Momentum rules
    f["rsi>50"] = (df["rsi"] > 50).astype(float)
    f["rsi<30"] = (df["rsi"] < 30).astype(float)
    f["rsi>70"] = (df["rsi"] > 70).astype(float)
    f["macd>signal"] = (df["macd"] > df["macd_signal"]).astype(float)
    f["macd_hist>0"] = (df["macd_hist"] > 0).astype(float)
    f["stoch<20"] = (df["stoch_k"] < 20).astype(float)
    f["stoch>80"] = (df["stoch_k"] > 80).astype(float)
    f["adx>25"] = (df["adx"] > 25).astype(float)
    f["adx>40"] = (df["adx"] > 40).astype(float)
    f["cci<-100"] = (df["cci"] < -100).astype(float)
    f["cci>100"] = (df["cci"] > 100).astype(float)
    f["mfi<20"] = (df["mfi"] < 20).astype(float)
    f["will<-80"] = (df["williams_r"] < -80).astype(float)
    # Volume
    f["vol_spike"] = (df["vol_ratio"] > 1.5).astype(float)
    f["vol_high"] = (df["vol_ratio"] > 2.0).astype(float)
    # Volatility
    f["below_bb"] = (df["close"] < df["bb_lower"]).astype(float)
    f["above_bb"] = (df["close"] > df["bb_upper"]).astype(float)
    f["below_keltner"] = (df["close"] < df["keltner_lower"]).astype(float)
    f["breakout20"] = (df["close"] > df["high_20"]).astype(float)
    # Recent crossovers (within last 3 bars)
    f["ema_xup_3"] = ((df["ema8"] > df["ema21"]) & (df["ema8"].shift(3) <= df["ema21"].shift(3))).astype(float)
    f["macd_xup_3"] = ((df["macd"] > df["macd_signal"]) & (df["macd"].shift(3) <= df["macd_signal"].shift(3))).astype(float)
    f["st_flip_3"] = ((df["close"] > df["supertrend"]) & (df["close"].shift(3) <= df["supertrend"].shift(3))).astype(float)
    f["psar_flip_3"] = ((df["close"] > df["psar"]) & (df["close"].shift(3) <= df["psar"].shift(3))).astype(float)
    # Combo scores
    f["trend_score"] = f[["ema8>21","above_ema50","above_supertrend","above_psar","above_cloud","obv>sma"]].sum(axis=1)
    f["mom_score"] = f[["rsi>50","macd>signal","adx>25"]].sum(axis=1)
    # Raw values (continuous)
    f["ret1"] = df["close"].pct_change(1)
    f["ret3"] = df["close"].pct_change(3)
    f["ret6"] = df["close"].pct_change(6)
    f["atr_pct"] = df["atr"] / df["close"]
    f["rsi"] = df["rsi"]
    f["adx"] = df["adx"]
    f["stoch"] = df["stoch_k"]
    f["bb_pos"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)
    return f

def build_labels(df, tp, sl, horizon):
    labels = np.zeros(len(df))
    c, h, l = df["close"].values, df["high"].values, df["low"].values
    for i in range(len(df) - horizon):
        entry = c[i]
        for j in range(i + 1, min(i + horizon + 1, len(df))):
            if h[j] >= entry * (1 + tp): labels[i] = 1; break
            if l[j] <= entry * (1 - sl): break
    return labels

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
    PARAMS = [(0.02,0.01,8),(0.03,0.015,8),(0.04,0.02,10),(0.06,0.03,12),
              (0.08,0.04,12),(0.10,0.05,15),(0.15,0.07,18)]

    btc_df = load_data("BTCUSDT_4h")
    if btc_df is not None: btc_df = calculate_indicators(btc_df)

    results = []; total = 0
    print("RULE-BASED ML — binary indicator rules + neural network ensemble", flush=True)
    print("Features: 35+ rules (is RSI oversold? is EMA crossed? etc) + BTC leading", flush=True)

    for asset in ASSETS:
        df = load_data(f"{asset}_4h")
        if df is None: continue
        df = calculate_indicators(df)
        features = rule_features(df)

        if btc_df is not None and asset != "BTCUSDT":
            n = min(len(features), len(btc_df))
            features["btc_ret1"] = btc_df["close"].pct_change(1).values[-n:][-len(features):]
            features["btc_ret3"] = btc_df["close"].pct_change(3).values[-n:][-len(features):]
            btc_trend = ((btc_df["close"] - btc_df["close"].rolling(50).mean()) / btc_df["close"].rolling(50).mean()).values
            features["btc_trend"] = btc_trend[-n:][-len(features):]

        features = features.dropna()
        if len(features) < 500: continue

        for tp, sl, horizon in PARAMS:
            total += 1
            try:
                labels = build_labels(df.loc[features.index], tp, sl, horizon)
                X = features.values; y = labels[:len(X)]
                split = int(len(X) * 0.7)
                scaler = StandardScaler()
                X_tr = scaler.fit_transform(X[:split]); X_te = scaler.transform(X[split:])
                y_tr, y_te = y[:split], y[split:]

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

                test_df = df.loc[features.index[split:]].reset_index(drop=True)
                cap, trades = backtest(test_df, y_pred[:len(test_df)], tp, sl, horizon)
                if len(trades) < 5: continue
                days = len(test_df) / 6
                daily = ((cap / INITIAL_CAPITAL - 1) * 100) / max(days, 1)
                w = [t for t in trades if t["pnl"] > 0]
                wr = len(w) / len(trades) * 100
                tw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                tl = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                pf = tw / tl if tl > 0 else 0

                if daily > 0.05:
                    results.append({
                        "asset": asset, "model": "RuleML_Ensemble", "tf": "4h",
                        "tp_pct": tp, "sl_pct": sl, "roi_day": round(daily, 4),
                        "roi_yr": round(daily * 365, 1), "pf": round(pf, 2),
                        "wr": round(wr, 1), "trades": len(trades),
                        "accuracy": round(acc, 1), "precision": round(prec, 1),
                        "final_cap": round(cap, 0), "gdd": 0,
                        "trades_per_day": round(len(trades) / max(days, 1), 2),
                        "test_years": round(days / 365, 2),
                    })
                    print(f"  {daily:.3f}%/day {asset} TP={tp*100}% PF={pf:.2f} WR={wr:.1f}% Acc={acc:.0f}% Trades={len(trades)}", flush=True)
            except:
                pass

        results.sort(key=lambda x: -x["roi_day"])
        json.dump(results, open(os.path.join(STORAGE, "ml_results.json"), "w"), indent=2)
        print(f"  {asset} done ({total} tested, {len(results)} found)", flush=True)

    print(f"\nCOMPLETE: {len(results)} found", flush=True)
    for i, r in enumerate(results[:10]):
        print(f"  {i+1}. {r['roi_day']:.3f}%/day {r['asset']} PF={r['pf']} WR={r['wr']}% Acc={r['accuracy']}%", flush=True)
    print("DONE", flush=True)
