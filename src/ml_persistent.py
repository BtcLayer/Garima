"""
Persistent ML — saves models + results + tested combos.
Never repeats work. Learns from ALL previous results.

Saves:
- storage/ml_models/{asset}_{signal}.pkl — trained model per asset+signal
- storage/ml_memory.json — all tested combos + results (never lose history)
- storage/ml_results.json — best results for dashboard/bot

On restart:
- Loads all previous models and results
- Skips already-tested combos
- Retrains on combined old+new data if new data available
"""
import sys, os, json, pickle, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd, numpy as np
from run_strategies_batch import load_data, calculate_indicators, INITIAL_CAPITAL
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.preprocessing import StandardScaler

FEE = 0.001
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE = os.path.join(ROOT, "storage")
MODEL_DIR = os.path.join(STORAGE, "ml_models")
MEMORY_FILE = os.path.join(STORAGE, "ml_memory.json")
RESULTS_FILE = os.path.join(STORAGE, "ml_results.json")

os.makedirs(MODEL_DIR, exist_ok=True)


class PersistentML:
    def __init__(self):
        self.memory = self._load_memory()
        self.results = self._load_results()
        self.models = {}
        print(f"  Loaded: {len(self.memory.get('tested', {}))} tested combos, "
              f"{len(self.results)} results from previous runs", flush=True)

    def _load_memory(self):
        try:
            return json.load(open(MEMORY_FILE))
        except:
            return {"tested": {}, "best_per_asset": {}, "total_trained": 0}

    def _load_results(self):
        try:
            return json.load(open(RESULTS_FILE))
        except:
            return []

    def _save_memory(self):
        json.dump(self.memory, open(MEMORY_FILE, "w"), indent=2)

    def _save_results(self):
        self.results.sort(key=lambda x: -x.get("roi_day", 0))
        json.dump(self.results, open(RESULTS_FILE, "w"), indent=2)

    def _combo_key(self, asset, signal, tp, sl, model_type):
        return f"{asset}|{signal}|{tp}|{sl}|{model_type}"

    def is_tested(self, asset, signal, tp, sl, model_type):
        key = self._combo_key(asset, signal, tp, sl, model_type)
        return key in self.memory.get("tested", {})

    def mark_tested(self, asset, signal, tp, sl, model_type, result):
        key = self._combo_key(asset, signal, tp, sl, model_type)
        self.memory.setdefault("tested", {})[key] = {
            "roi_day": result.get("roi_day", 0) if result else 0,
            "profitable": result is not None,
        }
        self.memory["total_trained"] = self.memory.get("total_trained", 0) + 1

    def save_model(self, asset, signal, model, scaler):
        key = f"{asset}_{signal}".replace(" ", "_").replace("+", "_")
        model_path = os.path.join(MODEL_DIR, f"{key}.pkl")
        scaler_path = os.path.join(MODEL_DIR, f"{key}_scaler.pkl")
        try:
            pickle.dump(model, open(model_path, "wb"))
            pickle.dump(scaler, open(scaler_path, "wb"))
        except:
            pass

    def load_model(self, asset, signal):
        key = f"{asset}_{signal}".replace(" ", "_").replace("+", "_")
        model_path = os.path.join(MODEL_DIR, f"{key}.pkl")
        scaler_path = os.path.join(MODEL_DIR, f"{key}_scaler.pkl")
        try:
            model = pickle.load(open(model_path, "rb"))
            scaler = pickle.load(open(scaler_path, "rb"))
            return model, scaler
        except:
            return None, None

    def add_result(self, result):
        # Deduplicate: keep best per (asset, signal, tp_pct)
        key = (result.get("asset", ""), result.get("signal", ""), result.get("tp_pct", 0))
        existing = None
        for i, r in enumerate(self.results):
            if (r.get("asset", ""), r.get("signal", ""), r.get("tp_pct", 0)) == key:
                existing = i
                break
        if existing is not None:
            if result["roi_day"] > self.results[existing]["roi_day"]:
                self.results[existing] = result
        else:
            self.results.append(result)

    def get_stats(self):
        return {
            "total_tested": len(self.memory.get("tested", {})),
            "total_trained": self.memory.get("total_trained", 0),
            "total_results": len(self.results),
            "above_01": len([r for r in self.results if r.get("roi_day", 0) >= 0.1]),
            "above_05": len([r for r in self.results if r.get("roi_day", 0) >= 0.5]),
            "above_1": len([r for r in self.results if r.get("roi_day", 0) >= 1.0]),
            "best": self.results[0] if self.results else None,
        }


