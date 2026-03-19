"""
Profitable Strategy Combinations - Batch 3 (Strategies 31-45)
"""

STRATEGY_COMBINATIONS = [
    # Strategy 31: Triple Confirmation
    {
        "id": 31,
        "name": "Triple_Confirmation",
        "strategies": ["EMA_Cross", "MACD_Cross", "RSI_Oversold"],
        "stop_loss": 0.008,
        "take_profit": 0.06,
        "trailing_stop": 0.008,
        "min_agreement": 1,
        "description": "Three-way confirmation for entries"
    },
    # Strategy 32: Volatility Expansion
    {
        "id": 32,
        "name": "Volatility_Expansion",
        "strategies": ["BB_Lower", "Volume_Spike", "Breakout_20"],
        "stop_loss": 0.015,
        "take_profit": 0.09,
        "trailing_stop": 0.015,
        "min_agreement": 1,
        "description": "Trade volatility expansion"
    },
    # Strategy 33: Trend Line Break
    {
        "id": 33,
        "name": "Trend_Line_Break",
        "strategies": ["Breakout_20", "Supertrend", "ADX_Trend"],
        "stop_loss": 0.018,
        "take_profit": 0.10,
        "trailing_stop": 0.018,
        "min_agreement": 1,
        "description": "Breakout with trend confirmation"
    },
    # Strategy 34: EMA Convergence
    {
        "id": 34,
        "name": "EMA_Convergence",
        "strategies": ["EMA_Cross", "Trend_MA50", "VWAP"],
        "stop_loss": 0.01,
        "take_profit": 0.07,
        "trailing_stop": 0.01,
        "min_agreement": 1,
        "description": "Multiple EMAs converging"
    },
    # Strategy 35: RSI Momentum
    {
        "id": 35,
        "name": "RSI_Momentum_Burst",
        "strategies": ["RSI_Oversold", "MACD_Cross", "Volume_Spike"],
        "stop_loss": 0.012,
        "take_profit": 0.08,
        "trailing_stop": 0.012,
        "min_agreement": 1,
        "description": "RSI momentum with volume"
    },
    # Strategy 36: Golden Cross Pro
    {
        "id": 36,
        "name": "Golden_Cross_Pro",
        "strategies": ["EMA_Cross", "MACD_Cross", "ADX_Trend", "Trend_MA50"],
        "stop_loss": 0.015,
        "take_profit": 0.09,
        "trailing_stop": 0.015,
        "min_agreement": 2,
        "description": "Golden cross confirmation"
    },
    # Strategy 37: Oversold Recovery
    {
        "id": 37,
        "name": "Oversold_Recovery",
        "strategies": ["RSI_Oversold", "Stochastic", "BB_Lower", "VWAP"],
        "stop_loss": 0.008,
        "take_profit": 0.06,
        "trailing_stop": 0.008,
        "min_agreement": 2,
        "description": "Recovery from oversold conditions"
    },
    # Strategy 38: Breakout Momentum
    {
        "id": 38,
        "name": "Breakout_Momentum",
        "strategies": ["Breakout_20", "Volume_Spike", "MACD_Cross", "Supertrend"],
        "stop_loss": 0.02,
        "take_profit": 0.12,
        "trailing_stop": 0.02,
        "min_agreement": 2,
        "description": "Momentum following breakout"
    },
    # Strategy 39: ADX Volatility
    {
        "id": 39,
        "name": "ADX_Volatility_Trade",
        "strategies": ["ADX_Trend", "BB_Lower", "RSI_Oversold"],
        "stop_loss": 0.01,
        "take_profit": 0.07,
        "trailing_stop": 0.01,
        "min_agreement": 1,
        "description": "Trade with ADX strength"
    },
    # Strategy 40: Supertrend Cluster
    {
        "id": 40,
        "name": "Supertrend_Cluster_Pro",
        "strategies": ["Supertrend", "EMA_Cross", "Volume_Spike"],
        "stop_loss": 0.012,
        "take_profit": 0.08,
        "trailing_stop": 0.012,
        "min_agreement": 1,
        "description": "Multiple supertrend signals"
    },
    # Strategy 41: VWAP Break
    {
        "id": 41,
        "name": "VWAP_Break_Through",
        "strategies": ["VWAP", "Breakout_20", "Volume_Spike"],
        "stop_loss": 0.015,
        "take_profit": 0.09,
        "trailing_stop": 0.015,
        "min_agreement": 1,
        "description": "Break above VWAP with volume"
    },
    # Strategy 42: Dual Stochastic
    {
        "id": 42,
        "name": "Dual_Stochastic",
        "strategies": ["Stochastic", "RSI_Oversold", "MACD_Cross"],
        "stop_loss": 0.008,
        "take_profit": 0.06,
        "trailing_stop": 0.008,
        "min_agreement": 1,
        "description": "Double oversold indicators"
    },
    # Strategy 43: Channel Trend
    {
        "id": 43,
        "name": "Channel_Trend_Follow",
        "strategies": ["Breakout_20", "EMA_Cross", "ADX_Trend"],
        "stop_loss": 0.015,
        "take_profit": 0.09,
        "trailing_stop": 0.015,
        "min_agreement": 1,
        "description": "Follow channel trends"
    },
    # Strategy 44: MACD Zero Cross
    {
        "id": 44,
        "name": "MACD_Zero_Cross",
        "strategies": ["MACD_Cross", "EMA_Cross", "Supertrend"],
        "stop_loss": 0.01,
        "take_profit": 0.07,
        "trailing_stop": 0.01,
        "min_agreement": 1,
        "description": "MACD zero line crossover"
    },
    # Strategy 45: Support Resistance
    {
        "id": 45,
        "name": "Support_Resistance_Bounce",
        "strategies": ["BB_Lower", "VWAP", "Stochastic"],
        "stop_loss": 0.008,
        "take_profit": 0.06,
        "trailing_stop": 0.008,
        "min_agreement": 1,
        "description": "Bounce off S/R levels"
    }
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
    msg = "📈 *Profitable Strategy Combinations - Batch 3*\n\n"
    for s in STRATEGY_COMBINATIONS:
        msg += format_strategy_for_telegram(s)
        msg += "\n" + "="*30 + "\n\n"
    return msg

if __name__ == "__main__":
    print("=" * 60)
    print("PROFITABLE STRATEGIES - BATCH 3 (Strategies 31-45)")
    print("=" * 60)
    for s in STRATEGY_COMBINATIONS:
        print(f"\n#{s['id']}: {s['name']}")
        print(f"   Strategies: {', '.join(s['strategies'])}")
        print(f"   SL: {s['stop_loss']*100}%, TP: {s['take_profit']*100}%, TS: {s['trailing_stop']*100}%")
    print(f"\nTotal: {len(STRATEGY_COMBINATIONS)} strategies")
