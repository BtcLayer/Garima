"""
Profitable Strategy Combinations - Batch 19 (Strategies 226-240)
"""

STRATEGY_COMBINATIONS = [
    {"id": 211, "name": "EMA_Breakout_ADX", "strategies": ["EMA_Cross", "Breakout_20", "ADX_Trend", "Supertrend", "Volume_Spike"], "stop_loss": 0.02, "take_profit": 0.12, "trailing_stop": 0.02, "min_agreement": 3, "description": "EMA breakout ADX"},
    {"id": 212, "name": "RSI_Stochastic_VWAP_ADX", "strategies": ["RSI_Oversold", "Stochastic", "VWAP", "ADX_Trend", "MACD_Cross"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 3, "description": "RSI stochastic VWAP ADX"},
    {"id": 213, "name": "MACD_BB_Stochastic_ADX", "strategies": ["MACD_Cross", "BB_Lower", "Stochastic", "ADX_Trend", "Trend_MA50"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 3, "description": "MACD BB stochastic ADX"},
    {"id": 214, "name": "Breakout_EMA_ADX_VWAP", "strategies": ["Breakout_20", "EMA_Cross", "ADX_Trend", "VWAP", "Volume_Spike"], "stop_loss": 0.02, "take_profit": 0.12, "trailing_stop": 0.02, "min_agreement": 3, "description": "Breakout EMA ADX VWAP"},
    {"id": 215, "name": "Supertrend_RSI_MACD_ADX", "strategies": ["Supertrend", "RSI_Oversold", "MACD_Cross", "ADX_Trend", "EMA_Cross"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 3, "description": "Supertrend RSI MACD ADX"},
    {"id": 216, "name": "VWAP_BB_Stochastic_EMA", "strategies": ["VWAP", "BB_Lower", "Stochastic", "EMA_Cross", "ADX_Trend"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 3, "description": "VWAP BB stochastic EMA"},
    {"id": 217, "name": "ADX_EMA_VWAP_MACD", "strategies": ["ADX_Trend", "EMA_Cross", "VWAP", "MACD_Cross", "Supertrend"], "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 3, "description": "ADX EMA VWAP MACD"},
    {"id": 218, "name": "BB_Stochastic_ADX_Trend", "strategies": ["BB_Lower", "Stochastic", "ADX_Trend", "Trend_MA50", "EMA_Cross"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 3, "description": "BB stochastic ADX trend"},
    {"id": 219, "name": "Volume_Stochastic_MACD_ADX", "strategies": ["Volume_Spike", "Stochastic", "MACD_Cross", "ADX_Trend", "Trend_MA50", "Supertrend"], "stop_loss": 0.02, "take_profit": 0.12, "trailing_stop": 0.02, "min_agreement": 4, "description": "Volume stochastic MACD ADX"},
    {"id": 220, "name": "Ultimate_Entry", "strategies": ["EMA_Cross", "MACD_Cross", "RSI_Oversold", "Supertrend", "ADX_Trend", "VWAP", "Trend_MA50", "Volume_Spike"], "stop_loss": 0.025, "take_profit": 0.15, "trailing_stop": 0.025, "min_agreement": 5, "description": "Ultimate entry"}
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
📊 *Strategy #{strategy['id']}: {strategy['name']}*

🔹 *Description:* {strategy['description']}
🔹 *Strategies:* {', '.join(strategy['strategies'])}
🔹 *Stop Loss:* {strategy['stop_loss']*100}%
🔹 *Take Profit:* {strategy['take_profit']*100}%
🔹 *Trailing Stop:* {strategy['trailing_stop']*100}%
🔹 *Min Agreement:* {strategy['min_agreement']}
"""

def get_all_strategies_telegram():
    msg = "📈 *Profitable Strategy Combinations - Batch 19*\n\n"
    for s in STRATEGY_COMBINATIONS:
        msg += format_strategy_for_telegram(s)
        msg += "\n" + "="*30 + "\n\n"
    return msg

if __name__ == "__main__":
    print("PROFITABLE STRATEGIES - BATCH 19 (Strategies 211-220)")
    for s in STRATEGY_COMBINATIONS:
        print(f"#{s['id']}: {s['name']}")
    print(f"Total: {len(STRATEGY_COMBINATIONS)} strategies")
