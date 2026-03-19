"""
Profitable Strategy Combinations - Batch 16 (Strategies 181-195)
"""

STRATEGY_COMBINATIONS = [
    {"id": 181, "name": "EMA_BB_Stochastic", "strategies": ["EMA_Cross", "BB_Lower", "Stochastic", "VWAP"], "stop_loss": 0.01, "take_profit": 0.07, "trailing_stop": 0.01, "min_agreement": 2, "description": "EMA BB stochastic"},
    {"id": 182, "name": "RSI_Trend_ADX", "strategies": ["RSI_Oversold", "Trend_MA50", "ADX_Trend", "EMA_Cross"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 2, "description": "RSI trend ADX"},
    {"id": 183, "name": "MACD_VWAP_Supertrend", "strategies": ["MACD_Cross", "VWAP", "Supertrend", "Volume_Spike"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 2, "description": "MACD VWAP supertrend"},
    {"id": 184, "name": "Breakout_ADX_Pro", "strategies": ["Breakout_20", "ADX_Trend", "Volume_Spike", "EMA_Cross", "MACD_Cross"], "stop_loss": 0.02, "take_profit": 0.12, "trailing_stop": 0.02, "min_agreement": 3, "description": "Breakout ADX pro"},
    {"id": 185, "name": "Supertrend_Multi_Pro", "strategies": ["Supertrend", "EMA_Cross", "MACD_Cross", "ADX_Trend", "Trend_MA50"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 3, "description": "Supertrend multi pro"},
    {"id": 186, "name": "VWAP_Break_Entry", "strategies": ["VWAP", "Breakout_20", "ADX_Trend", "RSI_Oversold"], "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 2, "description": "VWAP break entry"},
    {"id": 187, "name": "ADX_EMA_BB", "strategies": ["ADX_Trend", "EMA_Cross", "BB_Lower", "Stochastic"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 2, "description": "ADX EMA BB"},
    {"id": 188, "name": "BB_Stochastic_VWAP", "strategies": ["BB_Lower", "Stochastic", "VWAP", "EMA_Cross"], "stop_loss": 0.01, "take_profit": 0.07, "trailing_stop": 0.01, "min_agreement": 2, "description": "BB stochastic VWAP"},
    {"id": 189, "name": "Volume_MACD_ADX", "strategies": ["Volume_Spike", "MACD_Cross", "ADX_Trend", "Trend_MA50", "Supertrend"], "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 3, "description": "Volume MACD ADX"},
    {"id": 190, "name": "Trend_All_Confirm", "strategies": ["Trend_MA50", "EMA_Cross", "ADX_Trend", "Supertrend", "MACD_Cross"], "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 3, "description": "Trend all confirm"}
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
    msg = "📈 *Profitable Strategy Combinations - Batch 16*\n\n"
    for s in STRATEGY_COMBINATIONS:
        msg += format_strategy_for_telegram(s)
        msg += "\n" + "="*30 + "\n\n"
    return msg

if __name__ == "__main__":
    print("PROFITABLE STRATEGIES - BATCH 16 (Strategies 181-190)")
    for s in STRATEGY_COMBINATIONS:
        print(f"#{s['id']}: {s['name']}")
    print(f"Total: {len(STRATEGY_COMBINATIONS)} strategies")
