#!/usr/bin/env python3
"""
ML IMPROVE WINNERS — Take the "fake profit" strategies, learn what made them
profit/fail, build smarter entry filters.

Step 1: Run the original winning signals (OBV, Lookback, Supertrend level)
Step 2: Label each trade: WIN or LOSS (actual trade-based, not signal×return)
Step 3: ML learns WHAT CONDITIONS led to winning vs losing trades
Step 4: Use ML as FILTER: only enter when ML predicts WIN
Step 5: Backtest filtered version — should have higher WR and PF
Step 6: Generate Pine Script for best result
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd, numpy as np
from run_strategies_batch import load_data, calculate_indicators, INITIAL_CAPITAL
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.preprocessing import StandardScaler

FEE = 0.001
STORAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage")


def get_signal_obv(df, length=11):
    """OBV momentum — the signal that hit 1.4%/day."""
    obv = (np.sign(df["close"].diff()) * df["volume"]).fillna(0).cumsum()
    obv_ema = obv.rolling(length).mean()
    ema200 = df["close"].rolling(200).mean()
    bull = (obv > obv_ema) & (df["close"] > ema200)
    bear = (obv < obv_ema) & (df["close"] < ema200)
    return bull.astype(int), bear.astype(int)


def get_signal_lookback(df, lookback=9):
    """Lookback momentum — the signal that hit 1.5%/day."""
    bull = df["close"] > df["close"].shift(lookback)
    bear = df["close"] < df["close"].shift(lookback)
    return bull.astype(int), bear.astype(int)


def get_signal_supertrend_level(df, mult=2.0, length=11):
    """Supertrend level — the signal that hit 1.1%/day."""
    atr = df["atr"] if "atr" in df.columns else (df["high"] - df["low"]).rolling(length).mean()
    upper = (df["high"] + df["low"]) / 2 + mult * atr
    lower = (df["high"] + df["low"]) / 2 - mult * atr
    ema200 = df["close"].rolling(200).mean()
    bull = (df["close"] > upper.shift(1)) & (df["close"] > ema200)
    bear = (df["close"] < lower.shift(1)) & (df["close"] < ema200)
    return bull.astype(int), bear.astype(int)


def collect_trades(df, bull_signal, bear_signal, tp=0.03, sl=0.01, horizon=12):
    """Run actual trades and record features at each entry point."""
    trades = []
    i = 0
    while i < len(df) - horizon - 1:
        side = None
        if bull_signal.iloc[i] == 1:
            side = "long"
        elif bear_signal.iloc[i] == 1:
            side = "short"

        if side:
            entry = df.iloc[i + 1]["open"] * (1 + FEE if side == "long" else 1 - FEE)
            tp_p = entry * (1 + tp) if side == "long" else entry * (1 - tp)
            sl_p = entry * (1 - sl) if side == "long" else entry * (1 + sl)
            result = 0  # 0=loss, 1=win

            for j in range(i + 2, min(i + horizon + 2, len(df))):
                if side == "long":
                    if df.iloc[j]["low"] <= sl_p:
                        result = 0; break
                    if df.iloc[j]["high"] >= tp_p:
                        result = 1; break
                else:
                    if df.iloc[j]["high"] >= sl_p:
                        result = 0; break
                    if df.iloc[j]["low"] <= tp_p:
                        result = 1; break

            trades.append({"bar_idx": i, "side": side, "result": result})
            i = j + 1 if j > i else i + 2
        else:
            i += 1
    return trades


def features_at_entry(df, bar_idx):
    """Extract rich features at the moment of entry — ML learns from these."""
    row = df.iloc[bar_idx]
    close = row["close"]
    f = {}

    # Trend state
    f["ema8_21_dist"] = (row.get("ema8", close) - row.get("ema21", close)) / close
    f["ema21_50_dist"] = (row.get("ema21", close) - row.get("ema50", close)) / close
    f["above_supertrend"] = float(close > row.get("supertrend", close))
    f["above_psar"] = float(close > row.get("psar", close))
    f["above_cloud"] = float(close > row.get("senkou_span_a", 0) and close > row.get("senkou_span_b", 0))

    # Momentum
    f["rsi"] = row.get("rsi", 50)
    f["macd_hist"] = row.get("macd_hist", 0)
    f["adx"] = row.get("adx", 0)
    f["stoch_k"] = row.get("stoch_k", 50)
    f["cci"] = row.get("cci", 0) / 200
    f["mfi"] = row.get("mfi", 50)
    f["williams"] = row.get("williams_r", -50)

    # Volume
    f["vol_ratio"] = row.get("vol_ratio", 1)
    f["obv_trend"] = float(row.get("obv", 0) > row.get("obv_sma20", 0))

    # Volatility
    f["atr_pct"] = row.get("atr", 0) / close if close > 0 else 0
    f["bb_pos"] = (close - row.get("bb_lower", close)) / max(row.get("bb_upper", close) - row.get("bb_lower", close), 0.001)
    f["bb_width"] = (row.get("bb_upper", close) - row.get("bb_lower", close)) / close

    # Price action (lookback)
    if bar_idx >= 12:
        closes = df["close"].iloc[bar_idx-12:bar_idx+1].values
        f["ret_1"] = (closes[-1] / closes[-2] - 1) if closes[-2] > 0 else 0
        f["ret_3"] = (closes[-1] / closes[-4] - 1) if closes[-4] > 0 else 0
        f["ret_6"] = (closes[-1] / closes[-7] - 1) if closes[-7] > 0 else 0
        f["ret_12"] = (closes[-1] / closes[0] - 1) if closes[0] > 0 else 0
        f["green_ratio_5"] = sum(1 for k in range(-5, 0) if closes[k] > closes[k-1]) / 5
        highs = df["high"].iloc[bar_idx-5:bar_idx+1].values
        f["near_high_5"] = close / max(highs) if max(highs) > 0 else 1
    else:
        f["ret_1"] = f["ret_3"] = f["ret_6"] = f["ret_12"] = 0
        f["green_ratio_5"] = 0.5
        f["near_high_5"] = 1

    # Trend score
    f["trend_score"] = (
        float(row.get("ema8", 0) > row.get("ema21", 0)) +
        float(close > row.get("ema50", 0)) +
        float(close > row.get("supertrend", 0)) +
        float(close > row.get("psar", 0)) +
        float(row.get("macd", 0) > row.get("macd_signal", 0)) +
        float(row.get("adx", 0) > 25)
    )

    return f


SIGNAL_GENERATORS = {
    "OBV_Momentum": get_signal_obv,
    "Lookback_Momentum": get_signal_lookback,
    "Supertrend_Level": get_signal_supertrend_level,
}

ASSETS = ["ETHUSDT", "BTCUSDT", "ADAUSDT", "SOLUSDT", "LINKUSDT",
          "BNBUSDT", "XRPUSDT", "AVAXUSDT", "DOTUSDT", "LTCUSDT"]
TP_SL = [(0.02, 0.01), (0.03, 0.015), (0.04, 0.02), (0.06, 0.03), (0.08, 0.04)]


if __name__ == "__main__":
    print("=" * 80, flush=True)
    print("  ML IMPROVE WINNERS — learn from fake-profit strategies", flush=True)
    print("  Step 1: Run winning signals, collect actual trades", flush=True)
    print("  Step 2: ML learns which entries WIN vs LOSE", flush=True)
    print("  Step 3: Filter entries with ML → higher WR and PF", flush=True)
    print("=" * 80, flush=True)

    all_results = []

    for sig_name, sig_func in SIGNAL_GENERATORS.items():
        print(f"\n--- Signal: {sig_name} ---", flush=True)

        for asset in ASSETS:
            df = load_data(f"{asset}_4h")
            if df is None: continue
            df = calculate_indicators(df)

            bull, bear = sig_func(df)

            for tp, sl in TP_SL:
                # Step 1: Collect all trades with labels
                trades = collect_trades(df, bull, bear, tp=tp, sl=sl, horizon=12)
                if len(trades) < 30: continue

                # Step 2: Build feature matrix from entry points
                X_list = []
                y_list = []
                for t in trades:
                    feat = features_at_entry(df, t["bar_idx"])
                    X_list.append(feat)
                    y_list.append(t["result"])

                X_df = pd.DataFrame(X_list).fillna(0)
                X = X_df.values
                y = np.array(y_list)

                # OOS split
                split = int(len(X) * 0.7)
                if split < 20 or len(X) - split < 10: continue

                scaler = StandardScaler()
                X_tr = scaler.fit_transform(X[:split])
                X_te = scaler.transform(X[split:])
                y_tr, y_te = y[:split], y[split:]

                # Original WR (no ML filter)
                orig_wr = y_te.mean() * 100
                orig_trades = len(y_te)

                # Step 3: Train ML to predict win/loss
                try:
                    ens = VotingClassifier(estimators=[
                        ("rf", RandomForestClassifier(n_estimators=150, max_depth=8,
                                                      min_samples_leaf=10, random_state=42, n_jobs=-1)),
                        ("gbm", GradientBoostingClassifier(n_estimators=150, max_depth=5,
                                                           learning_rate=0.05, random_state=42)),
                    ], voting="soft")
                    ens.fit(X_tr, y_tr)
                    proba = ens.predict_proba(X_te)[:, 1]
                except:
                    continue

                # Step 4: Try different confidence thresholds
                for conf_thresh in [0.5, 0.55, 0.6, 0.65, 0.7]:
                    filtered_mask = proba >= conf_thresh
                    filtered_trades = y_te[filtered_mask]
                    if len(filtered_trades) < 5: continue

                    filtered_wr = filtered_trades.mean() * 100
                    filtered_count = len(filtered_trades)

                    # Calculate actual PnL
                    wins = filtered_trades.sum()
                    losses = filtered_count - wins
                    # Approx PnL: wins get TP%, losses get SL%
                    gross_win = wins * tp
                    gross_loss = losses * sl
                    pf = gross_win / gross_loss if gross_loss > 0 else 0
                    # Daily ROI approximation
                    net_return = (gross_win - gross_loss) * 100
                    oos_days = (len(df) * 0.3) / 6
                    daily = net_return / max(oos_days, 1)

                    if daily > 0.05 and filtered_wr > orig_wr:
                        r = {
                            "asset": asset, "signal": sig_name, "model": f"MLFilter_C{int(conf_thresh*100)}",
                            "tf": "4h", "tp_pct": tp, "sl_pct": sl,
                            "roi_day": round(daily, 4), "roi_yr": round(daily * 365, 1),
                            "pf": round(pf, 2), "wr": round(filtered_wr, 1),
                            "trades": filtered_count, "orig_wr": round(orig_wr, 1),
                            "orig_trades": orig_trades, "improvement": round(filtered_wr - orig_wr, 1),
                            "confidence": conf_thresh,
                            "gdd": 0, "trades_per_day": round(filtered_count / max(oos_days, 1), 2),
                            "test_years": round(oos_days / 365, 2),
                        }
                        all_results.append(r)
                        if daily > 0.1:
                            print(f"  ** {daily:.3f}%/day {asset} {sig_name} C={conf_thresh} TP={tp*100}% "
                                  f"WR: {orig_wr:.0f}%→{filtered_wr:.0f}% (+{filtered_wr-orig_wr:.0f}%) "
                                  f"PF={pf:.2f} Trades: {orig_trades}→{filtered_count} **", flush=True)

            all_results.sort(key=lambda x: -x["roi_day"])
            json.dump(all_results, open(os.path.join(STORAGE, "ml_results.json"), "w"), indent=2)

        print(f"  {sig_name}: {len([r for r in all_results if r['signal']==sig_name])} improved strategies found", flush=True)

    print(f"\n{'='*80}", flush=True)
    print(f"  COMPLETE: {len(all_results)} improved strategies", flush=True)
    print(f"{'='*80}", flush=True)

    seen = set(); n = 0
    for r in all_results:
        k = (r["asset"], r["signal"])
        if k in seen: continue
        seen.add(k); n += 1
        if n > 15: break
        print(f"  {n}. {r['roi_day']:.3f}%/day {r['asset']} {r['signal']} "
              f"WR: {r['orig_wr']}%→{r['wr']}% (+{r['improvement']}%) "
              f"PF={r['pf']} Trades={r['trades']} C={r['confidence']}", flush=True)

    print("DONE", flush=True)
