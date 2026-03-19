"""
Profitable Strategy Combinations - Batch 1 (Strategies 1-15)
Each file generates 15 unique strategy combinations optimized for profitability.
These strategies are designed to be displayed on Telegram bot.
"""

# Strategy combinations for Batch 1
# Format: (name, strategies_list, stop_loss, take_profit, trailing_stop, min_agreement)

STRATEGY_COMBINATIONS = [
    # Strategy 1: EMA + RSI Momentum
    {
        "id": 1,
        "name": "EMA_RSI_Momentum",
        "strategies": ["EMA_Cross", "RSI_Oversold", "Trend_MA50"],
        "stop_loss": 0.008,
        "take_profit": 0.06,
        "trailing_stop": 0.008,
        "min_agreement": 1,
        "description": "EMA crossover with RSI oversold confirmation"
    },
    # Strategy 2: MACD Supertrend Combo
    {
        "id": 2,
        "name": "MACD_Supertrend_Combo",
        "strategies": ["MACD_Cross", "Supertrend", "ADX_Trend"],
        "stop_loss": 0.01,
        "take_profit": 0.07,
        "trailing_stop": 0.01,
        "min_agreement": 1,
        "description": "MACD crossover with supertrend confirmation"
    },
    # Strategy 3: Volume Breakout
    {
        "id": 3,
        "name": "Volume_Breakout_Pro",
        "strategies": ["Volume_Spike", "Breakout_20", "VWAP"],
        "stop_loss": 0.012,
        "take_profit": 0.08,
        "trailing_stop": 0.012,
        "min_agreement": 1,
        "description": "Volume spike with 20-day breakout"
    },
    # Strategy 4: Bollinger Bounce
    {
        "id": 4,
        "name": "Bollinger_Bounce",
        "strategies": ["BB_Lower", "RSI_Oversold", "Stochastic"],
        "stop_loss": 0.005,
        "take_profit": 0.05,
        "trailing_stop": 0.005,
        "min_agreement": 1,
        "description": "Buy at lower BB with RSI/Stochastic oversold"
    },
    # Strategy 5: Trend Follower Multi
    {
        "id": 5,
        "name": "Trend_Follower_Multi",
        "strategies": ["EMA_Cross", "MACD_Cross", "ADX_Trend", "Trend_MA50"],
        "stop_loss": 0.015,
        "take_profit": 0.09,
        "trailing_stop": 0.015,
        "min_agreement": 2,
        "description": "Multi-timeframe trend following"
    },
    # Strategy 6: Breakout Hunter
    {
        "id": 6,
        "name": "Breakout_Hunter",
        "strategies": ["Breakout_20", "Volume_Spike", "MACD_Cross", "Supertrend"],
        "stop_loss": 0.018,
        "take_profit": 0.10,
        "trailing_stop": 0.018,
        "min_agreement": 2,
        "description": "Aggressive breakout strategy"
    },
    # Strategy 7: Mean Reversion
    {
        "id": 7,
        "name": "Mean_Reversion_Pro",
        "strategies": ["BB_Lower", "RSI_Oversold", "Stochastic", "VWAP"],
        "stop_loss": 0.008,
        "take_profit": 0.06,
        "trailing_stop": 0.008,
        "min_agreement": 2,
        "description": "Mean reversion at support levels"
    },
    # Strategy 8: Momentum Burst
    {
        "id": 8,
        "name": "Momentum_Burst",
        "strategies": ["EMA_Cross", "Volume_Spike", "MACD_Cross"],
        "stop_loss": 0.012,
        "take_profit": 0.08,
        "trailing_stop": 0.012,
        "min_agreement": 1,
        "description": "Momentum confirmation with volume"
    },
    # Strategy 9: Stochastic Reversal
    {
        "id": 9,
        "name": "Stochastic_Reversal",
        "strategies": ["Stochastic", "RSI_Oversold", "BB_Lower"],
        "stop_loss": 0.005,
        "take_profit": 0.05,
        "trailing_stop": 0.005,
        "min_agreement": 1,
        "description": "Double oversold confirmation"
    },
    # Strategy 10: Supertrend Cluster
    {
        "id": 10,
        "name": "Supertrend_Cluster",
        "strategies": ["Supertrend", "ADX_Trend", "Trend_MA50"],
        "stop_loss": 0.01,
        "take_profit": 0.07,
        "trailing_stop": 0.01,
        "min_agreement": 1,
        "description": "Strong trend with supertrend"
    },
    # Strategy 11: VWAP Reversal
    {
        "id": 11,
        "name": "VWAP_Reversal",
        "strategies": ["VWAP", "RSI_Oversold", "BB_Lower"],
        "stop_loss": 0.008,
        "take_profit": 0.06,
        "trailing_stop": 0.008,
        "min_agreement": 1,
        "description": "Buy at VWAP support"
    },
    # Strategy 12: EMA Cloud
    {
        "id": 12,
        "name": "EMA_Cloud_Strength",
        "strategies": ["EMA_Cross", "Trend_MA50", "ADX_Trend"],
        "stop_loss": 0.015,
        "take_profit": 0.09,
        "trailing_stop": 0.015,
        "min_agreement": 2,
        "description": "EMA alignment with trend strength"
    },
    # Strategy 13: Volume Profile
    {
        "id": 13,
        "name": "Volume_Profile_Breakout",
        "strategies": ["Volume_Spike", "Breakout_20", "ADX_Trend"],
        "stop_loss": 0.018,
        "take_profit": 0.10,
        "trailing_stop": 0.018,
        "min_agreement": 1,
        "description": "Volume-weighted breakout"
    },
    # Strategy 14: Dual Confirmation
    {
        "id": 14,
        "name": "Dual_Confirmation",
        "strategies": ["MACD_Cross", "RSI_Oversold", "Supertrend"],
        "stop_loss": 0.01,
        "take_profit": 0.07,
        "trailing_stop": 0.01,
        "min_agreement": 1,
        "description": "MACD + RSI + Supertrend"
    },
    # Strategy 15: Aggressive Growth
    {
        "id": 15,
        "name": "Aggressive_Growth",
        "strategies": ["EMA_Cross", "MACD_Cross", "Volume_Spike", "Breakout_20", "ADX_Trend", "VWAP"],
        "stop_loss": 0.02,
        "take_profit": 0.12,
        "trailing_stop": 0.02,
        "min_agreement": 3,
        "description": "Maximum agreement for high confidence"
    }
]

