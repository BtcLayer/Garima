"""
Profitable Strategy Combinations - Batch 10 (Strategies 121-135)
"""

STRATEGY_COMBINATIONS = [
    {"id": 121, "name": "EMA_Breakout_Pro", "strategies": ["EMA_Cross", "Breakout_20", "Volume_Spike"], "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 1, "description": "EMA breakout pro"},
    {"id": 122, "name": "RSI_Trend_Trade", "strategies": ["RSI_Oversold", "Trend_MA50", "ADX_Trend"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 1, "description": "RSI trend trade"},
    {"id": 123, "name": "MACD_Supertrend", "strategies": ["MACD_Cross", "Supertrend", "VWAP"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 1, "description": "MACD supertrend"},
    {"id": 124, "name": "Breakout_Momentum", "strategies": ["Breakout_20", "Volume_Spike", "MACD_Cross"], "stop_loss": 0.02, "take_profit": 0.12, "trailing_stop": 0.02, "min_agreement": 1, "description": "Breakout momentum"},
    {"id": 125, "name": "Supertrend_Volume", "strategies": ["Supertrend", "Volume_Spike", "EMA_Cross"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 1, "description": "Supertrend volume"},
    {"id": 126, "name": "VWAP_ADX_Trade", "strategies": ["VWAP", "ADX_Trend", "MACD_Cross"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 1, "description": "VWAP ADX trade"},
    {"id": 127, "name": "ADX_BB_Combo", "strategies": ["ADX_Trend", "BB_Lower", "RSI_Oversold"], "stop_loss": 0.01, "take_profit": 0.07, "trailing_stop": 0.01, "min_agreement": 1, "description": "ADX BB combo"},
    {"id": 128, "name": "BB_VWAP_Strategy", "strategies": ["BB_Lower", "VWAP", "EMA_Cross"], "stop_loss": 0.01, "take_profit": 0.07, "trailing_stop": 0.01, "min_agreement": 1, "description": "BB VWAP strategy"},
    {"id": 129, "name": "Stochastic_ADX", "strategies": ["Stochastic", "ADX_Trend", "Supertrend"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 1, "description": "Stochastic ADX"},
    {"id": 130, "name": "Trend_Stochastic", "strategies": ["Trend_MA50", "Stochastic", "EMA_Cross"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 1, "description": "Trend stochastic"}
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
    msg = "📈 *Profitable Strategy Combinations - Batch 10*\n\n"
    for s in STRATEGY_COMBINATIONS:
        msg += format_strategy_for_telegram(s)
        msg += "\n" + "="*30 + "\n\n"
    return msg

if __name__ == "__main__":
    print("PROFITABLE STRATEGIES - BATCH 10 (Strategies 121-130)")
    for s in STRATEGY_COMBINATIONS:
        print(f"#{s['id']}: {s['name']}")
    print(f"Total: {len(STRATEGY_COMBINATIONS)} strategies")
