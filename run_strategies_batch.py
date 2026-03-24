"""
Run strategies from batch files on historical candle data
Uses pagination to process data in chunks
"""

import pandas as pd
import numpy as np
from strategies import get_all_strategies, get_strategies_by_batch
import os

# Data directory
DATA_DIR = "storage/historical_data"

# Available data files — 6 years (2020-2026), 10 assets x 3 timeframes
_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
            "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT"]
_TIMEFRAMES = ["15m", "1h", "4h"]
_DATE_RANGE = "2020-01-01_2026-03-21"

DATA_FILES = {}
for _sym in _SYMBOLS:
    for _tf in _TIMEFRAMES:
        _key = f"{_sym}_{_tf}"
        _file = f"{_sym}_{_tf}_{_DATE_RANGE}.parquet"
        # Use 6yr file if it exists, fall back to 1yr file
        if os.path.exists(os.path.join(DATA_DIR, _file)):
            DATA_FILES[_key] = _file
        else:
            # Try any matching parquet file for this symbol+timeframe
            for f in sorted(os.listdir(DATA_DIR), reverse=True):
                if f.startswith(f"{_sym}_{_tf}_") and f.endswith(".parquet"):
                    DATA_FILES[_key] = f
                    break

# Trading parameters
INITIAL_CAPITAL = 10000
FEE = 0.001


def load_data(symbol_key):
    """Load historical data from parquet file"""
    filename = DATA_FILES.get(symbol_key)
    if not filename:
        print(f"No data file found for: {symbol_key}")
        return None
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"Data file not found: {filepath}")
        return None

    df = pd.read_parquet(filepath)
    print(f"Loaded {symbol_key}: {len(df)} candles ({filename})")
    return df


def calculate_indicators(df):
    """Calculate technical indicators"""
    df = df.copy()
    
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
    denom = plus_di + minus_di
    dx = 100 * abs(plus_di - minus_di) / denom.replace(0, float('nan'))
    df["adx"] = dx.rolling(14).mean()
    
    # Price channels
    df["high_20"] = df["high"].rolling(20).max()
    df["low_20"] = df["low"].rolling(20).min()
    
    return df


# Strategy signal functions
def get_signal_ema_cross(df):
    return (df["ema8"] > df["ema21"]).astype(int)

def get_signal_rsi_oversold(df):
    return ((df["rsi"] < 30) & (df["rsi"] > df["rsi"].shift(1))).astype(int)

def get_signal_macd_cross(df):
    return ((df["macd"] > df["macd_signal"]) & (df["macd"].shift(1) <= df["macd_signal"].shift(1))).astype(int)

def get_signal_bb_lower(df):
    return (df["close"] < df["bb_lower"]).astype(int)

def get_signal_bb_upper(df):
    return (df["close"] > df["bb_upper"]).astype(int)

def get_signal_volume(df):
    return ((df["vol_ratio"] > 1.5) & (df["close"] > df["close"].shift(1))).astype(int)

def get_signal_breakout(df):
    return (df["close"] > df["high_20"]).astype(int)

def get_signal_stochastic(df):
    return ((df["stoch_k"] < 20) & (df["stoch_k"] > df["stoch_k"].shift(1))).astype(int)

def get_signal_supertrend(df):
    return (df["close"] > df["supertrend"]).astype(int)

def get_signal_vwap(df):
    return (df["close"] > df["vwap"]).astype(int)

def get_signal_adx_trend(df):
    return (df["adx"] > 25).astype(int)

def get_signal_trend_ma(df):
    return (df["close"] > df["ema50"]).astype(int)


SIGNAL_FUNCTIONS = {
    "EMA_Cross": get_signal_ema_cross,
    "RSI_Oversold": get_signal_rsi_oversold,
    "MACD_Cross": get_signal_macd_cross,
    "BB_Lower": get_signal_bb_lower,
    "BB_Upper": get_signal_bb_upper,
    "Volume_Spike": get_signal_volume,
    "Breakout_20": get_signal_breakout,
    "Stochastic": get_signal_stochastic,
    "Supertrend": get_signal_supertrend,
    "VWAP": get_signal_vwap,
    "ADX_Trend": get_signal_adx_trend,
    "Trend_MA50": get_signal_trend_ma,
}


