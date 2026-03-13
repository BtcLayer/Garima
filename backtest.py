import ccxt
import pandas as pd
import numpy as np

exchange = ccxt.binance()

ASSETS = ["BTC/USDT","ETH/USDT","SOL/USDT","LINK/USDT","AVAX/USDT"]
TIMEFRAMES = ["15m","1h","4h"]

STRATEGIES = [
"EMA_Crossover","RSI_Oversold","MACD_Crossover","Bollinger_Breakout",
"Bollinger_MeanReversion","Volume_Spike","Momentum","Trend_Strength",
"Breakout_High","Breakout_Low","VWAP_Cross","ATR_Breakout",
"EMA_RSI_Filter","Golden_Cross","Death_Cross","Donchian_Channel",
"Stochastic_Oversold","Stochastic_Overbought","Supertrend","RSI_Trend"
]

INITIAL_CAPITAL = 10000
FEE = 0.001

results = []


def fetch_data(symbol,timeframe):

    ohlcv = exchange.fetch_ohlcv(symbol,timeframe,limit=1500)

    df = pd.DataFrame(
        ohlcv,
        columns=["time","open","high","low","close","volume"]
    )

    df["time"] = pd.to_datetime(df["time"],unit="ms")

    return df


def compute_indicators(df):

    df["ema12"] = df["close"].ewm(span=12).mean()
    df["ema26"] = df["close"].ewm(span=26).mean()

    df["ma20"] = df["close"].rolling(20).mean()
    df["std20"] = df["close"].rolling(20).std()

    df["upper_bb"] = df["ma20"] + (2*df["std20"])
    df["lower_bb"] = df["ma20"] - (2*df["std20"])

    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    df["rsi"] = 100 - (100/(1+rs))

    df["vol_avg"] = df["volume"].rolling(20).mean()

    df["high20"] = df["high"].rolling(20).max()
    df["low20"] = df["low"].rolling(20).min()

    return df


def generate_signal(df,strategy):

    df["signal"] = 0

    if strategy == "EMA_Crossover":
        df.loc[df["ema12"] > df["ema26"],"signal"] = 1

    elif strategy == "RSI_Oversold":
        df.loc[df["rsi"] < 30,"signal"] = 1

    elif strategy == "MACD_Crossover":
        macd = df["ema12"] - df["ema26"]
        signal = macd.ewm(span=9).mean()
        df.loc[macd > signal,"signal"] = 1

    elif strategy == "Bollinger_Breakout":
        df.loc[df["close"] > df["upper_bb"],"signal"] = 1

    elif strategy == "Bollinger_MeanReversion":
        df.loc[df["close"] < df["lower_bb"],"signal"] = 1

    elif strategy == "Volume_Spike":
        df.loc[df["volume"] > df["vol_avg"]*2,"signal"] = 1

    elif strategy == "Momentum":
        df.loc[df["close"] > df["close"].shift(10),"signal"] = 1

    elif strategy == "Trend_Strength":
        df.loc[df["ema12"] > df["ema26"],"signal"] = 1

    elif strategy == "Breakout_High":
        df.loc[df["close"] > df["high20"],"signal"] = 1

    elif strategy == "Breakout_Low":
        df.loc[df["close"] < df["low20"],"signal"] = 1

    elif strategy == "VWAP_Cross":
        vwap = (df["close"]*df["volume"]).cumsum()/df["volume"].cumsum()
        df.loc[df["close"] > vwap,"signal"] = 1

    elif strategy == "ATR_Breakout":
        tr = df["high"] - df["low"]
        atr = tr.rolling(14).mean()
        df.loc[(df["close"]-df["close"].shift(1)) > atr,"signal"] = 1

    elif strategy == "EMA_RSI_Filter":
        df.loc[(df["ema12"] > df["ema26"]) & (df["rsi"] < 40),"signal"] = 1

    elif strategy == "Golden_Cross":
        ma50 = df["close"].rolling(50).mean()
        ma200 = df["close"].rolling(200).mean()
        df.loc[ma50 > ma200,"signal"] = 1

    elif strategy == "Death_Cross":
        ma50 = df["close"].rolling(50).mean()
        ma200 = df["close"].rolling(200).mean()
        df.loc[ma50 < ma200,"signal"] = 1

    elif strategy == "Donchian_Channel":
        df.loc[df["close"] > df["high20"],"signal"] = 1

    elif strategy == "Stochastic_Oversold":
        low14 = df["low"].rolling(14).min()
        high14 = df["high"].rolling(14).max()
        stoch = (df["close"]-low14)/(high14-low14)*100
        df.loc[stoch < 20,"signal"] = 1

    elif strategy == "Stochastic_Overbought":
        low14 = df["low"].rolling(14).min()
        high14 = df["high"].rolling(14).max()
        stoch = (df["close"]-low14)/(high14-low14)*100
        df.loc[stoch > 80,"signal"] = 1

    elif strategy == "Supertrend":
        df.loc[df["ema12"] > df["ema26"],"signal"] = 1

    elif strategy == "RSI_Trend":
        df.loc[df["rsi"] > 50,"signal"] = 1

    return df


def run_backtest(df):

    capital = INITIAL_CAPITAL
    position = 0
    position_size = 0

    entry_price = 0
    trades = []

    for _,row in df.iterrows():

        if row["signal"] == 1 and position == 0:

            entry_price = row["close"]
            position_size = capital / entry_price
            entry_time = row["time"]
            position = 1

        elif row["signal"] == 0 and position == 1:

            exit_price = row["close"]

            capital_before = position_size * entry_price
            capital_after = position_size * exit_price * (1-FEE)

            pnl = capital_after - capital_before
            capital = capital_after

            trades.append({"entry":entry_time,"exit":row["time"],"pnl":pnl})

            position = 0

    return capital,trades


rank = 1

for strategy in STRATEGIES:
    for asset in ASSETS:
        for tf in TIMEFRAMES:

            df = fetch_data(asset,tf)

            df = compute_indicators(df)

            df = generate_signal(df,strategy)

            final_capital,trades = run_backtest(df)

            if len(trades) < 20:
                continue

            days = (df["time"].iloc[-1] - df["time"].iloc[0]).days

            roi_percent = ((final_capital-INITIAL_CAPITAL)/INITIAL_CAPITAL)*100
            roi_annum_percent = roi_percent*(365/days)
            roi_annum = INITIAL_CAPITAL*(roi_annum_percent/100)

            wins = sum(1 for t in trades if t["pnl"]>0)
            losses = len(trades)-wins

            win_rate = (wins/len(trades))*100

            results.append({

                "Rank":rank,
                "Strategy":strategy,
                "Asset":asset,
                "Timeframe":tf,
                "Initial_Capital_USD":INITIAL_CAPITAL,
                "Final_Capital_USD":round(final_capital,2),
                "Net_Profit_USD":round(final_capital-INITIAL_CAPITAL,2),
                "ROI/annum":round(roi_annum,2),
                "ROI_Percent":round(roi_percent,2),
                "ROI_per_annum%":round(roi_annum_percent,2),
                "Total_Trades":len(trades),
                "Winning_Trades":wins,
                "Losing_Trades":losses,
                "Win_Rate_Percent":round(win_rate,2),
                "Data_Source":"Binance",
                "Paramters: Candle period":tf
            })

            rank += 1


df_results = pd.DataFrame(results)

df_results = df_results.sort_values(by="ROI_per_annum%",ascending=False)

df_results["Rank"] = range(1,len(df_results)+1)

df_results.to_csv("multi_asset_backtest_results.csv",index=False)

print(df_results.head())