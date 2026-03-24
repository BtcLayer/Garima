"""
Run all batch strategies on all assets and find profitable ones
"""

import pandas as pd
import numpy as np
from strategies import get_all_strategies, get_strategies_by_batch
import os
import json

# Data directory
DATA_DIR = "storage/historical_data"

# Available data files
DATA_FILES = {
    "BTCUSDT_15m": "BTCUSDT_15m_2025-03-17_2026-03-17.parquet",
    "BTCUSDT_1h": "BTCUSDT_1h_2025-03-17_2026-03-17.parquet",
    "ETHUSDT_15m": "ETHUSDT_15m_2025-03-17_2026-03-17.parquet",
    "ETHUSDT_1h": "ETHUSDT_1h_2025-03-17_2026-03-17.parquet",
    "BNBUSDT_15m": "BNBUSDT_15m_2025-03-17_2026-03-17.parquet",
    "BNBUSDT_1h": "BNBUSDT_1h_2025-03-17_2026-03-17.parquet",
}

INITIAL_CAPITAL = 10000
FEE = 0.001

def load_data(symbol_key):
    filepath = os.path.join(DATA_DIR, DATA_FILES.get(symbol_key))
    if not os.path.exists(filepath):
        return None
    df = pd.read_parquet(filepath)
    return df

