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
FEE = 0.0003  # 0.03% per side = 0.06% round-trip (matches TradingView 0.06%)


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

    # ── New indicators (batch 21+) ──────────────────────────────────

    # OBV (On Balance Volume)
    obv_sign = np.sign(df["close"].diff())
    df["obv"] = (obv_sign * df["volume"]).fillna(0).cumsum()
    df["obv_sma20"] = df["obv"].rolling(20).mean()

    # CCI (Commodity Channel Index, period=20)
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    tp_sma = typical_price.rolling(20).mean()
    tp_mad = typical_price.rolling(20).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    df["cci"] = (typical_price - tp_sma) / (0.015 * tp_mad)

    # Ichimoku Cloud
    df["tenkan_sen"] = (df["high"].rolling(9).max() + df["low"].rolling(9).min()) / 2
    df["kijun_sen"] = (df["high"].rolling(26).max() + df["low"].rolling(26).min()) / 2
    df["senkou_span_a"] = ((df["tenkan_sen"] + df["kijun_sen"]) / 2).shift(26)
    df["senkou_span_b"] = ((df["high"].rolling(52).max() + df["low"].rolling(52).min()) / 2).shift(26)

    # PSAR (Parabolic SAR) — simplified vectorised implementation
    psar = np.full(len(df), np.nan)
    bull = True
    psar[0] = df["low"].iloc[0]
    ep = df["high"].iloc[0]
    af = 0.02
    for i in range(1, len(df)):
        prev_psar = psar[i - 1] if not np.isnan(psar[i - 1]) else df["low"].iloc[i]
        if bull:
            psar[i] = prev_psar + af * (ep - prev_psar)
            psar[i] = min(psar[i], df["low"].iloc[i - 1])
            if i >= 2:
                psar[i] = min(psar[i], df["low"].iloc[i - 2])
            if df["low"].iloc[i] < psar[i]:
                bull = False
                psar[i] = ep
                ep = df["low"].iloc[i]
                af = 0.02
            else:
                if df["high"].iloc[i] > ep:
                    ep = df["high"].iloc[i]
                    af = min(af + 0.02, 0.2)
        else:
            psar[i] = prev_psar + af * (ep - prev_psar)
            psar[i] = max(psar[i], df["high"].iloc[i - 1])
            if i >= 2:
                psar[i] = max(psar[i], df["high"].iloc[i - 2])
            if df["high"].iloc[i] > psar[i]:
                bull = True
                psar[i] = ep
                ep = df["high"].iloc[i]
                af = 0.02
            else:
                if df["low"].iloc[i] < ep:
                    ep = df["low"].iloc[i]
                    af = min(af + 0.02, 0.2)
    df["psar"] = psar

    # MFI (Money Flow Index, period=14)
    tp = typical_price
    raw_money_flow = tp * df["volume"]
    pos_flow = raw_money_flow.where(tp > tp.shift(1), 0)
    neg_flow = raw_money_flow.where(tp < tp.shift(1), 0)
    pos_sum = pos_flow.rolling(14).sum()
    neg_sum = neg_flow.rolling(14).sum()
    mfr = pos_sum / neg_sum.replace(0, float("nan"))
    df["mfi"] = 100 - (100 / (1 + mfr))

    # Keltner Channel (EMA20 +/- 2*ATR10)
    df["keltner_mid"] = df["close"].ewm(span=20).mean()
    atr10 = tr.rolling(10).mean()
    df["keltner_upper"] = df["keltner_mid"] + 2 * atr10
    df["keltner_lower"] = df["keltner_mid"] - 2 * atr10

    # Williams %R (period=14)
    df["williams_r"] = ((high14 - df["close"]) / (high14 - low14)) * -100

    return df


# ══════════════════════════════════════════════════════════════════
# LONG ENTRY signals — CROSSOVER based (fire once, not every bar)
# ══════════════════════════════════════════════════════════════════

def get_signal_ema_cross(df):
    """EMA8 crosses ABOVE EMA21 (fires once on cross, not while above)"""
    above = df["ema8"] > df["ema21"]
    return (above & ~above.shift(1).fillna(False)).astype(int)

def get_signal_rsi_oversold(df):
    """RSI crosses above 30 from below (bounce from oversold)"""
    return ((df["rsi"] > 30) & (df["rsi"].shift(1) <= 30)).astype(int)

