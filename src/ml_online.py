"""
Online Learning ML — improves from TV validation feedback.

How it works:
1. Generate strategy candidates from backtester
2. User tests on TV, reports results
3. TV results stored as ground truth in tv_feedback.json
4. ML retrains on combined backtester + TV feedback data
5. Learns: "when backtester says X but TV says Y, what's the real pattern?"
6. Next generation of strategies is smarter

Key insight: The model learns the GAP between backtester and TV,
not just the backtester patterns. Over time it predicts what
actually works on TV, not what works on our backtester.
"""
import sys, os, json, pickle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd, numpy as np
from run_strategies_batch import load_data, calculate_indicators, INITIAL_CAPITAL
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE = os.path.join(ROOT, "storage")
FEEDBACK_FILE = os.path.join(STORAGE, "tv_feedback.json")
MODEL_FILE = os.path.join(STORAGE, "ml_online_model.pkl")
SCALER_FILE = os.path.join(STORAGE, "ml_online_scaler.pkl")
HISTORY_FILE = os.path.join(STORAGE, "ml_online_history.json")


def load_feedback():
    try:
        return json.load(open(FEEDBACK_FILE))
    except:
        return []


def save_feedback(feedback):
    json.dump(feedback, open(FEEDBACK_FILE, "w"), indent=2)


def add_tv_result(strategy_name, asset, tf, params, tv_result):
    """Add TV validation result as ground truth.

    tv_result = {
        "net_profit_pct": float,  # e.g. +28.7 or -95.0
        "win_rate": float,        # e.g. 53.3
        "profit_factor": float,   # e.g. 1.80
        "trades": int,
        "max_drawdown": float,    # e.g. -23.4
        "profitable": bool,       # True/False
        "sharpe": float,
    }
    """
    feedback = load_feedback()
    try:
        bt_features = get_strategy_features(asset, tf, params)
    except:
        bt_features = params.copy()  # use params as features if data unavailable
    entry = {
        "strategy": strategy_name,
        "asset": asset,
        "tf": tf,
        "params": params,
        "tv_result": tv_result,
        "backtester_features": bt_features,
        "timestamp": pd.Timestamp.now().isoformat(),
    }
    feedback.append(entry)
    save_feedback(feedback)
    print(f"  Added TV feedback: {strategy_name} {asset} = {'PROFIT' if tv_result.get('profitable') else 'LOSS'}")
    return len(feedback)


def get_strategy_features(asset, tf, params):
    """Extract features that describe the strategy + market conditions."""
    df = load_data(f"{asset}_{tf}")
    if df is None:
        return {}

    df = calculate_indicators(df)
    # Use last 500 bars as "recent market" features
    recent = df.tail(500)

    features = {
        # Strategy params
        "tp_pct": params.get("tp", 0),
        "sl_pct": params.get("sl", 0),
        "tp_sl_ratio": params.get("tp", 1) / max(params.get("sl", 1), 0.001),

        # Market conditions (average of recent period)
        "avg_atr_pct": (recent["atr"] / recent["close"]).mean(),
        "avg_adx": recent["adx"].mean(),
        "avg_vol_ratio": recent["vol_ratio"].mean(),
        "avg_rsi": recent["rsi"].mean(),
        "trend_strength": (recent["ema8"] > recent["ema21"]).mean(),  # % of time in uptrend
        "volatility_trend": (recent["atr"] / recent["close"]).diff().mean(),  # expanding or contracting
        "avg_bb_width": ((recent["bb_upper"] - recent["bb_lower"]) / recent["close"]).mean(),

        # Asset characteristics
        "asset_idx": ["ETHUSDT","BTCUSDT","ADAUSDT","SOLUSDT","LINKUSDT",
                      "BNBUSDT","XRPUSDT","AVAXUSDT","DOTUSDT","LTCUSDT"].index(asset)
                      if asset in ["ETHUSDT","BTCUSDT","ADAUSDT","SOLUSDT","LINKUSDT",
                                   "BNBUSDT","XRPUSDT","AVAXUSDT","DOTUSDT","LTCUSDT"] else -1,

        # Backtester result (what our system predicted)
        "bt_roi_day": params.get("bt_roi_day", 0),
        "bt_pf": params.get("bt_pf", 0),
        "bt_wr": params.get("bt_wr", 0),
        "bt_trades": params.get("bt_trades", 0),
        "bt_gdd": params.get("bt_gdd", 0),

        # Strategy type encoding
        "has_ema": float("ema" in params.get("signals", "").lower()),
        "has_rsi": float("rsi" in params.get("signals", "").lower()),
        "has_macd": float("macd" in params.get("signals", "").lower()),
        "has_supertrend": float("supertrend" in params.get("signals", "").lower()),
        "has_bb": float("bb" in params.get("signals", "").lower() or "bollinger" in params.get("signals", "").lower()),
        "has_volume": float("vol" in params.get("signals", "").lower()),
        "has_adx": float("adx" in params.get("signals", "").lower()),
        "has_ichimoku": float("ichi" in params.get("signals", "").lower()),
        "n_signals": len(params.get("signals", "").split("+")),
    }
    return features


