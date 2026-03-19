"""
Profitable Strategy Combinations - Batch 2 (Strategies 16-30)
Each file generates 15 unique strategy combinations optimized for profitability.
"""

STRATEGY_COMBINATIONS = [
    # Strategy 16: RSI Extreme
    {
        "id": 16,
        "name": "RSI_Extreme_Play",
        "strategies": ["RSI_Oversold", "Stochastic", "Trend_MA50"],
        "stop_loss": 0.005,
        "take_profit": 0.05,
        "trailing_stop": 0.005,
        "min_agreement": 1,
        "description": "Extreme RSI oversold with trend confirmation"
    },
    # Strategy 17: MACD Divergence
    {
        "id": 17,
        "name": "MACD_Divergence",
        "strategies": ["MACD_Cross", "EMA_Cross", "BB_Lower"],
        "stop_loss": 0.008,
        "take_profit": 0.06,
        "trailing_stop": 0.008,
        "min_agreement": 1,
        "description": "MACD bullish divergence"
    },
    # Strategy 18: Channel Breakout
    {
        "id": 18,
        "name": "Channel_Breakout",
        "strategies": ["Breakout_20", "Volume_Spike", "Supertrend"],
        "stop_loss": 0.015,
        "take_profit": 0.09,
        "trailing_stop": 0.015,
        "min_agreement": 1,
        "description": "Price channel breakout"
    },
    # Strategy 19: Support Bounce
    {
        "id": 19,
        "name": "Support_Bounce",
        "strategies": ["BB_Lower", "VWAP", "RSI_Oversold"],
        "stop_loss": 0.008,
        "take_profit": 0.06,
        "trailing_stop": 0.008,
        "min_agreement": 1,
        "description": "Bounce from support levels"
    },
    # Strategy 20: Trend Acceleration
    {
        "id": 20,
        "name": "Trend_Acceleration",
        "strategies": ["EMA_Cross", "ADX_Trend", "Volume_Spike", "Trend_MA50"],
        "stop_loss": 0.018,
        "take_profit": 0.10,
        "trailing_stop": 0.018,
        "min_agreement": 2,
        "description": "Accelerating trend entries"
    },
    # Strategy 21: Bollinger Squeeze
    {
        "id": 21,
        "name": "Bollinger_Squeeze_Entry",
        "strategies": ["BB_Lower", "MACD_Cross", "Stochastic"],
        "stop_loss": 0.01,
        "take_profit": 0.07,
        "trailing_stop": 0.01,
        "min_agreement": 1,
        "description": "Entry after BB squeeze"
    },
    # Strategy 22: VWAP Trend
    {
        "id": 22,
        "name": "VWAP_Trend_Follow",
        "strategies": ["VWAP", "EMA_Cross", "ADX_Trend"],
        "stop_loss": 0.012,
        "take_profit": 0.08,
        "trailing_stop": 0.012,
        "min_agreement": 1,
        "description": "VWAP with trend confirmation"
    },
    # Strategy 23: Multi Timeframe
    {
        "id": 23,
        "name": "Multi_Timeframe_Entry",
        "strategies": ["EMA_Cross", "MACD_Cross", "Supertrend", "ADX_Trend"],
        "stop_loss": 0.015,
        "take_profit": 0.09,
        "trailing_stop": 0.015,
        "min_agreement": 2,
        "description": "Multi-timeframe alignment"
    },
    # Strategy 24: Volume Surge
    {
        "id": 24,
        "name": "Volume_Surge_Entry",
        "strategies": ["Volume_Spike", "EMA_Cross", "RSI_Oversold"],
        "stop_loss": 0.008,
        "take_profit": 0.06,
        "trailing_stop": 0.008,
        "min_agreement": 1,
        "description": "Volume surge entries"
    },
    # Strategy 25: Stochastic Cross
    {
        "id": 25,
        "name": "Stochastic_Cross_Pro",
        "strategies": ["Stochastic", "MACD_Cross", "Trend_MA50"],
        "stop_loss": 0.01,
        "take_profit": 0.07,
        "trailing_stop": 0.01,
        "min_agreement": 1,
        "description": "Stochastic K/D crossover"
    },
    # Strategy 26: ADX Strength
    {
        "id": 26,
        "name": "ADX_Strength_Entry",
        "strategies": ["ADX_Trend", "EMA_Cross", "Supertrend"],
        "stop_loss": 0.012,
        "take_profit": 0.08,
        "trailing_stop": 0.012,
        "min_agreement": 1,
        "description": "Strong ADX trend entries"
    },
    # Strategy 27: EMA Retracement
    {
        "id": 27,
        "name": "EMA_Retracement",
        "strategies": ["EMA_Cross", "BB_Lower", "RSI_Oversold"],
        "stop_loss": 0.008,
        "take_profit": 0.06,
        "trailing_stop": 0.008,
        "min_agreement": 1,
        "description": "Retracement to EMA support"
    },
    # Strategy 28: Breakout Pullback
    {
        "id": 28,
        "name": "Breakout_Pullback",
        "strategies": ["Breakout_20", "RSI_Oversold", "BB_Lower"],
        "stop_loss": 0.01,
        "take_profit": 0.07,
        "trailing_stop": 0.01,
        "min_agreement": 1,
        "description": "Pullback after breakout"
    },
    # Strategy 29: Supertrend Reversal
    {
        "id": 29,
        "name": "Supertrend_Reversal",
        "strategies": ["Supertrend", "RSI_Oversold", "Stochastic"],
        "stop_loss": 0.008,
        "take_profit": 0.06,
        "trailing_stop": 0.008,
        "min_agreement": 1,
        "description": "Reversal at supertrend"
    },
    # Strategy 30: Conservative Growth
    {
        "id": 30,
        "name": "Conservative_Growth",
        "strategies": ["EMA_Cross", "ADX_Trend", "Trend_MA50", "VWAP"],
        "stop_loss": 0.01,
        "take_profit": 0.07,
        "trailing_stop": 0.01,
        "min_agreement": 2,
        "description": "Conservative long-term growth"
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
    msg = "📈 *Profitable Strategy Combinations - Batch 2*\n\n"
    for s in STRATEGY_COMBINATIONS:
        msg += format_strategy_for_telegram(s)
        msg += "\n" + "="*30 + "\n\n"
    return msg

if __name__ == "__main__":
    print("=" * 60)
    print("PROFITABLE STRATEGIES - BATCH 2 (Strategies 16-30)")
    print("=" * 60)
    for s in STRATEGY_COMBINATIONS:
        print(f"\n#{s['id']}: {s['name']}")
        print(f"   Strategies: {', '.join(s['strategies'])}")
        print(f"   SL: {s['stop_loss']*100}%, TP: {s['take_profit']*100}%, TS: {s['trailing_stop']*100}%")
        print(f"   Description: {s['description']}")
    print("\n" + "=" * 60)
    print(f"Total: {len(STRATEGY_COMBINATIONS)} strategies")
    print("=" * 60)
