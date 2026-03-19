"""
Profitable Strategy Combinations - Batch 9 (Strategies 111-125)
"""

STRATEGY_COMBINATIONS = [
    {"id": 111, "name": "EMA_Acceleration", "strategies": ["EMA_Cross", "MACD_Cross", "Volume_Spike"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 1, "description": "EMA acceleration"},
    {"id": 112, "name": "RSI_MACD_Combo", "strategies": ["RSI_Oversold", "MACD_Cross", "Supertrend"], "stop_loss": 0.01, "take_profit": 0.07, "trailing_stop": 0.01, "min_agreement": 1, "description": "RSI MACD combo"},
    {"id": 113, "name": "Breakout_Volume_Pro", "strategies": ["Breakout_20", "Volume_Spike", "EMA_Cross"], "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 1, "description": "Breakout volume pro"},
    {"id": 114, "name": "Supertrend_ADX", "strategies": ["Supertrend", "ADX_Trend", "Trend_MA50"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 1, "description": "Supertrend ADX"},
    {"id": 115, "name": "VWAP_EMA_Strength", "strategies": ["VWAP", "EMA_Cross", "ADX_Trend"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 1, "description": "VWAP EMA strength"},
    {"id": 116, "name": "ADX_Volume_Trade", "strategies": ["ADX_Trend", "Volume_Spike", "MACD_Cross"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 1, "description": "ADX volume trade"},
    {"id": 117, "name": "BB_Stochastic_Pro", "strategies": ["BB_Lower", "Stochastic", "MACD_Cross"], "stop_loss": 0.008, "take_profit": 0.06, "trailing_stop": 0.008, "min_agreement": 1, "description": "BB stochastic pro"},
    {"id": 118, "name": "Trend_Volume", "strategies": ["Trend_MA50", "Volume_Spike", "EMA_Cross"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 1, "description": "Trend volume"},
    {"id": 119, "name": "Breakout_Confirmation", "strategies": ["Breakout_20", "Supertrend", "MACD_Cross"], "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 1, "description": "Breakout confirmation"},
    {"id": 120, "name": "Multi_Indicator", "strategies": ["EMA_Cross", "MACD_Cross", "RSI_Oversold", "ADX_Trend"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 2, "description": "Multi indicator"}
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
    msg = "📈 *Profitable Strategy Combinations - Batch 9*\n\n"
    for s in STRATEGY_COMBINATIONS:
        msg += format_strategy_for_telegram(s)
        msg += "\n" + "="*30 + "\n\n"
    return msg

if __name__ == "__main__":
    print("PROFITABLE STRATEGIES - BATCH 9 (Strategies 111-120)")
    for s in STRATEGY_COMBINATIONS:
        print(f"#{s['id']}: {s['name']}")
    print(f"Total: {len(STRATEGY_COMBINATIONS)} strategies")