def train_online_model():
    """Train model on TV feedback — learns what ACTUALLY works on TV."""
    feedback = load_feedback()
    if len(feedback) < 3:
        print(f"  Need at least 3 TV results to train. Currently: {len(feedback)}")
        return None

    X_list = []
    y_list = []
    for entry in feedback:
        feat = entry.get("backtester_features", {})
        if not feat:
            continue
        tv = entry.get("tv_result", {})
        X_list.append(feat)
        # Target: TV net profit % (what we're trying to predict)
        y_list.append(tv.get("net_profit_pct", 0))

    if len(X_list) < 3:
        return None

    X_df = pd.DataFrame(X_list).fillna(0)
    X = X_df.values
    y = np.array(y_list)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = GradientBoostingRegressor(n_estimators=100, max_depth=4,
                                       learning_rate=0.1, random_state=42)
    model.fit(X_scaled, y)

    # Save model
    pickle.dump(model, open(MODEL_FILE, "wb"))
    pickle.dump(scaler, open(SCALER_FILE, "wb"))
    pickle.dump(X_df.columns.tolist(), open(MODEL_FILE + ".cols", "wb"))

    # Score
    score = model.score(X_scaled, y)
    print(f"  Online model trained on {len(X)} TV results. R² = {score:.3f}")

    # Feature importance
    cols = X_df.columns.tolist()
    imp = model.feature_importances_
    top = sorted(zip(cols, imp), key=lambda x: -x[1])[:10]
    print(f"  Top features for TV prediction:")
    for name, importance in top:
        print(f"    {importance:.3f}  {name}")

    return model, scaler


def predict_tv_success(strategy_params_list):
    """Predict which strategies will work on TV (using learned model)."""
    try:
        model = pickle.load(open(MODEL_FILE, "rb"))
        scaler = pickle.load(open(SCALER_FILE, "rb"))
        cols = pickle.load(open(MODEL_FILE + ".cols", "rb"))
    except:
        print("  No online model yet. Need TV feedback first.")
        return []

    predictions = []
    for params in strategy_params_list:
        feat = get_strategy_features(params["asset"], params.get("tf", "4h"), params)
        feat_df = pd.DataFrame([feat]).reindex(columns=cols, fill_value=0)
        X = scaler.transform(feat_df.values)
        pred = model.predict(X)[0]
        predictions.append({
            **params,
            "predicted_tv_profit": round(pred, 2),
        })

    predictions.sort(key=lambda x: -x["predicted_tv_profit"])
    return predictions


def generate_candidates(n=20):
    """Generate strategy candidates for TV testing — ranked by predicted TV success."""
    from scripts.ml_scored import build_features, build_scored_labels, backtest_scored
    from sklearn.ensemble import VotingRegressor, RandomForestRegressor, GradientBoostingRegressor
    from sklearn.neural_network import MLPRegressor

    ASSETS = ["ETHUSDT", "BTCUSDT", "ADAUSDT", "SOLUSDT", "LINKUSDT",
              "BNBUSDT", "XRPUSDT", "AVAXUSDT", "DOTUSDT", "LTCUSDT",
              "FILUSDT", "NEARUSDT", "LDOUSDT", "OPUSDT", "INJUSDT",
              "SUIUSDT", "DOGEUSDT", "APTUSDT", "ARBUSDT", "UNIUSDT"]
    TP_SL = [(0.02,0.01), (0.03,0.015), (0.04,0.02), (0.06,0.03), (0.08,0.04), (0.10,0.05)]

    candidates = []
    for asset in ASSETS:
        df = load_data(f"{asset}_4h")
        if df is None: continue
        df = calculate_indicators(df)
        features = build_features(df).replace([np.inf, -np.inf], np.nan).dropna()
        if len(features) < 500: continue

        scores = build_scored_labels(df.loc[features.index])
        X = features.values; y = scores[:len(X)]
        split = int(len(X) * 0.7)
        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X[:split])
        X_te = scaler.transform(X[split:])

        try:
            ens = VotingRegressor(estimators=[
                ("rf", RandomForestRegressor(n_estimators=100, max_depth=10, min_samples_leaf=15, random_state=42, n_jobs=-1)),
                ("gbm", GradientBoostingRegressor(n_estimators=100, max_depth=5, learning_rate=0.05, random_state=42)),
            ])
            ens.fit(X_tr, y[:split])
            y_pred = ens.predict(X_te)
        except:
            continue

        test_df = df.loc[features.index[split:]].reset_index(drop=True)

        for tp, sl in TP_SL:
            for threshold in [50, 60, 70]:
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
                        candidates.append({
                            "asset": asset, "tf": "4h", "tp": tp, "sl": sl,
                            "threshold": threshold,
                            "bt_roi_day": round(daily, 4), "bt_pf": round(pf, 2),
                            "bt_wr": round(wr, 1), "bt_trades": len(trades),
                            "bt_gdd": 0,
                            "signals": f"ML_Scored_T{threshold}",
                        })
                except:
                    pass

    # If we have a trained online model, rank by predicted TV success
    feedback = load_feedback()
    if len(feedback) >= 3:
        candidates = predict_tv_success(candidates)
        candidates.sort(key=lambda x: -x.get("predicted_tv_profit", x.get("bt_roi_day", 0)))
    else:
        candidates.sort(key=lambda x: -x.get("bt_roi_day", 0))

    return candidates[:n]


def get_status():
    """Get online learning status."""
    feedback = load_feedback()
    profitable = len([f for f in feedback if f.get("tv_result", {}).get("profitable")])
    unprofitable = len(feedback) - profitable

    try:
        history = json.load(open(HISTORY_FILE))
    except:
        history = []

    return {
        "total_feedback": len(feedback),
        "profitable_on_tv": profitable,
        "unprofitable_on_tv": unprofitable,
        "model_trained": os.path.exists(MODEL_FILE),
        "training_rounds": len(history),
    }