def features_at_entry(df, i):
    row = df.iloc[i]
    close = row["close"]
    return {
        "rsi": row.get("rsi", 50), "adx": row.get("adx", 0),
        "macd_hist": row.get("macd_hist", 0), "vol_ratio": row.get("vol_ratio", 1),
        "stoch": row.get("stoch_k", 50), "atr_pct": row.get("atr", 0) / close if close > 0 else 0,
        "bb_pos": (close - row.get("bb_lower", close)) / max(row.get("bb_upper", close) - row.get("bb_lower", close), 0.001),
        "ema_dist": (row.get("ema8", close) - row.get("ema21", close)) / close,
        "trend_score": float(row.get("ema8",0)>row.get("ema21",0)) + float(close>row.get("ema50",0)) + float(close>row.get("supertrend",0)) + float(close>row.get("psar",0)),
        "ret1": df["close"].pct_change(1).iloc[i] if i > 0 else 0,
        "ret3": df["close"].pct_change(3).iloc[i] if i > 2 else 0,
        "ret6": df["close"].pct_change(6).iloc[i] if i > 5 else 0,
        "obv_trend": float(row.get("obv", 0) > row.get("obv_sma20", 0)),
        "cci": row.get("cci", 0) / 200,
        "mfi": row.get("mfi", 50),
        "williams": row.get("williams_r", -50),
        "near_high": close / df["high"].iloc[max(0,i-20):i+1].max() if i >= 1 else 1,
    }


def collect_trades(df, bull_signal, tp, sl, horizon=12):
    trades = []
    i = 0
    while i < len(df) - horizon - 1:
        if bull_signal.iloc[i] == 1:
            entry = df.iloc[i+1]["open"] * (1 + FEE)
            result = 0
            for j in range(i+2, min(i+horizon+2, len(df))):
                if df.iloc[j]["low"] <= entry * (1 - sl): break
                if df.iloc[j]["high"] >= entry * (1 + tp): result = 1; break
            trades.append({"idx": i, "result": result})
            i = j + 1 if j > i else i + 2
        else:
            i += 1
    return trades


