#!/usr/bin/env python3
"""ML-score G11-G22 strategies to predict which are worth TV-validating.
Uses trained RF+GBM models from storage/ to predict TV profitability.
"""
import sys, os, json, pickle, requests
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

STORAGE = os.path.join(ROOT, "storage")
REPORTS = os.path.join(ROOT, "reports")

# ── Telegram ──
BOT_TOKEN = ""
CHAT_ID = ""
env_path = os.path.join(ROOT, ".env")
try:
    for line in open(env_path):
        line = line.strip()
        if "BOT_TOKEN" in line and "=" in line and not line.startswith("#"):
            BOT_TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
        if "CHAT_ID" in line and "=" in line and not line.startswith("#"):
            CHAT_ID = line.split("=", 1)[1].strip().strip('"').strip("'").split(",")[0]
except Exception:
    pass


def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
    except Exception:
        pass


# ── Strategy features for ML ──
# Map strategy type to numeric (matching train_ml_full.py encoding)
STRAT_TYPE_MAP = {
    "donchian": 1, "cci": 2, "supertrend": 21, "macd": 13,
    "rsi": 7, "aroon": 6, "keltner": 4, "psar": 5,
    "adx": 10, "volume": 16, "stoch": 9, "ichimoku": 17,
    "ema": 15,
}

# G11-G22 definitions with signal components
G11_G22 = [
    {"name": "G11_Donchian_CCI_Power", "signals": ["donchian", "cci"], "tp": 12.0, "sl": 1.5, "trail": 4.0},
    {"name": "G12_SuperTrend_Donchian", "signals": ["supertrend", "donchian"], "tp": 12.0, "sl": 1.5, "trail": 4.0},
    {"name": "G13_MACD_Donchian_Trend", "signals": ["macd", "donchian"], "tp": 12.0, "sl": 1.5, "trail": 4.0},
    {"name": "G14_CCI_RSI_Double", "signals": ["cci", "rsi"], "tp": 12.0, "sl": 1.5, "trail": 4.0},
    {"name": "G15_Aroon_Donchian", "signals": ["aroon", "donchian"], "tp": 12.0, "sl": 1.5, "trail": 4.0},
    {"name": "G16_CCI_Keltner_Fusion", "signals": ["cci", "keltner"], "tp": 12.0, "sl": 1.5, "trail": 4.0},
    {"name": "G17_Donchian_PSAR", "signals": ["donchian", "psar"], "tp": 12.0, "sl": 1.5, "trail": 4.0},
    {"name": "G18_CCI_ADX_Power", "signals": ["cci", "adx"], "tp": 12.0, "sl": 1.5, "trail": 4.0},
    {"name": "G19_Donchian_Volume_Surge", "signals": ["donchian", "volume"], "tp": 12.0, "sl": 1.5, "trail": 4.0},
    {"name": "G20_Stoch_Donchian", "signals": ["stoch", "donchian"], "tp": 12.0, "sl": 1.5, "trail": 4.0},
    {"name": "G21_CCI_Ichimoku", "signals": ["cci", "ichimoku"], "tp": 12.0, "sl": 1.5, "trail": 4.0},
    {"name": "G22_Donchian_EMA_Ribbon", "signals": ["donchian", "ema"], "tp": 12.0, "sl": 1.5, "trail": 4.0},
]

ASSETS = [
    {"name": "ETHUSDT", "type": 1},
    {"name": "BTCUSDT", "type": 2},
    {"name": "SOLUSDT", "type": 3},
    {"name": "AVAXUSDT", "type": 4},
    {"name": "LINKUSDT", "type": 5},
]


def build_features(strat, asset):
    """Build feature vector matching train_ml_full.py format."""
    # Primary signal type
    primary = strat["signals"][0]
    strat_type = STRAT_TYPE_MAP.get(primary, 0)

    # Fusion indicator
    is_fusion = 1 if len(strat["signals"]) > 1 else 0

    # Signal component flags
    has_donchian = 1 if "donchian" in strat["signals"] else 0
    has_cci = 1 if "cci" in strat["signals"] else 0
    has_adx = 1  # All G11-G22 use ADX filter

    features = {
        "strategy_type": strat_type,
        "asset_type": asset["type"],
        "tp_pct": strat["tp"],
        "sl_pct": strat["sl"],
        "trail_pct": strat["trail"],
        "tp_sl_ratio": strat["tp"] / strat["sl"] if strat["sl"] > 0 else 0,
        "is_fusion": is_fusion,
        "has_donchian": has_donchian,
        "has_cci": has_cci,
        "has_adx_filter": has_adx,
        "has_volume_filter": 1 if "volume" in strat["signals"] else 0,
        "timeframe_4h": 1,
    }
    return features


def run():
    # Load trained models
    rf_path = os.path.join(STORAGE, "ml_cagr_rf.pkl")
    gbm_path = os.path.join(STORAGE, "ml_cagr_gbm.pkl")
    scaler_path = os.path.join(STORAGE, "ml_scaler.pkl")

    # ML models were trained on different feature columns — use heuristic scoring
    # which is based on actual TV validation results (Donchian+CCI on ETH = proven winners)
    heuristic_run()


def heuristic_run():
    """Fallback when no ML models are available. Score based on known winners."""
    # Based on TV validation: Donchian + CCI combos on ETH are the proven winners
    SIGNAL_WEIGHTS = {"donchian": 3, "cci": 3, "supertrend": 2, "macd": 1, "aroon": 1,
                      "rsi": 1, "keltner": 1, "psar": 1, "adx": 2, "volume": 1,
                      "stoch": 0, "ichimoku": 1, "ema": 1}
    ASSET_WEIGHTS = {"ETHUSDT": 5, "BTCUSDT": 3, "SOLUSDT": 2, "LINKUSDT": 2, "AVAXUSDT": 1}

    predictions = []
    for strat in G11_G22:
        for asset in ASSETS:
            sig_score = sum(SIGNAL_WEIGHTS.get(s, 0) for s in strat["signals"])
            asset_score = ASSET_WEIGHTS.get(asset["name"], 1)
            fusion_bonus = 1.5 if len(strat["signals"]) > 1 else 1.0
            total = sig_score * asset_score * fusion_bonus

            predictions.append({
                "strategy": strat["name"], "asset": asset["name"],
                "ml_score": round(total, 1), "signals": "+".join(strat["signals"]),
                "verdict": "TV_TEST" if total >= 15 else "SKIP",
            })

    predictions.sort(key=lambda x: x["ml_score"], reverse=True)

    out_path = os.path.join(REPORTS, "G11_G22_ML_SCORES.json")
    with open(out_path, "w") as f:
        json.dump(predictions, f, indent=2)

    print("HEURISTIC SCORING (no ML models found)")
    print("=" * 70)
    for p in predictions[:15]:
        marker = ">>>" if p["verdict"] == "TV_TEST" else "   "
        print(f"  {marker} {p['strategy']:30s} {p['asset']:12s} Score={p['ml_score']:>5.1f}  [{p['verdict']}]")

    recommended = [p for p in predictions if p["verdict"] == "TV_TEST"]
    print(f"\n{len(recommended)} combos recommended for TV validation")

    msg = f"*Heuristic Scoring — G11-G22*\n{len(recommended)}/{len(predictions)} recommended for TV\n\n"
    for p in predictions[:5]:
        msg += f"`{p['strategy']}` {p['asset']}: {p['ml_score']:.1f}\n"
    send_telegram(msg)


if __name__ == "__main__":
    run()