def get_signal_macd_cross(df):
    """MACD crosses above signal line"""
    return ((df["macd"] > df["macd_signal"]) & (df["macd"].shift(1) <= df["macd_signal"].shift(1))).astype(int)

def get_signal_bb_lower(df):
    """Price crosses above lower BB from below (bounce)"""
    return ((df["close"] > df["bb_lower"]) & (df["close"].shift(1) <= df["bb_lower"].shift(1))).astype(int)

def get_signal_bb_upper(df):
    """Price crosses above upper BB (breakout)"""
    return ((df["close"] > df["bb_upper"]) & (df["close"].shift(1) <= df["bb_upper"].shift(1))).astype(int)

def get_signal_volume(df):
    """Volume spike with bullish candle (already momentary)"""
    return ((df["vol_ratio"] > 1.5) & (df["close"] > df["close"].shift(1))).astype(int)

def get_signal_breakout(df):
    """Price crosses above 20-bar high (breakout)"""
    prev_high = df["high_20"].shift(1)
    return ((df["close"] > prev_high) & (df["close"].shift(1) <= prev_high.shift(1))).astype(int)

def get_signal_stochastic(df):
    """Stochastic crosses above 20 from below (oversold bounce)"""
    return ((df["stoch_k"] > 20) & (df["stoch_k"].shift(1) <= 20)).astype(int)

def get_signal_supertrend(df):
    """Price crosses ABOVE supertrend (fires once on cross)"""
    above = df["close"] > df["supertrend"]
    return (above & ~above.shift(1).fillna(False)).astype(int)

def get_signal_vwap(df):
    """Price crosses above VWAP"""
    above = df["close"] > df["vwap"]
    return (above & ~above.shift(1).fillna(False)).astype(int)

def get_signal_adx_trend(df):
    """ADX crosses above 25 (trend starts)"""
    return ((df["adx"] > 25) & (df["adx"].shift(1) <= 25)).astype(int)

def get_signal_trend_ma(df):
    """Price crosses above EMA50"""
    above = df["close"] > df["ema50"]
    return (above & ~above.shift(1).fillna(False)).astype(int)


# ── New signal functions (batch 21+) — CROSSOVER based ───────────

def get_signal_obv_rising(df):
    """OBV crosses above its 20-SMA"""
    above = df["obv"] > df["obv_sma20"]
    return (above & ~above.shift(1).fillna(False)).astype(int)

def get_signal_cci_oversold(df):
    """CCI crosses above -100 from below (bounce from oversold)"""
    return ((df["cci"] > -100) & (df["cci"].shift(1) <= -100)).astype(int)

def get_signal_ichimoku_bull(df):
    """Price crosses above Ichimoku cloud"""
    cloud_top = df[["senkou_span_a", "senkou_span_b"]].max(axis=1)
    above = df["close"] > cloud_top
    return (above & ~above.shift(1).fillna(False)).astype(int)

def get_signal_psar_bull(df):
    """Price crosses above PSAR (trend flip)"""
    above = df["close"] > df["psar"]
    return (above & ~above.shift(1).fillna(False)).astype(int)

def get_signal_mfi_oversold(df):
    """MFI crosses above 20 from below"""
    return ((df["mfi"] > 20) & (df["mfi"].shift(1) <= 20)).astype(int)

def get_signal_keltner_lower(df):
    """Price crosses above Keltner lower from below (bounce)"""
    return ((df["close"] > df["keltner_lower"]) & (df["close"].shift(1) <= df["keltner_lower"].shift(1))).astype(int)

def get_signal_williams_oversold(df):
    """Williams %R crosses above -80 from below"""
    return ((df["williams_r"] > -80) & (df["williams_r"].shift(1) <= -80)).astype(int)


# ══════════════════════════════════════════════════════════════════
# LONG EXIT signals — fire when condition REVERSES
# ══════════════════════════════════════════════════════════════════

