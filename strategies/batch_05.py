"""
Profitable Strategy Combinations - Batch 5 (Strategies 61-75)
"""

STRATEGY_COMBINATIONS = [
    # Strategy 61: EMA Cross Trend
    {
        "id": 61,
        "name": "EMA_Cross_Trend",
        "strategies": ["EMA_Cross", "ADX_Trend", "Supertrend"],
        "stop_loss": 0.012,
        "take_profit": 0.08,
        "trailing_stop": 0.012,
        "min_agreement": 1,
        "description": "EMA cross in trending market"
    },
    # Strategy 62: RSI Extreme Reversal
    {
        "id": 62,
        "name": "RSI_Extreme_Reversal",
        "strategies": ["RSI_Oversold", "Stochastic", "BB_Lower", "VWAP"],
        "stop_loss": 0.005,
        "take_profit": 0.05,
        "trailing_stop": 0.005,
        "min_agreement": 2,
        "description": "Extreme reversal setup"
    },
    # Strategy 63: MACD Signal Line
    {
        "id": 63,
        "name": "MACD_Signal_Line",
        "strategies": ["MACD_Cross", "EMA_Cross", "Trend_MA50"],
        "stop_loss": 0.01,
        "take_profit": 0.07,
        "trailing_stop": 0.01,
        "min_agreement": 1,
        "description": "MACD signal line cross"
    },
    # Strategy 64: VWAP Support
    {
        "id": 64,
        "name": "VWAP_Support_Level",
        "strategies": ["VWAP", "BB_Lower", "RSI_Oversold"],
        "stop_loss": 0.008,
        "take_profit": 0.06,
        "trailing_stop": 0.008,
        "min_agreement": 1,
        "description": "Buy at VWAP support"
    },
    # Strategy 65: Supertrend Reversal
    {
        "id": 65,
        "name": "Supertrend_Reversal_Pro",
        "strategies": ["Supertrend", "RSI_Oversold", "MACD_Cross"],
        "stop_loss": 0.01,
        "take_profit": 0.07,
        "trailing_stop": 0.01,
        "min_agreement": 1,
        "description": "Reversal at supertrend line"
    },
    # Strategy 66: Volume Surge Breakout
    {
        "id": 66,
        "name": "Volume_Surge_Breakout",
        "strategies": ["Volume_Spike", "Breakout_20", "Supertrend"],
        "stop_loss": 0.015,
        "take_profit": 0.09,
        "trailing_stop": 0.015,
        "min_agreement": 1,
        "description": "Volume surge breakout"
    },
    # Strategy 67: ADX Trend Strength
    {
        "id": 67,
        "name": "ADX_Trend_Strength",
        "strategies": ["ADX_Trend", "EMA_Cross", "MACD_Cross"],
        "stop_loss": 0.012,
        "take_profit": 0.08,
        "trailing_stop": 0.012,
        "min_agreement": 1,
        "description": "ADX trend strength entry"
    },
    # Strategy 68: Bollinger Break
    {
        "id": 68,
        "name": "Bollinger_Break_Upper",
        "strategies": ["BB_Upper", "Volume_Spike", "Breakout_20"],
        "stop_loss": 0.015,
        "take_profit": 0.09,
        "trailing_stop": 0.015,
        "min_agreement": 1,
        "description": "Break above upper BB"
    },
    # Strategy 69: Stochastic Cross
    {
        "id": 69,
        "name": "Stochastic_KD_Cross",
        "strategies": ["Stochastic", "EMA_Cross", "RSI_Oversold"],
        "stop_loss": 0.008,
        "take_profit": 0.06,
        "trailing_stop": 0.008,
        "min_agreement": 1,
        "description": "Stochastic K cross D"
    },
    # Strategy 70: EMA Momentum
    {
        "id": 70,
        "name": "EMA_Momentum_Entry",
        "strategies": ["EMA_Cross", "MACD_Cross", "Volume_Spike"],
        "stop_loss": 0.012,
        "take_profit": 0.08,
        "trailing_stop": 0.012,
        "min_agreement": 1,
        "description": "EMA momentum entry"
    },
    # Strategy 71: Trend Channel
    {
        "id": 71,
        "name": "Trend_Channel_Bounce",
        "strategies": ["BB_Lower", "Trend_MA50", "VWAP"],
        "stop_loss": 0.01,
        "take_profit": 0.07,
        "trailing_stop": 0.01,
        "min_agreement": 1,
        "description": "Bounce in trend channel"
    },
    # Strategy 72: Breakout Volume
    {
        "id": 72,
        "name": "Breakout_Volume_Confirm",
        "strategies": ["Breakout_20", "Volume_Spike", "ADX_Trend"],
        "stop_loss": 0.018,
        "take_profit": 0.10,
        "trailing_stop": 0.018,
        "min_agreement": 1,
        "description": "Breakout with volume"
    },
    # Strategy 73: Multi Signal
    {
        "id": 73,
        "name": "Multi_Signal_Entry",
        "strategies": ["EMA_Cross", "RSI_Oversold", "MACD_Cross", "Supertrend"],
        "stop_loss": 0.012,
        "take_profit": 0.08,
        "trailing_stop": 0.012,
        "min_agreement": 2,
        "description": "Multiple signal entry"
    },
    # Strategy 74: VWAP Trend Pro
    {
        "id": 74,
        "name": "VWAP_Trend_Pro",
        "strategies": ["VWAP", "EMA_Cross", "ADX_Trend", "Trend_MA50"],
        "stop_loss": 0.015,
        "take_profit": 0.09,
        "trailing_stop": 0.015,
        "min_agreement": 2,
        "description": "VWAP with strong trend"
    },
    # Strategy 75: High Momentum
    {
        "id": 75,
        "name": "High_Momentum_Entry",
        "strategies": ["EMA_Cross", "MACD_Cross", "Volume_Spike", "ADX_Trend", "Breakout_20"],
        "stop_loss": 0.02,
        "take_profit": 0.12,
        "trailing_stop": 0.02,
        "min_agreement": 3,
        "description": "High momentum entry"
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
    msg = "📈 *Profitable Strategy Combinations - Batch 5*\n\n"
    for s in STRATEGY_COMBINATIONS:
        msg += format_strategy_for_telegram(s)
        msg += "\n" + "="*30 + "\n\n"
    return msg

if __name__ == "__main__":
    print("=" * 60)
    print("PROFITABLE STRATEGIES - BATCH 5 (Strategies 61-75)")
    print("=" * 60)
    for s in STRATEGY_COMBINATIONS:
        print(f"\n#{s['id']}: {s['name']}")
        print(f"   Strategies: {', '.join(s['strategies'])}")
        print(f"   SL: {s['stop_loss']*100}%, TP: {s['take_profit']*100}%, TS: {s['trailing_stop']*100}%")
    print(f"\nTotal: {len(STRATEGY_COMBINATIONS)} strategies")
