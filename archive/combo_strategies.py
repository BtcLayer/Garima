"""
Combined Multi-Strategy Trading System
Enhanced version with ensemble strategy combinations for profitable trading
"""

import ccxt
import pandas as pd
import numpy as np
from itertools import combinations

# Exchange configuration
exchange = ccxt.binance()

# Trading parameters
ASSETS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "LINK/USDT", "AVAX/USDT"]
TIMEFRAMES = ["15m", "1h", "4h"]
INITIAL_CAPITAL = 10000
FEE = 0.001
MAX_POSITIONS = 3  # Maximum concurrent positions

# Risk parameters - Multiple configs for optimization
# Config 1: Conservative (lower risk, moderate returns)
# Config 2: Moderate (balanced risk/reward)
# Config 3: Aggressive (higher risk, higher returns)
# Config 4: Very Aggressive (maximum returns)

STOP_LOSS = 0.015  # 1.5%
TAKE_PROFIT = 0.035  # 3.5%
TRAILING_STOP = 0.01  # 1%

# Higher ROI parameters (for testing) - Optimized for HIGHER returns
HIGH_ROI_CONFIGS = [
    {"stop_loss": 0.005, "take_profit": 0.05, "trailing_stop": 0.005, "name": "Max_1"},
    {"stop_loss": 0.008, "take_profit": 0.06, "trailing_stop": 0.008, "name": "Max_2"},
    {"stop_loss": 0.01, "take_profit": 0.07, "trailing_stop": 0.01, "name": "Max_3"},
    {"stop_loss": 0.012, "take_profit": 0.08, "trailing_stop": 0.012, "name": "Max_4"},
    {"stop_loss": 0.015, "take_profit": 0.09, "trailing_stop": 0.015, "name": "Max_5"},
    {"stop_loss": 0.018, "take_profit": 0.10, "trailing_stop": 0.018, "name": "Max_6"},
    {"stop_loss": 0.02, "take_profit": 0.12, "trailing_stop": 0.02, "name": "Max_7"},
    {"stop_loss": 0.025, "take_profit": 0.15, "trailing_stop": 0.025, "name": "Max_8"},
]

results = []


def fetch_data(symbol, timeframe, limit=None):
    """Fetch OHLCV data - 365+ days for all timeframes"""
    # Calculate minimum candles needed - at least 15000 for all timeframes
    if timeframe == "15m":
        min_candles = 50000  # Extra buffer for 15m
    elif timeframe == "1h":
        min_candles = 20000  # Extra buffer for 1h
    elif timeframe == "4h":
        min_candles = 15000  # Minimum 15000 for 4h
    else:
        min_candles = 15000
    
    # Fetch data for specific date range
    try:
        # Convert dates to timestamps
        start_time = int(pd.Timestamp("2024-01-01").timestamp() * 1000)
        end_time = int(pd.Timestamp("2026-01-01").timestamp() * 1000)
        
        # Fetch with date range using 'since' parameter
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=start_time, limit=min_candles)
        
        # Filter data to end date
        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "volume"])
        df = df[df["time"] <= end_time]
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        
        # Print debug info
        print(f"  Fetched {len(df)} candles from {df['time'].iloc[0] if len(df)>0 else 'N/A'} to {df['time'].iloc[-1] if len(df)>0 else 'N/A'}")
        
        return df
    except Exception as e:
        print(f"Error fetching {symbol} {timeframe}: {e}")
        return None


