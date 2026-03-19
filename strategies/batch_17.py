"""
Profitable Strategy Combinations - Batch 17 (Strategies 196-210)
"""

STRATEGY_COMBINATIONS = [
    {"id": 191, "name": "EMA_BB_ADX", "strategies": ["EMA_Cross", "BB_Lower", "ADX_Trend", "Supertrend"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 2, "description": "EMA BB ADX"},
    {"id": 192, "name": "RSI_Stochastic_ADX", "strategies": ["RSI_Oversold", "Stochastic", "ADX_Trend", "MACD_Cross"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 2, "description": "RSI stochastic ADX"},
    {"id": 193, "name": "MACD_Trend_Strength", "strategies": ["MACD_Cross", "Trend_MA50", "ADX_Trend", "EMA_Cross", "Volume_Spike"], "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 3, "description": "MACD trend strength"},
    {"id": 194, "name": "Breakout_Volume_ADX", "strategies": ["Breakout_20", "Volume_Spike", "ADX_Trend", "Supertrend", "VWAP"], "stop_loss": 0.02, "take_profit": 0.12, "trailing_stop": 0.02, "min_agreement": 3, "description": "Breakout volume ADX"},
    {"id": 195, "name": "Supertrend_Volume_ADX", "strategies": ["Supertrend", "Volume_Spike", "ADX_Trend", "EMA_Cross", "MACD_Cross"], "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 3, "description": "Supertrend volume ADX"},
    {"id": 196, "name": "VWAP_MACD_ADX", "strategies": ["VWAP", "MACD_Cross", "ADX_Trend", "Trend_MA50", "EMA_Cross"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 3, "description": "VWAP MACD ADX"},
    {"id": 197, "name": "ADX_BB_MACD", "strategies": ["ADX_Trend", "BB_Lower", "MACD_Cross", "Stochastic"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 2, "description": "ADX BB MACD"},
    {"id": 198, "name": "BB_VWAP_ADX", "strategies": ["BB_Lower", "VWAP", "ADX_Trend", "EMA_Cross"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 2, "description": "BB VWAP ADX"},
    {"id": 199, "name": "Stochastic_Trend_MACD", "strategies": ["Stochastic", "Trend_MA50", "MACD_Cross", "EMA_Cross", "ADX_Trend"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 3, "description": "Stochastic trend MACD"},
    {"id": 200, "name": "Volume_All_Confirm", "strategies": ["Volume_Spike", "EMA_Cross", "MACD_Cross", "ADX_Trend", "Supertrend", "VWAP"], "stop_loss": 0.02, "take_profit": 0.12, "trailing_stop": 0.02, "min_agreement": 4, "description": "Volume all confirm"}
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
    msg = "📈 *Profitable Strategy Combinations - Batch 17*\n\n"
    for s in STRATEGY_COMBINATIONS:
        msg += format_strategy_for_telegram(s)
        msg += "\n" + "="*30 + "\n\n"
    return msg

if __name__ == "__main__":
    print("PROFITABLE STRATEGIES - BATCH 17 (Strategies 191-200)")
    for s in STRATEGY_COMBINATIONS:
        print(f"#{s['id']}: {s['name']}")
    print(f"Total: {len(STRATEGY_COMBINATIONS)} strategies")
