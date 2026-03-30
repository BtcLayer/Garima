"""
Parameter Sweep Engine for indicator tuning.

Sweeps EMA periods, RSI levels, BB/ATR params, SL/TP/TS combos
across top signal combos and multiple assets.  Saves results to CSV.

Usage:
    .tbenv/Scripts/python scripts/param_sweep_engine.py
"""

import os
import sys
import time
import itertools
from datetime import datetime

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
INITIAL = 10_000
FEE = 0.0003  # 0.03 % per side  =  0.06 % round-trip (matches TV)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "storage", "historical_data")
DATA_DIR = os.path.normpath(DATA_DIR)

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
REPORTS_DIR = os.path.normpath(REPORTS_DIR)

# Assets to test (4h timeframe)
ASSETS = ["ETHUSDT", "BNBUSDT", "BTCUSDT", "ADAUSDT", "SOLUSDT", "LINKUSDT"]
TIMEFRAME = "4h"

# ---------------------------------------------------------------------------
# Default indicator parameters
# ---------------------------------------------------------------------------
DEFAULT_PARAMS = {
    "ema_fast": 8,
    "ema_slow": 21,
    "ema_trend": 50,
    "rsi_period": 14,
    "rsi_oversold": 30,
    "bb_period": 20,
    "bb_std": 2.0,
    "atr_period": 14,
    "atr_mult": 3.0,
    "adx_threshold": 25,
    "vol_mult": 1.5,
    "stoch_period": 14,
    "psar_af": 0.02,
    "psar_max": 0.2,
    "ichi_tenkan": 9,
    "ichi_kijun": 26,
    "ichi_senkou": 52,
}

# Sweep ranges per parameter
SWEEP_RANGES = {
    "ema_fast": [5, 8, 10, 12],
    "ema_slow": [15, 21, 26, 30],
    "ema_trend": [50, 100, 200],
    "rsi_period": [7, 10, 14, 21],
    "rsi_oversold": [20, 25, 30, 35],
    "bb_period": [15, 20, 25],
    "bb_std": [1.5, 2.0, 2.5],
    "atr_period": [10, 14, 20],
    "atr_mult": [2.0, 2.5, 3.0, 3.5],
    "adx_threshold": [20, 25, 30, 35],
    "vol_mult": [1.2, 1.5, 2.0],
    "stoch_period": [9, 14, 21],
    "psar_af": [0.01, 0.02, 0.03],
    "psar_max": [0.1, 0.2, 0.3],
    "ichi_tenkan": [7, 9, 12],
    "ichi_kijun": [22, 26, 30],
    "ichi_senkou": [44, 52, 60],
}

# SL / TP / TS sweep values
SL_RANGE = [0.005, 0.01, 0.015, 0.02]
TP_RANGE = [0.015, 0.025, 0.035, 0.05]
TS_RANGE = [0.002, 0.004, 0.006, 0.008]

# Top signal combos to sweep
TOP_COMBOS = [
    {
        "name": "PSAR_Vol_EMA_ST_Trend",
        "signals": ["PSAR_Bull", "Volume_Spike", "EMA_Cross", "Supertrend", "Trend_MA50"],
        "min_agreement": 4,
    },
    {
        "name": "Ichi_OBV_Vol_PSAR_Trend",
        "signals": ["Ichimoku_Bull", "OBV_Rising", "Volume_Spike", "PSAR_Bull", "Trend_MA50"],
        "min_agreement": 4,
    },
    {
        "name": "PSAR_EMA_ST_ADX_Trend_OBV",
        "signals": ["PSAR_Bull", "EMA_Cross", "Supertrend", "ADX_Trend", "Trend_MA50", "OBV_Rising"],
        "min_agreement": 5,
    },
]

# Which indicator params each signal actually depends on, so we only sweep
# the params that matter for a given combo.
SIGNAL_PARAM_DEPS = {
    "EMA_Cross":      ["ema_fast", "ema_slow"],
    "Trend_MA50":     ["ema_trend"],
    "Supertrend":     ["atr_period", "atr_mult"],
    "PSAR_Bull":      ["psar_af", "psar_max"],
    "Volume_Spike":   ["vol_mult"],
    "ADX_Trend":      ["atr_period", "adx_threshold"],
    "OBV_Rising":     [],           # no tuneable params
    "Ichimoku_Bull":  ["ichi_tenkan", "ichi_kijun", "ichi_senkou"],
    "Stochastic":     ["stoch_period"],
    "RSI_Oversold":   ["rsi_period", "rsi_oversold"],
    "BB_Lower":       ["bb_period", "bb_std"],
    "MACD_Cross":     ["ema_slow", "ema_trend"],
}

# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------
_DATA_CACHE: dict[str, pd.DataFrame] = {}


def _find_data_file(symbol: str, tf: str) -> str | None:
    prefix = f"{symbol}_{tf}_"
    for f in sorted(os.listdir(DATA_DIR), reverse=True):
        if f.startswith(prefix) and f.endswith(".parquet"):
            return os.path.join(DATA_DIR, f)
    return None


def load_data(symbol: str, tf: str = TIMEFRAME) -> pd.DataFrame | None:
    key = f"{symbol}_{tf}"
    if key in _DATA_CACHE:
        return _DATA_CACHE[key]
    path = _find_data_file(symbol, tf)
    if path is None:
        print(f"  [WARN] No data file for {key}")
        return None
    df = pd.read_parquet(path)
    _DATA_CACHE[key] = df
    print(f"  Loaded {key}: {len(df):,} candles")
    return df


# ---------------------------------------------------------------------------
# Parameterised indicator calculation
# ---------------------------------------------------------------------------
def _compute_psar(high: np.ndarray, low: np.ndarray, af_step: float, af_max: float) -> np.ndarray:
    """Vectorised-loop Parabolic SAR."""
    n = len(high)
    psar = np.empty(n)
    psar[0] = low[0]
    bull = True
    ep = high[0]
    af = af_step
    for i in range(1, n):
        prev = psar[i - 1]
        if bull:
            psar[i] = prev + af * (ep - prev)
            psar[i] = min(psar[i], low[i - 1])
            if i >= 2:
                psar[i] = min(psar[i], low[i - 2])
            if low[i] < psar[i]:
                bull = False
                psar[i] = ep
                ep = low[i]
                af = af_step
            else:
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + af_step, af_max)
        else:
            psar[i] = prev + af * (ep - prev)
            psar[i] = max(psar[i], high[i - 1])
            if i >= 2:
                psar[i] = max(psar[i], high[i - 2])
            if high[i] > psar[i]:
                bull = True
                psar[i] = ep
                ep = high[i]
                af = af_step
            else:
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + af_step, af_max)
    return psar


