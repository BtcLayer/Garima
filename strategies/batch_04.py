"""
Profitable Strategy Combinations - Batch 4 (Strategies 46-60)
"""

STRATEGY_COMBINATIONS = [
    # Strategy 46: EMA Rainbow
    {
        "id": 46,
        "name": "EMA_Rainbow_Stack",
        "strategies": ["EMA_Cross", "Trend_MA50", "ADX_Trend", "VWAP"],
        "stop_loss": 0.012,
        "take_profit": 0.08,
        "trailing_stop": 0.012,
        "min_agreement": 2,
        "description": "Stacked EMA confirmation"
    },
    # Strategy 47: Volume Weighted
    {
        "id": 47,
        "name": "Volume_Weighted_Entry",
        "strategies": ["Volume_Spike", "VWAP", "EMA_Cross"],
        "stop_loss": 0.01,
        "take_profit": 0.07,
        "trailing_stop": 0.01,
        "min_agreement": 1,
        "description": "Volume-weighted entries"
    },
    # Strategy 48: Breakout Retest
    {
        "id": 48,
        "name": "Breakout_Retest",
        "strategies": ["Breakout_20", "RSI_Oversold", "BB_Lower"],
        "stop_loss": 0.008,
        "take_profit": 0.06,
        "trailing_stop": 0.008,
        "min_agreement": 1,
        "description": "Retest after breakout"
    },
    # Strategy 49: Stochastic Momentum
    {
        "id": 49,
        "name": "Stochastic_Momentum",
        "strategies": ["Stochastic", "MACD_Cross", "ADX_Trend"],
        "stop_loss": 0.01,
        "take_profit": 0.07,
        "trailing_stop": 0.01,
        "min_agreement": 1,
        "description": "Stochastic with momentum"
    },
    # Strategy 50: BB Squeeze Exit
    {
        "id": 50,
        "name": "BB_Squeeze_Exit",
        "strategies": ["BB_Lower", "Volume_Spike", "Supertrend"],
        "stop_loss": 0.015,
        "take_profit": 0.09,
        "trailing_stop": 0.015,
        "min_agreement": 1,
        "description": "Exit from BB squeeze"
    },
    # Strategy 51: Trend Pullback
    {
        "id": 51,
        "name": "Trend_Pullback_Entry",
        "strategies": ["EMA_Cross", "BB_Lower", "Trend_MA50"],
        "stop_loss": 0.008,
        "take_profit": 0.06,
        "trailing_stop": 0.008,
        "min_agreement": 1,
        "description": "Pullback to trend"
    },
    # Strategy 52: MACD Histogram
    {
        "id": 52,
        "name": "MACD_Histogram_Trade",
        "strategies": ["MACD_Cross", "RSI_Oversold", "VWAP"],
        "stop_loss": 0.01,
        "take_profit": 0.07,
        "trailing_stop": 0.01,
        "min_agreement": 1,
        "description": "MACD histogram signals"
    },
    # Strategy 53: ADX Breakout
    {
        "id": 53,
        "name": "ADX_Breakout_Pro",
        "strategies": ["ADX_Trend", "Breakout_20", "Volume_Spike"],
        "stop_loss": 0.018,
        "take_profit": 0.10,
        "trailing_stop": 0.018,
        "min_agreement": 1,
        "description": "ADX strength breakout"
    },
    # Strategy 54: Supertrend VWAP
    {
        "id": 54,
        "name": "Supertrend_VWAP_Combo",
        "strategies": ["Supertrend", "VWAP", "EMA_Cross"],
        "stop_loss": 0.012,
        "take_profit": 0.08,
        "trailing_stop": 0.012,
        "min_agreement": 1,
        "description": "Supertrend with VWAP"
    },
    # Strategy 55: Double Bottom
    {
        "id": 55,
        "name": "Double_Bottom_Formation",
        "strategies": ["BB_Lower", "RSI_Oversold", "Stochastic", "VWAP"],
        "stop_loss": 0.008,
        "take_profit": 0.06,
        "trailing_stop": 0.008,
        "min_agreement": 2,
        "description": "Double bottom pattern"
    },
    # Strategy 56: Triple EMA
    {
        "id": 56,
        "name": "Triple_EMA_Cross",
        "strategies": ["EMA_Cross", "MACD_Cross", "Trend_MA50"],
        "stop_loss": 0.01,
        "take_profit": 0.07,
        "trailing_stop": 0.01,
        "min_agreement": 1,
        "description": "Three EMA alignment"
    },
    # Strategy 57: Volume Spike Trend
    {
        "id": 57,
        "name": "Volume_Spike_Trend",
        "strategies": ["Volume_Spike", "EMA_Cross", "ADX_Trend"],
        "stop_loss": 0.015,
        "take_profit": 0.09,
        "trailing_stop": 0.015,
        "min_agreement": 1,
        "description": "Volume with trending"
    },
    # Strategy 58: RSI Divergence
    {
        "id": 58,
        "name": "RSI_Bullish_Divergence",
        "strategies": ["RSI_Oversold", "MACD_Cross", "BB_Lower"],
        "stop_loss": 0.008,
        "take_profit": 0.06,
        "trailing_stop": 0.008,
        "min_agreement": 1,
        "description": "RSI bullish divergence"
    },
    # Strategy 59: Breakout Cluster
    {
        "id": 59,
        "name": "Breakout_Cluster",
        "strategies": ["Breakout_20", "Volume_Spike", "EMA_Cross", "MACD_Cross"],
        "stop_loss": 0.018,
        "take_profit": 0.10,
        "trailing_stop": 0.018,
        "min_agreement": 2,
        "description": "Multiple breakout signals"
    },
    # Strategy 60: Consolidation Break
    {
        "id": 60,
        "name": "Consolidation_Break",
        "strategies": ["Breakout_20", "Supertrend", "ADX_Trend", "Volume_Spike"],
        "stop_loss": 0.02,
        "take_profit": 0.12,
        "trailing_stop": 0.02,
        "min_agreement": 2,
        "description": "Break from consolidation"
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
    msg = "📈 *Profitable Strategy Combinations - Batch 4*\n\n"
    for s in STRATEGY_COMBINATIONS:
        msg += format_strategy_for_telegram(s)
        msg += "\n" + "="*30 + "\n\n"
    return msg

if __name__ == "__main__":
    print("=" * 60)
    print("PROFITABLE STRATEGIES - BATCH 4 (Strategies 46-60)")
    print("=" * 60)
    for s in STRATEGY_COMBINATIONS:
        print(f"\n#{s['id']}: {s['name']}")
        print(f"   Strategies: {', '.join(s['strategies'])}")
        print(f"   SL: {s['stop_loss']*100}%, TP: {s['take_profit']*100}%, TS: {s['trailing_stop']*100}%")
    print(f"\nTotal: {len(STRATEGY_COMBINATIONS)} strategies")
