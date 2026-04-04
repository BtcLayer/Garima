"""Use trained ML to predict which new strategies + assets will work on TV."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ml_online import predict_tv_success

# ═══════════════════════════════════════════
# Predict success for new strategies (#37-44) on expanded asset list
# ═══════════════════════════════════════════

STRATEGIES = [
    {"name": "PSAR_Trend", "signals": "psar+adx+ema+volume", "tp": 12.0, "sl": 1.5, "trail": 4.0},
    {"name": "ADX_DI_Cross", "signals": "adx+di_cross+ema+volume", "tp": 12.0, "sl": 1.5, "trail": 4.0},
    {"name": "Chandelier_Exit", "signals": "chandelier+adx+ema+volume", "tp": 12.0, "sl": 1.5, "trail": 4.0},
    {"name": "CCI_Trend", "signals": "cci+adx+ema+volume", "tp": 12.0, "sl": 1.5, "trail": 4.0},
    {"name": "Williams_R", "signals": "williams_r+adx+ema+volume", "tp": 12.0, "sl": 1.5, "trail": 4.0},
    {"name": "Keltner_Breakout", "signals": "keltner+adx+ema+volume", "tp": 12.0, "sl": 1.5, "trail": 4.0},
    {"name": "TRIX_Signal", "signals": "trix+adx+ema+volume", "tp": 12.0, "sl": 1.5, "trail": 4.0},
    {"name": "Aroon_Trend", "signals": "aroon+adx+ema+volume", "tp": 12.0, "sl": 1.5, "trail": 4.0},
    # Also predict proven strategies on NEW assets
    {"name": "Donchian_Trend", "signals": "donchian+adx+ema+volume", "tp": 12.0, "sl": 1.5, "trail": 4.0},
    {"name": "HA_Trend", "signals": "heikin_ashi+adx+ema+volume", "tp": 10.0, "sl": 1.5, "trail": 3.5},
    {"name": "Momentum_V2", "signals": "roc+multi_tf+adx+ema+volume", "tp": 10.0, "sl": 1.5, "trail": 3.5},
    {"name": "Breakout_Retest", "signals": "breakout_retest+adx+volume", "tp": 10.0, "sl": 1.5, "trail": 3.5},
    {"name": "BB_Squeeze_V2", "signals": "bb+squeeze+adx+ema+volume", "tp": 10.0, "sl": 1.5, "trail": 3.5},
]

ASSETS = ["ETHUSDT", "BTCUSDT", "DOTUSDT", "SOLUSDT", "LINKUSDT",
          "BNBUSDT", "XRPUSDT", "AVAXUSDT", "ADAUSDT", "LTCUSDT"]

# Build all combinations
candidates = []
for strat in STRATEGIES:
    for asset in ASSETS:
        candidates.append({
            "asset": asset,
            "tf": "4h",
            **strat
        })

print(f"Predicting TV success for {len(candidates)} strategy-asset combos...\n")

predictions = predict_tv_success(candidates)

# Show top predictions
print("=" * 80)
print("TOP 30 PREDICTED TV-PROFITABLE COMBOS (sorted by predicted profit)")
print("=" * 80)
print(f"{'Rank':<5} {'Strategy':<20} {'Asset':<12} {'Predicted TV Profit%':<22} {'TP/SL':<8}")
print("-" * 80)

for i, p in enumerate(predictions[:30], 1):
    print(f"{i:<5} {p['name']:<20} {p['asset']:<12} {p['predicted_tv_profit']:<22.2f} {p['tp']}/{p['sl']}")

print("\n" + "=" * 80)
print("BOTTOM 10 (avoid these)")
print("=" * 80)
for p in predictions[-10:]:
    print(f"  {p['name']:<20} {p['asset']:<12} {p['predicted_tv_profit']:<22.2f}")

# Summary by strategy
print("\n" + "=" * 80)
print("AVERAGE PREDICTED PROFIT BY STRATEGY")
print("=" * 80)
from collections import defaultdict
strat_avg = defaultdict(list)
for p in predictions:
    strat_avg[p['name']].append(p['predicted_tv_profit'])

sorted_strats = sorted(strat_avg.items(), key=lambda x: -sum(x[1])/len(x[1]))
for name, vals in sorted_strats:
    avg = sum(vals) / len(vals)
    best = max(vals)
    print(f"  {name:<20} avg={avg:>10.2f}%  best={best:>10.2f}%")

# Summary by asset
print("\n" + "=" * 80)
print("AVERAGE PREDICTED PROFIT BY ASSET")
print("=" * 80)
asset_avg = defaultdict(list)
for p in predictions:
    asset_avg[p['asset']].append(p['predicted_tv_profit'])

sorted_assets = sorted(asset_avg.items(), key=lambda x: -sum(x[1])/len(x[1]))
for name, vals in sorted_assets:
    avg = sum(vals) / len(vals)
    best = max(vals)
    print(f"  {name:<12} avg={avg:>10.2f}%  best={best:>10.2f}%")