LONG_EXIT_FUNCTIONS = {
    "EMA_Cross": lambda df: ((df["ema8"] < df["ema21"]) & (df["ema8"].shift(1) >= df["ema21"].shift(1))).astype(int),
    "RSI_Oversold": lambda df: ((df["rsi"] < 50) & (df["rsi"].shift(1) >= 50)).astype(int),
    "MACD_Cross": lambda df: ((df["macd"] < df["macd_signal"]) & (df["macd"].shift(1) >= df["macd_signal"].shift(1))).astype(int),
    "BB_Lower": lambda df: (df["close"] < df["bb_lower"]).astype(int),
    "BB_Upper": lambda df: (df["close"] < df["bb_mid"]).astype(int),
    "Volume_Spike": lambda df: pd.Series(0, index=df.index),  # no exit signal
    "Breakout_20": lambda df: (df["close"] < df["low_20"]).astype(int),
    "Stochastic": lambda df: ((df["stoch_k"] > 80) & (df["stoch_k"] < df["stoch_k"].shift(1))).astype(int),
    "Supertrend": lambda df: ((df["close"] < df["supertrend"]) & (df["close"].shift(1) >= df["supertrend"].shift(1))).astype(int),
    "VWAP": lambda df: ((df["close"] < df["vwap"]) & (df["close"].shift(1) >= df["vwap"].shift(1))).astype(int),
    "ADX_Trend": lambda df: ((df["adx"] < 20) & (df["adx"].shift(1) >= 20)).astype(int),
    "Trend_MA50": lambda df: ((df["close"] < df["ema50"]) & (df["close"].shift(1) >= df["ema50"].shift(1))).astype(int),
    "OBV_Rising": lambda df: ((df["obv"] < df["obv_sma20"]) & (df["obv"].shift(1) >= df["obv_sma20"].shift(1))).astype(int),
    "CCI_Oversold": lambda df: (df["cci"] > 100).astype(int),
    "Ichimoku_Bull": lambda df: (df["close"] < df[["senkou_span_a", "senkou_span_b"]].min(axis=1)).astype(int),
    "PSAR_Bull": lambda df: ((df["close"] < df["psar"]) & (df["close"].shift(1) >= df["psar"].shift(1))).astype(int),
    "MFI_Oversold": lambda df: (df["mfi"] > 80).astype(int),
    "Keltner_Lower": lambda df: (df["close"] > df["keltner_upper"]).astype(int),
    "Williams_Oversold": lambda df: ((df["williams_r"] > -20) & (df["williams_r"].shift(1) <= -20)).astype(int),
}

# ══════════════════════════════════════════════════════════════════
# SHORT ENTRY signals — CROSSOVER based (opposite of long)
# ══════════════════════════════════════════════════════════════════

SHORT_ENTRY_FUNCTIONS = {
    "EMA_Cross": lambda df: ((df["ema8"] < df["ema21"]) & (df["ema8"].shift(1) >= df["ema21"].shift(1))).astype(int),
    "RSI_Oversold": lambda df: ((df["rsi"] < 70) & (df["rsi"].shift(1) >= 70)).astype(int),
    "MACD_Cross": lambda df: ((df["macd"] < df["macd_signal"]) & (df["macd"].shift(1) >= df["macd_signal"].shift(1))).astype(int),
    "Supertrend": lambda df: ((df["close"] < df["supertrend"]) & (df["close"].shift(1) >= df["supertrend"].shift(1))).astype(int),
    "PSAR_Bull": lambda df: ((df["close"] < df["psar"]) & (df["close"].shift(1) >= df["psar"].shift(1))).astype(int),
    "Ichimoku_Bull": lambda df: (lambda cloud_bot: (df["close"] < cloud_bot) & (df["close"].shift(1) >= cloud_bot.shift(1)))(df[["senkou_span_a", "senkou_span_b"]].min(axis=1)).astype(int),
    "Trend_MA50": lambda df: ((df["close"] < df["ema50"]) & (df["close"].shift(1) >= df["ema50"].shift(1))).astype(int),
    "Stochastic": lambda df: ((df["stoch_k"] < 80) & (df["stoch_k"].shift(1) >= 80)).astype(int),
    "BB_Lower": lambda df: ((df["close"] < df["bb_lower"]) & (df["close"].shift(1) >= df["bb_lower"].shift(1))).astype(int),
    "Breakout_20": lambda df: ((df["close"] < df["low_20"]) & (df["close"].shift(1) >= df["low_20"].shift(1))).astype(int),
    "Volume_Spike": lambda df: ((df["vol_ratio"] > 1.5) & (df["close"] < df["close"].shift(1))).astype(int),
}


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
    # New signals (batch 21+)
    "OBV_Rising": get_signal_obv_rising,
    "CCI_Oversold": get_signal_cci_oversold,
    "Ichimoku_Bull": get_signal_ichimoku_bull,
    "PSAR_Bull": get_signal_psar_bull,
    "MFI_Oversold": get_signal_mfi_oversold,
    "Keltner_Lower": get_signal_keltner_lower,
    "Williams_Oversold": get_signal_williams_oversold,
}