def calculate_indicators(df):
    """Calculate technical indicators for all strategies"""
    
    # EMAs
    df["ema8"] = df["close"].ewm(span=8).mean()
    df["ema21"] = df["close"].ewm(span=21).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()
    
    # SMAs
    df["sma20"] = df["close"].rolling(20).mean()
    df["sma50"] = df["close"].rolling(50).mean()
    df["sma200"] = df["close"].rolling(200).mean()
    
    # Bollinger Bands
    df["bb_mid"] = df["sma20"]
    df["bb_std"] = df["close"].rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2 * df["bb_std"]
    df["bb_lower"] = df["bb_mid"] - 2 * df["bb_std"]
    
    # RSI
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))
    
    # MACD
    df["macd"] = df["ema21"] - df["ema50"]
    df["macd_signal"] = df["macd"].ewm(span=9).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    
    # Stochastic
    low14 = df["low"].rolling(14).min()
    high14 = df["high"].rolling(14).max()
    df["stoch_k"] = 100 * (df["close"] - low14) / (high14 - low14)
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()
    
    # Volume
    df["vol_ma"] = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / df["vol_ma"]
    
    # ATR
    high_low = df["high"] - df["low"]
    high_close = abs(df["high"] - df["close"].shift())
    low_close = abs(df["low"] - df["close"].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean()
    
    # VWAP
    df["vwap"] = (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum()
    
    # Supertrend
    hl_avg = (df["high"] + df["low"]) / 2
    df["supertrend"] = hl_avg - 3 * df["atr"]
    
    # ADX
    plus_dm = df["high"].diff().clip(lower=0)
    minus_dm = (-df["low"].diff()).clip(lower=0)
    plus_di = 100 * plus_dm.rolling(14).mean() / df["atr"]
    minus_di = 100 * minus_dm.rolling(14).mean() / df["atr"]
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    df["adx"] = dx.rolling(14).mean()
    
    # Price channels
    df["high_20"] = df["high"].rolling(20).max()
    df["low_20"] = df["low"].rolling(20).min()
    
    return df


# Define individual strategy signal functions
def strategy_ema_crossover(df):
    """EMA 8/21 crossover"""
    return (df["ema8"] > df["ema21"]).astype(int)

def strategy_rsi_oversold(df):
    """RSI oversold (<30) with recovery"""
    return ((df["rsi"] < 30) & (df["rsi"] > df["rsi"].shift(1))).astype(int)

def strategy_macd_cross(df):
    """MACD crosses above signal"""
    return ((df["macd"] > df["macd_signal"]) & (df["macd"].shift(1) <= df["macd_signal"].shift(1))).astype(int)

def strategy_bb_lower(df):
    """Price at lower Bollinger Band"""
    return (df["close"] < df["bb_lower"]).astype(int)

def strategy_bb_upper(df):
    """Price at upper Bollinger Band"""
    return (df["close"] > df["bb_upper"]).astype(int)

def strategy_volume(df):
    """Volume spike with price up"""
    return ((df["vol_ratio"] > 1.5) & (df["close"] > df["close"].shift(1))).astype(int)

def strategy_breakout(df):
    """20-day high breakout"""
    return (df["close"] > df["high_20"]).astype(int)

def strategy_stochastic(df):
    """Stochastic oversold"""
    return ((df["stoch_k"] < 20) & (df["stoch_k"] > df["stoch_k"].shift(1))).astype(int)

def strategy_supertrend(df):
    """Price above supertrend"""
    return (df["close"] > df["supertrend"]).astype(int)

def strategy_vwap(df):
    """Price above VWAP"""
    return (df["close"] > df["vwap"]).astype(int)

def strategy_adx_trend(df):
    """ADX shows strong trend"""
    return (df["adx"] > 25).astype(int)

def strategy_trend_ma(df):
    """Price above 50 EMA (medium trend)"""
    return (df["close"] > df["ema50"]).astype(int)

# Map strategy names to functions
STRATEGY_FUNCTIONS = {
    "EMA_Cross": strategy_ema_crossover,
    "RSI_Oversold": strategy_rsi_oversold,
    "MACD_Cross": strategy_macd_cross,
    "BB_Lower": strategy_bb_lower,
    "BB_Upper": strategy_bb_upper,
    "Volume_Spike": strategy_volume,
    "Breakout_20": strategy_breakout,
    "Stochastic": strategy_stochastic,
    "Supertrend": strategy_supertrend,
    "VWAP": strategy_vwap,
    "ADX_Trend": strategy_adx_trend,
    "Trend_MA50": strategy_trend_ma,
}


def combine_strategies(df, strategy_names, min_agreement=2):
    """Combine multiple strategies with agreement threshold"""
    
    # Get signals from each strategy
    signals = pd.DataFrame(index=df.index)
    for name in strategy_names:
        if name in STRATEGY_FUNCTIONS:
            signals[name] = STRATEGY_FUNCTIONS[name](df)
    
    # Combined signal = sum of all strategy signals
    if len(signals.columns) > 0:
        df["combo_signal"] = signals.sum(axis=1)
        df["entry_signal"] = (df["combo_signal"] >= min_agreement).astype(int)
    else:
        df["entry_signal"] = 0
    
    # Exit when combo signal drops
    df["exit_signal"] = (df["combo_signal"] < 1).astype(int)
    
    return df


def run_backtest_with_combo(df, stop_loss_pct=STOP_LOSS, take_profit_pct=TAKE_PROFIT, trailing_stop_pct=TRAILING_STOP):
    """Run backtest with combined strategies"""
    
    capital = INITIAL_CAPITAL
    position = 0
    position_size = 0
    entry_price = 0
    entry_time = None
    peak_price = 0
    trades = []
    
    for idx, row in df.iterrows():
        
        # Entry
        if row["entry_signal"] == 1 and position == 0:
            entry_price = row["close"]
            position_size = capital * 0.95 / entry_price
            entry_time = row["time"]
            peak_price = entry_price
            position = 1
            
        # Position management
        elif position == 1:
            current_price = row["close"]
            peak_price = max(peak_price, current_price)
            
            # Update trailing stop
            trailing_stop = peak_price * (1 - trailing_stop_pct)
            
            # Check exit conditions
            should_exit = False
            
            # Strategy exit signal
            if row["exit_signal"] == 1:
                should_exit = True
            
            # Stop loss
            if current_price <= entry_price * (1 - stop_loss_pct):
                should_exit = True
            
            # Take profit
            if current_price >= entry_price * (1 + take_profit_pct):
                should_exit = True
            
            # Trailing stop
            if current_price <= trailing_stop:
                should_exit = True
            
            if should_exit:
                exit_price = row["close"]
                pnl = position_size * exit_price * (1 - FEE) - position_size * entry_price
                capital += pnl
                
                trades.append({
                    "entry": entry_time,
                    "exit": row["time"],
                    "pnl": pnl,
                    "return_pct": (exit_price - entry_price) / entry_price * 100
                })
                position = 0
    
    # Close final position
    if position == 1:
        exit_price = df.iloc[-1]["close"]
        pnl = position_size * exit_price * (1 - FEE) - position_size * entry_price
        capital += pnl
        trades.append({
            "entry": entry_time,
            "exit": df.iloc[-1]["time"],
            "pnl": pnl,
            "return_pct": (exit_price - entry_price) / entry_price * 100
        })
    
    return capital, trades


def get_strategy_combinations():
    """Generate different strategy combinations to test"""
    
    strategies = list(STRATEGY_FUNCTIONS.keys())
    
    combos = []
    
    # Conservative combos (3-4 strategies)
    combos.append(["EMA_Cross", "RSI_Oversold", "Supertrend", "Trend_MA50"])
    combos.append(["EMA_Cross", "MACD_Cross", "ADX_Trend", "Trend_MA50"])
    combos.append(["RSI_Oversold", "Stochastic", "BB_Lower", "Trend_MA50"])
    
    # Moderate combos (4-5 strategies)
    combos.append(["EMA_Cross", "MACD_Cross", "RSI_Oversold", "Supertrend", "ADX_Trend"])
    combos.append(["BB_Lower", "Volume_Spike", "RSI_Oversold", "Stochastic", "Trend_MA50"])
    combos.append(["Breakout_20", "Volume_Spike", "MACD_Cross", "Supertrend", "VWAP"])
    
    # Aggressive combos (5-6 strategies)
    combos.append(["EMA_Cross", "MACD_Cross", "Volume_Spike", "Breakout_20", "ADX_Trend", "VWAP"])
    combos.append(["RSI_Oversold", "Stochastic", "BB_Lower", "Volume_Spike", "Supertrend", "Trend_MA50"])
    
    # All strategies combined
    combos.append(strategies)
    
    return combos


def calculate_sharpe(trades, risk_free_rate=0.02):
    """Calculate Sharpe ratio"""
    if len(trades) < 2:
        return 0
    
    returns = [t["return_pct"] / 100 for t in trades]
    if np.std(returns) == 0:
        return 0
    
    sharpe = (np.mean(returns) - risk_free_rate / 252) / np.std(returns) * np.sqrt(252)
    return sharpe


def calculate_max_drawdown(trades):
    """Calculate maximum drawdown"""
    if not trades:
        return 0
    
    equity = INITIAL_CAPITAL
    peak = INITIAL_CAPITAL
    max_dd = 0
    
    for trade in trades:
        equity += trade["pnl"]
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak
        max_dd = max(max_dd, dd)
    
    return max_dd * 100


def run_full_backtest():
    """Run complete backtest across all combinations"""
    
    print("=" * 70)
    print("COMBINED MULTI-STRATEGY TRADING SYSTEM")
    print("=" * 70)
    
    strategy_combos = get_strategy_combinations()
    combo_names = [
        "EMA_RSI_Supertrend_MA50",
        "EMA_MACD_ADX_MA50",
        "RSI_Stoch_BB_MA50",
        "EMA_MACD_RSI_Supertrend_ADX",
        "BB_Volume_RSI_Stoch_MA50",
        "Breakout_Volume_MACD_Supertrend_VWAP",
        "EMA_MACD_Volume_Breakout_ADX_VWAP",
        "RSI_Stoch_BB_Volume_Supertrend_MA50",
        "All_12_Strategies"
    ]
    
    rank = 1
    
    # Test all parameter configurations including high ROI configs
    all_configs = HIGH_ROI_CONFIGS.copy()
    
    for combo_idx, combo in enumerate(strategy_combos):
        combo_name = combo_names[combo_idx] if combo_idx < len(combo_names) else f"Combo_{combo_idx}"
        
        for config in all_configs:
            config_name = f"{combo_name}_{config['name']}"
            
            for asset in ASSETS:
                for tf in TIMEFRAMES:
                    try:
                        print(f"Testing: {config_name} | {asset} | {tf}")
                        
                        df = fetch_data(asset, tf)
                        if df is None or len(df) < 200:
                            continue
                        
                        df = calculate_indicators(df)
                        df = combine_strategies(df, combo, min_agreement=1)  # More trades for higher ROI
                        
                        final_capital, trades = run_backtest_with_combo(
                            df, 
                            stop_loss_pct=config["stop_loss"],
                            take_profit_pct=config["take_profit"],
                            trailing_stop_pct=config["trailing_stop"]
                        )
                        
                        if len(trades) < 10 or len(trades) > 100:  # Require 10-100 trades
                            continue
                        
                        wins = [t for t in trades if t["pnl"] > 0]
                        losses = [t for t in trades if t["pnl"] <= 0]
                        win_rate = len(wins) / len(trades) * 100
                        
                        days = (df["time"].iloc[-1] - df["time"].iloc[0]).days
                        
                        # ROI calculation
                        roi = (final_capital - INITIAL_CAPITAL) / INITIAL_CAPITAL
                        
                        # ROI in percentage
                        roi_percent = roi * 100
                        
                        # Annualized ROI
                        roi_annum = roi * (365 / days) if days > 0 else 0
                        roi_annum_percent = roi_annum * 100
                        
                        sharpe = calculate_sharpe(trades)
                        max_dd = calculate_max_drawdown(trades)
                        
                        # Additional metrics
                        avg_trade_pct = np.mean([t["return_pct"] for t in trades]) if trades else 0
                        
                        # Profit Factor
                        total_wins = sum([t["pnl"] for t in wins]) if wins else 0
                        total_losses = abs(sum([t["pnl"] for t in losses])) if losses else 1
                        profit_factor = total_wins / total_losses if total_losses > 0 else 0
                        
                        # Performance Grade (adjusted for 10-50% ROI target)
                        if roi_annum_percent > 50 and win_rate > 45 and sharpe > 1.2:
                            performance_grade = "A+"
                        elif roi_annum_percent > 40 and win_rate > 40:
                            performance_grade = "A"
                        elif roi_annum_percent > 30 and win_rate > 35:
                            performance_grade = "B"
                        elif roi_annum_percent > 15 and win_rate > 30:
                            performance_grade = "C"
                        elif roi_annum_percent > 10:
                            performance_grade = "D"
                        else:
                            performance_grade = "F"
                        
                        # Deployment Status (adjusted for 10-50% ROI target)
                        if roi_annum_percent > 40 and max_dd < 25:
                            deployment_status = "Ready"
                        elif roi_annum_percent > 25:
                            deployment_status = "Paper Trading"
                        elif roi_annum_percent > 10:
                            deployment_status = "Monitor"
                        else:
                            deployment_status = "Not Recommended"
                        
                        # Use the config parameters in output
                        params_str = f"SL:{config['stop_loss']*100}%, TP:{config['take_profit']*100}%, TS:{config['trailing_stop']*100}%"
                        
                        time_start = df["time"].iloc[0].strftime("%Y-%m-%d")
                        time_end = df["time"].iloc[-1].strftime("%Y-%m-%d")
                        
                        results.append({
                            "Rank": rank,
                            "Strategy": config_name,
                            "Asset": asset,
                            "Timeframe": tf,
                            "Initial_Capital_USD": INITIAL_CAPITAL,
                            "Final_Capital_USD": round(final_capital, 2),
                            "Net_Profit_USD": round(final_capital - INITIAL_CAPITAL, 2),
                            "ROI_Percent": round(roi_percent, 2),
                            "roi_annum": round(roi_annum * INITIAL_CAPITAL, 2),
                            "ROI/annum%": round(roi_annum_percent, 2),
                            "Year_1_ROI": round(roi_annum_percent * 1, 2) if days > 365 else round(roi_percent, 2),
                            "Winning_Trades": len(wins),
                            "Losing_Trades": len(losses),
                            "Win_Rate_Percent": round(win_rate, 2),
                            "Profit_Factor": round(profit_factor, 2),
                            "Sharpe_Ratio": round(sharpe, 2),
                            "Avg_Trade_Percent": round(avg_trade_pct, 2),
                            "Performance_Grade": performance_grade,
                            "Deployment_Status": deployment_status,
                            "Data_Source": "Binance",
                            "Time_period_checked": days,
                            "Time_start": time_start,
                            "time_end": time_end,
                            "fees_exchange": FEE,
                            "Paramters: Candle period": tf,
                            "paramters_others": params_str
                        })
                        
                        rank += 1
                        
                        # Stop after 10 results for testing
                        if rank > 10:
                            print("\n=== Test complete - 10 results generated ===")
                            break
                    
                    except Exception as e:
                        print(f"Error: {e}")
                        continue
                
                # Break outer loops if test complete
                if rank > 10:
                    break
            
            if rank > 10:
                break
        
        if rank > 10:
            break
    
    # Process results
    if results:
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values(by="ROI/annum%", ascending=False)
        df_results["Rank"] = range(1, len(df_results) + 1)
        
        # Save results
        df_results.to_csv("combo_strategy_results.csv", index=False)
        
        print("\n" + "=" * 70)
        print("TOP 15 MOST PROFITABLE STRATEGY COMBINATIONS")
        print("=" * 70)
        print(df_results.head(15).to_string())
        
        # Summary
        profitable = df_results[df_results["Net_Profit_USD"] > 0]
        print(f"\n\nSUMMARY:")
        print(f"Total combinations tested: {len(df_results)}")
        print(f"Profitable combinations: {len(profitable)} ({len(profitable)/len(df_results)*100:.1f}%)")
        
        if len(profitable) > 0:
            print(f"\nBest ROI (Annual): {profitable['ROI/annum%'].max():.2f}%")
            print(f"Best Win Rate: {profitable['Win_Rate_Percent'].max():.2f}%")
            print(f"Best Sharpe Ratio: {profitable['Sharpe_Ratio'].max():.2f}")
            
            print("\n\nTOP 5 BY SHARPE RATIO:")
            print(df_results.nlargest(5, "Sharpe_Ratio")[["Strategy", "Asset", "Timeframe", "ROI/annum%", "Win_Rate_Percent", "Sharpe_Ratio", "Performance_Grade"]].to_string())
        
    else:
        print("No results generated")


if __name__ == "__main__":
    run_full_backtest()
