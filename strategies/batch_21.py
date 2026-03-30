"""
Profitable Strategy Combinations - Batch 21 (Strategies 231-242)
New indicator combinations: Ichimoku, PSAR, OBV, CCI, MFI, Keltner, Williams %R
Optimised for 4h timeframe.
"""

STRATEGY_COMBINATIONS = [
    {"id": 231, "name": "Ichimoku_Trend_Pro", "strategies": ["Ichimoku_Bull", "EMA_Cross", "ADX_Trend", "OBV_Rising"], "stop_loss": 0.02, "take_profit": 0.12, "trailing_stop": 0.02, "min_agreement": 3, "description": "Ichimoku cloud + EMA + ADX trend confirmation with OBV volume"},
    {"id": 232, "name": "PSAR_Momentum", "strategies": ["PSAR_Bull", "MACD_Cross", "Volume_Spike", "ADX_Trend"], "stop_loss": 0.02, "take_profit": 0.12, "trailing_stop": 0.02, "min_agreement": 2, "description": "Parabolic SAR momentum with MACD and volume"},
    {"id": 233, "name": "Keltner_Breakout", "strategies": ["Keltner_Lower", "RSI_Oversold", "Volume_Spike", "OBV_Rising"], "stop_loss": 0.015, "take_profit": 0.10, "trailing_stop": 0.015, "min_agreement": 2, "description": "Keltner channel bounce with RSI and volume confirmation"},
    {"id": 234, "name": "MFI_Volume_Entry", "strategies": ["MFI_Oversold", "Volume_Spike", "EMA_Cross", "Supertrend"], "stop_loss": 0.02, "take_profit": 0.12, "trailing_stop": 0.02, "min_agreement": 2, "description": "Money flow reversal with volume and trend"},
    {"id": 235, "name": "CCI_Reversal", "strategies": ["CCI_Oversold", "Stochastic", "BB_Lower", "Volume_Spike"], "stop_loss": 0.015, "take_profit": 0.10, "trailing_stop": 0.015, "min_agreement": 2, "description": "CCI oversold bounce with stochastic and BB confirmation"},
    {"id": 236, "name": "Williams_Bounce", "strategies": ["Williams_Oversold", "RSI_Oversold", "BB_Lower", "OBV_Rising"], "stop_loss": 0.015, "take_profit": 0.10, "trailing_stop": 0.015, "min_agreement": 2, "description": "Williams %R oversold with RSI and BB support"},
    {"id": 237, "name": "Ichimoku_MACD_Pro", "strategies": ["Ichimoku_Bull", "MACD_Cross", "OBV_Rising", "Volume_Spike"], "stop_loss": 0.02, "take_profit": 0.15, "trailing_stop": 0.02, "min_agreement": 2, "description": "Ichimoku cloud with MACD crossover and volume"},
    {"id": 238, "name": "PSAR_EMA_Breakout", "strategies": ["PSAR_Bull", "EMA_Cross", "Breakout_20", "ADX_Trend"], "stop_loss": 0.02, "take_profit": 0.15, "trailing_stop": 0.02, "min_agreement": 2, "description": "PSAR uptrend with EMA cross and breakout"},
    {"id": 239, "name": "Full_Momentum", "strategies": ["PSAR_Bull", "Ichimoku_Bull", "MACD_Cross", "ADX_Trend", "OBV_Rising"], "stop_loss": 0.025, "take_profit": 0.15, "trailing_stop": 0.025, "min_agreement": 3, "description": "Full momentum stack: PSAR + Ichimoku + MACD + ADX + OBV"},
    {"id": 240, "name": "Keltner_VWAP_Cross", "strategies": ["Keltner_Lower", "VWAP", "EMA_Cross", "Volume_Spike"], "stop_loss": 0.015, "take_profit": 0.10, "trailing_stop": 0.015, "min_agreement": 2, "description": "Keltner lower with VWAP and EMA cross"},
    {"id": 241, "name": "MFI_Stochastic_BB", "strategies": ["MFI_Oversold", "Stochastic", "BB_Lower", "MACD_Cross"], "stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "min_agreement": 2, "description": "MFI + stochastic + BB oversold with MACD confirmation"},
    {"id": 242, "name": "CCI_ADX_Trend", "strategies": ["CCI_Oversold", "ADX_Trend", "EMA_Cross", "Supertrend"], "stop_loss": 0.02, "take_profit": 0.12, "trailing_stop": 0.02, "min_agreement": 2, "description": "CCI bounce with ADX trend and EMA + Supertrend"},
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
Strategy #{strategy['id']}: {strategy['name']}

Description: {strategy['description']}
Strategies: {', '.join(strategy['strategies'])}
Stop Loss: {strategy['stop_loss']*100}%
Take Profit: {strategy['take_profit']*100}%
Trailing Stop: {strategy['trailing_stop']*100}%
Min Agreement: {strategy['min_agreement']}
"""

def get_all_strategies_telegram():
    msg = "Profitable Strategy Combinations - Batch 21\n\n"
    for s in STRATEGY_COMBINATIONS:
        msg += format_strategy_for_telegram(s)
        msg += "\n" + "="*30 + "\n\n"
    return msg

if __name__ == "__main__":
    print("=" * 60)
    print("PROFITABLE STRATEGIES - BATCH 21 (Strategies 231-242)")
    print("=" * 60)
    for s in STRATEGY_COMBINATIONS:
        print(f"#{s['id']}: {s['name']} - {', '.join(s['strategies'])}")
    print(f"Total: {len(STRATEGY_COMBINATIONS)} strategies")
    print("=" * 60)
