"""
Run all strategies on XRPUSDT - All Timeframes (15m, 1h, 4h)
Enhanced version with comprehensive metrics
"""

import pandas as pd
import numpy as np
import os
from strategies import get_all_strategies

DATA_DIR = "storage/historical_data"
INITIAL_CAPITAL = 10000
FEE = 0.0001  # 0.01% Binance fee (entry + exit)

DATA_FILES = {
    "15m": "XRPUSDT_15m_2025-03-17_2026-03-17.parquet",
    "1h": "XRPUSDT_1h_2025-03-17_2026-03-17.parquet",
    "4h": "XRPUSDT_4h_2025-03-17_2026-03-17.parquet",
}

def load_data(timeframe):
    # Try local file first
    filepath = os.path.join(DATA_DIR, DATA_FILES.get(timeframe))
    if os.path.exists(filepath):
        df = pd.read_parquet(filepath)
        time_col = 'timestamp' if 'timestamp' in df.columns else 'open_time'
        time_start = df[time_col].min()
        time_end = df[time_col].max()
        return df, time_start, time_end
    
    # Fetch from Binance if not available
    print(f"Fetching XRPUSDT {timeframe} data from Binance...")
    try:
        from binance.client import Client
        from dotenv import load_dotenv
        load_dotenv()
        client = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_API_SECRET'))
        interval_map = {"15m": "15m", "1h": "1h", "4h": "4h"}
        
        # Get 1 year of data
        klines = client.get_klines(
            symbol='XRPUSDT',
            interval=interval_map.get(timeframe, "1h"),
            limit=1000
        )
        
        df = pd.DataFrame(klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        
        # Save to local for future use
        save_path = os.path.join(DATA_DIR, f"XRPUSDT_{timeframe}_2025-03-17_2026-03-17.parquet")
        df.to_parquet(save_path, index=False)
        print(f"  Saved to {save_path}")
        
        time_start = pd.to_datetime(df['open_time'], unit='ms').min()
        time_end = pd.to_datetime(df['open_time'], unit='ms').max()
        
        return df, time_start, time_end
    except Exception as e:
        print(f"Could not fetch XRPUSDT data: {e}")
        return None, None, None

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

SIGNALS = {
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
    for s in strategy_combo:
        if s in SIGNALS:
            signals[s] = SIGNALS[s](df)
    if len(signals.columns) > 0:
        df["combo_signal"] = signals.sum(axis=1)
        df["entry_signal"] = (df["combo_signal"] >= min_agreement).astype(int)
    else:
        df["entry_signal"] = 0
    return df

def run_backtest_detailed(df, sl, tp, ts):
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
            trailing_stop_price = peak_price * (1 - ts)
            should_exit = False
            if current_price <= entry_price * (1 - sl):
                should_exit = True
            if current_price >= entry_price * (1 + tp):
                should_exit = True
            if current_price <= trailing_stop_price:
                should_exit = True
            if should_exit:
                exit_price = row["close"]
                # Fee on both entry and exit
                pnl = position_size * exit_price * (1 - FEE) - position_size * entry_price * (1 + FEE)
                pnl_percent = (exit_price - entry_price) / entry_price * 100
                capital += pnl
                trades.append({"pnl": pnl, "pnl_percent": pnl_percent, "capital": capital})
                position = 0
    
    final_capital = capital
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t["pnl"] > 0])
    losing_trades = len([t for t in trades if t["pnl"] <= 0])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    gross_profit = sum([t["pnl"] for t in trades if t["pnl"] > 0])
    gross_loss = abs(sum([t["pnl"] for t in trades if t["pnl"] < 0]))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0
    avg_trade_pct = np.mean([t["pnl_percent"] for t in trades]) if trades else 0
    sharpe = np.std([t["pnl_percent"] for t in trades]) if len(trades) > 1 else 0
    roi = (final_capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    
    # Calculate Max Drawdown
    equity_curve = [INITIAL_CAPITAL]
    for t in trades:
        equity_curve.append(t["capital"])
    peak = INITIAL_CAPITAL
    max_dd = 0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100 if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
    
    return {
        "final_capital": final_capital,
        "net_profit": final_capital - INITIAL_CAPITAL,
        "roi": roi,
        "roi_annum": roi,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "sharpe_ratio": sharpe,
        "avg_trade_percent": avg_trade_pct,
        "max_drawdown": max_dd
    }

def get_performance_grade(roi, win_rate, sharpe):
    score = 0
    if roi > 50: score += 2
    elif roi > 20: score += 1
    if win_rate > 50: score += 2
    elif win_rate > 40: score += 1
    if sharpe > 1.5: score += 2
    elif sharpe > 1: score += 1
    if score >= 6: return "A+"
    elif score >= 5: return "A"
    elif score >= 4: return "B+"
    elif score >= 3: return "B"
    elif score >= 2: return "C"
    else: return "D"

def run_all():
    results = []
    strategies = get_all_strategies()
    timeframes = ["15m", "1h", "4h"]
    
    print("="*60)
    print("XRPUSDT - Testing ALL Strategies on ALL Timeframes")
    print("="*60)
    
    for tf in timeframes:
        print(f"\n--- Timeframe: {tf} ---")
        df, time_start, time_end = load_data(tf)
        if df is None:
            print(f"No data for {tf}")
            continue
        
        if hasattr(time_start, 'timestamp'):
            period_days = (time_end - time_start).total_seconds() / (24*3600)
        elif hasattr(time_start, 'days'):
            period_days = time_end.days - time_start.days
        else:
            period_days = 365
            
        ts_str = str(time_start)[:10] if time_start else "N/A"
        te_str = str(time_end)[:10] if time_end else "N/A"
        
        df = calculate_indicators(df)
        
        for strategy in strategies:
            try:
                df_copy = apply_strategy(df.copy(), strategy["strategies"], strategy.get("min_agreement", 1))
                metrics = run_backtest_detailed(df_copy, strategy["stop_loss"], strategy["take_profit"], strategy["trailing_stop"])
                
                if metrics["total_trades"] >= 5:
                    grade = get_performance_grade(metrics["roi"], metrics["win_rate"], metrics["sharpe_ratio"])
                    
                    results.append({
                        "Rank": 0,
                        "Strategy": strategy["name"],
                        "Asset": "XRPUSDT",
                        "Timeframe": tf,
                        "Initial_Capital_USD": INITIAL_CAPITAL,
                        "Final_Capital_USD": round(metrics["final_capital"], 2),
                        "Net_Profit_USD": round(metrics["net_profit"], 2),
                        "roi": round(metrics["roi"], 2),
                        "ROI/annum": round(metrics["roi_annum"], 2),
                        "ROI_per_annum_Percent": round(metrics["roi_annum"], 2),
                        "Total_Trades": metrics["total_trades"],
                        "Winning_Trades": metrics["winning_trades"],
                        "Losing_Trades": metrics["losing_trades"],
                        "Win_Rate_Percent": round(metrics["win_rate"], 2),
                        "Profit_Factor": round(metrics["profit_factor"], 2),
                        "Sharpe_Ratio": round(metrics["sharpe_ratio"], 2),
                        "Avg_Trade_Percent": round(metrics["avg_trade_percent"], 2),
                        "Max_Drawdown": round(metrics["max_drawdown"], 2),
                        "Performance_Grade": grade,
                        "Deployment_Status": "Active" if metrics["roi"] > 0 else "Inactive",
                        "Data_Source": "Binance_API" if tf not in DATA_FILES else "Historical_Parquet",
                        "Time_period_checked": f"{int(period_days)} days",
                        "Time_start": ts_str,
                        "time_end": te_str,
                        "fees_exchnage": "Entry:0.01% + Exit:0.01%",
                        "Parameters": f"SL:{strategy['stop_loss']}, TP:{strategy['take_profit']}, TS:{strategy['trailing_stop']}",
                        "Candle_Period": tf
                    })
                    
                    if metrics["roi"] > 0:
                        print(f"  ✅ {strategy['name']} ({tf}): ROI={metrics['roi']:.2f}%")
            except Exception as e:
                print(f"Error: {e}")
                continue
    
    if len(results) > 0:
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values("roi", ascending=False).reset_index(drop=True)
        df_results["Rank"] = range(1, len(df_results) + 1)
        
        cols = ["Rank", "Strategy", "Asset", "Timeframe", "Initial_Capital_USD", 
                "Final_Capital_USD", "Net_Profit_USD", "roi", "ROI/annum", 
                "ROI_per_annum_Percent", "Total_Trades", "Winning_Trades", 
                "Losing_Trades", "Win_Rate_Percent", "Profit_Factor", 
                "Sharpe_Ratio", "Avg_Trade_Percent", "Performance_Grade",
                "Deployment_Status", "Data_Source", "Time_period_checked",
                "Time_start", "time_end", "fees_exchnage", "Parameters", "Candle_Period"]
        
        df_results = df_results[cols]
        df_results.to_csv("xrp_all_results.csv", index=False)
        
        profitable = df_results[df_results["roi"] > 0].sort_values("roi", ascending=False)
        print(f"\n{'='*60}")
        print(f"PROFITABLE STRATEGIES: {len(profitable)}")
        print("="*60)
        print(profitable.head(20).to_string())
    else:
        print("\n⚠️ No results generated - no data available for XRPUSDT")
        cols = ["Rank", "Strategy", "Asset", "Timeframe", "Initial_Capital_USD", 
                "Final_Capital_USD", "Net_Profit_USD", "roi", "ROI/annum", 
                "ROI_per_annum_Percent", "Total_Trades", "Winning_Trades", 
                "Losing_Trades", "Win_Rate_Percent", "Profit_Factor", 
                "Sharpe_Ratio", "Avg_Trade_Percent", "Performance_Grade",
                "Deployment_Status", "Data_Source", "Time_period_checked",
                "Time_start", "time_end", "fees_exchnage", "Parameters", "Candle_Period"]
        pd.DataFrame(columns=cols).to_csv("xrp_all_results.csv", index=False)
    
    return results

if __name__ == "__main__":
    run_all()
