"""
Profitable Strategy Combinations - Batch 8 (Strategies 101-115)
Extended strategies for portfolio expansion
"""

STRATEGY_COMBINATIONS = [
    {"id": 101, "name": "EMA_Cloud_Strategy", "strategies": ["EMA_Cross", "Trend_MA50", "VWAP"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 1, "description": "EMA cloud strategy"},
    {"id": 102, "name": "RSI_Divergence_Pro", "strategies": ["RSI_Oversold", "MACD_Cross", "BB_Lower"], "stop_loss": 0.008, "take_profit": 0.06, "trailing_stop": 0.008, "min_agreement": 1, "description": "RSI divergence pro"},
    {"id": 103, "name": "MACD_Histogram_Pro", "strategies": ["MACD_Cross", "Supertrend", "Volume_Spike"], "stop_loss": 0.01, "take_profit": 0.07, "trailing_stop": 0.01, "min_agreement": 1, "description": "MACD histogram"},
    {"id": 104, "name": "Breakout_Success", "strategies": ["Breakout_20", "Volume_Spike", "ADX_Trend"], "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 1, "description": "Breakout success"},
    {"id": 105, "name": "Supertrend_Alpha", "strategies": ["Supertrend", "EMA_Cross", "ADX_Trend"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 1, "description": "Supertrend alpha"},
    {"id": 106, "name": "VWAP_Break_Pro", "strategies": ["VWAP", "Breakout_20", "MACD_Cross"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 1, "description": "VWAP break pro"},
    {"id": 107, "name": "ADX_Momentum", "strategies": ["ADX_Trend", "EMA_Cross", "RSI_Oversold"], "stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "min_agreement": 1, "description": "ADX momentum"},
    {"id": 108, "name": "BB_Stochastic_Combo", "strategies": ["BB_Lower", "Stochastic", "VWAP"], "stop_loss": 0.008, "take_profit": 0.06, "trailing_stop": 0.008, "min_agreement": 1, "description": "BB stochastic combo"},
    {"id": 109, "name": "Volume_EMA_Trade", "strategies": ["Volume_Spike", "EMA_Cross", "ADX_Trend"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 1, "description": "Volume EMA trade"},
    {"id": 110, "name": "Trend_Break_Pro", "strategies": ["Trend_MA50", "Breakout_20", "Supertrend"], "stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "min_agreement": 1, "description": "Trend break pro"}
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
    msg = "📈 *Profitable Strategy Combinations - Batch 8*\n\n"
    for s in STRATEGY_COMBINATIONS:
        msg += format_strategy_for_telegram(s)
        msg += "\n" + "="*30 + "\n\n"
    return msg

if __name__ == "__main__":
    print("PROFITABLE STRATEGIES - BATCH 8 (Strategies 101-110)")
    for s in STRATEGY_COMBINATIONS:
        print(f"#{s['id']}: {s['name']} - {', '.join(s['strategies'])}")
    print(f"Total: {len(STRATEGY_COMBINATIONS)} strategies")
