"""
Profitable Strategy Combinations - Batch 14 (Strategies 161-175)
"""

STRATEGY_COMBINATIONS = [
    {"id": 161, "name": "EMA_Break_Momentum", "strategies": ["EMA_Cross", "Breakout_20", "MACD_Cross", "ADX_Trend"], "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 2, "description": "EMA break momentum"},
    {"id": 162, "name": "RSI_Stochastic_Pro", "strategies": ["RSI_Oversold", "Stochastic", "BB_Lower", "MACD_Cross"], "stop_loss": 0.008, "take_profit": 0.06, "trailing_stop": 0.008, "min_agreement": 2, "description": "RSI stochastic pro"},
    {"id": 163, "name": "MACD_Supertrend_ADX", "strategies": ["MACD_Cross", "Supertrend", "ADX_Trend", "Trend_MA50"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 2, "description": "MACD supertrend ADX"},
    {"id": 164, "name": "Breakout_Confirmation", "strategies": ["Breakout_20", "Volume_Spike", "EMA_Cross", "Supertrend"], "stop_loss": 0.02, "take_profit": 0.12, "trailing_stop": 0.02, "min_agreement": 2, "description": "Breakout confirmation"},
    {"id": 165, "name": "Supertrend_Multi_Entry", "strategies": ["Supertrend", "EMA_Cross", "VWAP", "ADX_Trend", "Volume_Spike"], "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 3, "description": "Supertrend multi entry"},
    {"id": 166, "name": "VWAP_ADX_Strength", "strategies": ["VWAP", "ADX_Trend", "EMA_Cross", "MACD_Cross"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 2, "description": "VWAP ADX strength"},
    {"id": 167, "name": "ADX_Volume_Break", "strategies": ["ADX_Trend", "Volume_Spike", "Breakout_20", "EMA_Cross"], "stop_loss": 0.02, "take_profit": 0.12, "trailing_stop": 0.02, "min_agreement": 2, "description": "ADX volume break"},
    {"id": 168, "name": "BB_Stochastic_ADX", "strategies": ["BB_Lower", "Stochastic", "ADX_Trend", "VWAP"], "stop_loss": 0.01, "take_profit": 0.07, "trailing_stop": 0.01, "min_agreement": 2, "description": "BB stochastic ADX"},
    {"id": 169, "name": "Volume_EMA_ADX", "strategies": ["Volume_Spike", "EMA_Cross", "ADX_Trend", "Trend_MA50"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 2, "description": "Volume EMA ADX"},
    {"id": 170, "name": "Trend_Strength_Entry", "strategies": ["Trend_MA50", "EMA_Cross", "ADX_Trend", "Supertrend"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 2, "description": "Trend strength entry"}
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
    msg = "📈 *Profitable Strategy Combinations - Batch 14*\n\n"
    for s in STRATEGY_COMBINATIONS:
        msg += format_strategy_for_telegram(s)
        msg += "\n" + "="*30 + "\n\n"
    return msg

if __name__ == "__main__":
    print("PROFITABLE STRATEGIES - BATCH 14 (Strategies 161-170)")
    for s in STRATEGY_COMBINATIONS:
        print(f"#{s['id']}: {s['name']}")
    print(f"Total: {len(STRATEGY_COMBINATIONS)} strategies")
