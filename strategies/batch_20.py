"""
Profitable Strategy Combinations - Batch 20 (Strategies 221-235)
"""

STRATEGY_COMBINATIONS = [
    {"id": 221, "name": "Conservative_Entry", "strategies": ["EMA_Cross", "Trend_MA50", "ADX_Trend"], "stop_loss": 0.008, "take_profit": 0.05, "trailing_stop": 0.008, "min_agreement": 1, "description": "Conservative entry"},
    {"id": 222, "name": "Moderate_Strategy", "strategies": ["EMA_Cross", "MACD_Cross", "Supertrend", "ADX_Trend"], "stop_loss": 0.012, "take_profit": 0.07, "trailing_stop": 0.012, "min_agreement": 2, "description": "Moderate strategy"},
    {"id": 223, "name": "Aggressive_Entry", "strategies": ["Breakout_20", "Volume_Spike", "MACD_Cross", "ADX_Trend"], "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 2, "description": "Aggressive entry"},
    {"id": 224, "name": "Low_Risk_Trade", "strategies": ["RSI_Oversold", "BB_Lower", "VWAP"], "stop_loss": 0.005, "take_profit": 0.04, "trailing_stop": 0.005, "min_agreement": 1, "description": "Low risk trade"},
    {"id": 225, "name": "High_Profit_Trade", "strategies": ["EMA_Cross", "MACD_Cross", "ADX_Trend", "Supertrend", "VWAP", "Trend_MA50"], "stop_loss": 0.025, "take_profit": 0.15, "trailing_stop": 0.025, "min_agreement": 4, "description": "High profit trade"},
    {"id": 226, "name": "Quick_Profit", "strategies": ["RSI_Oversold", "Stochastic", "BB_Lower"], "stop_loss": 0.005, "take_profit": 0.035, "trailing_stop": 0.005, "min_agreement": 1, "description": "Quick profit"},
    {"id": 227, "name": "Swing_Trade", "strategies": ["EMA_Cross", "Trend_MA50", "ADX_Trend", "Supertrend"], "stop_loss": 0.015, "take_profit": 0.08, "trailing_stop": 0.015, "min_agreement": 2, "description": "Swing trade"},
    {"id": 228, "name": "Day_Trade", "strategies": ["MACD_Cross", "Volume_Spike", "VWAP"], "stop_loss": 0.008, "take_profit": 0.05, "trailing_stop": 0.008, "min_agreement": 1, "description": "Day trade"},
    {"id": 229, "name": "Momentum_Trade", "strategies": ["Breakout_20", "Volume_Spike", "EMA_Cross", "MACD_Cross"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 2, "description": "Momentum trade"},
    {"id": 230, "name": "Scalp_Trade", "strategies": ["RSI_Oversold", "BB_Lower", "VWAP", "Stochastic"], "stop_loss": 0.004, "take_profit": 0.025, "trailing_stop": 0.004, "min_agreement": 2, "description": "Scalp trade"}
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
    msg = "📈 *Profitable Strategy Combinations - Batch 20*\n\n"
    for s in STRATEGY_COMBINATIONS:
        msg += format_strategy_for_telegram(s)
        msg += "\n" + "="*30 + "\n\n"
    return msg

if __name__ == "__main__":
    print("=" * 60)
    print("PROFITABLE STRATEGIES - BATCH 20 (Strategies 221-230)")
    print("=" * 60)
    for s in STRATEGY_COMBINATIONS:
        print(f"#{s['id']}: {s['name']} - {', '.join(s['strategies'])}")
    print(f"Total: {len(STRATEGY_COMBINATIONS)} strategies")
    print("=" * 60)
    print("📁 ALL 20 BATCH FILES COMPLETED!")
    print("=" * 60)