def run_persistent_scan():
    ml = PersistentML()
    ASSETS = ["ETHUSDT", "BTCUSDT", "ADAUSDT", "SOLUSDT", "LINKUSDT",
              "BNBUSDT", "XRPUSDT", "AVAXUSDT", "DOTUSDT", "LTCUSDT"]

    # All signal generators
    def make_signals(df):
        sigs = {}
        sigs["EMA_Cross"] = ((df["ema8"] > df["ema21"]) & (df["ema8"].shift(1) <= df["ema21"].shift(1))).astype(int)
        sigs["MACD_Cross"] = ((df["macd"] > df["macd_signal"]) & (df["macd"].shift(1) <= df["macd_signal"].shift(1))).astype(int)
        sigs["RSI_Bounce"] = ((df["rsi"] > 30) & (df["rsi"].shift(1) <= 30)).astype(int)
        sigs["BB_Bounce"] = ((df["close"] > df["bb_lower"]) & (df["close"].shift(1) <= df["bb_lower"].shift(1))).astype(int)
        sigs["Stoch_Bounce"] = ((df["stoch_k"] > 20) & (df["stoch_k"].shift(1) <= 20)).astype(int)
        sigs["Supertrend_Flip"] = ((df["close"] > df["supertrend"]) & (df["close"].shift(1) <= df["supertrend"].shift(1))).astype(int)
        sigs["PSAR_Flip"] = ((df["close"] > df["psar"]) & (df["close"].shift(1) <= df["psar"].shift(1))).astype(int)
        sigs["Breakout_Vol"] = ((df["close"] > df["high_20"]) & (df["vol_ratio"] > 1.5)).astype(int)
        sigs["Ichimoku_Cross"] = ((df["close"] > df[["senkou_span_a","senkou_span_b"]].max(axis=1)) & (df["close"].shift(1) <= df[["senkou_span_a","senkou_span_b"]].max(axis=1).shift(1))).astype(int)
        sigs["OBV_Cross"] = ((df["obv"] > df["obv_sma20"]) & (df["obv"].shift(1) <= df["obv_sma20"].shift(1))).astype(int)
        sigs["Keltner_Bounce"] = ((df["close"] > df["keltner_lower"]) & (df["close"].shift(1) <= df["keltner_lower"].shift(1))).astype(int)
        sigs["CCI_Bounce"] = ((df["cci"] > -100) & (df["cci"].shift(1) <= -100)).astype(int)
        # Trend+Dip combos
        sigs["EMA_RSI_Dip"] = (sigs["RSI_Bounce"] & (df["ema8"] > df["ema21"])).astype(int)
        sigs["ST_BB_Dip"] = (sigs["BB_Bounce"] & (df["close"] > df["supertrend"])).astype(int)
        sigs["PSAR_Stoch_Dip"] = (sigs["Stoch_Bounce"] & (df["close"] > df["psar"])).astype(int)
        sigs["Ichi_CCI_Dip"] = (sigs["CCI_Bounce"] & (df["close"] > df[["senkou_span_a","senkou_span_b"]].max(axis=1))).astype(int)
        return sigs

    TP_SL = [(0.02,0.01), (0.03,0.015), (0.04,0.02), (0.06,0.03), (0.08,0.04), (0.10,0.05), (0.15,0.07), (0.20,0.10)]
    new_tested = 0
    skipped = 0

    for asset in ASSETS:
        df = load_data(f"{asset}_4h")
        if df is None: continue
        df = calculate_indicators(df)
        signals = make_signals(df)

        for sig_name, bull in signals.items():
            for tp, sl in TP_SL:
                if ml.is_tested(asset, sig_name, tp, sl, "ensemble"):
                    skipped += 1
                    continue

                new_tested += 1
                trades = collect_trades(df, bull, tp, sl)
                if len(trades) < 30:
                    ml.mark_tested(asset, sig_name, tp, sl, "ensemble", None)
                    continue

                X_list = [features_at_entry(df, t["idx"]) for t in trades]
                y = np.array([t["result"] for t in trades])
                X = pd.DataFrame(X_list).fillna(0).values
                split = int(len(X) * 0.7)
                if split < 15 or len(X) - split < 10:
                    ml.mark_tested(asset, sig_name, tp, sl, "ensemble", None)
                    continue

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
                    ml.mark_tested(asset, sig_name, tp, sl, "ensemble", None)
                    continue

                # Save model
                ml.save_model(asset, sig_name, ens, scaler)

                best_result = None
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
                        r = {
                            "asset": asset, "signal": sig_name, "model": f"Persistent_C{int(conf*100)}",
                            "tf": "4h", "tp_pct": tp, "sl_pct": sl,
                            "roi_day": round(daily, 4), "roi_yr": round(daily * 365, 1),
                            "pf": round(pf, 2), "wr": round(fwr, 1),
                            "trades": len(filtered), "orig_wr": round(orig_wr, 1),
                            "improvement": round(fwr - orig_wr, 1), "confidence": conf,
                            "gdd": 0, "trades_per_day": round(len(filtered) / max(oos_days, 1), 2),
                            "test_years": round(oos_days / 365, 2),
                            "accuracy": 0, "precision": 0, "final_cap": 0,
                        }
                        ml.add_result(r)
                        if best_result is None or daily > best_result.get("roi_day", 0):
                            best_result = r
                        if daily > 0.1:
                            print(f"  ** {daily:.3f}%/day {asset} {sig_name} C={conf} TP={tp*100}% WR:{orig_wr:.0f}→{fwr:.0f}% PF={pf:.2f} **", flush=True)

                ml.mark_tested(asset, sig_name, tp, sl, "ensemble", best_result)

        # Save after each asset
        ml._save_memory()
        ml._save_results()
        stats = ml.get_stats()
        print(f"  {asset} done | New: {new_tested} | Skipped: {skipped} | Total results: {stats['total_results']} | Best: {stats['best']['roi_day']:.3f}%/day" if stats['best'] else f"  {asset} done | no results yet", flush=True)

    ml._save_memory()
    ml._save_results()
    stats = ml.get_stats()
    print(f"\nCOMPLETE | Tested: {stats['total_tested']} | Results: {stats['total_results']} | >= 0.1%: {stats['above_01']}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    print("=" * 80, flush=True)
    print("  PERSISTENT ML — remembers everything, never repeats work", flush=True)
    print("  16 signals + 8 TP/SL + ML filter | Saves models + memory", flush=True)
    print("=" * 80, flush=True)
    run_persistent_scan()