# ── Short (bearish) signal functions ────────────────────────────────
def get_signal_ema_cross_short(df):
    """EMA8 crosses below EMA21 (bearish EMA cross)"""
    return ((df["ema8"] < df["ema21"]) & (df["ema8"].shift(1) >= df["ema21"].shift(1))).astype(int)

def get_signal_rsi_overbought(df):
    """RSI overbought and turning down"""
    return ((df["rsi"] > 70) & (df["rsi"] < df["rsi"].shift(1))).astype(int)

def get_signal_macd_cross_short(df):
    """MACD crosses below signal line (bearish)"""
    return ((df["macd"] < df["macd_signal"]) & (df["macd"].shift(1) >= df["macd_signal"].shift(1))).astype(int)

def get_signal_bb_upper_short(df):
    """Price above upper Bollinger Band (overbought, short signal)"""
    return (df["close"] > df["bb_upper"]).astype(int)

def get_signal_bb_lower_short(df):
    """Price below lower Bollinger Band (breakdown continuation)"""
    return (df["close"] < df["bb_lower"]).astype(int)

def get_signal_volume_short(df):
    """Volume spike with bearish candle"""
    return ((df["vol_ratio"] > 1.5) & (df["close"] < df["close"].shift(1))).astype(int)

def get_signal_breakdown(df):
    """Price breaks below 20-bar low (bearish breakout)"""
    return (df["close"] < df["low_20"]).astype(int)

def get_signal_stochastic_short(df):
    """Stochastic overbought cross down"""
    return ((df["stoch_k"] > 80) & (df["stoch_k"] < df["stoch_k"].shift(1))).astype(int)

def get_signal_supertrend_short(df):
    """Price below supertrend (bearish)"""
    return (df["close"] < df["supertrend"]).astype(int)

def get_signal_vwap_short(df):
    """Price below VWAP (bearish)"""
    return (df["close"] < df["vwap"]).astype(int)

def get_signal_adx_trend_short(df):
    """ADX strong trend (same for both sides — trend strength)"""
    return (df["adx"] > 25).astype(int)

def get_signal_trend_ma_short(df):
    """Price below EMA50 (bearish trend)"""
    return (df["close"] < df["ema50"]).astype(int)


# ── New short (bearish) signal functions (batch 21+) ─────────────

def get_signal_obv_falling(df):
    """OBV below its 20-period SMA (bearish volume trend)"""
    return (df["obv"] < df["obv_sma20"]).astype(int)

def get_signal_cci_overbought(df):
    """CCI overbought (> 100) and turning down"""
    return ((df["cci"] > 100) & (df["cci"] < df["cci"].shift(1))).astype(int)

def get_signal_ichimoku_bear(df):
    """Price below Ichimoku cloud"""
    return ((df["close"] < df["senkou_span_a"]) & (df["close"] < df["senkou_span_b"])).astype(int)

def get_signal_psar_bear(df):
    """Price below Parabolic SAR (downtrend)"""
    return (df["close"] < df["psar"]).astype(int)

def get_signal_mfi_overbought(df):
    """MFI overbought (> 80) and turning down"""
    return ((df["mfi"] > 80) & (df["mfi"] < df["mfi"].shift(1))).astype(int)

def get_signal_keltner_upper(df):
    """Price above Keltner upper channel"""
    return (df["close"] > df["keltner_upper"]).astype(int)

def get_signal_williams_overbought(df):
    """Williams %R overbought (> -20) and turning down"""
    return ((df["williams_r"] > -20) & (df["williams_r"] < df["williams_r"].shift(1))).astype(int)


