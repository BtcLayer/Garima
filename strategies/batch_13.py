"""
Profitable Strategy Combinations - Batch 13 (Strategies 151-165)
"""

STRATEGY_COMBINATIONS = [
    {"id": 151, "name": "EMA_Pro_Entry", "strategies": ["EMA_Cross", "MACD_Cross", "RSI_Oversold", "Supertrend"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 2, "description": "EMA pro entry"},
    {"id": 152, "name": "RSI_Confirmation", "strategies": ["RSI_Oversold", "Stochastic", "BB_Lower", "VWAP"], "stop_loss": 0.008, "take_profit": 0.06, "trailing_stop": 0.008, "min_agreement": 2, "description": "RSI confirmation"},
    {"id": 153, "name": "MACD_Trend_Follow", "strategies": ["MACD_Cross", "ADX_Trend", "Trend_MA50"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 1, "description": "MACD trend follow"},
    {"id": 154, "name": "Breakout_VWAP", "strategies": ["Breakout_20", "VWAP", "Volume_Spike", "MACD_Cross"], "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 2, "description": "Breakout VWAP"},
    {"id": 155, "name": "Supertrend_ADX_Pro", "strategies": ["Supertrend", "ADX_Trend", "EMA_Cross", "Volume_Spike"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 2, "description": "Supertrend ADX pro"},
    {"id": 156, "name": "VWAP_Trend_Strength", "strategies": ["VWAP", "Trend_MA50", "ADX_Trend"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 1, "description": "VWAP trend strength"},
    {"id": 157, "name": "ADX_BB_Entry", "strategies": ["ADX_Trend", "BB_Lower", "EMA_Cross"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 1, "description": "ADX BB entry"},
    {"id": 158, "name": "BB_MACD_Trade", "strategies": ["BB_Lower", "MACD_Cross", "Stochastic"], "stop_loss": 0.01, "take_profit": 0.07, "trailing_stop": 0.01, "min_agreement": 1, "description": "BB MACD trade"},
    {"id": 159, "name": "Stochastic_Trend_ADX", "strategies": ["Stochastic", "Trend_MA50", "ADX_Trend", "EMA_Cross"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 2, "description": "Stochastic trend ADX"},
    {"id": 160, "name": "Volume_Break_Pro", "strategies": ["Volume_Spike", "Breakout_20", "Supertrend", "ADX_Trend"], "stop_loss": 0.02, "take_profit": 0.12, "trailing_stop": 0.02, "min_agreement": 2, "description": "Volume break pro"}
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
    msg = "📈 *Profitable Strategy Combinations - Batch 13*\n\n"
    for s in STRATEGY_COMBINATIONS:
        msg += format_strategy_for_telegram(s)
        msg += "\n" + "="*30 + "\n\n"
    return msg

if __name__ == "__main__":
    print("PROFITABLE STRATEGIES - BATCH 13 (Strategies 151-160)")
    for s in STRATEGY_COMBINATIONS:
        print(f"#{s['id']}: {s['name']}")
    print(f"Total: {len(STRATEGY_COMBINATIONS)} strategies")
