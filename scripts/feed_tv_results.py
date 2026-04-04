"""Feed all TV validation results from April 3 into online learning ML."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ml_online import add_tv_result, train_online_model

# ═══════════════════════════════════════════
# April 3, 2026 — TV Validation Results (all 4h)
# Strategy upgrades with BB Squeeze V2 risk management
# ═══════════════════════════════════════════

results = [
    # TIER_1 (STRONG)
    ("Donchian_Trend", "ETHUSDT", "4h", {"signals": "donchian+adx+ema+volume", "tp": 12.0, "sl": 1.5, "trail": 4.0},
     {"net_profit_pct": 1709101, "roi_ann": 435.74, "win_rate": 83.21, "profit_factor": 12.05, "trades": 1263, "max_drawdown": -1.61, "profitable": True, "sharpe": 2.04, "tier": "TIER_1"}),

    ("Donchian_Trend", "BTCUSDT", "4h", {"signals": "donchian+adx+ema+volume", "tp": 12.0, "sl": 1.5, "trail": 4.0},
     {"net_profit_pct": 75095.25, "roi_ann": 271.11, "win_rate": 82.13, "profit_factor": 10.16, "trades": 1237, "max_drawdown": -3.29, "profitable": True, "sharpe": 2.15, "tier": "TIER_1"}),

    # TIER_2 (PROMISING)
    ("Donchian_Trend", "DOTUSDT", "4h", {"signals": "donchian+adx+ema+volume", "tp": 12.0, "sl": 1.5, "trail": 4.0},
     {"net_profit_pct": 18581.58, "roi_ann": 487.84, "win_rate": 80.29, "profit_factor": 5.4, "trades": 766, "max_drawdown": -14.12, "profitable": True, "sharpe": 1.81, "tier": "TIER_2"}),

    ("Donchian_Trend", "LDOUSDT", "4h", {"signals": "donchian+adx+ema+volume", "tp": 12.0, "sl": 1.5, "trail": 4.0},
     {"net_profit_pct": 2079.187, "roi_ann": 638.16, "win_rate": 82.85, "profit_factor": 6.17, "trades": 519, "max_drawdown": -1.64, "profitable": True, "sharpe": 2.46, "tier": "TIER_2"}),

    ("HA_Trend", "ETHUSDT", "4h", {"signals": "heikin_ashi+adx+ema+volume", "tp": 10.0, "sl": 1.5, "trail": 3.5},
     {"net_profit_pct": 1122.016, "roi_ann": 127.02, "win_rate": 83.23, "profit_factor": 1.79, "trades": 835, "max_drawdown": -1.62, "profitable": True, "sharpe": 2.62, "tier": "TIER_2"}),

    ("HA_Trend", "DOTUSDT", "4h", {"signals": "heikin_ashi+adx+ema+volume", "tp": 10.0, "sl": 1.5, "trail": 3.5},
     {"net_profit_pct": 124.6408, "roi_ann": 138.41, "win_rate": 77.45, "profit_factor": 6.77, "trades": 541, "max_drawdown": -6.2, "profitable": True, "sharpe": 2.7, "tier": "TIER_2"}),

    ("HA_Trend", "BTCUSDT", "4h", {"signals": "heikin_ashi+adx+ema+volume", "tp": 10.0, "sl": 1.5, "trail": 3.5},
     {"net_profit_pct": 124.565, "roi_ann": 75.95, "win_rate": 76.0, "profit_factor": 9.17, "trades": 825, "max_drawdown": -1.73, "profitable": True, "sharpe": 2.97, "tier": "TIER_2"}),

    ("HA_Trend", "LDOUSDT", "4h", {"signals": "heikin_ashi+adx+ema+volume", "tp": 10.0, "sl": 1.5, "trail": 3.5},
     {"net_profit_pct": 44.6988, "roi_ann": 170.48, "win_rate": 83.24, "profit_factor": 8.08, "trades": 436, "max_drawdown": -3.21, "profitable": True, "sharpe": 3.66, "tier": "TIER_2"}),

    ("Momentum_V2", "ETHUSDT", "4h", {"signals": "roc+multi_tf+adx+ema+volume", "tp": 10.0, "sl": 1.5, "trail": 3.5},
     {"net_profit_pct": 60.0485, "roi_ann": 61.65, "win_rate": 80.09, "profit_factor": 11.38, "trades": 457, "max_drawdown": -1.61, "profitable": True, "sharpe": 2.19, "tier": "TIER_2"}),

    ("Momentum_V2", "DOTUSDT", "4h", {"signals": "roc+multi_tf+adx+ema+volume", "tp": 10.0, "sl": 1.5, "trail": 3.5},
     {"net_profit_pct": 18.2798, "roi_ann": 70.26, "win_rate": 79.64, "profit_factor": 12.66, "trades": 352, "max_drawdown": -3.16, "profitable": True, "sharpe": 3.28, "tier": "TIER_2"}),

    ("Momentum_V2", "LDOUSDT", "4h", {"signals": "roc+multi_tf+adx+ema+volume", "tp": 10.0, "sl": 1.5, "trail": 3.5},
     {"net_profit_pct": 7.408, "roi_ann": 74.35, "win_rate": 82.38, "profit_factor": 7.09, "trades": 193, "max_drawdown": -3.08, "profitable": True, "sharpe": 2.6, "tier": "TIER_2"}),

    ("Breakout_Retest", "DOTUSDT", "4h", {"signals": "breakout_retest+adx+volume", "tp": 10.0, "sl": 1.5, "trail": 3.5},
     {"net_profit_pct": 9.0429, "roi_ann": 51.35, "win_rate": 78.24, "profit_factor": 7.72, "trades": 262, "max_drawdown": -3.49, "profitable": True, "sharpe": 2.79, "tier": "TIER_2"}),

    ("Breakout_Retest", "LDOUSDT", "4h", {"signals": "breakout_retest+adx+volume", "tp": 10.0, "sl": 1.5, "trail": 3.5},
     {"net_profit_pct": 5.3186, "roi_ann": 62.21, "win_rate": 78.53, "profit_factor": 6.63, "trades": 177, "max_drawdown": -1.6, "profitable": True, "sharpe": 2.71, "tier": "TIER_2"}),

    # PAPER_TRADE (TESTING)
    ("Momentum_V2", "BTCUSDT", "4h", {"signals": "roc+multi_tf+adx+ema+volume", "tp": 10.0, "sl": 1.5, "trail": 3.5},
     {"net_profit_pct": 17.9397, "roi_ann": 41.1, "win_rate": 79.82, "profit_factor": 9.75, "trades": 436, "max_drawdown": -3.34, "profitable": True, "sharpe": 2.68, "tier": "PAPER_TRADE"}),

    ("Breakout_Retest", "ETHUSDT", "4h", {"signals": "breakout_retest+adx+volume", "tp": 10.0, "sl": 1.5, "trail": 3.5},
     {"net_profit_pct": 17.8535, "roi_ann": 41.03, "win_rate": 81.49, "profit_factor": 13.82, "trades": 335, "max_drawdown": -1.78, "profitable": True, "sharpe": 2.15, "tier": "PAPER_TRADE"}),

    ("Breakout_Retest", "BTCUSDT", "4h", {"signals": "breakout_retest+adx+volume", "tp": 10.0, "sl": 1.5, "trail": 3.5},
     {"net_profit_pct": 8.7749, "roi_ann": 30.59, "win_rate": 80.05, "profit_factor": 10.41, "trades": 240, "max_drawdown": -2.4, "profitable": True, "sharpe": 2.84, "tier": "PAPER_TRADE"}),

    ("Engulfing_V2", "ETHUSDT", "4h", {"signals": "engulfing+volume+ema+adx+rsi", "tp": 10.0, "sl": 1.5, "trail": 3.5},
     {"net_profit_pct": 10.3982, "roi_ann": 32.88, "win_rate": 84.62, "profit_factor": 17.51, "trades": 175, "max_drawdown": -1.61, "profitable": True, "sharpe": 2.29, "tier": "PAPER_TRADE"}),

    ("Engulfing_V2", "BTCUSDT", "4h", {"signals": "engulfing+volume+ema+adx+rsi", "tp": 10.0, "sl": 1.5, "trail": 3.5},
     {"net_profit_pct": 4.3995, "roi_ann": 21.76, "win_rate": 83.33, "profit_factor": 11.02, "trades": 153, "max_drawdown": -1.61, "profitable": True, "sharpe": 2.32, "tier": "PAPER_TRADE"}),

    ("Ichimoku_V2", "LDOUSDT", "4h", {"signals": "ichimoku+adx+volume+momentum", "tp": 10.0, "sl": 1.5, "trail": 3.5},
     {"net_profit_pct": 2.8914, "roi_ann": 44.31, "win_rate": 77.19, "profit_factor": 6.3, "trades": 114, "max_drawdown": -3.11, "profitable": True, "sharpe": 2.06, "tier": "PAPER_TRADE"}),

    ("Ichimoku_V2", "BTCUSDT", "4h", {"signals": "ichimoku+adx+volume+momentum", "tp": 10.0, "sl": 1.5, "trail": 3.5},
     {"net_profit_pct": 3.0537, "roi_ann": 17.82, "win_rate": 81.71, "profit_factor": 18.33, "trades": 175, "max_drawdown": -1.61, "profitable": True, "sharpe": 2.12, "tier": "PAPER_TRADE"}),

    ("Ichimoku_V2", "DOTUSDT", "4h", {"signals": "ichimoku+adx+volume+momentum", "tp": 10.0, "sl": 1.5, "trail": 3.5},
     {"net_profit_pct": 1.9501, "roi_ann": 21.65, "win_rate": 76.36, "profit_factor": 7.96, "trades": 110, "max_drawdown": -1.63, "profitable": True, "sharpe": 1.89, "tier": "PAPER_TRADE"}),

    # WEAK/IGNORE
    ("Ensemble_Fusion", "ETHUSDT", "4h", {"signals": "ichimoku+engulfing+roc+squeeze", "tp": 12.0, "sl": 1.5, "trail": 4.0},
     {"net_profit_pct": 2.0986, "roi_ann": 14.14, "win_rate": 85.71, "profit_factor": 17.21, "trades": 98, "max_drawdown": -6.72, "profitable": True, "sharpe": 1.62, "tier": "WEAK"}),

    ("Ensemble_Fusion", "BTCUSDT", "4h", {"signals": "ichimoku+engulfing+roc+squeeze", "tp": 12.0, "sl": 1.5, "trail": 4.0},
     {"net_profit_pct": 0.9571, "roi_ann": 9.1, "win_rate": 84.86, "profit_factor": 12.41, "trades": 61, "max_drawdown": -2.89, "profitable": True, "sharpe": 1.68, "tier": "WEAK"}),

    ("VWAP_Reversion", "BTCUSDT", "4h", {"signals": "vwap+rsi+ema", "tp": 8.0, "sl": 1.5, "trail": 3.0},
     {"net_profit_pct": 0.8769, "roi_ann": 8.05, "win_rate": 80.0, "profit_factor": 11.12, "trades": 130, "max_drawdown": -2.35, "profitable": True, "sharpe": 1.68, "tier": "WEAK"}),

    ("VWAP_Reversion", "ETHUSDT", "4h", {"signals": "vwap+rsi+ema", "tp": 8.0, "sl": 1.5, "trail": 3.0},
     {"net_profit_pct": 1.6471, "roi_ann": 12.5, "win_rate": 81.56, "profit_factor": 13.71, "trades": 141, "max_drawdown": -1.61, "profitable": True, "sharpe": 2.02, "tier": "WEAK"}),

    ("VWAP_Reversion", "DOTUSDT", "4h", {"signals": "vwap+rsi+ema", "tp": 8.0, "sl": 1.5, "trail": 3.0},
     {"net_profit_pct": 1.4485, "roi_ann": 18.5, "win_rate": 83.33, "profit_factor": 11.7, "trades": 96, "max_drawdown": -1.6, "profitable": True, "sharpe": 2.22, "tier": "PAPER_TRADE"}),

    ("VWAP_Reversion", "LDOUSDT", "4h", {"signals": "vwap+rsi+ema", "tp": 8.0, "sl": 1.5, "trail": 3.0},
     {"net_profit_pct": 0.8267, "roi_ann": 17.56, "win_rate": 76.39, "profit_factor": 5.18, "trades": 72, "max_drawdown": -2.54, "profitable": True, "sharpe": 1.91, "tier": "PAPER_TRADE"}),
]

print(f"Feeding {len(results)} TV validation results into ML...\n")

for strat, asset, tf, params, tv_result in results:
    try:
        add_tv_result(strat, asset, tf, params, tv_result)
    except Exception as e:
        print(f"  Warning: {strat} {asset} — {e}")

print(f"\nTotal results fed. Training online model...")

try:
    model = train_online_model()
    if model:
        print("Model trained successfully!")
    else:
        print("Model training skipped (check data)")
except Exception as e:
    print(f"Training error: {e}")

print("\nDone! ML now has data from 26+ new TV-validated strategies.")
