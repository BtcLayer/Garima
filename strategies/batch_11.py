"""
Profitable Strategy Combinations - Batch 11 (Strategies 131-145)
"""

STRATEGY_COMBINATIONS = [
    {"id": 131, "name": "EMA_Cluster", "strategies": ["EMA_Cross", "Trend_MA50", "VWAP"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 1, "description": "EMA cluster"},
    {"id": 132, "name": "RSI_BB_Combo", "strategies": ["RSI_Oversold", "BB_Lower", "MACD_Cross"], "stop_loss": 0.008, "take_profit": 0.06, "trailing_stop": 0.008, "min_agreement": 1, "description": "RSI BB combo"},
    {"id": 133, "name": "MACD_Volume", "strategies": ["MACD_Cross", "Volume_Spike", "ADX_Trend"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 1, "description": "MACD volume"},
    {"id": 134, "name": "Breakout_ADX", "strategies": ["Breakout_20", "ADX_Trend", "Supertrend"], "stop_loss": 0.02, "take_profit": 0.12, "trailing_stop": 0.02, "min_agreement": 1, "description": "Breakout ADX"},
    {"id": 135, "name": "Supertrend_RSI", "strategies": ["Supertrend", "RSI_Oversold", "Trend_MA50"], "stop_loss": 0.01, "take_profit": 0.07, "trailing_stop": 0.01, "min_agreement": 1, "description": "Supertrend RSI"},
    {"id": 136, "name": "VWAP_Stochastic", "strategies": ["VWAP", "Stochastic", "EMA_Cross"], "stop_loss": 0.01, "take_profit": 0.07, "trailing_stop": 0.01, "min_agreement": 1, "description": "VWAP stochastic"},
    {"id": 137, "name": "ADX_EMA_Trade", "strategies": ["ADX_Trend", "EMA_Cross", "MACD_Cross"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 1, "description": "ADX EMA trade"},
    {"id": 138, "name": "BB_EMA_Pro", "strategies": ["BB_Lower", "EMA_Cross", "VWAP"], "stop_loss": 0.01, "take_profit": 0.07, "trailing_stop": 0.01, "min_agreement": 1, "description": "BB EMA pro"},
    {"id": 139, "name": "Stochastic_MACD", "strategies": ["Stochastic", "MACD_Cross", "Supertrend"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 1, "description": "Stochastic MACD"},
    {"id": 140, "name": "Trend_BB_Trade", "strategies": ["Trend_MA50", "BB_Lower", "ADX_Trend"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 1, "description": "Trend BB trade"}
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
    msg = "📈 *Profitable Strategy Combinations - Batch 11*\n\n"
    for s in STRATEGY_COMBINATIONS:
        msg += format_strategy_for_telegram(s)
        msg += "\n" + "="*30 + "\n\n"
    return msg

if __name__ == "__main__":
    print("PROFITABLE STRATEGIES - BATCH 11 (Strategies 131-140)")
    for s in STRATEGY_COMBINATIONS:
        print(f"#{s['id']}: {s['name']}")
    print(f"Total: {len(STRATEGY_COMBINATIONS)} strategies")