# Maps each long signal name to its short (bearish) counterpart
SHORT_SIGNAL_FUNCTIONS = {
    "EMA_Cross": get_signal_ema_cross_short,
    "RSI_Oversold": get_signal_rsi_overbought,
    "MACD_Cross": get_signal_macd_cross_short,
    "BB_Lower": get_signal_bb_lower_short,
    "BB_Upper": get_signal_bb_upper_short,
    "Volume_Spike": get_signal_volume_short,
    "Breakout_20": get_signal_breakdown,
    "Stochastic": get_signal_stochastic_short,
    "Supertrend": get_signal_supertrend_short,
    "VWAP": get_signal_vwap_short,
    "ADX_Trend": get_signal_adx_trend_short,
    "Trend_MA50": get_signal_trend_ma_short,
    # New short signals (batch 21+)
    "OBV_Rising": get_signal_obv_falling,
    "CCI_Oversold": get_signal_cci_overbought,
    "Ichimoku_Bull": get_signal_ichimoku_bear,
    "PSAR_Bull": get_signal_psar_bear,
    "MFI_Oversold": get_signal_mfi_overbought,
    "Keltner_Lower": get_signal_keltner_upper,
    "Williams_Oversold": get_signal_williams_overbought,
}


def apply_strategy_short(df, strategy_combo, min_agreement=1):
    """Apply bearish (short) version of a strategy combination.

    Returns the same df with ``entry_signal`` and ``exit_signal`` columns
    populated for short entries.  Uses the mirrored signal functions defined
    in ``SHORT_SIGNAL_FUNCTIONS``.
    """
    signals = pd.DataFrame(index=df.index)

    for strat_name in strategy_combo:
        if strat_name in SHORT_SIGNAL_FUNCTIONS:
            signals[strat_name] = SHORT_SIGNAL_FUNCTIONS[strat_name](df)

    if len(signals.columns) > 0:
        df["combo_signal"] = signals.sum(axis=1)
        df["entry_signal"] = (df["combo_signal"] >= min_agreement).astype(int)
    else:
        df["entry_signal"] = 0

    df["exit_signal"] = (df["combo_signal"] < 1).astype(int)
    return df


def apply_strategy(df, strategy_combo, min_agreement=1):
    """Apply strategy with CROSSOVER entry + SIGNAL-BASED exit.

    Entry: fires when enough crossover signals fire on same bar.
    Exit: fires when ANY signal's exit condition triggers (reversal).
    """
    # Entry signals (crossovers — fire once)
    entry_signals = pd.DataFrame(index=df.index)
    for strat_name in strategy_combo:
        if strat_name in SIGNAL_FUNCTIONS:
            entry_signals[strat_name] = SIGNAL_FUNCTIONS[strat_name](df)

    if len(entry_signals.columns) > 0:
        df["combo_signal"] = entry_signals.sum(axis=1)
        df["entry_signal"] = (df["combo_signal"] >= min_agreement).astype(int)
    else:
        df["entry_signal"] = 0

    # Exit signals (signal reversal — adaptive, not fixed %)
    exit_signals = pd.DataFrame(index=df.index)
    for strat_name in strategy_combo:
        if strat_name in LONG_EXIT_FUNCTIONS:
            exit_signals[strat_name] = LONG_EXIT_FUNCTIONS[strat_name](df)

    if len(exit_signals.columns) > 0:
        # Exit when ANY exit signal fires
        df["exit_signal"] = (exit_signals.sum(axis=1) >= 1).astype(int)
    else:
        df["exit_signal"] = 0

    # Short entry signals
    short_entries = pd.DataFrame(index=df.index)
    for strat_name in strategy_combo:
        if strat_name in SHORT_ENTRY_FUNCTIONS:
            short_entries[strat_name] = SHORT_ENTRY_FUNCTIONS[strat_name](df)

    if len(short_entries.columns) > 0:
        df["short_entry_signal"] = (short_entries.sum(axis=1) >= min_agreement).astype(int)
    else:
        df["short_entry_signal"] = 0

    # Short exit = long entry signal (flip)
    df["short_exit_signal"] = df["entry_signal"]

    return df


