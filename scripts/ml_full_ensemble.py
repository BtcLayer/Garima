#!/usr/bin/env python3
"""
ML FULL ENSEMBLE — uses ALL archive strategies + their combos.
Takes the 9 ensemble combos from combo_strategies.py,
runs each as a signal, then ML filters for realistic winners.

Signals from archives:
- 12 individual indicators (EMA, RSI, MACD, BB, Volume, Breakout, Stoch, Supertrend, VWAP, ADX, Trend_MA, OBV)
- 9 ensemble combos (Conservative, Moderate, Aggressive)
- 3 winning signals from tournament (OBV_momentum, Lookback, Supertrend_level)
- Squeeze momentum (linreg)
= 25 total signal sources

ML learns which signal + which conditions = WIN
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd, numpy as np
from run_strategies_batch import load_data, calculate_indicators, INITIAL_CAPITAL
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.preprocessing import StandardScaler

FEE = 0.001
STORAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage")

# ── ALL SIGNAL GENERATORS ──

def sig_ema_cross(df): return ((df["ema8"] > df["ema21"]).astype(int), (df["ema8"] < df["ema21"]).astype(int))
def sig_rsi(df): return ((df["rsi"] < 30).astype(int), (df["rsi"] > 70).astype(int))
def sig_macd(df):
    bull = ((df["macd"] > df["macd_signal"]) & (df["macd"].shift(1) <= df["macd_signal"].shift(1))).astype(int)
    bear = ((df["macd"] < df["macd_signal"]) & (df["macd"].shift(1) >= df["macd_signal"].shift(1))).astype(int)
    return bull, bear
def sig_bb(df): return ((df["close"] < df["bb_lower"]).astype(int), (df["close"] > df["bb_upper"]).astype(int))
def sig_volume(df): return (((df["vol_ratio"] > 1.5) & (df["close"] > df["close"].shift(1))).astype(int), ((df["vol_ratio"] > 1.5) & (df["close"] < df["close"].shift(1))).astype(int))
def sig_breakout(df): return ((df["close"] > df["high_20"]).astype(int), (df["close"] < df["low_20"]).astype(int))
def sig_stoch(df): return ((df["stoch_k"] < 20).astype(int), (df["stoch_k"] > 80).astype(int))
def sig_supertrend(df): return ((df["close"] > df["supertrend"]).astype(int), (df["close"] < df["supertrend"]).astype(int))
def sig_vwap(df): return ((df["close"] > df["vwap"]).astype(int), (df["close"] < df["vwap"]).astype(int))
def sig_adx(df): return ((df["adx"] > 25).astype(int), (df["adx"] > 25).astype(int))
def sig_trend_ma(df): return ((df["close"] > df["ema50"]).astype(int), (df["close"] < df["ema50"]).astype(int))
def sig_obv(df): return ((df["obv"] > df["obv_sma20"]).astype(int), (df["obv"] < df["obv_sma20"]).astype(int))
def sig_ichimoku(df):
    cloud_top = df[["senkou_span_a", "senkou_span_b"]].max(axis=1)
    cloud_bot = df[["senkou_span_a", "senkou_span_b"]].min(axis=1)
    return ((df["close"] > cloud_top).astype(int), (df["close"] < cloud_bot).astype(int))
def sig_psar(df): return ((df["close"] > df["psar"]).astype(int), (df["close"] < df["psar"]).astype(int))
def sig_lookback(df, n=9):
    return ((df["close"] > df["close"].shift(n)).astype(int), (df["close"] < df["close"].shift(n)).astype(int))
def sig_squeeze(df):
    if "keltner_upper" in df.columns:
        sq = (df["bb_upper"] < df["keltner_upper"]) & (df["bb_lower"] > df["keltner_lower"])
        release = ~sq & sq.shift(1).fillna(False)
        mom = df["close"].pct_change(20)
        return ((release & (mom > 0)).astype(int), (release & (mom < 0)).astype(int))
    return (pd.Series(0, index=df.index), pd.Series(0, index=df.index))

ALL_SIGNALS = {
    "EMA_Cross": sig_ema_cross, "RSI": sig_rsi, "MACD": sig_macd,
    "BB": sig_bb, "Volume": sig_volume, "Breakout": sig_breakout,
    "Stochastic": sig_stoch, "Supertrend": sig_supertrend,
    "VWAP": sig_vwap, "ADX": sig_adx, "Trend_MA": sig_trend_ma,
    "OBV": sig_obv, "Ichimoku": sig_ichimoku, "PSAR": sig_psar,
    "Lookback": sig_lookback, "Squeeze": sig_squeeze,
}

# Archive ensemble combos
ENSEMBLE_COMBOS = [
    ("Conservative_1", ["EMA_Cross", "RSI", "Supertrend", "Trend_MA"], 2),
    ("Conservative_2", ["EMA_Cross", "MACD", "ADX", "Trend_MA"], 2),
    ("Conservative_3", ["RSI", "Stochastic", "BB", "Trend_MA"], 2),
    ("Moderate_1", ["EMA_Cross", "MACD", "RSI", "Supertrend", "ADX"], 3),
    ("Moderate_2", ["BB", "Volume", "RSI", "Stochastic", "Trend_MA"], 3),
    ("Moderate_3", ["Breakout", "Volume", "MACD", "Supertrend", "VWAP"], 3),
    ("Aggressive_1", ["EMA_Cross", "MACD", "Volume", "Breakout", "ADX", "VWAP"], 3),
    ("Aggressive_2", ["RSI", "Stochastic", "BB", "Volume", "Supertrend", "Trend_MA"], 3),
    ("Full_Ensemble", list(ALL_SIGNALS.keys()), 5),
]


def collect_ensemble_trades(df, combo_signals, combo_shorts, min_ag, tp, sl, horizon):
    """Collect trades from ensemble signal."""
    bull = combo_signals.sum(axis=1) >= min_ag
    bear = combo_shorts.sum(axis=1) >= min_ag

    trades = []
    i = 0
    while i < len(df) - horizon - 1:
        side = None
        if bull.iloc[i]: side = "long"
        elif bear.iloc[i]: side = "short"

        if side:
            entry = df.iloc[i + 1]["open"] * (1 + FEE if side == "long" else 1 - FEE)
            tp_p = entry * (1 + tp) if side == "long" else entry * (1 - tp)
            sl_p = entry * (1 - sl) if side == "long" else entry * (1 + sl)
            result = 0
            for j in range(i + 2, min(i + horizon + 2, len(df))):
                if side == "long":
                    if df.iloc[j]["low"] <= sl_p: break
                    if df.iloc[j]["high"] >= tp_p: result = 1; break
                else:
                    if df.iloc[j]["high"] >= sl_p: break
                    if df.iloc[j]["low"] <= tp_p: result = 1; break

            # Features at entry
            row = df.iloc[i]
            close = row["close"]
            feat = {
                "ema_dist": (row.get("ema8", close) - row.get("ema21", close)) / close,
                "rsi": row.get("rsi", 50), "adx": row.get("adx", 0),
                "macd_hist": row.get("macd_hist", 0), "vol_ratio": row.get("vol_ratio", 1),
                "stoch": row.get("stoch_k", 50), "atr_pct": row.get("atr", 0) / close if close > 0 else 0,
                "bb_pos": (close - row.get("bb_lower", close)) / max(row.get("bb_upper", close) - row.get("bb_lower", close), 0.001),
                "trend_score": float(row.get("ema8", 0) > row.get("ema21", 0)) + float(close > row.get("ema50", 0)) + float(close > row.get("supertrend", 0)) + float(close > row.get("psar", 0)),
                "ret1": df["close"].pct_change(1).iloc[i],
                "ret3": df["close"].pct_change(3).iloc[i],
                "ret6": df["close"].pct_change(6).iloc[i],
                "obv_trend": float(row.get("obv", 0) > row.get("obv_sma20", 0)),
                "cci": row.get("cci", 0) / 200,
                "mfi": row.get("mfi", 50),
                "combo_score": combo_signals.sum(axis=1).iloc[i],
                "side_is_long": float(side == "long"),
            }
            trades.append({"features": feat, "result": result, "bar_idx": i, "side": side})
            i = j + 1 if 'j' in dir() and j > i else i + 2
        else:
            i += 1
    return trades


ASSETS = ["ETHUSDT", "BTCUSDT", "ADAUSDT", "SOLUSDT", "LINKUSDT",
          "BNBUSDT", "XRPUSDT", "AVAXUSDT", "DOTUSDT", "LTCUSDT"]
TP_SL = [(0.02, 0.01), (0.03, 0.015), (0.04, 0.02), (0.06, 0.03), (0.08, 0.04)]


if __name__ == "__main__":
    print("=" * 80, flush=True)
    print("  ML FULL ENSEMBLE — 16 signals + 9 combos + ML filter", flush=True)
    print("  Training ML on WIN/LOSS of EACH ensemble combo", flush=True)
    print("=" * 80, flush=True)

    all_results = []
    total = 0

    for asset in ASSETS:
        df = load_data(f"{asset}_4h")
        if df is None: continue
        df = calculate_indicators(df)

        # Pre-compute all signals
        all_bulls = {}
        all_bears = {}
        for name, func in ALL_SIGNALS.items():
            try:
                b, s = func(df)
                all_bulls[name] = b
                all_bears[name] = s
            except:
                all_bulls[name] = pd.Series(0, index=df.index)
                all_bears[name] = pd.Series(0, index=df.index)

        for combo_name, sig_names, min_ag in ENSEMBLE_COMBOS:
            combo_bulls = pd.DataFrame({n: all_bulls.get(n, pd.Series(0, index=df.index)) for n in sig_names})
            combo_bears = pd.DataFrame({n: all_bears.get(n, pd.Series(0, index=df.index)) for n in sig_names})

            for tp, sl in TP_SL:
                total += 1
                trades = collect_ensemble_trades(df, combo_bulls, combo_bears, min_ag, tp, sl, 12)
                if len(trades) < 30: continue

                X_list = [t["features"] for t in trades]
                y = np.array([t["result"] for t in trades])
                X_df = pd.DataFrame(X_list).fillna(0)
                X = X_df.values

                split = int(len(X) * 0.7)
                if split < 20 or len(X) - split < 10: continue

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
                except: continue

                for conf in [0.5, 0.55, 0.6, 0.65, 0.7]:
                    filtered = y_te[proba >= conf]
                    if len(filtered) < 5: continue
                    fwr = filtered.mean() * 100
                    wins = filtered.sum()
                    losses = len(filtered) - wins
                    gross_win = wins * tp
                    gross_loss = losses * sl
                    pf = gross_win / gross_loss if gross_loss > 0 else 0
                    net_ret = (gross_win - gross_loss) * 100
                    oos_days = (len(df) * 0.3) / 6
                    daily = net_ret / max(oos_days, 1)

                    if daily > 0.03 and fwr > orig_wr:
                        r = {
                            "asset": asset, "signal": combo_name, "model": f"Ensemble_C{int(conf*100)}",
                            "tf": "4h", "tp_pct": tp, "sl_pct": sl,
                            "roi_day": round(daily, 4), "roi_yr": round(daily * 365, 1),
                            "pf": round(pf, 2), "wr": round(fwr, 1),
                            "trades": len(filtered), "orig_wr": round(orig_wr, 1),
                            "orig_trades": len(y_te), "improvement": round(fwr - orig_wr, 1),
                            "confidence": conf, "gdd": 0,
                            "trades_per_day": round(len(filtered) / max(oos_days, 1), 2),
                            "test_years": round(oos_days / 365, 2),
                        }
                        all_results.append(r)
                        if daily > 0.1:
                            print(f"  ** {daily:.3f}%/day {asset} {combo_name} C={conf} TP={tp*100}% WR:{orig_wr:.0f}→{fwr:.0f}% PF={pf:.2f} Trades={len(filtered)} **", flush=True)

        all_results.sort(key=lambda x: -x["roi_day"])
        json.dump(all_results, open(os.path.join(STORAGE, "ml_results.json"), "w"), indent=2)
        print(f"  {asset} done ({total} tested, {len(all_results)} found)", flush=True)

    print(f"\n{'='*80}", flush=True)
    print(f"  COMPLETE: {len(all_results)} improved strategies", flush=True)
    print(f"{'='*80}", flush=True)
    seen = set(); n = 0
    for r in all_results:
        k = (r["asset"], r["signal"])
        if k in seen: continue
        seen.add(k); n += 1
        if n > 20: break
        print(f"  {n}. {r['roi_day']:.3f}%/day {r['asset']} {r['signal']} WR:{r['orig_wr']}→{r['wr']}% PF={r['pf']} Trades={r['trades']}", flush=True)
    print("DONE", flush=True)
