"""
Profitable Strategy Combinations - Batch 18 (Strategies 211-225)
"""

STRATEGY_COMBINATIONS = [
    {"id": 201, "name": "EMA_RSI_MACD_ADX", "strategies": ["EMA_Cross", "RSI_Oversold", "MACD_Cross", "ADX_Trend"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 2, "description": "EMA RSI MACD ADX"},
    {"id": 202, "name": "RSI_BB_MACD_Stochastic", "strategies": ["RSI_Oversold", "BB_Lower", "MACD_Cross", "Stochastic"], "stop_loss": 0.01, "take_profit": 0.07, "trailing_stop": 0.01, "min_agreement": 2, "description": "RSI BB MACD stochastic"},
    {"id": 203, "name": "MACD_VWAP_Breakout", "strategies": ["MACD_Cross", "VWAP", "Breakout_20", "Volume_Spike"], "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 2, "description": "MACD VWAP breakout"},
    {"id": 204, "name": "Breakout_Stochastic_ADX", "strategies": ["Breakout_20", "Stochastic", "ADX_Trend", "Supertrend", "EMA_Cross"], "stop_loss": 0.02, "take_profit": 0.12, "trailing_stop": 0.02, "min_agreement": 3, "description": "Breakout stochastic ADX"},
    {"id": 205, "name": "Supertrend_BB_Entry", "strategies": ["Supertrend", "BB_Lower", "EMA_Cross", "MACD_Cross", "RSI_Oversold"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 3, "description": "Supertrend BB entry"},
    {"id": 206, "name": "VWAP_Trend_Entry", "strategies": ["VWAP", "Trend_MA50", "EMA_Cross", "ADX_Trend", "MACD_Cross"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 3, "description": "VWAP trend entry"},
    {"id": 207, "name": "ADX_Stochastic_VWAP", "strategies": ["ADX_Trend", "Stochastic", "VWAP", "BB_Lower", "Volume_Spike"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 3, "description": "ADX stochastic VWAP"},
    {"id": 208, "name": "BB_Stochastic_MACD_ADX", "strategies": ["BB_Lower", "Stochastic", "MACD_Cross", "ADX_Trend", "Supertrend"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 3, "description": "BB stochastic MACD ADX"},
    {"id": 209, "name": "Volume_EMA_Stochastic_ADX", "strategies": ["Volume_Spike", "EMA_Cross", "Stochastic", "ADX_Trend", "Trend_MA50"], "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 3, "description": "Volume EMA stochastic ADX"},
    {"id": 210, "name": "Mega_Confirmation", "strategies": ["EMA_Cross", "MACD_Cross", "RSI_Oversold", "Supertrend", "ADX_Trend", "VWAP", "Trend_MA50"], "stop_loss": 0.025, "take_profit": 0.15, "trailing_stop": 0.025, "min_agreement": 4, "description": "Mega confirmation"}
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
    msg = "📈 *Profitable Strategy Combinations - Batch 18*\n\n"
    for s in STRATEGY_COMBINATIONS:
        msg += format_strategy_for_telegram(s)
        msg += "\n" + "="*30 + "\n\n"
    return msg

if __name__ == "__main__":
    print("PROFITABLE STRATEGIES - BATCH 18 (Strategies 201-210)")
    for s in STRATEGY_COMBINATIONS:
        print(f"#{s['id']}: {s['name']}")
    print(f"Total: {len(STRATEGY_COMBINATIONS)} strategies")