def run_backtest(df, stop_loss=0, take_profit=0, trailing_stop=0, use_tight=False,
                 side="both", slippage_pct=0.0):
    """Run backtest matching TradingView execution — long+short with signal-based exits.

    Key behaviors (matching TV):
    1. Entry at NEXT bar open
    2. Position sizing: 100% of current equity (compounds)
    3. Signal-based exits (adaptive) — SL/TP optional backup
    4. Long+Short with instant position flipping
    5. Fees: 0.1% commission (matching the working strategies)
    """
    if use_tight:
        stop_loss = stop_loss / 2 if stop_loss else 0
        take_profit = take_profit / 2 if take_profit else 0
        trailing_stop = trailing_stop / 2 if trailing_stop else 0

    do_long = side in ("long", "both")
    do_short = side in ("short", "both")
    fee = 0.001  # 0.1% per trade (matching working strategies)

    capital = INITIAL_CAPITAL
    position = 0     # 0=flat, 1=long, -1=short
    position_size = 0
    entry_price = 0
    peak_price = 0
    trades = []
    pending_entry = None  # None, "long", or "short"

    rows = list(df.iterrows())
    for i, (idx, row) in enumerate(rows):
        current_price = row["close"]
        high = row.get("high", current_price)
        low = row.get("low", current_price)
        bar_open = row.get("open", current_price)

        # Execute pending entry at this bar's open
        if pending_entry and position == 0:
            if pending_entry == "long":
                entry_price = bar_open * (1 + fee)
                position = 1
            elif pending_entry == "short":
                entry_price = bar_open * (1 - fee)
                position = -1
            position_size = capital / entry_price
            peak_price = entry_price
            pending_entry = None

        # ── Check for exit + new entry (position flipping) ──
        if position != 0:
            exit_price = None
            exit_reason = None

            if position == 1:  # LONG
                if high > peak_price:
                    peak_price = high

                # Signal-based exit (primary — like working strategies)
                if row.get("exit_signal", 0) == 1:
                    exit_price = current_price * (1 - fee)
                    exit_reason = "SIGNAL"
                # Backup: SL if set
                elif stop_loss > 0 and low <= entry_price * (1 - stop_loss):
                    exit_price = entry_price * (1 - stop_loss) * (1 - fee)
                    exit_reason = "SL"
                # Backup: TP if set
                elif take_profit > 0 and high >= entry_price * (1 + take_profit):
                    exit_price = entry_price * (1 + take_profit) * (1 - fee)
                    exit_reason = "TP"
                # Instant flip: short entry while long → close long, open short
                elif do_short and row.get("short_entry_signal", 0) == 1:
                    exit_price = current_price * (1 - fee)
                    exit_reason = "FLIP_SHORT"

                if exit_price:
                    pnl = (exit_price - entry_price) * position_size
                    capital += pnl
                    trades.append({
                        "entry": round(entry_price, 6),
                        "exit": round(exit_price, 6),
                        "pnl": round(pnl, 2),
                        "return_pct": round((exit_price / entry_price - 1) * 100, 3),
                        "side": "long",
                        "exit_reason": exit_reason,
                        "exit_date": str(row.get("timestamp", ""))[:19],
                        "capital_after": round(capital, 2),
                    })
                    position = 0
                    position_size = 0

                    # If flipping to short, set pending
                    if exit_reason == "FLIP_SHORT":
                        pending_entry = "short"

            elif position == -1:  # SHORT
                if low < peak_price:
                    peak_price = low

                if row.get("short_exit_signal", 0) == 1:
                    exit_price = current_price * (1 + fee)
                    exit_reason = "SIGNAL"
                elif stop_loss > 0 and high >= entry_price * (1 + stop_loss):
                    exit_price = entry_price * (1 + stop_loss) * (1 + fee)
                    exit_reason = "SL"
                elif take_profit > 0 and low <= entry_price * (1 - take_profit):
                    exit_price = entry_price * (1 - take_profit) * (1 + fee)
                    exit_reason = "TP"
                elif do_long and row.get("entry_signal", 0) == 1:
                    exit_price = current_price * (1 + fee)
                    exit_reason = "FLIP_LONG"

                if exit_price:
                    pnl = (entry_price - exit_price) * position_size
                    capital += pnl
                    trades.append({
                        "entry": round(entry_price, 6),
                        "exit": round(exit_price, 6),
                        "pnl": round(pnl, 2),
                        "return_pct": round((entry_price / exit_price - 1) * 100, 3),
                        "side": "short",
                        "exit_reason": exit_reason,
                        "exit_date": str(row.get("timestamp", ""))[:19],
                        "capital_after": round(capital, 2),
                    })
                    position = 0
                    position_size = 0

                    if exit_reason == "FLIP_LONG":
                        pending_entry = "long"

        # ── Check for new entry (only if flat) ──
        if position == 0 and pending_entry is None:
            if do_long and row.get("entry_signal", 0) == 1:
                pending_entry = "long"
            elif do_short and row.get("short_entry_signal", 0) == 1:
                pending_entry = "short"

    return capital, trades


