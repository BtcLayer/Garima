"""
Profitable Strategy Combinations - Batch 12 (Strategies 141-155)
"""

STRATEGY_COMBINATIONS = [
    {"id": 141, "name": "EMA_ADX_Pro", "strategies": ["EMA_Cross", "ADX_Trend", "Volume_Spike"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 1, "description": "EMA ADX pro"},
    {"id": 142, "name": "RSI_VWAP_Trade", "strategies": ["RSI_Oversold", "VWAP", "BB_Lower"], "stop_loss": 0.008, "take_profit": 0.06, "trailing_stop": 0.008, "min_agreement": 1, "description": "RSI VWAP trade"},
    {"id": 143, "name": "MACD_BB_Strategy", "strategies": ["MACD_Cross", "BB_Lower", "Supertrend"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 1, "description": "MACD BB strategy"},
    {"id": 144, "name": "Breakout_Stochastic", "strategies": ["Breakout_20", "Stochastic", "Volume_Spike"], "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 1, "description": "Breakout stochastic"},
    {"id": 145, "name": "Supertrend_Cluster", "strategies": ["Supertrend", "EMA_Cross", "VWAP", "ADX_Trend"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 2, "description": "Supertrend cluster"},
    {"id": 146, "name": "VWAP_Breakout", "strategies": ["VWAP", "Breakout_20", "MACD_Cross", "ADX_Trend"], "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 2, "description": "VWAP breakout"},
    {"id": 147, "name": "ADX_Stochastic_Trade", "strategies": ["ADX_Trend", "Stochastic", "Trend_MA50"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 1, "description": "ADX stochastic trade"},
    {"id": 148, "name": "BB_Stochastic_Trade", "strategies": ["BB_Lower", "Stochastic", "RSI_Oversold", "VWAP"], "stop_loss": 0.008, "take_profit": 0.06, "trailing_stop": 0.008, "min_agreement": 2, "description": "BB stochastic trade"},
    {"id": 149, "name": "Volume_Trend_Pro", "strategies": ["Volume_Spike", "Trend_MA50", "EMA_Cross"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 1, "description": "Volume trend pro"},
    {"id": 150, "name": "Multi_Trend_Entry", "strategies": ["Trend_MA50", "EMA_Cross", "MACD_Cross", "ADX_Trend"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 2, "description": "Multi trend entry"}
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
    msg = "📈 *Profitable Strategy Combinations - Batch 12*\n\n"
    for s in STRATEGY_COMBINATIONS:
        msg += format_strategy_for_telegram(s)
        msg += "\n" + "="*30 + "\n\n"
    return msg

if __name__ == "__main__":
    print("PROFITABLE STRATEGIES - BATCH 12 (Strategies 141-150)")
    for s in STRATEGY_COMBINATIONS:
        print(f"#{s['id']}: {s['name']}")
    print(f"Total: {len(STRATEGY_COMBINATIONS)} strategies")