def get_strategies():
    """Return all strategy combinations for this batch"""
    return STRATEGY_COMBINATIONS

def get_strategy_by_id(strategy_id):
    """Get a specific strategy by ID"""
    for s in STRATEGY_COMBINATIONS:
        if s["id"] == strategy_id:
            return s
    return None

# Telegram display format
def format_strategy_for_telegram(strategy):
    """Format a strategy for Telegram display"""
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
    """Format all strategies for Telegram"""
    msg = "📈 *Profitable Strategy Combinations - Batch 1*\n\n"
    for s in STRATEGY_COMBINATIONS:
        msg += format_strategy_for_telegram(s)
        msg += "\n" + "="*30 + "\n\n"
    return msg

if __name__ == "__main__":
    print("=" * 60)
    print("PROFITABLE STRATEGIES - BATCH 1 (Strategies 1-15)")
    print("=" * 60)
    for s in STRATEGY_COMBINATIONS:
        print(f"\n#{s['id']}: {s['name']}")
        print(f"   Strategies: {', '.join(s['strategies'])}")
        print(f"   SL: {s['stop_loss']*100}%, TP: {s['take_profit']*100}%, TS: {s['trailing_stop']*100}%")
        print(f"   Description: {s['description']}")
    print("\n" + "=" * 60)
    print(f"Total: {len(STRATEGY_COMBINATIONS)} strategies")
    print("=" * 60)
