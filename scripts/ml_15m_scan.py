#!/usr/bin/env python3
"""ML scan on 15m tournament data — RF + GBM, walk-forward OOS."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import numpy as np
from src.ml_strategy import build_features, build_labels, run_ml_backtest, INITIAL_CAPITAL
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from run_strategies_batch import calculate_indicators

DATA_DIR_15M = "/home/ubuntu/tradingview_webhook_bot/storage/backtest_data"
DATA_DIR_OUR = "/home/ubuntu/Garima/storage/historical_data"
ASSETS = ["FILUSDT", "NEARUSDT", "LDOUSDT", "OPUSDT", "INJUSDT", "SUIUSDT",
          "APTUSDT", "DOGEUSDT", "SOLUSDT", "AVAXUSDT", "ARBUSDT", "LINKUSDT",
          "ETHUSDT", "BTCUSDT", "ADAUSDT", "BNBUSDT"]
TIMEFRAMES = ["15m", "1h", "4h"]
PARAMS = [
    (0.02, 0.01, 12), (0.03, 0.015, 12), (0.04, 0.02, 18),
    (0.06, 0.03, 18), (0.08, 0.04, 24), (0.10, 0.05, 24),
]

results = []
total = 0
print("ML SCAN — 4h ONLY, 16 assets, walk-forward OOS", flush=True)

for tf in ["4h"]:
    print(f"\n{'='*60}", flush=True)
    print(f"  TIMEFRAME: {tf}", flush=True)
    print(f"{'='*60}", flush=True)

    for asset in ASSETS:
        path = None
        for f in sorted(os.listdir(DATA_DIR_OUR), reverse=True):
            if f.startswith(f"{asset}_{tf}") and (f.endswith(".parquet") or f.endswith(".csv")):
                path = os.path.join(DATA_DIR_OUR, f)
                break
        if path is None:
            continue

        try:
            if path.endswith(".parquet"):
                df = pd.read_parquet(path)
            else:
                df = pd.read_csv(path)
        except:
            continue

        if not all(c in df.columns for c in ["open", "high", "low", "close", "volume"]):
            continue

        d = calculate_indicators(df)
        features = build_features(d)
        features = features.dropna()
        if len(features) < 500:
            continue

        bars_per_day = 6  # 4h only

        for tp_pct, sl_pct, horizon in PARAMS:
            for model_type in ["rf", "gbm"]:
                total += 1
                try:
                    labels = build_labels(d.loc[features.index], tp_pct=tp_pct, sl_pct=sl_pct, horizon=horizon)
                    X = features.values
                    y = labels[:len(X)]
                    split = int(len(X) * 0.7)
                    X_tr, X_te = X[:split], X[split:]
                    y_tr, y_te = y[:split], y[split:]

                    if model_type == "rf":
                        model = RandomForestClassifier(n_estimators=200, max_depth=10,
                                                       min_samples_leaf=20, random_state=42, n_jobs=-1)
                    else:
                        model = GradientBoostingClassifier(n_estimators=200, max_depth=5,
                                                           min_samples_leaf=20, learning_rate=0.05, random_state=42)
                    model.fit(X_tr, y_tr)
                    y_pred = model.predict(X_te)
                    acc = (y_pred == y_te).mean() * 100
                    prec = (y_te[y_pred == 1].sum() / y_pred.sum() * 100) if y_pred.sum() > 0 else 0
                    n_signals = int(y_pred.sum())

                    test_df = d.loc[features.index[split:]].reset_index(drop=True)
                    cap, trades = run_ml_backtest(test_df, y_pred[:len(test_df)],
                                                  tp_pct=tp_pct, sl_pct=sl_pct, horizon=horizon)
                    if len(trades) < 10:
                        continue

                    oos_days = len(test_df) / bars_per_day
                    roi = (cap / INITIAL_CAPITAL - 1) * 100
                    daily = roi / max(oos_days, 1)
                    w = [t for t in trades if t["pnl"] > 0]
                    wr = len(w) / len(trades) * 100
                    tw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                    tl = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                    pf = tw / tl if tl > 0 else 0

                    r = {
                        "asset": asset, "model": model_type, "tf": tf,
                        "tp_pct": tp_pct, "sl_pct": sl_pct,
                        "roi_day": round(daily, 4), "roi_yr": round(daily * 365, 1),
                        "pf": round(pf, 2), "wr": round(wr, 1),
                        "trades": len(trades), "trades_per_day": round(len(trades) / max(oos_days, 1), 2),
                        "accuracy": round(acc, 1), "precision": round(prec, 1),
                        "final_cap": round(cap, 0), "signals": n_signals,
                        "gdd": 0, "test_years": round(oos_days / 365, 2),
                    }
                    if daily > 0.05:
                        results.append(r)
                        print(f"  {daily:.3f}%/day {asset} {tf} {model_type} TP={tp_pct*100}% "
                              f"PF={pf:.2f} WR={wr:.1f}% Acc={acc:.0f}% Trades={len(trades)}", flush=True)
                except Exception:
                    pass

        # Save after each asset
        results.sort(key=lambda x: -x["roi_day"])
        json.dump(results, open("/home/ubuntu/Garima/storage/ml_results.json", "w"), indent=2)
        print(f"  {asset} {tf} done ({total} tested, {len(results)} found)", flush=True)

results.sort(key=lambda x: -x["roi_day"])
json.dump(results, open("/home/ubuntu/Garima/storage/ml_results.json", "w"), indent=2)

print(f"\nML COMPLETE: {total} tested, {len(results)} found", flush=True)
print(f">= 1%: {len([r for r in results if r['roi_day'] >= 1.0])}", flush=True)
print(f">= 0.5%: {len([r for r in results if r['roi_day'] >= 0.5])}", flush=True)
print(f">= 0.25%: {len([r for r in results if r['roi_day'] >= 0.25])}", flush=True)
for i, r in enumerate(results[:10]):
    print(f"  {i+1}. {r['roi_day']:.3f}%/day {r['asset']} {r['model']} "
          f"PF={r['pf']} WR={r['wr']}% Trades={r['trades']}", flush=True)
print("DONE", flush=True)
