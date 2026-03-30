"""
TV-Validated Alpha Strategies - Batch 22 (Strategies 243-260)
Based on TradingView backtesting results. Focus on high Sharpe + Win Rate.
Best performer: PSAR_Volume_Surge on ETH 4h — 508%/yr, 62.7% WR, 1.81 Sharpe on TV.
"""

STRATEGY_COMBINATIONS = [
    # --- TV-proven high performers (modified for more trades) ---
    {"id": 243, "name": "PSAR_Vol_Surge_v2", "strategies": ["PSAR_Bull", "Volume_Spike", "EMA_Cross", "Supertrend", "Trend_MA50", "ADX_Trend", "OBV_Rising"], "stop_loss": 0.015, "take_profit": 0.06, "trailing_stop": 0.007, "min_agreement": 5, "description": "Modified 44 — relaxed volume, added MA50+ADX+OBV, 5 of 7"},
    {"id": 244, "name": "Ichi_PSAR_ADX_v2", "strategies": ["Ichimoku_Bull", "PSAR_Bull", "ADX_Trend", "OBV_Rising", "EMA_Cross", "Supertrend"], "stop_loss": 0.015, "take_profit": 0.06, "trailing_stop": 0.007, "min_agreement": 5, "description": "Modified 28 — added EMA+Supertrend, 5 of 7"},
    {"id": 245, "name": "Trend_Confirm_v2", "strategies": ["EMA_Cross", "Trend_MA50", "Ichimoku_Bull", "PSAR_Bull", "Supertrend", "ADX_Trend", "OBV_Rising"], "stop_loss": 0.015, "take_profit": 0.06, "trailing_stop": 0.007, "min_agreement": 6, "description": "Modified 26 — 8 signals 6 of 8 agree"},

    # --- Pure persistent trend (no volume/momentary signals — maximum trades) ---
    {"id": 246, "name": "Pure_Trend_5of6", "strategies": ["EMA_Cross", "Supertrend", "PSAR_Bull", "ADX_Trend", "Trend_MA50", "OBV_Rising"], "stop_loss": 0.015, "take_profit": 0.06, "trailing_stop": 0.007, "min_agreement": 5, "description": "6 persistent signals, 5 must agree"},
    {"id": 247, "name": "Pure_Trend_4of6", "strategies": ["EMA_Cross", "Supertrend", "PSAR_Bull", "ADX_Trend", "Trend_MA50", "OBV_Rising"], "stop_loss": 0.015, "take_profit": 0.06, "trailing_stop": 0.007, "min_agreement": 4, "description": "Same 6 persistent signals, 4 must agree — more trades"},
    {"id": 248, "name": "Pure_Trend_All7", "strategies": ["EMA_Cross", "Supertrend", "PSAR_Bull", "ADX_Trend", "Trend_MA50", "OBV_Rising", "Ichimoku_Bull"], "stop_loss": 0.015, "take_profit": 0.06, "trailing_stop": 0.007, "min_agreement": 7, "description": "7 persistent, ALL must agree — most selective"},

    # --- Ichimoku-focused (best WR on TV: 84.8%) ---
    {"id": 249, "name": "Ichi_Full_Stack", "strategies": ["Ichimoku_Bull", "PSAR_Bull", "EMA_Cross", "Supertrend", "Trend_MA50", "ADX_Trend"], "stop_loss": 0.015, "take_profit": 0.06, "trailing_stop": 0.007, "min_agreement": 5, "description": "Ichimoku + 5 trend confirms, 5 of 6"},
    {"id": 250, "name": "Ichi_EMA_PSAR", "strategies": ["Ichimoku_Bull", "EMA_Cross", "PSAR_Bull", "Trend_MA50"], "stop_loss": 0.015, "take_profit": 0.06, "trailing_stop": 0.007, "min_agreement": 4, "description": "4 persistent trends ALL agree"},

    # --- Tight SL/TP variants for high Sharpe ---
    {"id": 251, "name": "Micro_PSAR_Trend", "strategies": ["PSAR_Bull", "EMA_Cross", "Supertrend", "ADX_Trend", "Trend_MA50"], "stop_loss": 0.008, "take_profit": 0.03, "trailing_stop": 0.004, "min_agreement": 5, "description": "Ultra tight SL/TP, ALL 5 agree"},
    {"id": 252, "name": "Micro_Ichi_EMA", "strategies": ["Ichimoku_Bull", "EMA_Cross", "PSAR_Bull", "Supertrend", "OBV_Rising"], "stop_loss": 0.008, "take_profit": 0.03, "trailing_stop": 0.004, "min_agreement": 5, "description": "Ultra tight with Ichimoku"},
    {"id": 253, "name": "Nano_All_Trend", "strategies": ["EMA_Cross", "Ichimoku_Bull", "PSAR_Bull", "Supertrend", "ADX_Trend", "Trend_MA50", "OBV_Rising"], "stop_loss": 0.005, "take_profit": 0.02, "trailing_stop": 0.003, "min_agreement": 6, "description": "Tightest possible, 6 of 7"},

    # --- Volume + trend combos (balanced) ---
    {"id": 254, "name": "Vol_Trend_Fusion", "strategies": ["Volume_Spike", "EMA_Cross", "PSAR_Bull", "Supertrend", "ADX_Trend"], "stop_loss": 0.015, "take_profit": 0.06, "trailing_stop": 0.007, "min_agreement": 4, "description": "Volume spike + 4 trend signals, 4 of 5"},
    {"id": 255, "name": "Vol_Ichi_PSAR", "strategies": ["Volume_Spike", "Ichimoku_Bull", "PSAR_Bull", "EMA_Cross", "OBV_Rising"], "stop_loss": 0.015, "take_profit": 0.06, "trailing_stop": 0.007, "min_agreement": 4, "description": "Volume + Ichimoku + PSAR, 4 of 5"},

    # --- Breakout + trend (for higher ROI) ---
    {"id": 256, "name": "Break_Trend_Pro", "strategies": ["Breakout_20", "EMA_Cross", "PSAR_Bull", "Supertrend", "ADX_Trend"], "stop_loss": 0.015, "take_profit": 0.08, "trailing_stop": 0.007, "min_agreement": 4, "description": "Breakout with 4 trend confirms"},
    {"id": 257, "name": "Break_Ichi_PSAR", "strategies": ["Breakout_20", "Ichimoku_Bull", "PSAR_Bull", "ADX_Trend", "OBV_Rising"], "stop_loss": 0.015, "take_profit": 0.08, "trailing_stop": 0.007, "min_agreement": 4, "description": "Breakout + Ichimoku + PSAR, 4 of 5"},

    # --- MACD + trend (our walk-forward validated combo) ---
    {"id": 258, "name": "MACD_Trend_Stack", "strategies": ["MACD_Cross", "EMA_Cross", "PSAR_Bull", "Supertrend", "ADX_Trend", "Trend_MA50"], "stop_loss": 0.015, "take_profit": 0.06, "trailing_stop": 0.007, "min_agreement": 4, "description": "MACD + 5 trend signals, 4 of 6"},
]


def get_strategies():
    return STRATEGY_COMBINATIONS

def get_strategy_by_id(strategy_id):
    for s in STRATEGY_COMBINATIONS:
        if s["id"] == strategy_id:
            return s
    return None

def format_strategy_for_telegram(strategy):
    return f"""
Strategy #{strategy['id']}: {strategy['name']}

Description: {strategy['description']}
Strategies: {', '.join(strategy['strategies'])}
Stop Loss: {strategy['stop_loss']*100}%
Take Profit: {strategy['take_profit']*100}%
Trailing Stop: {strategy['trailing_stop']*100}%
Min Agreement: {strategy['min_agreement']}
"""

def get_all_strategies_telegram():
    msg = "TV-Validated Alpha Strategies - Batch 22\n\n"
    for s in STRATEGY_COMBINATIONS:
        msg += format_strategy_for_telegram(s)
        msg += "\n" + "=" * 30 + "\n\n"
    return msg
