import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, Optional

# Try to import optimized parameters
try:
    from src.auto_optimizer import get_optimized_strategy_params
    _optimized_params = get_optimized_strategy_params()
except ImportError:
    _optimized_params = {}


def get_strategy_params() -> Dict[str, Any]:
    """Get current strategy parameters (optimized if available)."""
    return {
        'rsi_length': _optimized_params.get('rsi_length', 14),
        'rsi_oversold': _optimized_params.get('rsi_oversold', 30),
        'rsi_overbought': _optimized_params.get('rsi_overbought', 70),
        'smc_lookback': _optimized_params.get('smc_lookback', 10),
        'squeeze_length': _optimized_params.get('squeeze_length', 20),
    }


class StrategyManager:
    @staticmethod
    def apply_smc_lux(df, lookback: Optional[int] = None):
        """1. Smart Money Concepts [LuxAlgo] [cite: 1, 6]"""
        # Use optimized lookback if available
        if lookback is None:
            lookback = get_strategy_params().get('smc_lookback', 10)
        
        # high_signal = ta.highest(high, 10) 
        df['high_signal'] = df['high'].rolling(window=lookback).max()
        df['low_signal'] = df['low'].rolling(window=lookback).min()

        latest = df.iloc[-1]
        # bos_bullish = ta.crossover(close, high_signal[1]) 
        if latest['close'] > df['high_signal'].iloc[-2]:
            return "BUY"
        elif latest['close'] < df['low_signal'].iloc[-2]:
            return "SELL"
        return "HOLD"

    @staticmethod
    def apply_rsi_strategy(df, length: Optional[int] = None, 
                          overbought: Optional[int] = None, 
                          oversold: Optional[int] = None):
        """10. RSI Strategy [cite: 109, 113]"""
        # Use optimized parameters if available
        params = get_strategy_params()
        if length is None:
            length = params.get('rsi_length', 14)
        if overbought is None:
            overbought = params.get('rsi_overbought', 70)
        if oversold is None:
            oversold = params.get('rsi_oversold', 30)
        
        # rsival = ta.rsi(close, 14) [cite: 113]
        rsi = ta.rsi(df['close'], length=length)
        
        # if ta.crossover(rsival, 30) -> strategy.entry [cite: 114, 115]
        if rsi.iloc[-2] <= oversold and rsi.iloc[-1] > oversold:
            return "BUY"
        # if ta.crossover(rsival, 70) -> strategy.close [cite: 116, 117]
        elif rsi.iloc[-2] <= overbought and rsi.iloc[-1] > overbought:
            return "SELL"
        return "HOLD"

    @staticmethod
    def apply_squeeze_momentum(df, length: Optional[int] = None):
        """16. Squeeze Momentum [LazyBear] [cite: 180, 186]"""
        # Use optimized length if available
        if length is None:
            length = get_strategy_params().get('squeeze_length', 20)
        
        # Logic for BB and KC calculation to determine Squeeze [cite: 188-196]
        # Linear regression for momentum histogram [cite: 200]
        # Simplified momentum check based on PDF logic [cite: 203]
        val = ta.linreg(df['close'] - df['close'].rolling(length).mean(), length=length)
        
        if val.iloc[-1] > 0 and val.iloc[-1] > val.iloc[-2]:
            return "BUY" # Momentum is rising [cite: 203]
        elif val.iloc[-1] > 0 and val.iloc[-1] < val.iloc[-2]:
            return "SELL" # Momentum starts to fade [cite: 206]
        return "HOLD"