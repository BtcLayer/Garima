"""
Pine Script Generator

Generates TradingView Pine Script v5 from strategy parameters.
"""

from typing import Dict, Any, Optional


class PineGenerator:
    """Generates Pine Script v5 code from strategy parameters."""
    
    def __init__(self):
        self.default_params = {
            'rsi_length': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'ema_fast': 9,
            'ema_slow': 21,
            'ema200': 200,
            'atr_length': 14,
            'atr_multiplier': 2.0,
            'risk_reward_ratio': 2.0,
        }
    
    def generate_header(self, strategy_name: str, symbol: str, timeframe: str) -> str:
        """Generate Pine Script header."""
        return f"""//@version=5
strategy("{strategy_name}", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=10)

// Input parameters
symbol = "{symbol}"
timeframe = "{timeframe}"
"""
    
    def generate_rsi_strategy(
        self,
        symbol: str = "BTCUSDT",
        timeframe: str = "15m",
        rsi_length: int = 14,
        oversold: int = 30,
        overbought: int = 70,
        use_ema_filter: bool = True,
        ema_period: int = 200
    ) -> str:
        """Generate RSI strategy Pine Script."""
        
        header = self.generate_header(f"RSI Strategy {symbol}", symbol, timeframe)
        
        # Main strategy
        script = f"""{header}
// RSI Indicator
rsiLength = input.int({rsi_length}, minval=1, title="RSI Length")
rsiOversold = input.int({oversold}, title="RSI Oversold")
rsiOverbought = input.int({overbought}, title="RSI Overbought")

rsi = ta.rsi(close, rsiLength)

// Plot RSI
plot(rsi, title="RSI", color=color.purple)
hline(rsiOversold, "Oversold", color=color.green)
hline(rsiOverbought, "Overbought", color=color.red)

// EMA Trend Filter
useTrendFilter = input.bool({str(use_ema_filter).lower()}, title="Use EMA Trend Filter")
ema200 = ta.ema(close, {ema_period})
plot(ema200, "EMA 200", color=color.orange)
bullishTrend = close > ema200
bearishTrend = close < ema200

// Signals
longCondition = ta.crossover(rsi, rsiOversold)
shortCondition = ta.crossunder(rsi, rsiOverbought)

// Apply trend filter
if useTrendFilter
    longCondition := longCondition and bullishTrend
    shortCondition := shortCondition and bearishTrend

// Entry and Exit
if (longCondition)
    strategy.entry("Long", strategy.long)

if (shortCondition)
    strategy.entry("Short", strategy.short)

// Exit on opposite signal
if (ta.crossunder(rsi, rsiOverbought))
    strategy.close("Long")

if (ta.crossover(rsi, rsiOversold))
    strategy.close("Short")

// Stop Loss and Take Profit
useStopLoss = input.bool(true, title="Use Stop Loss")
stopLossPercent = input.float(1.0, title="Stop Loss %") / 100
takeProfitPercent = input.float(2.0, title="Take Profit %") / 100

if (useStopLoss)
    strategy.exit("SL/TP", "Long", stop=strategy.position_avg_price * (1 - stopLossPercent), limit=strategy.position_avg_price * (1 + takeProfitPercent))
    strategy.exit("SL/TP", "Short", stop=strategy.position_avg_price * (1 + stopLossPercent), limit=strategy.position_avg_price * (1 - takeProfitPercent))

// Plot shapes
plotshape(longCondition, title="Buy Signal", location=location.belowbar, color=color.green, style=shape.triangleup, size=size.tiny, text="BUY")
plotshape(shortCondition, title="Sell Signal", location=location.abovebar, color=color.red, style=shape.triangledown, size=size.tiny, text="SELL")

// Alerts
alertcondition(longCondition, title="RSI Buy", message="RSI Buy Signal on {symbol}")
alertcondition(shortCondition, title="RSI Sell", message="RSI Sell Signal on {symbol}")
"""
        return script
    
    def generate_ema_crossover_strategy(
        self,
        symbol: str = "BTCUSDT",
        timeframe: str = "1h",
        fast_ema: int = 9,
        slow_ema: int = 21
    ) -> str:
        """Generate EMA Crossover strategy Pine Script."""
        
        header = self.generate_header(f"EMA Crossover {symbol}", symbol, timeframe)
        
        script = f"""{header}
// EMA Crossover Strategy

fastLength = input.int({fast_ema}, title="Fast EMA")
slowLength = input.int({slow_ema}, title="Slow EMA")

emaFast = ta.ema(close, fastLength)
emaSlow = ta.ema(close, slowLength)

// Plot EMAs
plot(emaFast, title="Fast EMA", color=color.blue)
plot(emaSlow, title="Slow EMA", color=color.red)

// Signals
longCondition = ta.crossover(emaFast, emaSlow)
shortCondition = ta.crossunder(emaFast, emaSlow)

// Entry
if (longCondition)
    strategy.entry("Long", strategy.long)

if (shortCondition)
    strategy.entry("Short", strategy.short)

// Exit on reverse crossover
if (ta.crossunder(emaFast, emaSlow))
    strategy.close("Long")

if (ta.crossover(emaFast, emaSlow))
    strategy.close("Short")

// Stop Loss
useStopLoss = input.bool(true, title="Use Stop Loss")
stopLossPercent = input.float(2.0, title="Stop Loss %") / 100

if (useStopLoss)
    strategy.exit("SL", "Long", stop=strategy.position_avg_price * (1 - stopLossPercent))
    strategy.exit("SL", "Short", stop=strategy.position_avg_price * (1 + stopLossPercent))

// Plots
plotshape(longCondition, title="Buy", location=location.belowbar, color=color.green, style=shape.triangleup)
plotshape(shortCondition, title="Sell", location=location.abovebar, color=color.red, style=shape.triangledown)

alertcondition(longCondition, title="EMA Buy", message="EMA Crossover Buy on {{ticker}}")
alertcondition(shortCondition, title="EMA Sell", message="EMA Crossover Sell on {{ticker}}")
"""
        return script
    
    def generate_macd_strategy(
        self,
        symbol: str = "BTCUSDT",
        timeframe: str = "4h",
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> str:
        """Generate MACD strategy Pine Script."""
        
        header = self.generate_header(f"MACD Strategy {symbol}", symbol, timeframe)
        
        script = f"""{header}
// MACD Strategy

fastLength = input.int({fast})
slowLength = input.int({slow})
signalLength = input.int({signal})

[macdLine, signalLine, histLine] = ta.macd(close, fastLength, slowLength, signalLength)

// Plot MACD
plot(macdLine, title="MACD", color=color.blue)
plot(signalLine, title="Signal", color=color.orange)
plot(histLine, title="Histogram", color=color.purple, style=plot.style_histogram)
hline(0, "Zero Line", color=color.gray)

// Signals
longCondition = ta.crossover(macdLine, signalLine)
shortCondition = ta.crossunder(macdLine, signalLine)

// Entry
if (longCondition)
    strategy.entry("Long", strategy.long)

if (shortCondition)
    strategy.entry("Short", strategy.short)

// Exit
if (ta.crossunder(macdLine, signalLine))
    strategy.close("Long")

if (ta.crossover(macdLine, signalLine))
    strategy.close("Short")

// Stop Loss
stopLossPercent = input.float(2.0, title="Stop Loss %") / 100

if (strategy.position_size > 0)
    strategy.exit("SL", "Long", stop=strategy.position_avg_price * (1 - stopLossPercent))

if (strategy.position_size < 0)
    strategy.exit("SL", "Short", stop=strategy.position_avg_price * (1 + stopLossPercent))

plotshape(longCondition, title="Buy", location=location.belowbar, color=color.green, style=shape.triangleup)
plotshape(shortCondition, title="Sell", location=location.abovebar, color=color.red, style=shape.triangledown)

alertcondition(longCondition, title="MACD Buy", message="MACD Buy on {{ticker}}")
alertcondition(shortCondition, title="MACD Sell", message="MACD Sell on {{ticker}}")
"""
        return script
    
    def save_to_file(self, script: str, filename: str) -> None:
        """Save Pine Script to file."""
        with open(filename, 'w') as f:
            f.write(script)
        print(f"Saved to {filename}")


if __name__ == "__main__":
    gen = PineGenerator()
    script = gen.generate_rsi_strategy("BTCUSDT", "15m", 14, 30, 70)
    gen.save_to_file(script, "rsi_strategy.pine")
    print("Generated RSI strategy Pine Script")