def calculate_indicators_custom(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Calculate all technical indicators using *params* (not hardcoded)."""
    p = {**DEFAULT_PARAMS, **params}
    df = df.copy()

    # EMAs
    df["ema_fast"] = df["close"].ewm(span=p["ema_fast"]).mean()
    df["ema_slow"] = df["close"].ewm(span=p["ema_slow"]).mean()
    df["ema_trend"] = df["close"].ewm(span=p["ema_trend"]).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()

    # SMAs
    df["sma20"] = df["close"].rolling(p["bb_period"]).mean()

    # Bollinger Bands
    bb_std_val = df["close"].rolling(p["bb_period"]).std()
    df["bb_upper"] = df["sma20"] + p["bb_std"] * bb_std_val
    df["bb_lower"] = df["sma20"] - p["bb_std"] * bb_std_val

    # RSI
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(p["rsi_period"]).mean()
    avg_loss = loss.rolling(p["rsi_period"]).mean()
    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))

    # MACD (uses ema_slow & ema_trend as 12/26 proxies, signal=9)
    df["macd"] = df["ema_slow"] - df["ema_trend"]
    df["macd_signal"] = df["macd"].ewm(span=9).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    # Stochastic
    sp = p["stoch_period"]
    low_n = df["low"].rolling(sp).min()
    high_n = df["high"].rolling(sp).max()
    df["stoch_k"] = 100 * (df["close"] - low_n) / (high_n - low_n)
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()

    # Volume
    df["vol_ma"] = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / df["vol_ma"]

    # ATR / True Range
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(p["atr_period"]).mean()

    # Supertrend
    hl_avg = (df["high"] + df["low"]) / 2
    df["supertrend"] = hl_avg - p["atr_mult"] * df["atr"]

    # ADX
    plus_dm = df["high"].diff().clip(lower=0)
    minus_dm = (-df["low"].diff()).clip(lower=0)
    plus_di = 100 * plus_dm.rolling(p["atr_period"]).mean() / df["atr"]
    minus_di = 100 * minus_dm.rolling(p["atr_period"]).mean() / df["atr"]
    denom = plus_di + minus_di
    dx = 100 * (plus_di - minus_di).abs() / denom.replace(0, float("nan"))
    df["adx"] = dx.rolling(p["atr_period"]).mean()

    # OBV
    obv_sign = np.sign(df["close"].diff())
    df["obv"] = (obv_sign * df["volume"]).fillna(0).cumsum()
    df["obv_sma20"] = df["obv"].rolling(20).mean()

    # Ichimoku
    df["tenkan_sen"] = (df["high"].rolling(p["ichi_tenkan"]).max()
                        + df["low"].rolling(p["ichi_tenkan"]).min()) / 2
    df["kijun_sen"] = (df["high"].rolling(p["ichi_kijun"]).max()
                       + df["low"].rolling(p["ichi_kijun"]).min()) / 2
    df["senkou_span_a"] = ((df["tenkan_sen"] + df["kijun_sen"]) / 2).shift(p["ichi_kijun"])
    df["senkou_span_b"] = ((df["high"].rolling(p["ichi_senkou"]).max()
                            + df["low"].rolling(p["ichi_senkou"]).min()) / 2).shift(p["ichi_kijun"])

    # PSAR
    df["psar"] = _compute_psar(
        df["high"].values, df["low"].values,
        af_step=p["psar_af"], af_max=p["psar_max"],
    )

    # Price channels
    df["high_20"] = df["high"].rolling(20).max()
    df["low_20"] = df["low"].rolling(20).min()

    return df


# ---------------------------------------------------------------------------
# Parameterised signal functions
# ---------------------------------------------------------------------------
def _sig_ema_cross(df: pd.DataFrame, _p: dict) -> pd.Series:
    return (df["ema_fast"] > df["ema_slow"]).astype(np.int8)


def _sig_rsi_oversold(df: pd.DataFrame, p: dict) -> pd.Series:
    return ((df["rsi"] < p["rsi_oversold"]) & (df["rsi"] > df["rsi"].shift(1))).astype(np.int8)


def _sig_macd_cross(df: pd.DataFrame, _p: dict) -> pd.Series:
    return ((df["macd"] > df["macd_signal"])
            & (df["macd"].shift(1) <= df["macd_signal"].shift(1))).astype(np.int8)


def _sig_bb_lower(df: pd.DataFrame, _p: dict) -> pd.Series:
    return (df["close"] < df["bb_lower"]).astype(np.int8)


def _sig_volume_spike(df: pd.DataFrame, p: dict) -> pd.Series:
    return ((df["vol_ratio"] > p["vol_mult"])
            & (df["close"] > df["close"].shift(1))).astype(np.int8)


def _sig_supertrend(df: pd.DataFrame, _p: dict) -> pd.Series:
    return (df["close"] > df["supertrend"]).astype(np.int8)


def _sig_adx_trend(df: pd.DataFrame, p: dict) -> pd.Series:
    return (df["adx"] > p["adx_threshold"]).astype(np.int8)


def _sig_trend_ma(df: pd.DataFrame, _p: dict) -> pd.Series:
    return (df["close"] > df["ema_trend"]).astype(np.int8)


def _sig_obv_rising(df: pd.DataFrame, _p: dict) -> pd.Series:
    return (df["obv"] > df["obv_sma20"]).astype(np.int8)


def _sig_ichimoku_bull(df: pd.DataFrame, _p: dict) -> pd.Series:
    return ((df["close"] > df["senkou_span_a"])
            & (df["close"] > df["senkou_span_b"])).astype(np.int8)


def _sig_psar_bull(df: pd.DataFrame, _p: dict) -> pd.Series:
    return (df["close"] > df["psar"]).astype(np.int8)


def _sig_stochastic(df: pd.DataFrame, _p: dict) -> pd.Series:
    return ((df["stoch_k"] < 20)
            & (df["stoch_k"] > df["stoch_k"].shift(1))).astype(np.int8)


SIGNAL_FN = {
    "EMA_Cross":      _sig_ema_cross,
    "RSI_Oversold":   _sig_rsi_oversold,
    "MACD_Cross":     _sig_macd_cross,
    "BB_Lower":       _sig_bb_lower,
    "Volume_Spike":   _sig_volume_spike,
    "Supertrend":     _sig_supertrend,
    "ADX_Trend":      _sig_adx_trend,
    "Trend_MA50":     _sig_trend_ma,
    "OBV_Rising":     _sig_obv_rising,
    "Ichimoku_Bull":  _sig_ichimoku_bull,
    "PSAR_Bull":      _sig_psar_bull,
    "Stochastic":     _sig_stochastic,
}


# ---------------------------------------------------------------------------
# Apply strategy with parameterised signals
# ---------------------------------------------------------------------------
def apply_strategy_custom(df: pd.DataFrame, signal_names: list[str],
                          params: dict, min_agreement: int = 1) -> pd.DataFrame:
    """Build entry/exit columns from parameterised signal functions."""
    p = {**DEFAULT_PARAMS, **params}
    combo = np.zeros(len(df), dtype=np.int8)
    for name in signal_names:
        fn = SIGNAL_FN.get(name)
        if fn is not None:
            combo = combo + fn(df, p).values
    df["combo_signal"] = combo
    df["entry_signal"] = (combo >= min_agreement).astype(np.int8)
    df["exit_signal"] = (combo < 1).astype(np.int8)
    return df


# ---------------------------------------------------------------------------
# Vectorised backtest (much faster than row-by-row iterrows)
# ---------------------------------------------------------------------------
def run_backtest_fast(df: pd.DataFrame, sl: float, tp: float, ts: float) -> dict:
    """
    Run a long-only backtest.  Returns dict with ROI, WR, PF, Sharpe, GDD, trades.
    Uses NumPy arrays for speed.
    """
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    entry_sig = df["entry_signal"].values
    exit_sig = df["exit_signal"].values
    n = len(close)

    capital = float(INITIAL)
    position = False
    entry_price = 0.0
    peak_price = 0.0
    pos_size = 0.0

    wins = 0
    losses = 0
    gross_win = 0.0
    gross_loss = 0.0
    returns_list: list[float] = []

    # Equity tracking for drawdown
    equity_peak = float(INITIAL)
    max_dd = 0.0

    for i in range(n):
        if entry_sig[i] == 1 and not position:
            entry_price = close[i]
            pos_size = capital * 0.95 / entry_price
            position = True
            peak_price = entry_price
            continue

        if position:
            cur = close[i]
            h = high[i]
            lo = low[i]

            if cur > peak_price:
                peak_price = cur
            ts_price = peak_price * (1.0 - ts)

            should_exit = False
            if exit_sig[i] == 1:
                should_exit = True
            if lo <= entry_price * (1.0 - sl):
                should_exit = True
            if h >= entry_price * (1.0 + tp):
                should_exit = True
            if ts > 0 and cur <= ts_price:
                should_exit = True

            if should_exit:
                exit_price = cur
                pnl = pos_size * exit_price * (1.0 - FEE) - pos_size * entry_price * (1.0 + FEE)
                ret_pct = (exit_price - entry_price) / entry_price * 100.0
                capital += pnl
                returns_list.append(ret_pct)
                if pnl > 0:
                    wins += 1
                    gross_win += pnl
                else:
                    losses += 1
                    gross_loss += abs(pnl)
                # Drawdown
                if capital > equity_peak:
                    equity_peak = capital
                dd = (equity_peak - capital) / equity_peak * 100.0
                if dd > max_dd:
                    max_dd = dd
                position = False

    total_trades = wins + losses
    if total_trades == 0:
        return {"roi": 0, "wr": 0, "pf": 0, "sharpe": 0, "gdd": 0, "trades": 0, "final": capital}

    roi = (capital - INITIAL) / INITIAL * 100.0
    wr = wins / total_trades * 100.0
    pf = gross_win / gross_loss if gross_loss > 0 else 0.0

    # Daily Sharpe (TV-style): mean / std * sqrt(N)
    arr = np.array(returns_list)
    avg_r = arr.mean()
    std_r = arr.std() if len(arr) > 1 else 1.0
    sharpe = (avg_r / std_r) * np.sqrt(total_trades) if std_r > 0 else 0.0

    return {
        "roi": round(roi, 2),
        "wr": round(wr, 2),
        "pf": round(pf, 3),
        "sharpe": round(sharpe, 2),
        "gdd": round(max_dd, 2),
        "trades": total_trades,
        "final": round(capital, 2),
    }


# ---------------------------------------------------------------------------
# Determine which indicator params to sweep for a given signal combo
# ---------------------------------------------------------------------------
def _relevant_params(signal_names: list[str]) -> list[str]:
    """Return sorted unique list of param keys that affect *signal_names*."""
    keys: set[str] = set()
    for s in signal_names:
        keys.update(SIGNAL_PARAM_DEPS.get(s, []))
    return sorted(keys)


def _build_indicator_grid(param_keys: list[str], max_combos: int = 500) -> list[dict]:
    """
    Build a list of param dicts by sweeping only *param_keys*.
    If full grid exceeds *max_combos*, sample down.
    """
    if not param_keys:
        return [{}]

    ranges = [SWEEP_RANGES[k] for k in param_keys]
    grid = list(itertools.product(*ranges))

    if len(grid) > max_combos:
        rng = np.random.default_rng(42)
        indices = rng.choice(len(grid), size=max_combos, replace=False)
        grid = [grid[i] for i in sorted(indices)]

    return [dict(zip(param_keys, vals)) for vals in grid]


# ---------------------------------------------------------------------------
# Indicator cache: avoid recalculating when params are identical
# ---------------------------------------------------------------------------
_INDICATOR_CACHE: dict[tuple, pd.DataFrame] = {}


def _cache_key(symbol: str, params: dict) -> tuple:
    return (symbol, tuple(sorted(params.items())))


def _get_indicators(raw_df: pd.DataFrame, symbol: str, params: dict) -> pd.DataFrame:
    ck = _cache_key(symbol, params)
    if ck in _INDICATOR_CACHE:
        return _INDICATOR_CACHE[ck]
    df = calculate_indicators_custom(raw_df, params)
    # Keep cache bounded (LRU-ish: just cap size)
    if len(_INDICATOR_CACHE) > 200:
        # Drop oldest half
        keys = list(_INDICATOR_CACHE.keys())
        for k in keys[:100]:
            del _INDICATOR_CACHE[k]
    _INDICATOR_CACHE[ck] = df
    return df


# ---------------------------------------------------------------------------
# sweep_for_tier2
# ---------------------------------------------------------------------------
def sweep_for_tier2(
    asset_symbol: str,
    signals: list[str],
    min_agreement: int,
    combo_name: str = "",
) -> pd.DataFrame:
    """
    Sweep indicator params + SL/TP/TS for one signal combo on one asset.
    Returns top-20 results sorted by PF (filtered: PF>=1.4, WR>=45%, trades>=100).
    """
    raw_df = load_data(asset_symbol, TIMEFRAME)
    if raw_df is None:
        return pd.DataFrame()

    param_keys = _relevant_params(signals)
    ind_grid = _build_indicator_grid(param_keys, max_combos=500)
    sltp_grid = list(itertools.product(SL_RANGE, TP_RANGE, TS_RANGE))

    print(f"    Sweep {asset_symbol} | {combo_name} | "
          f"{len(ind_grid)} ind combos x {len(sltp_grid)} SL/TP/TS = "
          f"{len(ind_grid) * len(sltp_grid):,} runs")

    rows: list[dict] = []

    for ip, ind_params in enumerate(ind_grid):
        merged = {**DEFAULT_PARAMS, **ind_params}
        df_ind = _get_indicators(raw_df, asset_symbol, merged)

        # Apply signals once per indicator set
        df_sig = apply_strategy_custom(df_ind.copy(), signals, merged, min_agreement)

        for sl, tp, ts in sltp_grid:
            res = run_backtest_fast(df_sig, sl, tp, ts)
            if res["trades"] < 100:
                continue
            if res["pf"] < 1.4:
                continue
            if res["wr"] < 45:
                continue
            row = {
                "asset": asset_symbol,
                "combo": combo_name,
                "signals": " + ".join(signals),
                "min_agree": min_agreement,
                "sl": sl,
                "tp": tp,
                "ts": ts,
                **{k: v for k, v in merged.items() if k in param_keys},
                "roi": res["roi"],
                "wr": res["wr"],
                "pf": res["pf"],
                "sharpe": res["sharpe"],
                "gdd": res["gdd"],
                "trades": res["trades"],
                "final_capital": res["final"],
            }
            rows.append(row)

    if not rows:
        return pd.DataFrame()

    out = pd.DataFrame(rows).sort_values("pf", ascending=False).head(20).reset_index(drop=True)
    return out


# ---------------------------------------------------------------------------
# run_full_sweep
# ---------------------------------------------------------------------------
def run_full_sweep() -> pd.DataFrame:
    """
    Sweep all TOP_COMBOS x ASSETS. Save everything with PF >= 1.2 to CSV.
    """
    t0 = time.time()
    all_rows: list[dict] = []

    for combo in TOP_COMBOS:
        for asset in ASSETS:
            raw_df = load_data(asset, TIMEFRAME)
            if raw_df is None:
                continue

            param_keys = _relevant_params(combo["signals"])
            ind_grid = _build_indicator_grid(param_keys, max_combos=500)
            sltp_grid = list(itertools.product(SL_RANGE, TP_RANGE, TS_RANGE))

            total = len(ind_grid) * len(sltp_grid)
            print(f"\n  [{combo['name']}] {asset} -- {total:,} param combos")

            count = 0
            hits = 0
            for ind_params in ind_grid:
                merged = {**DEFAULT_PARAMS, **ind_params}
                df_ind = _get_indicators(raw_df, asset, merged)
                df_sig = apply_strategy_custom(
                    df_ind.copy(), combo["signals"], merged, combo["min_agreement"],
                )

                for sl, tp, ts in sltp_grid:
                    res = run_backtest_fast(df_sig, sl, tp, ts)
                    count += 1
                    if res["pf"] < 1.2 or res["trades"] < 50:
                        continue
                    hits += 1
                    row = {
                        "asset": asset,
                        "combo": combo["name"],
                        "signals": " + ".join(combo["signals"]),
                        "min_agree": combo["min_agreement"],
                        "sl": sl,
                        "tp": tp,
                        "ts": ts,
                        **{k: v for k, v in merged.items() if k in param_keys},
                        "roi": res["roi"],
                        "wr": res["wr"],
                        "pf": res["pf"],
                        "sharpe": res["sharpe"],
                        "gdd": res["gdd"],
                        "trades": res["trades"],
                        "final_capital": res["final"],
                    }
                    all_rows.append(row)

            print(f"    -> {count:,} tested, {hits} passed PF>=1.2")

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"Full sweep done in {elapsed/60:.1f} min  |  {len(all_rows):,} results with PF>=1.2")

    if not all_rows:
        print("No results passed filters.")
        return pd.DataFrame()

    df_out = pd.DataFrame(all_rows).sort_values("pf", ascending=False).reset_index(drop=True)

    os.makedirs(REPORTS_DIR, exist_ok=True)
    csv_path = os.path.join(REPORTS_DIR, "param_sweep_results.csv")
    df_out.to_csv(csv_path, index=False)
    print(f"Saved {len(df_out):,} rows -> {csv_path}")

    # Print top-20 summary
    print(f"\n{'='*60}")
    print("TOP 20 by Profit Factor")
    print(f"{'='*60}")
    cols = ["asset", "combo", "sl", "tp", "ts", "pf", "wr", "roi", "sharpe", "gdd", "trades"]
    print(df_out[cols].head(20).to_string(index=False))

    return df_out


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"Param Sweep Engine  |  {datetime.now():%Y-%m-%d %H:%M}")
    print(f"FEE={FEE}  INITIAL={INITIAL}")
    print(f"Assets: {ASSETS}")
    print(f"Timeframe: {TIMEFRAME}")
    print()

    if len(sys.argv) > 1 and sys.argv[1] == "--tier2":
        # Single combo + asset sweep for tier-2 refinement
        asset = sys.argv[2] if len(sys.argv) > 2 else "ETHUSDT"
        combo_idx = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        combo = TOP_COMBOS[combo_idx]
        result = sweep_for_tier2(asset, combo["signals"], combo["min_agreement"], combo["name"])
        if not result.empty:
            print(f"\nTop-20 Tier-2 results for {asset} / {combo['name']}:")
            print(result.to_string(index=False))
        else:
            print("No results passed tier-2 filters.")
    else:
        run_full_sweep()
