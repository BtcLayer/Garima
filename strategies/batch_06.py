"""
Profitable Strategy Combinations - Batch 6 (Strategies 76-90)
"""

STRATEGY_COMBINATIONS = [
    {"id": 76, "name": "EMA_Divergence", "strategies": ["EMA_Cross", "RSI_Oversold", "BB_Lower"], "stop_loss": 0.008, "take_profit": 0.06, "trailing_stop": 0.008, "min_agreement": 1, "description": "EMA with divergence"},
    {"id": 77, "name": "MACD_Confirmation", "strategies": ["MACD_Cross", "Supertrend", "ADX_Trend"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 1, "description": "MACD trend confirmation"},
    {"id": 78, "name": "Volume_Profile", "strategies": ["Volume_Spike", "VWAP", "Breakout_20"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 1, "description": "Volume profile breakout"},
    {"id": 79, "name": "RSI_Recovery", "strategies": ["RSI_Oversold", "Stochastic", "Trend_MA50"], "stop_loss": 0.008, "take_profit": 0.06, "trailing_stop": 0.008, "min_agreement": 1, "description": "RSI recovery signal"},
    {"id": 80, "name": "Supertrend_Momentum", "strategies": ["Supertrend", "EMA_Cross", "MACD_Cross"], "stop_loss": 0.01, "take_profit": 0.07, "trailing_stop": 0.01, "min_agreement": 1, "description": "Supertrend momentum"},
    {"id": 81, "name": "Breakout_Thermo", "strategies": ["Breakout_20", "Volume_Spike", "ADX_Trend", "Trend_MA50"], "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 2, "description": "Thermometer breakout"},
    {"id": 82, "name": "BB_Squeeze_Pro", "strategies": ["BB_Lower", "RSI_Oversold", "VWAP"], "stop_loss": 0.008, "take_profit": 0.06, "trailing_stop": 0.008, "min_agreement": 1, "description": "BB squeeze entry"},
    {"id": 83, "name": "ADX_Strength_Pro", "strategies": ["ADX_Trend", "EMA_Cross", "Volume_Spike"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 1, "description": "ADX strength play"},
    {"id": 84, "name": "VWAP_Cluster", "strategies": ["VWAP", "Supertrend", "RSI_Oversold"], "stop_loss": 0.01, "take_profit": 0.07, "trailing_stop": 0.01, "min_agreement": 1, "description": "VWAP cluster signal"},
    {"id": 85, "name": "Stochastic_Trend", "strategies": ["Stochastic", "Trend_MA50", "ADX_Trend"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 1, "description": "Stochastic with trend"},
    {"id": 86, "name": "EMA_Convergence_Pro", "strategies": ["EMA_Cross", "Trend_MA50", "VWAP", "MACD_Cross"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 2, "description": "EMA convergence"},
    {"id": 87, "name": "Breakout_Retest_Pro", "strategies": ["Breakout_20", "RSI_Oversold", "MACD_Cross"], "stop_loss": 0.01, "take_profit": 0.07, "trailing_stop": 0.01, "min_agreement": 1, "description": "Breakout retest"},
    {"id": 88, "name": "Volume_Spike_Pro", "strategies": ["Volume_Spike", "EMA_Cross", "Stochastic"], "stop_loss": 0.01, "take_profit": 0.07, "trailing_stop": 0.01, "min_agreement": 1, "description": "Volume spike entry"},
    {"id": 89, "name": "MACD_ADX_Combo", "strategies": ["MACD_Cross", "ADX_Trend", "Supertrend", "Trend_MA50"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 2, "description": "MACD ADX combo"},
    {"id": 90, "name": "Max_Agreement", "strategies": ["EMA_Cross", "MACD_Cross", "RSI_Oversold", "Supertrend", "ADX_Trend", "VWAP"], "stop_loss": 0.025, "take_profit": 0.15, "trailing_stop": 0.025, "min_agreement": 3, "description": "Maximum agreement"}
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
    msg = "📈 *Profitable Strategy Combinations - Batch 6*\n\n"
    for s in STRATEGY_COMBINATIONS:
        msg += format_strategy_for_telegram(s)
        msg += "\n" + "="*30 + "\n\n"
    return msg

if __name__ == "__main__":
    print("PROFITABLE STRATEGIES - BATCH 6 (Strategies 76-90)")
    for s in STRATEGY_COMBINATIONS:
        print(f"#{s['id']}: {s['name']} - {', '.join(s['strategies'])}")
    print(f"Total: {len(STRATEGY_COMBINATIONS)} strategies")