# ══════════════════════════════════════════════════════════════════
# TOURNAMENT-STYLE BACKTESTER — matches strategy_tournament.py exactly
# Signal × bar_return model (no individual trade tracking)
# ══════════════════════════════════════════════════════════════════

def calculate_adx(df, n=14):
    """ADX calculation matching tournament's my_strategies.py."""
    h, l, c = df["high"], df["low"], df["close"]
    tr = np.maximum(h - l, np.maximum(abs(h - c.shift(1)), abs(l - c.shift(1))))
    atr = tr.rolling(n).mean()
    upmove = (h - h.shift(1)).clip(lower=0)
    downmove = (l.shift(1) - l).clip(lower=0)
    plus_di = 100 * (upmove.rolling(n).mean() / atr)
    minus_di = 100 * (downmove.rolling(n).mean() / atr)
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    return dx.rolling(n).mean().fillna(0)


def tournament_apply_strategy(df, strategy_name, mult=2.5, length=14):
    """Apply strategy matching tournament's my_strategies.py — returns signal array (1/-1/0)."""
    close, high, low = df["close"], df["high"], df["low"]
    name_upper = strategy_name.upper()
    ema_200 = close.rolling(200).mean()
    adx = calculate_adx(df, n=int(length))
    strong_trend = adx > 18

    # Category 1: Trend Following
    if any(k in name_upper for k in ["SUPERTREND", "ATR", "SMA", "EMA", "RIBBON", "CROSS",
                                      "AGGRESSIVE", "KELTNER"]):
        atr_val = (high - low).rolling(int(length)).mean()
        adj_mult = mult * 1.1 if "RIBBON" in name_upper else mult
        upper = (high + low) / 2 + (adj_mult * atr_val)
        lower = (high + low) / 2 - (adj_mult * atr_val)
        raw = np.where(close > upper.shift(1), 1, np.where(close < lower.shift(1), -1, 0))
        return np.where((raw == 1) & (close > ema_200), 1, np.where((raw == -1) & (close < ema_200), -1, 0))

    # Category 2: Mean Reversion / ML
    elif any(k in name_upper for k in ["SQUEEZE", "REVERSION", "LORENTZIAN", "ML", "MATRIX"]):
        basis = close.rolling(int(length)).mean()
        dev = mult * close.rolling(int(length)).std()
        return np.where(close < basis - dev, 1, np.where(close > basis + dev, -1, 0))

    # Category 3: Volume & Momentum
    elif any(k in name_upper for k in ["OBV", "WAVETREND", "MACD", "MOMENTUM", "FLOW"]):
        obv = (np.sign(close.diff()) * df["volume"]).fillna(0).cumsum()
        obv_ema = obv.rolling(int(length)).mean()
        raw = np.where(obv > obv_ema, 1, -1)
        return np.where(strong_trend, raw, 0)

    # Category 4: SMC & Liquidity
    elif any(k in name_upper for k in ["SMC", "LIQUIDITY", "INSTITUTIONAL", "HYBRID"]):
        lookback = int(length)
        raw = np.where(close > close.shift(lookback), 1, np.where(close < close.shift(lookback), -1, 0))
        return np.where(strong_trend, raw, 0)

    # Category 5: Ichimoku
    elif "ICHIMOKU" in name_upper:
        tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
        kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
        senkou_a = ((tenkan + kijun) / 2).shift(26)
        senkou_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
        cloud_top = pd.concat([senkou_a, senkou_b], axis=1).max(axis=1)
        cloud_bot = pd.concat([senkou_a, senkou_b], axis=1).min(axis=1)
        raw = np.where((close > cloud_top) & (tenkan > kijun), 1,
                       np.where((close < cloud_bot) & (tenkan < kijun), -1, 0))
        return raw

    # Fallback: EMA crossover
    else:
        fast = close.rolling(int(length)).mean()
        slow = close.rolling(int(length * 2.1)).mean()
        return np.where(fast > slow, 1, -1)


