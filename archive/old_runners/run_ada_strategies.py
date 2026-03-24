"""
Run all strategies on ADAUSDT - All Timeframes (15m, 1h, 4h)
"""

import pandas as pd
import numpy as np
import os
from strategies import get_all_strategies
from datetime import datetime

DATA_DIR = "storage/historical_data"
INITIAL_CAPITAL = 10000
FEE = 0.0001

DATA_FILES = {
    "15m": "ADAUSDT_15m_2025-03-17_2026-03-17.parquet",
    "1h":  "ADAUSDT_1h_2025-03-17_2026-03-17.parquet",
    "4h":  "ADAUSDT_4h_2025-03-17_2026-03-17.parquet",
}

ASSET = "ADAUSDT"
OUTPUT_CSV = "ada_all_results.csv"

# ── copy helpers from run_btc_strategies.py ──────────────────────────────────

def load_data(timeframe):
    filepath = os.path.join(DATA_DIR, DATA_FILES.get(timeframe, ""))
    if not os.path.exists(filepath):
        return None, None, None
    df = pd.read_parquet(filepath)
    time_col = "timestamp" if "timestamp" in df.columns else "open_time"
    return df, df[time_col].min(), df[time_col].max()

def calculate_indicators(df):
    df = df.copy()
    df["ema8"]   = df["close"].ewm(span=8).mean()
    df["ema21"]  = df["close"].ewm(span=21).mean()
    df["ema50"]  = df["close"].ewm(span=50).mean()
    df["sma20"]  = df["close"].rolling(20).mean()
    df["bb_mid"] = df["sma20"]
    df["bb_std"] = df["close"].rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2 * df["bb_std"]
    df["bb_lower"] = df["bb_mid"] - 2 * df["bb_std"]
    delta = df["close"].diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    rs    = gain.rolling(14).mean() / loss.rolling(14).mean()
    df["rsi"]          = 100 - (100 / (1 + rs))
    df["macd"]         = df["ema21"] - df["ema50"]
    df["macd_signal"]  = df["macd"].ewm(span=9).mean()
    low14 = df["low"].rolling(14).min()
    high14 = df["high"].rolling(14).max()
    df["stoch_k"]  = 100 * (df["close"] - low14) / (high14 - low14)
    df["vol_ma"]   = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / df["vol_ma"]
    high_low   = df["high"] - df["low"]
    high_close = abs(df["high"] - df["close"].shift())
    low_close  = abs(df["low"]  - df["close"].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"]        = tr.rolling(14).mean()
    df["vwap"]       = (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum()
    hl_avg           = (df["high"] + df["low"]) / 2
    df["supertrend"] = hl_avg - 3 * df["atr"]
    plus_dm  = df["high"].diff().clip(lower=0)
    minus_dm = (-df["low"].diff()).clip(lower=0)
    plus_di  = 100 * plus_dm.rolling(14).mean() / df["atr"]
    minus_di = 100 * minus_dm.rolling(14).mean() / df["atr"]
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    df["adx"]    = dx.rolling(14).mean()
    df["high_20"] = df["high"].rolling(20).max()
    return df

SIGNALS = {
    "EMA_Cross":    lambda df: (df["ema8"] > df["ema21"]).astype(int),
    "RSI_Oversold": lambda df: ((df["rsi"] < 30) & (df["rsi"] > df["rsi"].shift(1))).astype(int),
    "MACD_Cross":   lambda df: ((df["macd"] > df["macd_signal"]) & (df["macd"].shift(1) <= df["macd_signal"].shift(1))).astype(int),
    "BB_Lower":     lambda df: (df["close"] < df["bb_lower"]).astype(int),
    "Volume_Spike": lambda df: ((df["vol_ratio"] > 1.5) & (df["close"] > df["close"].shift(1))).astype(int),
    "Breakout_20":  lambda df: (df["close"] > df["high_20"]).astype(int),
    "Stochastic":   lambda df: ((df["stoch_k"] < 20) & (df["stoch_k"] > df["stoch_k"].shift(1))).astype(int),
    "Supertrend":   lambda df: (df["close"] > df["supertrend"]).astype(int),
    "VWAP":         lambda df: (df["close"] > df["vwap"]).astype(int),
    "ADX_Trend":    lambda df: (df["adx"] > 25).astype(int),
    "Trend_MA50":   lambda df: (df["close"] > df["ema50"]).astype(int),
}

def apply_strategy(df, strategy_combo, min_agreement=1):
    signals = pd.DataFrame(index=df.index)
    for s in strategy_combo:
        if s in SIGNALS:
            signals[s] = SIGNALS[s](df)
    df["combo_signal"] = signals.sum(axis=1) if len(signals.columns) > 0 else 0
    df["entry_signal"] = (df["combo_signal"] >= min_agreement).astype(int)
    return df

def run_backtest_detailed(df, sl, tp, ts):
    capital = INITIAL_CAPITAL
    position = 0
    position_size = entry_price = 0
    trades = []
    peak_price = 0

    for _, row in df.iterrows():
        if row["entry_signal"] == 1 and position == 0:
            entry_price   = row["close"]
            position_size = capital * 0.95 / entry_price
            position = 1
            peak_price = entry_price
        elif position == 1:
            current_price = row["close"]
            if current_price > peak_price:
                peak_price = current_price
            should_exit = (
                current_price <= entry_price * (1 - sl) or
                current_price >= entry_price * (1 + tp) or
                current_price <= peak_price * (1 - ts)
            )
            if should_exit:
                pnl = position_size * current_price * (1 - FEE) - position_size * entry_price * (1 + FEE)
                pnl_pct = (current_price - entry_price) / entry_price * 100
                capital += pnl
                trades.append({"pnl": pnl, "pnl_percent": pnl_pct, "capital": capital})
                position = 0

    total_trades   = len(trades)
    winning_trades = sum(1 for t in trades if t["pnl"] > 0)
    losing_trades  = total_trades - winning_trades
    win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
    gross_profit = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gross_loss   = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0)
    avg_trade_pct = np.mean([t["pnl_percent"] for t in trades]) if trades else 0
    sharpe = np.std([t["pnl_percent"] for t in trades]) if len(trades) > 1 else 0
    roi = (capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

    equity = [INITIAL_CAPITAL] + [t["capital"] for t in trades]
    peak = INITIAL_CAPITAL
    max_dd = 0
    for eq in equity:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100 if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd

    return {
        "final_capital": capital, "net_profit": capital - INITIAL_CAPITAL,
        "roi": round(roi, 2), "roi_annum": round(roi, 2),
        "total_trades": total_trades, "winning_trades": winning_trades,
        "losing_trades": losing_trades, "win_rate": win_rate,
        "profit_factor": profit_factor, "sharpe_ratio": sharpe,
        "avg_trade_percent": avg_trade_pct, "max_drawdown": max_dd,
    }

def get_performance_grade(roi, win_rate, sharpe):
    score = (2 if roi > 50 else 1 if roi > 20 else 0) + \
            (2 if win_rate > 50 else 1 if win_rate > 40 else 0) + \
            (2 if sharpe > 1.5 else 1 if sharpe > 1 else 0)
    return ["D","D","C","B","B+","A","A+"][min(score, 6)]

def run_all():
    results  = []
    strategies = get_all_strategies()
    timeframes = ["15m", "1h", "4h"]

    print("=" * 60)
    print(f"{ASSET} - Testing ALL Strategies on ALL Timeframes")
    print("=" * 60)

    for tf in timeframes:
        print(f"\n--- Timeframe: {tf} ---")
        df, time_start, time_end = load_data(tf)
        if df is None:
            print(f"  No data for {tf} — run fetch_new_assets.py first")
            continue

        period_days = (time_end - time_start).total_seconds() / 86400 if hasattr(time_start, "timestamp") else 365
        ts_str = str(time_start)[:10]
        te_str = str(time_end)[:10]
        df = calculate_indicators(df)

        for strategy in strategies:
            try:
                df_copy  = apply_strategy(df.copy(), strategy["strategies"], strategy.get("min_agreement", 1))
                metrics  = run_backtest_detailed(df_copy, strategy["stop_loss"], strategy["take_profit"], strategy["trailing_stop"])
                if metrics["total_trades"] < 5:
                    continue
                grade = get_performance_grade(metrics["roi"], metrics["win_rate"], metrics["sharpe_ratio"])
                results.append({
                    "Rank": 0, "Strategy": strategy["name"], "Asset": ASSET, "Timeframe": tf,
                    "Initial_Capital_USD": INITIAL_CAPITAL, "Final_Capital_USD": round(metrics["final_capital"], 2),
                    "Net_Profit_USD": round(metrics["net_profit"], 2), "roi": round(metrics["roi"], 2),
                    "ROI/annum": round(metrics["roi_annum"], 2), "ROI_per_annum_Percent": round(metrics["roi_annum"], 2),
                    "Total_Trades": metrics["total_trades"], "Winning_Trades": metrics["winning_trades"],
                    "Losing_Trades": metrics["losing_trades"], "Win_Rate_Percent": round(metrics["win_rate"], 2),
                    "Profit_Factor": round(metrics["profit_factor"], 2), "Sharpe_Ratio": round(metrics["sharpe_ratio"], 2),
                    "Avg_Trade_Percent": round(metrics["avg_trade_percent"], 2), "Max_Drawdown": round(metrics["max_drawdown"], 2),
                    "Performance_Grade": grade, "Deployment_Status": "Active" if metrics["roi"] > 0 else "Inactive",
                    "Data_Source": "Historical_Parquet", "Time_period_checked": f"{int(period_days)} days",
                    "Time_start": ts_str, "time_end": te_str,
                    "fees_exchnage": f"Entry:{FEE*100}% + Exit:{FEE*100}%",
                    "Parameters": f"SL:{strategy['stop_loss']}, TP:{strategy['take_profit']}, TS:{strategy['trailing_stop']}",
                    "Candle_Period": tf,
                })
                if metrics["roi"] > 0:
                    print(f"  ✅ {strategy['name']} ({tf}): ROI={metrics['roi']:.2f}%")
            except Exception as e:
                print(f"  Error in {strategy['name']}: {e}")

    if results:
        df_out = pd.DataFrame(results).sort_values("roi", ascending=False).reset_index(drop=True)
        df_out["Rank"] = range(1, len(df_out) + 1)
        cols = ["Rank","Strategy","Asset","Timeframe","Initial_Capital_USD","Final_Capital_USD",
                "Net_Profit_USD","roi","ROI/annum","ROI_per_annum_Percent","Total_Trades",
                "Winning_Trades","Losing_Trades","Win_Rate_Percent","Profit_Factor","Sharpe_Ratio",
                "Avg_Trade_Percent","Max_Drawdown","Performance_Grade","Deployment_Status",
                "Data_Source","Time_period_checked","Time_start","time_end","fees_exchnage",
                "Parameters","Candle_Period"]
        df_out[cols].to_csv(OUTPUT_CSV, index=False)
        profitable = df_out[df_out["roi"] > 0]
        print(f"\n{'='*60}")
        print(f"PROFITABLE STRATEGIES: {len(profitable)} / {len(df_out)}")
        print("=" * 60)
        print(profitable.head(15).to_string())
    else:
        print("\n⚠️  No results. Check data files exist.")
    return results

if __name__ == "__main__":
    run_all()
