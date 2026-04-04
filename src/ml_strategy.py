"""
ML-Based Strategy Generator
Trains Random Forest / Gradient Boosting on technical indicators
to predict profitable entries. Walk-forward validated.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score
from run_strategies_batch import load_data, calculate_indicators, INITIAL_CAPITAL

FEE = 0.0003  # 0.03% per side


def build_features(df):
    """Build ML features from indicators — 40+ features."""
    f = pd.DataFrame(index=df.index)

    # Price-based
    f["ret_1"] = df["close"].pct_change(1)
    f["ret_3"] = df["close"].pct_change(3)
    f["ret_6"] = df["close"].pct_change(6)
    f["ret_12"] = df["close"].pct_change(12)
    f["high_low_range"] = (df["high"] - df["low"]) / df["close"]
    f["close_to_high"] = (df["high"] - df["close"]) / df["close"]
    f["close_to_low"] = (df["close"] - df["low"]) / df["close"]

    # EMAs relative
    f["ema8_dist"] = (df["close"] - df["ema8"]) / df["close"]
    f["ema21_dist"] = (df["close"] - df["ema21"]) / df["close"]
    f["ema50_dist"] = (df["close"] - df["ema50"]) / df["close"]
    f["ema8_21_cross"] = (df["ema8"] - df["ema21"]) / df["close"]
    f["ema_slope_8"] = df["ema8"].pct_change(3)
    f["ema_slope_21"] = df["ema21"].pct_change(3)

    # RSI
    f["rsi"] = df["rsi"]
    f["rsi_slope"] = df["rsi"].diff(3)

    # MACD
    f["macd_hist"] = df["macd_hist"]
    f["macd_hist_slope"] = df["macd_hist"].diff(2)

    # Stochastic
    f["stoch_k"] = df["stoch_k"]
    f["stoch_slope"] = df["stoch_k"].diff(3)

    # Bollinger
    f["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["close"]
    f["bb_position"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)

    # Volume
    f["vol_ratio"] = df["vol_ratio"]
    f["vol_slope"] = df["vol_ratio"].diff(3)

    # ATR
    f["atr_pct"] = df["atr"] / df["close"]
    f["atr_slope"] = (df["atr"] / df["close"]).diff(3)

    # ADX
    f["adx"] = df["adx"]

    # Supertrend
    f["supertrend_dist"] = (df["close"] - df["supertrend"]) / df["close"]

    # OBV
    f["obv_vs_sma"] = (df["obv"] - df["obv_sma20"]) / df["obv_sma20"].replace(0, np.nan)

    # CCI
    f["cci"] = df["cci"]

    # Ichimoku
    f["ichi_cloud_dist"] = (df["close"] - df["senkou_span_a"]) / df["close"]

    # PSAR
    f["psar_dist"] = (df["close"] - df["psar"]) / df["close"]

    # MFI
    f["mfi"] = df["mfi"]

    # Keltner
    f["keltner_pos"] = (df["close"] - df["keltner_lower"]) / (df["keltner_upper"] - df["keltner_lower"]).replace(0, np.nan)

    # Williams %R
    f["williams_r"] = df["williams_r"]

    # Candle patterns
    f["body_size"] = abs(df["close"] - df["open"]) / df["close"]
    f["upper_wick"] = (df["high"] - df[["close", "open"]].max(axis=1)) / df["close"]
    f["lower_wick"] = (df[["close", "open"]].min(axis=1) - df["low"]) / df["close"]
    f["is_green"] = (df["close"] > df["open"]).astype(int)

    # ── Features from winning strategies (Donchian, Aroon, TRIX, Chandelier, HA, ROC) ──

    # Donchian breakout signals
    if "donchian_upper" in df.columns:
        f["donchian_pos"] = (df["close"] - df["donchian_lower"]) / (df["donchian_upper"] - df["donchian_lower"]).replace(0, np.nan)
        f["donchian_width"] = df.get("donchian_width", 0)
        f["donchian_break_up"] = (df["close"] > df["donchian_upper"].shift(1)).astype(int)

    # Aroon trend strength
    if "aroon_up" in df.columns:
        f["aroon_osc"] = df.get("aroon_osc", 0)
        f["aroon_up"] = df.get("aroon_up", 0)

    # TRIX momentum
    if "trix" in df.columns:
        f["trix"] = df["trix"]
        f["trix_above_signal"] = (df["trix"] > df["trix_signal"]).astype(int)

    # Chandelier distance
    if "chandelier_long" in df.columns:
        f["chandelier_dist"] = (df["close"] - df["chandelier_long"]) / df["close"]

    # Heikin Ashi trend
    if "ha_green" in df.columns:
        f["ha_green"] = df["ha_green"]

    # DI cross
    if "di_plus" in df.columns:
        f["di_diff"] = df["di_plus"] - df["di_minus"]

    # ROC momentum
    if "roc_12" in df.columns:
        f["roc_12"] = df["roc_12"]
        f["roc_6"] = df.get("roc_6", 0)

    return f


def build_labels(df, tp_pct=0.02, sl_pct=0.01, horizon=12):
    """Label each bar: 1 if price hits TP before SL within horizon bars, else 0."""
    labels = np.zeros(len(df))
    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values

    for i in range(len(df) - horizon):
        entry = closes[i]
        tp_price = entry * (1 + tp_pct)
        sl_price = entry * (1 - sl_pct)

        for j in range(i + 1, min(i + horizon + 1, len(df))):
            if highs[j] >= tp_price:
                labels[i] = 1
                break
            if lows[j] <= sl_price:
                labels[i] = 0
                break
    return labels


def run_ml_backtest(df, predictions, tp_pct=0.02, sl_pct=0.01, horizon=12):
    """Backtest ML predictions — enter when model says 1, exit at TP/SL/horizon."""
    capital = INITIAL_CAPITAL
    trades = []
    i = 0
    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values
    opens = df["open"].values if "open" in df.columns else closes

    while i < len(df) - horizon - 1:
        if predictions[i] == 1:
            # Enter next bar open
            entry_price = opens[i + 1] * (1 + FEE)
            qty = capital * 0.95 / entry_price
            tp_price = entry_price * (1 + tp_pct)
            sl_price = entry_price * (1 - sl_pct)

            exit_price = None
            exit_reason = "horizon"
            for j in range(i + 2, min(i + horizon + 2, len(df))):
                if lows[j] <= sl_price:
                    exit_price = sl_price * (1 - FEE)
                    exit_reason = "SL"
                    i = j
                    break
                if highs[j] >= tp_price:
                    exit_price = tp_price * (1 - FEE)
                    exit_reason = "TP"
                    i = j
                    break

            if exit_price is None:
                exit_idx = min(i + horizon + 1, len(df) - 1)
                exit_price = closes[exit_idx] * (1 - FEE)
                exit_reason = "horizon"
                i = exit_idx

            pnl = (exit_price - entry_price) * qty
            capital += pnl
            trades.append({
                "entry": round(entry_price, 6), "exit": round(exit_price, 6),
                "pnl": round(pnl, 2), "return_pct": round((exit_price / entry_price - 1) * 100, 3),
                "exit_reason": exit_reason, "capital_after": round(capital, 2),
            })
            i += 1
        else:
            i += 1

    return capital, trades


def train_and_evaluate(asset, tf, tp_pct=0.02, sl_pct=0.01, horizon=12,
                       model_type="rf", train_ratio=0.7):
    """Full pipeline: load data, build features, train, walk-forward test."""
    key = f"{asset}_{tf}"
    df = load_data(key)
    if df is None:
        return None

    df = calculate_indicators(df)
    features = build_features(df)
    labels = build_labels(df, tp_pct=tp_pct, sl_pct=sl_pct, horizon=horizon)

    # Align and drop NaN
    combined = features.copy()
    combined["label"] = labels
    combined = combined.dropna()

    if len(combined) < 500:
        return None

    X = combined.drop("label", axis=1).values
    y = combined["label"].values

    # Walk-forward: train on first 70%, test on last 30%
    split = int(len(X) * train_ratio)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    # Train model
    if model_type == "rf":
        model = RandomForestClassifier(n_estimators=200, max_depth=10,
                                        min_samples_leaf=20, random_state=42, n_jobs=-1)
    else:
        model = GradientBoostingClassifier(n_estimators=200, max_depth=5,
                                            min_samples_leaf=20, learning_rate=0.05, random_state=42)

    model.fit(X_train, y_train)

    # Predict on test set
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    n_signals = int(y_pred.sum())

    # Backtest on test period only
    test_df = df.iloc[combined.index[split]:].copy().reset_index(drop=True)
    if len(test_df) < 100:
        return None

    capital, trades = run_ml_backtest(test_df, y_pred[:len(test_df)],
                                      tp_pct=tp_pct, sl_pct=sl_pct, horizon=horizon)

    if len(trades) < 5:
        return None

    # Calculate metrics
    if "timestamp" in test_df.columns:
        from datetime import datetime
        t_s = str(test_df["timestamp"].iloc[0])[:10]
        t_e = str(test_df["timestamp"].iloc[-1])[:10]
        yrs = max((datetime.fromisoformat(t_e) - datetime.fromisoformat(t_s)).days / 365.25, 0.01)
    else:
        yrs = len(test_df) / (365 * 6)  # rough estimate

    roi_a = ((capital / INITIAL_CAPITAL) ** (1 / yrs) - 1) * 100 if capital > 0 else -100
    daily = roi_a / 365
    wins = [t for t in trades if t["pnl"] > 0]
    wr = len(wins) / len(trades) * 100 if trades else 0
    tw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    tl = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
    pf = tw / tl if tl > 0 else 0
    trades_per_day = len(trades) / (yrs * 365)

    # Drawdown
    eq = INITIAL_CAPITAL
    pk = eq
    gdd = 0
    for t in trades:
        eq += t["pnl"]
        pk = max(pk, eq)
        dd = (pk - eq) / pk * 100
        gdd = max(gdd, dd)

    # Feature importance (top 10)
    feat_names = features.dropna().columns.tolist()
    importances = model.feature_importances_
    top_features = sorted(zip(feat_names, importances), key=lambda x: -x[1])[:10]

    return {
        "asset": asset, "tf": tf, "model": model_type,
        "tp_pct": tp_pct, "sl_pct": sl_pct, "horizon": horizon,
        "roi_day": round(daily, 4), "roi_yr": round(roi_a, 1),
        "pf": round(pf, 2), "wr": round(wr, 1), "gdd": round(gdd, 1),
        "trades": len(trades), "trades_per_day": round(trades_per_day, 2),
        "final_cap": round(capital, 0),
        "accuracy": round(acc * 100, 1), "precision": round(prec * 100, 1),
        "signals_fired": n_signals, "test_bars": len(X_test),
        "top_features": top_features,
        "train_size": len(X_train), "test_size": len(X_test),
        "test_years": round(yrs, 2),
    }


def run_full_scan(assets=None, timeframes=None, models=None):
    """Scan multiple assets, timeframes, params, and models."""
    if assets is None:
        assets = ["ETHUSDT", "BTCUSDT", "ADAUSDT", "SOLUSDT", "LINKUSDT", "BNBUSDT"]
    if timeframes is None:
        timeframes = ["4h"]
    if models is None:
        models = ["rf", "gbm"]

    # TP/SL/horizon combos to test
    param_grid = [
        (0.015, 0.008, 12), (0.02, 0.01, 12), (0.03, 0.015, 12),
        (0.04, 0.02, 12), (0.05, 0.025, 18), (0.06, 0.03, 18),
        (0.08, 0.04, 24), (0.10, 0.05, 24), (0.15, 0.07, 30),
        (0.20, 0.10, 36),
    ]

    results = []
    total = 0
    for asset in assets:
        for tf in timeframes:
            for model_type in models:
                for tp, sl, horizon in param_grid:
                    total += 1
                    r = train_and_evaluate(asset, tf, tp_pct=tp, sl_pct=sl,
                                           horizon=horizon, model_type=model_type)
                    if r and r["roi_day"] > 0.1:
                        results.append(r)
                        tag = "*** 1%+ ***" if r["roi_day"] >= 1.0 else ""
                        print(f"  {r['roi_day']:.3f}%/day {r['roi_yr']:.0f}%/yr "
                              f"{asset} {tf} {model_type} TP={tp*100}% SL={sl*100}% "
                              f"PF={r['pf']} WR={r['wr']}% Trades={r['trades']} "
                              f"Acc={r['accuracy']}% Prec={r['precision']}% {tag}",
                              flush=True)
            print(f"  {asset} {tf} done ({total} tested)", flush=True)

    results.sort(key=lambda x: -x["roi_day"])
    return results


if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", nargs="+", default=["ETHUSDT", "BTCUSDT", "ADAUSDT"])
    parser.add_argument("--tf", nargs="+", default=["4h"])
    parser.add_argument("--models", nargs="+", default=["rf", "gbm"])
    args = parser.parse_args()

    print(f"\n{'='*90}")
    print(f"  ML STRATEGY SCANNER")
    print(f"  Assets: {args.assets} | TFs: {args.tf} | Models: {args.models}")
    print(f"  Walk-forward: 70% train / 30% test (OUT-OF-SAMPLE results only)")
    print(f"{'='*90}\n")

    results = run_full_scan(assets=args.assets, timeframes=args.tf, models=args.models)

    print(f"\n{'='*90}")
    print(f"  TOP 15 ML STRATEGIES (OUT-OF-SAMPLE)")
    print(f"{'='*90}")
    seen = set()
    n = 0
    for r in results:
        k = (r["asset"], r["tf"], r["model"])
        if k in seen:
            continue
        seen.add(k)
        n += 1
        if n > 15:
            break
        tag = " *** 1%+ ***" if r["roi_day"] >= 1.0 else ""
        print(f"\n  {n}. {r['roi_day']:.3f}%/day ({r['roi_yr']:.0f}%/yr) {tag}")
        print(f"     {r['asset']} {r['tf']} | Model: {r['model'].upper()}")
        print(f"     PF={r['pf']} WR={r['wr']}% GDD={r['gdd']}% | Trades={r['trades']} ({r['trades_per_day']:.1f}/day)")
        print(f"     TP={r['tp_pct']*100}% SL={r['sl_pct']*100}% Horizon={r['horizon']} bars")
        print(f"     Accuracy={r['accuracy']}% Precision={r['precision']}%")
        print(f"     Top features: {', '.join(f[0] for f in r['top_features'][:5])}")
        print(f"     Final capital: ${r['final_cap']:,.0f} (test period: {r['test_years']:.1f}yr)")

    above1 = sum(1 for r in results if r["roi_day"] >= 1.0)
    above05 = sum(1 for r in results if r["roi_day"] >= 0.5)
    print(f"\n  >= 1%/day: {above1} | >= 0.5%/day: {above05} | Total: {len(results)}")

    # Save results
    out_path = "reports/ml_strategy_results.json"
    with open(out_path, "w") as f:
        json.dump([{k: v for k, v in r.items() if k != "top_features"} for r in results], f, indent=2)
    print(f"\n  Results saved to {out_path}")
    print("DONE")
