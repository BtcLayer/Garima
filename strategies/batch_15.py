"""
Profitable Strategy Combinations - Batch 15 (Strategies 171-185)
"""

STRATEGY_COMBINATIONS = [
    {"id": 171, "name": "EMA_MACD_Stochastic", "strategies": ["EMA_Cross", "MACD_Cross", "Stochastic", "ADX_Trend"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 2, "description": "EMA MACD stochastic"},
    {"id": 172, "name": "RSI_BB_VWAP", "strategies": ["RSI_Oversold", "BB_Lower", "VWAP", "Supertrend"], "stop_loss": 0.01, "take_profit": 0.07, "trailing_stop": 0.01, "min_agreement": 2, "description": "RSI BB VWAP"},
    {"id": 173, "name": "MACD_Breakout", "strategies": ["MACD_Cross", "Breakout_20", "Volume_Spike", "ADX_Trend"], "stop_loss": 0.02, "take_profit": 0.12, "trailing_stop": 0.02, "min_agreement": 2, "description": "MACD breakout"},
    {"id": 174, "name": "Breakout_Multi_Signal", "strategies": ["Breakout_20", "Volume_Spike", "EMA_Cross", "MACD_Cross", "Supertrend"], "stop_loss": 0.02, "take_profit": 0.12, "trailing_stop": 0.02, "min_agreement": 3, "description": "Breakout multi signal"},
    {"id": 175, "name": "Supertrend_Confirm", "strategies": ["Supertrend", "EMA_Cross", "ADX_Trend", "RSI_Oversold", "MACD_Cross"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 3, "description": "Supertrend confirm"},
    {"id": 176, "name": "VWAP_Momentum_Pro", "strategies": ["VWAP", "EMA_Cross", "MACD_Cross", "Volume_Spike"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 2, "description": "VWAP momentum pro"},
    {"id": 177, "name": "ADX_Stochastic_BB", "strategies": ["ADX_Trend", "Stochastic", "BB_Lower", "RSI_Oversold"], "stop_loss": 0.01, "take_profit": 0.07, "trailing_stop": 0.01, "min_agreement": 2, "description": "ADX stochastic BB"},
    {"id": 178, "name": "BB_EMA_VWAP", "strategies": ["BB_Lower", "EMA_Cross", "VWAP", "Trend_MA50"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 2, "description": "BB EMA VWAP"},
    {"id": 179, "name": "Stochastic_Pro_Trade", "strategies": ["Stochastic", "EMA_Cross", "MACD_Cross", "Supertrend", "ADX_Trend"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 3, "description": "Stochastic pro trade"},
    {"id": 180, "name": "Volume_Trend_ADX", "strategies": ["Volume_Spike", "Trend_MA50", "ADX_Trend", "EMA_Cross", "MACD_Cross"], "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 3, "description": "Volume trend ADX"}
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
    msg = "📈 *Profitable Strategy Combinations - Batch 15*\n\n"
    for s in STRATEGY_COMBINATIONS:
        msg += format_strategy_for_telegram(s)
        msg += "\n" + "="*30 + "\n\n"
    return msg

if __name__ == "__main__":
    print("PROFITABLE STRATEGIES - BATCH 15 (Strategies 171-180)")
    for s in STRATEGY_COMBINATIONS:
        print(f"#{s['id']}: {s['name']}")
    print(f"Total: {len(STRATEGY_COMBINATIONS)} strategies")
