"""
Neural Network Strategy — MLP + Sequence Features
Uses sklearn MLPClassifier with engineered sequence features
to capture multi-bar patterns (like LSTM but lighter).
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from run_strategies_batch import load_data, calculate_indicators, INITIAL_CAPITAL

FEE = 0.001


def build_sequence_features(df, lookback=20):
    """Build features that capture SEQUENCES of bars (what LSTM would see).
    Instead of just current bar values, we capture patterns over lookback bars."""
    d = df.copy()
    f = pd.DataFrame(index=d.index)

    close = d["close"]
    high = d["high"]
    low = d["low"]
    volume = d["volume"]

    # ── Single bar features (standard) ──
    f["ret_1"] = close.pct_change(1)
    f["ret_3"] = close.pct_change(3)
    f["ret_6"] = close.pct_change(6)
    f["high_low_pct"] = (high - low) / close
    f["body_pct"] = abs(close - d["open"]) / close
    f["is_green"] = (close > d["open"]).astype(int)

    # ── Indicator values ──
    f["rsi"] = d.get("rsi", pd.Series(50, index=d.index))
    f["macd_hist"] = d.get("macd_hist", pd.Series(0, index=d.index))
    f["adx"] = d.get("adx", pd.Series(0, index=d.index))
    f["vol_ratio"] = d.get("vol_ratio", pd.Series(1, index=d.index))
    f["atr_pct"] = d["atr"] / close if "atr" in d.columns else 0
    f["bb_position"] = ((close - d.get("bb_lower", close)) /
                        (d.get("bb_upper", close) - d.get("bb_lower", close)).replace(0, np.nan))
    f["stoch_k"] = d.get("stoch_k", pd.Series(50, index=d.index))

    # ── SEQUENCE features (what LSTM captures) ──
    # Pattern: how many of last N bars were green
    f["green_ratio_5"] = d["close"].gt(d["open"]).rolling(5).mean()
    f["green_ratio_10"] = d["close"].gt(d["open"]).rolling(10).mean()
    f["green_ratio_20"] = d["close"].gt(d["open"]).rolling(20).mean()

    # Pattern: consecutive green/red bars
    is_green = (close > d["open"]).astype(int)
    consec = is_green.copy()
    for i in range(1, 6):
        consec += is_green.shift(i).fillna(0)
    f["consec_green"] = consec

    # Pattern: volatility compression (squeeze detection)
    f["atr_ratio_short_long"] = d["atr"] / d["atr"].rolling(50).mean() if "atr" in d.columns else 1
    f["bb_width"] = ((d.get("bb_upper", close) - d.get("bb_lower", close)) / close)
    f["bb_width_change"] = f["bb_width"].pct_change(5)

    # Pattern: momentum acceleration
    ret_5 = close.pct_change(5)
    ret_10 = close.pct_change(10)
    f["momentum_accel"] = ret_5 - ret_10 / 2  # short-term faster than long-term

    # Pattern: volume trend
    f["vol_trend_5"] = volume.rolling(5).mean() / volume.rolling(20).mean()
    f["vol_spike_count_10"] = (d.get("vol_ratio", pd.Series(1, index=d.index)) > 1.5).rolling(10).sum()

    # Pattern: price relative to moving averages (multi-scale)
    for period in [8, 21, 50]:
        ma = close.rolling(period).mean()
        f[f"dist_ma{period}"] = (close - ma) / close
        f[f"slope_ma{period}"] = ma.pct_change(3)

    # Pattern: RSI sequence (overbought/oversold duration)
    rsi = d.get("rsi", pd.Series(50, index=d.index))
    f["rsi_above_70_count"] = (rsi > 70).rolling(10).sum()
    f["rsi_below_30_count"] = (rsi < 30).rolling(10).sum()
    f["rsi_slope_5"] = rsi.diff(5)

    # Pattern: support/resistance (price near recent high/low)
    f["near_high_20"] = (close / high.rolling(20).max())
    f["near_low_20"] = (close / low.rolling(20).min())

    # Pattern: candle shapes over sequence
    upper_wick = (high - pd.concat([close, d["open"]], axis=1).max(axis=1)) / close
    lower_wick = (pd.concat([close, d["open"]], axis=1).min(axis=1) - low) / close
    f["avg_upper_wick_5"] = upper_wick.rolling(5).mean()
    f["avg_lower_wick_5"] = lower_wick.rolling(5).mean()
    f["wick_ratio_5"] = (f["avg_upper_wick_5"] / f["avg_lower_wick_5"].replace(0, np.nan))

    # Pattern: higher highs / lower lows
    f["higher_highs_5"] = (high > high.shift(1)).rolling(5).sum()
    f["lower_lows_5"] = (low < low.shift(1)).rolling(5).sum()

    # Pattern: MACD histogram sequence
    macd_h = d.get("macd_hist", pd.Series(0, index=d.index))
    f["macd_hist_positive_5"] = (macd_h > 0).rolling(5).sum()
    f["macd_hist_slope_3"] = macd_h.diff(3)

    return f


def build_labels(df, tp_pct=0.03, sl_pct=0.015, horizon=12):
    """Label: 1 if price hits TP before SL within horizon bars."""
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
                break
    return labels


def backtest_predictions(df, predictions, tp_pct=0.03, sl_pct=0.015, horizon=12):
    """Backtest: enter when model says 1, exit at TP/SL/horizon."""
    capital = INITIAL_CAPITAL
    trades = []
    i = 0

    while i < len(df) - horizon - 1:
        if predictions[i] == 1:
            entry = df.iloc[i + 1]["open"] * (1 + FEE)
            qty = capital * 0.95 / entry
            tp_price = entry * (1 + tp_pct)
            sl_price = entry * (1 - sl_pct)
            exit_price = None

            for j in range(i + 2, min(i + horizon + 2, len(df))):
                if df.iloc[j]["low"] <= sl_price:
                    exit_price = sl_price * (1 - FEE)
                    break
                if df.iloc[j]["high"] >= tp_price:
                    exit_price = tp_price * (1 - FEE)
                    break

            if exit_price is None:
                exit_price = df.iloc[min(i + horizon + 1, len(df) - 1)]["close"] * (1 - FEE)
                j = min(i + horizon + 1, len(df) - 1)

            pnl = (exit_price - entry) * qty
            capital += pnl
            trades.append({"pnl": pnl, "return_pct": (exit_price / entry - 1) * 100})
            i = j + 1
        else:
            i += 1

    return capital, trades


def add_cross_asset_features(features_df, btc_df, asset_df):
    """Add BTC as leading indicator — BTC moves first, alts follow."""
    f = features_df.copy()

    btc_close = btc_df["close"].values
    asset_close = asset_df["close"].values

    # Align lengths (use min length)
    n = min(len(f), len(btc_close), len(asset_close))
    btc_close = btc_close[-n:]

    # BTC returns (leading signal for alts)
    btc_ret = pd.Series(btc_close).pct_change()
    f["btc_ret_1"] = btc_ret.values[-len(f):]
    f["btc_ret_3"] = pd.Series(btc_close).pct_change(3).values[-len(f):]
    f["btc_ret_6"] = pd.Series(btc_close).pct_change(6).values[-len(f):]

    # BTC momentum vs asset momentum (divergence = opportunity)
    btc_mom_10 = pd.Series(btc_close).pct_change(10)
    asset_mom_10 = pd.Series(asset_close[-n:]).pct_change(10)
    f["btc_asset_divergence"] = (asset_mom_10 - btc_mom_10).values[-len(f):]

    # BTC volatility (high BTC vol = risky for alts)
    btc_vol = pd.Series(btc_close).pct_change().rolling(20).std()
    f["btc_volatility"] = btc_vol.values[-len(f):]

    # BTC trend (above/below MA50)
    btc_ma50 = pd.Series(btc_close).rolling(50).mean()
    f["btc_trend"] = ((pd.Series(btc_close) - btc_ma50) / btc_ma50).values[-len(f):]

    # BTC consecutive direction (strong trend = alts follow)
    btc_green = (pd.Series(btc_close).diff() > 0).astype(int)
    f["btc_green_streak_5"] = btc_green.rolling(5).sum().values[-len(f):]

    return f


def add_multi_tf_features(features_df, df_1h, df_4h):
    """Add 1h features to 4h model — higher resolution entry timing."""
    f = features_df.copy()

    # 1h RSI at 4h bar close (every 4th 1h bar)
    if "rsi" in df_1h.columns and len(df_1h) >= len(f) * 4:
        rsi_1h = df_1h["rsi"].values
        # Sample every 4th bar (aligned to 4h)
        rsi_1h_sampled = rsi_1h[3::4]  # take 4th bar of each 4h period
        n = min(len(f), len(rsi_1h_sampled))
        f["rsi_1h"] = pd.Series(rsi_1h_sampled[-n:]).values[-len(f):] if n > 0 else 50

        # 1h MACD histogram
        if "macd_hist" in df_1h.columns:
            mh_1h = df_1h["macd_hist"].values[3::4]
            n = min(len(f), len(mh_1h))
            f["macd_hist_1h"] = pd.Series(mh_1h[-n:]).values[-len(f):] if n > 0 else 0

        # 1h volume trend
        if "vol_ratio" in df_1h.columns:
            vr_1h = df_1h["vol_ratio"].values[3::4]
            n = min(len(f), len(vr_1h))
            f["vol_ratio_1h"] = pd.Series(vr_1h[-n:]).values[-len(f):] if n > 0 else 1

    return f


def run_neural_scan(assets=None, tf="4h"):
    """Run neural network + ensemble scan with cross-asset + multi-TF features."""
    if assets is None:
        assets = ["ETHUSDT", "BTCUSDT", "ADAUSDT", "SOLUSDT", "LINKUSDT",
                  "BNBUSDT", "XRPUSDT", "AVAXUSDT", "DOTUSDT", "LTCUSDT"]

    PARAMS = [
        (0.02, 0.01, 8), (0.03, 0.015, 8), (0.04, 0.02, 10),
        (0.06, 0.03, 12), (0.08, 0.04, 12), (0.10, 0.05, 15),
        (0.15, 0.07, 18), (0.20, 0.10, 20),
    ]

    results = []
    total = 0

    # Pre-load BTC data (leading indicator for all alts)
    btc_4h = load_data("BTCUSDT_4h")
    if btc_4h is not None:
        btc_4h = calculate_indicators(btc_4h)
    print("  BTC loaded as leading indicator", flush=True)

    for asset in assets:
        df = load_data(f"{asset}_{tf}")
        if df is None:
            continue
        df = calculate_indicators(df)
        features = build_sequence_features(df)

        # Add cross-asset features (BTC leading indicator)
        if btc_4h is not None and asset != "BTCUSDT":
            try:
                features = add_cross_asset_features(features, btc_4h, df)
            except:
                pass

        # Add multi-timeframe features (1h into 4h)
        try:
            df_1h = load_data(f"{asset}_1h")
            if df_1h is not None:
                df_1h = calculate_indicators(df_1h)
                features = add_multi_tf_features(features, df_1h, df)
        except:
            pass

        features = features.dropna()
        if len(features) < 500:
            continue

        for tp, sl, horizon in PARAMS:
            total += 1
            try:
                labels = build_labels(df.loc[features.index], tp_pct=tp, sl_pct=sl, horizon=horizon)
                X = features.values
                y = labels[:len(X)]
                split = int(len(X) * 0.7)

                # Scale features for neural network
                scaler = StandardScaler()
                X_tr = scaler.fit_transform(X[:split])
                X_te = scaler.transform(X[split:])
                y_tr, y_te = y[:split], y[split:]

                # Ensemble: MLP + RF + GBM voting
                mlp = MLPClassifier(hidden_layer_sizes=(64, 32, 16), max_iter=200,
                                    learning_rate="adaptive", early_stopping=True,
                                    random_state=42, verbose=False)
                rf = RandomForestClassifier(n_estimators=100, max_depth=10,
                                            min_samples_leaf=20, random_state=42, n_jobs=-1)
                gbm = GradientBoostingClassifier(n_estimators=100, max_depth=5,
                                                  learning_rate=0.05, random_state=42)

                # Train ensemble
                ensemble = VotingClassifier(
                    estimators=[("mlp", mlp), ("rf", rf), ("gbm", gbm)],
                    voting="soft"
                )
                ensemble.fit(X_tr, y_tr)
                y_pred = ensemble.predict(X_te)

                acc = (y_pred == y_te).mean() * 100
                prec = (y_te[y_pred == 1].sum() / y_pred.sum() * 100) if y_pred.sum() > 0 else 0
                n_signals = int(y_pred.sum())

                # Backtest on OOS
                test_df = df.loc[features.index[split:]].reset_index(drop=True)
                cap, trades = backtest_predictions(test_df, y_pred[:len(test_df)],
                                                    tp_pct=tp, sl_pct=sl, horizon=horizon)
                if len(trades) < 5:
                    continue

                oos_days = len(test_df) / 6  # 4h = 6 bars/day
                roi = (cap / INITIAL_CAPITAL - 1) * 100
                daily = roi / max(oos_days, 1)
                w = [t for t in trades if t["pnl"] > 0]
                wr = len(w) / len(trades) * 100
                tw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                tl = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                pf = tw / tl if tl > 0 else 0

                r = {
                    "asset": asset, "model": "MLP+RF+GBM", "tf": tf,
                    "tp_pct": tp, "sl_pct": sl, "horizon": horizon,
                    "roi_day": round(daily, 4), "roi_yr": round(daily * 365, 1),
                    "pf": round(pf, 2), "wr": round(wr, 1),
                    "trades": len(trades), "trades_per_day": round(len(trades) / max(oos_days, 1), 2),
                    "accuracy": round(acc, 1), "precision": round(prec, 1),
                    "final_cap": round(cap, 0), "signals": n_signals,
                    "gdd": 0, "test_years": round(oos_days / 365, 2),
                }
                if daily > 0.05:
                    results.append(r)
                    print(f"  {daily:.3f}%/day {asset} {tf} MLP+RF+GBM TP={tp*100}% "
                          f"PF={pf:.2f} WR={wr:.1f}% Acc={acc:.0f}% Trades={len(trades)}", flush=True)

            except Exception as e:
                pass

        # Save after each asset
        results.sort(key=lambda x: -x["roi_day"])
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "storage", "ml_results.json"), "w") as f:
            json.dump(results, f, indent=2)
        print(f"  {asset} done ({total} tested, {len(results)} found)", flush=True)

    return results


if __name__ == "__main__":
    print("=" * 80, flush=True)
    print("  NEURAL NETWORK + ENSEMBLE STRATEGY SCANNER", flush=True)
    print("  MLP (64→32→16) + RandomForest + GBM — Voting Ensemble", flush=True)
    print("  Sequence features (multi-bar patterns) + Walk-forward OOS", flush=True)
    print("  4h timeframe only", flush=True)
    print("=" * 80, flush=True)

    results = run_neural_scan()

    print(f"\nCOMPLETE: {len(results)} strategies found", flush=True)
    print(f">= 1%: {len([r for r in results if r['roi_day'] >= 1.0])}", flush=True)
    print(f">= 0.5%: {len([r for r in results if r['roi_day'] >= 0.5])}", flush=True)
    print(f">= 0.25%: {len([r for r in results if r['roi_day'] >= 0.25])}", flush=True)

    for i, r in enumerate(results[:10]):
        print(f"  {i+1}. {r['roi_day']:.3f}%/day {r['asset']} PF={r['pf']} "
              f"WR={r['wr']}% Acc={r['accuracy']}% Trades={r['trades']}", flush=True)
    print("DONE", flush=True)