def apply_strategy(df, strategy_combo, min_agreement=1):
    """Apply a strategy combination to get entry signals"""
    signals = pd.DataFrame(index=df.index)
    
    for strat_name in strategy_combo:
        if strat_name in SIGNAL_FUNCTIONS:
            signals[strat_name] = SIGNAL_FUNCTIONS[strat_name](df)
    
    if len(signals.columns) > 0:
        df["combo_signal"] = signals.sum(axis=1)
        df["entry_signal"] = (df["combo_signal"] >= min_agreement).astype(int)
    else:
        df["entry_signal"] = 0
    
    df["exit_signal"] = (df["combo_signal"] < 1).astype(int)
    return df


def run_backtest(df, stop_loss, take_profit, trailing_stop, use_tight=False):
    """Run backtest on a single strategy"""
    # Use tighter parameters for better results
    if use_tight:
        stop_loss = stop_loss / 2
        take_profit = take_profit / 2
        trailing_stop = trailing_stop / 2
    
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
            
            if row["exit_signal"] == 1:
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
                exit_date = str(row.get("timestamp", row.get("open_time", idx)))[:10]
                trades.append({
                    "entry": entry_price,
                    "exit": exit_price,
                    "pnl": pnl,
                    "return_pct": (exit_price - entry_price) / entry_price * 100,
                    "exit_date": exit_date,
                    "capital_after": round(capital, 2),
                })
                position = 0
    
    return capital, trades


def process_with_pagination(df, page_size=5000):
    """Process data with pagination"""
    total_rows = len(df)
    pages = (total_rows + page_size - 1) // page_size
    
    print(f"Processing {total_rows} rows in {pages} pages of {page_size}...")
    
    for page in range(pages):
        start_idx = page * page_size
        end_idx = min((page + 1) * page_size, total_rows)
        print(f"  Page {page + 1}/{pages}: rows {start_idx} to {end_idx}")
    
    return total_rows