def run_tournament_backtest(df, strategy_name, mult=2.5, length=14,
                            sl=0.01, tp=0.03, max_daily_loss=-0.03,
                            cooldown_trigger=3, cooldown_bars=4,
                            use_adx=True, use_atr=True, oos_split=0.0):
    """Run backtest matching tournament's run_test() exactly.

    Returns: (daily_roi, gross_dd, net_dd, win_rate, sharpe, total_trades, metrics_dict)
    If oos_split > 0, returns (is_metrics, oos_metrics).
    """
    d = df.copy()
    d["pct"] = d["close"].pct_change()

    # Apply strategy signal
    d["sig"] = tournament_apply_strategy(d, strategy_name, mult, length)

    # Filter 1: ADX > 20
    if use_adx:
        adx = calculate_adx(d, n=int(length))
        d["sig"] = np.where(adx > 20, d["sig"], 0)

    # Filter 2: ATR volatility
    if use_atr:
        atr_14 = (d["high"] - d["low"]).rolling(14).mean()
        atr_ma = atr_14.rolling(100).mean()
        d["sig"] = np.where(atr_14 > 2 * atr_ma, 0, d["sig"])

    # Calculate returns: signal × bar_return, clipped to SL/TP
    d["daily_ret"] = d["sig"].shift(1) * d["pct"]
    d["daily_ret"] = d["daily_ret"].clip(lower=-sl, upper=tp)

    # Filter 3: Consecutive loss cooldown
    rets = d["daily_ret"].values.copy()
    consec_losses = 0
    skip_remaining = 0
    for i in range(len(rets)):
        if skip_remaining > 0:
            rets[i] = 0.0
            skip_remaining -= 1
            continue
        if rets[i] < 0:
            consec_losses += 1
            if consec_losses >= cooldown_trigger:
                skip_remaining = cooldown_bars
                consec_losses = 0
        else:
            consec_losses = 0
    d["daily_ret"] = rets

    # Filter 4: Daily circuit breaker
    if "timestamp" in d.columns:
        d["_date"] = pd.to_datetime(d["timestamp"]).dt.date
        d["_daily_cum"] = d.groupby("_date")["daily_ret"].cumsum()
        d.loc[d["_daily_cum"] < max_daily_loss, "daily_ret"] = 0.0
        d.drop(columns=["_date", "_daily_cum"], inplace=True)

    def calc_metrics(series):
        total_return = series.sum() * 100
        total_days = max(len(series) / 96, 1)  # 96 bars per day on 15m
        daily_roi = total_return / total_days

        # Gross DD (compounding)
        cum = (1 + series.fillna(0)).cumprod()
        gdd_series = ((cum - cum.cummax()) / cum.cummax()) * 100
        gross_dd = gdd_series.min()

        # Net DD (fixed sizing)
        cum_sum = series.fillna(0).cumsum() * 100
        net_dd = (cum_sum - cum_sum.cummax()).min()

        # Win rate
        trades = series[series != 0]
        total_trades = len(trades)
        winning = len(trades[trades > 0])
        win_rate = round(winning / total_trades * 100, 1) if total_trades > 0 else 0

        # Sharpe
        mean_r = series.mean()
        std_r = series.std()
        sharpe = round((mean_r / std_r) * np.sqrt(35040), 2) if std_r > 0 else 0

        # PF
        gross_win = trades[trades > 0].sum()
        gross_loss = abs(trades[trades < 0].sum())
        pf = round(gross_win / gross_loss, 2) if gross_loss > 0 else 0

        return {
            "daily_roi": round(daily_roi, 4),
            "gross_dd": round(gross_dd, 2),
            "net_dd": round(net_dd, 2),
            "win_rate": win_rate,
            "sharpe": sharpe,
            "pf": pf,
            "total_trades": total_trades,
            "total_bars": len(series),
        }

    if oos_split > 0:
        split = int(len(d) * (1 - oos_split))
        is_metrics = calc_metrics(d["daily_ret"].iloc[:split])
        oos_metrics = calc_metrics(d["daily_ret"].iloc[split:])
        return is_metrics, oos_metrics
    else:
        return calc_metrics(d["daily_ret"])


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