def calculate_indicators(df):
    df = df.copy()
    df["ema8"] = df["close"].ewm(span=8).mean()
    df["ema21"] = df["close"].ewm(span=21).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()
    df["sma20"] = df["close"].rolling(20).mean()
    df["bb_mid"] = df["sma20"]
    df["bb_std"] = df["close"].rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2 * df["bb_std"]
    df["bb_lower"] = df["bb_mid"] - 2 * df["bb_std"]
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))
    df["macd"] = df["ema21"] - df["ema50"]
    df["macd_signal"] = df["macd"].ewm(span=9).mean()
    low14 = df["low"].rolling(14).min()
    high14 = df["high"].rolling(14).max()
    df["stoch_k"] = 100 * (df["close"] - low14) / (high14 - low14)
    df["vol_ma"] = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / df["vol_ma"]
    high_low = df["high"] - df["low"]
    high_close = abs(df["high"] - df["close"].shift())
    low_close = abs(df["low"] - df["close"].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean()
    df["vwap"] = (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum()
    hl_avg = (df["high"] + df["low"]) / 2
    df["supertrend"] = hl_avg - 3 * df["atr"]
    plus_dm = df["high"].diff().clip(lower=0)
    minus_dm = (-df["low"].diff()).clip(lower=0)
    plus_di = 100 * plus_dm.rolling(14).mean() / df["atr"]
    minus_di = 100 * minus_dm.rolling(14).mean() / df["atr"]
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    df["adx"] = dx.rolling(14).mean()
    df["high_20"] = df["high"].rolling(20).max()
    return df

SIGNAL_FUNCTIONS = {
    "EMA_Cross": lambda df: (df["ema8"] > df["ema21"]).astype(int),
    "RSI_Oversold": lambda df: ((df["rsi"] < 30) & (df["rsi"] > df["rsi"].shift(1))).astype(int),
    "MACD_Cross": lambda df: ((df["macd"] > df["macd_signal"]) & (df["macd"].shift(1) <= df["macd_signal"].shift(1))).astype(int),
    "BB_Lower": lambda df: (df["close"] < df["bb_lower"]).astype(int),
    "Volume_Spike": lambda df: ((df["vol_ratio"] > 1.5) & (df["close"] > df["close"].shift(1))).astype(int),
    "Breakout_20": lambda df: (df["close"] > df["high_20"]).astype(int),
    "Stochastic": lambda df: ((df["stoch_k"] < 20) & (df["stoch_k"] > df["stoch_k"].shift(1))).astype(int),
    "Supertrend": lambda df: (df["close"] > df["supertrend"]).astype(int),
    "VWAP": lambda df: (df["close"] > df["vwap"]).astype(int),
    "ADX_Trend": lambda df: (df["adx"] > 25).astype(int),
    "Trend_MA50": lambda df: (df["close"] > df["ema50"]).astype(int),
}

def apply_strategy(df, strategy_combo, min_agreement=1):
    signals = pd.DataFrame(index=df.index)
    for strat_name in strategy_combo:
        if strat_name in SIGNAL_FUNCTIONS:
            signals[strat_name] = SIGNAL_FUNCTIONS[strat_name](df)
    if len(signals.columns) > 0:
        df["combo_signal"] = signals.sum(axis=1)
        df["entry_signal"] = (df["combo_signal"] >= min_agreement).astype(int)
    else:
        df["entry_signal"] = 0
    return df

def run_backtest(df, stop_loss, take_profit, trailing_stop):
    capital = INITIAL_CAPITAL
    position = 0
    position_size = 0
    entry_price = 0
    trades = []
    
    for idx, row in df.iterrows():
        if row["entry_signal"] == 1 and position == 0:
            entry_price = row["close"]
            position_size = capital * 0.95 / entry_price
            position = 1
        elif position == 1:
            current_price = row["close"]
            peak_price = max(entry_price, current_price)
            trailing_stop_price = peak_price * (1 - trailing_stop)
            should_exit = False
            if row.get("exit_signal", 0) == 1:
                should_exit = True
            if current_price <= entry_price * (1 - stop_loss):
                should_exit = True
            if current_price >= entry_price * (1 + take_profit):
                should_exit = True
            if current_price <= trailing_stop_price:
                should_exit = True
            if should_exit:
                exit_price = row["close"]
                pnl = position_size * exit_price * (1 - FEE) - position_size * entry_price
                capital += pnl
                trades.append({"pnl": pnl, "return_pct": (exit_price - entry_price) / entry_price * 100})
                position = 0
    return capital, trades

def run_all():
    all_profitable = []
    
    print("="*70)
    print("RUNNING ALL BATCHES ON ALL ASSETS")
    print("="*70)
    
    assets = list(DATA_FILES.keys())
    total = len(assets) * 20
    count = 0
    
    for asset_key in assets:
        df = load_data(asset_key)
        if df is None:
            continue
        print(f"\nLoading {asset_key}...")
        df = calculate_indicators(df)
        
        for batch_num in range(1, 21):
            count += 1
            strategies = get_strategies_by_batch(batch_num)
            
            for strategy in strategies:
                try:
                    df_copy = apply_strategy(df.copy(), strategy["strategies"], strategy.get("min_agreement", 1))
                    final_capital, trades = run_backtest(df_copy, strategy["stop_loss"], strategy["take_profit"], strategy["trailing_stop"])
                    
                    if len(trades) >= 5:
                        roi = (final_capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
                        
                        if roi > 0:
                            wins = [t for t in trades if t["pnl"] > 0]
                            win_rate = len(wins) / len(trades) * 100 if trades else 0
                            
                            result = {
                                "asset": asset_key,
                                "batch": batch_num,
                                "id": strategy["id"],
                                "name": strategy["name"],
                                "strategies": strategy["strategies"],
                                "trades": len(trades),
                                "win_rate": round(win_rate, 2),
                                "roi": round(roi, 2),
                                "sl": strategy["stop_loss"],
                                "tp": strategy["take_profit"],
                                "ts": strategy["trailing_stop"]
                            }
                            all_profitable.append(result)
                            print(f"  ✅ #{strategy['id']} {strategy['name']} on {asset_key}: ROI={roi:.2f}%")
                except:
                    pass
    
    print("\n" + "="*70)
    print(f"FOUND {len(all_profitable)} PROFITABLE STRATEGIES")
    print("="*70)
    
    # Sort by ROI
    all_profitable.sort(key=lambda x: x["roi"], reverse=True)
    
    # Print top 20
    print("\nTOP 20 MOST PROFITABLE:")
    print("-"*70)
    for i, p in enumerate(all_profitable[:20]):
        print(f"{i+1}. {p['name']} | {p['asset']} | ROI: {p['roi']}% | Trades: {p['trades']} | Win%: {p['win_rate']}")
    
    # Save to JSON
    with open("profitable_strategies_all.json", "w") as f:
        json.dump(all_profitable, f, indent=2)
    
    print(f"\nResults saved to profitable_strategies_all.json")
    return all_profitable

if __name__ == "__main__":
    run_all()