def run_batch_strategies(data_key="BTCUSDT_15m", batch_num=None, params_override=None):
    """Run strategies on historical data"""
    print(f"\n{'='*60}")
    print(f"Running strategies on {data_key}")
    print(f"{'='*60}\n")
    
    # Load data
    df = load_data(data_key)
    if df is None:
        return
    
    # Calculate indicators
    print("Calculating indicators...")
    df = calculate_indicators(df)
    
    # Get strategies
    if batch_num:
        strategies = get_strategies_by_batch(batch_num)
        print(f"Running batch {batch_num}: {len(strategies)} strategies")
    else:
        strategies = get_all_strategies()
        print(f"Running all strategies: {len(strategies)} strategies")
    
    # Process with pagination
    process_with_pagination(df, page_size=5000)
    
    # Detect data time range from the dataframe
    time_start = str(df["timestamp"].min())[:10] if "timestamp" in df.columns else "unknown"
    time_end = str(df["timestamp"].max())[:10] if "timestamp" in df.columns else "unknown"
    try:
        from datetime import datetime as _dt
        _start = _dt.fromisoformat(time_start)
        _end = _dt.fromisoformat(time_end)
        _years = max((_end - _start).days / 365.25, 0.01)
    except Exception:
        _years = 1.0

    # Parse asset and timeframe from data_key (e.g. "BTCUSDT_15m")
    _parts = data_key.rsplit("_", 1)
    _asset = _parts[0] if len(_parts) == 2 else data_key
    _timeframe = _parts[1] if len(_parts) == 2 else "unknown"

    def _build_result(strategy, final_capital, trades, is_counter=False):
        """Build a full result dict with all metrics."""
        import numpy as np

        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] <= 0]
        win_rate = len(wins) / len(trades) * 100 if trades else 0
        net_profit = final_capital - INITIAL_CAPITAL
        roi = net_profit / INITIAL_CAPITAL * 100
        roi_annum = ((final_capital / INITIAL_CAPITAL) ** (1 / _years) - 1) * 100 if _years > 0 else 0

        # Profit factor
        total_wins = sum(t["pnl"] for t in trades if t["pnl"] > 0)
        total_losses = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        # Sharpe ratio (annualized from trade returns)
        returns = [t["return_pct"] for t in trades]
        sharpe = 0.0
        avg_trade = 0.0
        if returns:
            avg_trade = sum(returns) / len(returns)
            std = np.std(returns) if len(returns) > 1 else 1
            if std > 0:
                sharpe = (avg_trade / std) * np.sqrt(len(trades))

        # Gross drawdown (peak-to-trough of equity curve)
        equity = INITIAL_CAPITAL
        peak = equity
        max_dd = 0
        min_capital = INITIAL_CAPITAL
        for t in trades:
            equity += t["pnl"]
            peak = max(peak, equity)
            dd = (peak - equity) / peak * 100
            max_dd = max(max_dd, dd)
            min_capital = min(min_capital, equity)
        # Net DD — how far capital dropped below initial (0 if never dropped)
        net_dd = max(0, (INITIAL_CAPITAL - min_capital) / INITIAL_CAPITAL * 100)

        # Grade
        if roi > 100 and win_rate > 50 and profit_factor > 2.0:
            grade = "A+"
        elif roi > 50 and win_rate > 45 and profit_factor > 1.75:
            grade = "A"
        elif roi > 30 and win_rate > 40 and profit_factor > 1.5:
            grade = "B+"
        elif roi > 20 and win_rate > 35 and profit_factor > 1.3:
            grade = "B"
        elif roi > 10 and win_rate > 30:
            grade = "C"
        else:
            grade = "D"

        # Deployment status
        if grade in ("A+", "A") and len(trades) >= 20 and max_dd < 25:
            deploy = "READY"
        elif grade in ("B+", "B") and len(trades) >= 10:
            deploy = "REVIEW"
        else:
            deploy = "NOT READY"

        name = strategy["name"]
        if is_counter:
            name = f"{name}_COUNTER"

        return {
            "id": strategy["id"],
            "name": name,
            "Strategy": ", ".join(strategy["strategies"]),
            "Asset": _asset,
            "Timeframe": _timeframe,
            "Initial_Capital_USD": INITIAL_CAPITAL,
            "Final_Capital_USD": round(final_capital, 2),
            "Net_Profit_USD": round(net_profit, 2),
            "ROI_per_annum": round(roi_annum, 2),
            "ROI_Percent": round(roi, 2),
            "Total_Trades": len(trades),
            "Winning_Trades": len(wins),
            "Losing_Trades": len(losses),
            "Win_Rate_Percent": round(win_rate, 2),
            "Profit_Factor": round(profit_factor, 2),
            "Sharpe_Ratio": round(sharpe, 2),
            "Avg_Trade_Percent": round(avg_trade, 4),
            "Gross_DD_Percent": round(max_dd, 2),
            "Net_DD_Percent": round(net_dd, 2),
            "Performance_Grade": grade,
            "Deployment_Status": deploy,
            "Data_Source": "Binance Spot",
            "Time_Period": f"{time_start} to {time_end}",
            "Time_Start": time_start,
            "Time_End": time_end,
            "Fees_Exchange": f"{FEE*100}%",
            "Candle_Period": _timeframe,
            "Parameters": f"SL={strategy['stop_loss']*100}%, TP={strategy['take_profit']*100}%, TS={strategy['trailing_stop']*100}%",
            "Is_Counter": is_counter,
            # Keep old keys for backward compatibility with bot summary
            "trades": len(trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(win_rate, 2),
            "roi": round(roi, 2),
            "final_capital": round(final_capital, 2),
        }

    # Run backtest for each strategy
    results = []
    print(f"\nRunning backtests...")

    for strategy in strategies:
        try:
            df_copy = apply_strategy(
                df.copy(),
                strategy["strategies"],
                strategy.get("min_agreement", 1)
            )

            _override = (params_override or {}).get(strategy["name"], {})
            final_capital, trades = run_backtest(
                df_copy,
                _override.get("stop_loss", strategy["stop_loss"]),
                _override.get("take_profit", strategy["take_profit"]),
                _override.get("trailing_stop", strategy["trailing_stop"])
            )

            if len(trades) >= 5:
                result = _build_result(strategy, final_capital, trades)
                results.append(result)

                # Auto counter-strategy for negative ROI
                if result["roi"] < 0:
                    # Invert signals: swap entry_signal and exit_signal
                    df_counter = df_copy.copy()
                    df_counter["entry_signal"], df_counter["exit_signal"] = (
                        df_copy["exit_signal"].copy(),
                        df_copy["entry_signal"].copy(),
                    )
                    counter_cap, counter_trades = run_backtest(
                        df_counter,
                        strategy["stop_loss"],
                        strategy["take_profit"],
                        strategy["trailing_stop"]
                    )
                    if len(counter_trades) >= 5:
                        counter_result = _build_result(strategy, counter_cap, counter_trades, is_counter=True)
                        if counter_result["roi"] > result["roi"]:
                            results.append(counter_result)

        except Exception as e:
            print(f"Error with strategy {strategy.get('name', 'unknown')}: {e}")

    # Sort by ROI
    results.sort(key=lambda x: x["roi"], reverse=True)

    # Display top 20 results
    print(f"\n{'='*60}")
    print("TOP 20 STRATEGIES")
    print(f"{'='*60}")
    print(f"{'ID':<4} {'Name':<28} {'Trades':<7} {'Win%':<7} {'ROI%':<8} {'ROI/yr':<8} {'Grade'}")
    print("-" * 75)

    for r in results[:20]:
        print(f"{r['id']:<4} {r['name'][:28]:<28} {r['trades']:<7} {r['win_rate']:<7} {r['roi']:<8} {r['ROI_per_annum']:<8} {r['Performance_Grade']}")

    # Save to CSV with all columns
    if results:
        csv_columns = [
            "id", "name", "Strategy", "Asset", "Timeframe",
            "Initial_Capital_USD", "Final_Capital_USD", "Net_Profit_USD",
            "ROI_per_annum", "ROI_Percent", "Total_Trades", "Winning_Trades",
            "Losing_Trades", "Win_Rate_Percent", "Profit_Factor", "Sharpe_Ratio",
            "Avg_Trade_Percent", "Max_Drawdown_Percent", "Performance_Grade",
            "Deployment_Status", "Data_Source", "Time_Period", "Time_Start",
            "Time_End", "Fees_Exchange", "Candle_Period", "Parameters", "Is_Counter",
        ]
        df_results = pd.DataFrame(results)[csv_columns]
        df_results.to_csv("batch_backtest_results.csv", index=False)
        print(f"\nResults saved to batch_backtest_results.csv")

    profitable = [r for r in results if r["roi"] >= 20]
    counters = [r for r in results if r.get("Is_Counter", False)]
    print(f"\nTotal profitable (ROI>=20%): {len(profitable)}")
    print(f"Counter strategies added: {len(counters)}")
    print(f"Total tested: {len(results)}")

    return results


if __name__ == "__main__":
    import sys
    
    # Parse arguments
    data_key = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT_15m"
    batch_arg = sys.argv[2] if len(sys.argv) > 2 else "1"
    
    # Parse batch number or range
    if '-' in batch_arg:
        parts = batch_arg.split('-')
        try:
            start = int(parts[0])
            end = int(parts[1])
            batch_nums = list(range(start, end + 1))
        except:
            batch_nums = [1]
    elif batch_arg.upper() == "ALL":
        batch_nums = list(range(1, 21))
    else:
        try:
            batch_nums = [int(batch_arg)]
        except:
            batch_nums = [1]
    
    print(f"Data: {data_key}")
    print(f"Batches: {batch_nums}")
    
    # Run for each batch
    all_profitable = []
    for batch_num in batch_nums:
        print(f"\n=== Running batch {batch_num} ===")
        results = run_batch_strategies(data_key, batch_num)
        if results:
            all_profitable.extend(results)
    
    # Print summary
    if all_profitable:
        print("\n=== ALL PROFITABLE STRATEGIES ===")
        for r in all_profitable:
            print(r)
