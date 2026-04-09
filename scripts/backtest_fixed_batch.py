#!/usr/bin/env python3
"""Backtest F01-F08 fixed strategies on ETHUSDT 4h."""
import sys, os, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["BACKTEST_SIZING_MODE"] = "fixed_notional"
os.environ["BACKTEST_FIXED_NOTIONAL_USD"] = "500"
os.environ["BACKTEST_SLIPPAGE_PCT"] = "0.001"
from run_strategies_batch import load_data, calculate_indicators, run_backtest_oos
import numpy as np

def add_f01_psar_donchian(df):
    df = df.copy()
    don_upper = df["high"].rolling(20).max()
    don_lower = df["low"].rolling(20).min()
    exit_lower = df["low"].rolling(10).min()
    exit_upper = df["high"].rolling(10).max()
    # Simple PSAR approx via EMA
    psar = df["close"].ewm(span=5).mean()
    psar_flip_up = (df["close"] > psar) & (df["close"].shift(1) <= psar.shift(1))
    psar_flip_down = (df["close"] < psar) & (df["close"].shift(1) >= psar.shift(1))
    df["entry_signal"] = ((don_upper.shift(1) < df["close"]) | psar_flip_up).astype(int) & (df["close"] > df["ema50"]).astype(int) & (df["adx"] > 18).astype(int)
    df["short_entry_signal"] = ((don_lower.shift(1) > df["close"]) | psar_flip_down).astype(int) & (df["close"] < df["ema50"]).astype(int) & (df["adx"] > 18).astype(int)
    df["exit_signal"] = ((df["close"] < exit_lower.shift(1)) | psar_flip_down).astype(int)
    df["short_exit_signal"] = ((df["close"] > exit_upper.shift(1)) | psar_flip_up).astype(int)
    return df

def add_f02_adx_di_donchian(df):
    df = df.copy()
    don_upper = df["high"].rolling(20).max()
    don_lower = df["low"].rolling(20).min()
    exit_lower = df["low"].rolling(10).min()
    exit_upper = df["high"].rolling(10).max()
    # DI cross approx
    h, l, c = df["high"], df["low"], df["close"]
    upmove = (h - h.shift(1)).clip(lower=0)
    downmove = (l.shift(1) - l).clip(lower=0)
    plus_di = upmove.rolling(14).mean()
    minus_di = downmove.rolling(14).mean()
    di_cross_up = (plus_di > minus_di) & (plus_di.shift(1) <= minus_di.shift(1))
    di_cross_down = (plus_di < minus_di) & (plus_di.shift(1) >= minus_di.shift(1))
    df["entry_signal"] = ((df["close"] > don_upper.shift(1)) | di_cross_up).astype(int) & (df["close"] > df["ema50"]).astype(int) & (df["adx"] > 18).astype(int)
    df["short_entry_signal"] = ((df["close"] < don_lower.shift(1)) | di_cross_down).astype(int) & (df["close"] < df["ema50"]).astype(int) & (df["adx"] > 18).astype(int)
    df["exit_signal"] = ((df["close"] < exit_lower.shift(1)) | di_cross_down).astype(int)
    df["short_exit_signal"] = ((df["close"] > exit_upper.shift(1)) | di_cross_up).astype(int)
    return df

def add_f03_supertrend_donchian(df):
    df = df.copy()
    don_upper = df["high"].rolling(20).max()
    don_lower = df["low"].rolling(20).min()
    exit_lower = df["low"].rolling(10).min()
    exit_upper = df["high"].rolling(10).max()
    hl2 = (df["high"] + df["low"]) / 2
    upper_band = hl2 + 3.0 * df["atr"]
    lower_band = hl2 - 3.0 * df["atr"]
    st = upper_band.copy()
    for i in range(1, len(df)):
        if df["close"].iloc[i-1] > st.iloc[i-1]:
            st.iloc[i] = max(lower_band.iloc[i], st.iloc[i-1]) if df["close"].iloc[i] > lower_band.iloc[i] else upper_band.iloc[i]
        else:
            st.iloc[i] = min(upper_band.iloc[i], st.iloc[i-1]) if df["close"].iloc[i] < upper_band.iloc[i] else lower_band.iloc[i]
    st_bull = df["close"] > st
    st_flip_up = st_bull & ~st_bull.shift(1).fillna(False)
    st_flip_down = ~st_bull & st_bull.shift(1).fillna(True)
    df["entry_signal"] = ((df["close"] > don_upper.shift(1)) | st_flip_up).astype(int) & (df["close"] > df["ema50"]).astype(int) & (df["adx"] > 18).astype(int)
    df["short_entry_signal"] = ((df["close"] < don_lower.shift(1)) | st_flip_down).astype(int) & (df["close"] < df["ema50"]).astype(int) & (df["adx"] > 18).astype(int)
    df["exit_signal"] = ((df["close"] < exit_lower.shift(1)) | st_flip_down).astype(int)
    df["short_exit_signal"] = ((df["close"] > exit_upper.shift(1)) | st_flip_up).astype(int)
    return df

def add_f04_trix_donchian(df):
    df = df.copy()
    don_upper = df["high"].rolling(20).max()
    don_lower = df["low"].rolling(20).min()
    exit_lower = df["low"].rolling(10).min()
    exit_upper = df["high"].rolling(10).max()
    ema1 = df["close"].ewm(span=15).mean()
    ema2 = ema1.ewm(span=15).mean()
    ema3 = ema2.ewm(span=15).mean()
    trix = (ema3 - ema3.shift(1)) / ema3.shift(1) * 10000
    trix_sig = trix.rolling(9).mean()
    trix_cross_up = (trix > trix_sig) & (trix.shift(1) <= trix_sig.shift(1))
    trix_cross_down = (trix < trix_sig) & (trix.shift(1) >= trix_sig.shift(1))
    df["entry_signal"] = ((df["close"] > don_upper.shift(1)) | trix_cross_up).astype(int) & (df["close"] > df["ema50"]).astype(int) & (df["adx"] > 18).astype(int)
    df["short_entry_signal"] = ((df["close"] < don_lower.shift(1)) | trix_cross_down).astype(int) & (df["close"] < df["ema50"]).astype(int) & (df["adx"] > 18).astype(int)
    df["exit_signal"] = ((df["close"] < exit_lower.shift(1)) | trix_cross_down).astype(int)
    df["short_exit_signal"] = ((df["close"] > exit_upper.shift(1)) | trix_cross_up).astype(int)
    return df

def add_f05_williams_donchian(df):
    df = df.copy()
    don_upper = df["high"].rolling(20).max()
    don_lower = df["low"].rolling(20).min()
    exit_lower = df["low"].rolling(10).min()
    exit_upper = df["high"].rolling(10).max()
    high14 = df["high"].rolling(14).max()
    low14 = df["low"].rolling(14).min()
    wr = ((high14 - df["close"]) / (high14 - low14) * -100).fillna(-50)
    wr_cross_up = (wr > -80) & (wr.shift(1) <= -80)
    wr_cross_down = (wr < -20) & (wr.shift(1) >= -20)
    df["entry_signal"] = ((df["close"] > don_upper.shift(1)) | wr_cross_up).astype(int) & (df["close"] > df["ema50"]).astype(int) & (df["adx"] > 18).astype(int)
    df["short_entry_signal"] = ((df["close"] < don_lower.shift(1)) | wr_cross_down).astype(int) & (df["close"] < df["ema50"]).astype(int) & (df["adx"] > 18).astype(int)
    df["exit_signal"] = ((df["close"] < exit_lower.shift(1)) | wr_cross_down).astype(int)
    df["short_exit_signal"] = ((df["close"] > exit_upper.shift(1)) | wr_cross_up).astype(int)
    return df

def add_f06_chandelier_donchian(df):
    df = df.copy()
    don_upper = df["high"].rolling(20).max()
    don_lower = df["low"].rolling(20).min()
    exit_lower = df["low"].rolling(10).min()
    exit_upper = df["high"].rolling(10).max()
    atr22 = df["close"].rolling(22).std() * 1.5  # approx
    ch_long = df["high"].rolling(22).max() - atr22 * 3
    ch_short = df["low"].rolling(22).min() + atr22 * 3
    ch_bull = df["close"] > ch_short
    ch_flip_up = ch_bull & ~ch_bull.shift(1).fillna(False)
    ch_flip_down = ~ch_bull & ch_bull.shift(1).fillna(True)
    df["entry_signal"] = ((df["close"] > don_upper.shift(1)) | ch_flip_up).astype(int) & (df["close"] > df["ema50"]).astype(int) & (df["adx"] > 18).astype(int)
    df["short_entry_signal"] = ((df["close"] < don_lower.shift(1)) | ch_flip_down).astype(int) & (df["close"] < df["ema50"]).astype(int) & (df["adx"] > 18).astype(int)
    df["exit_signal"] = ((df["close"] < exit_lower.shift(1)) | ch_flip_down).astype(int)
    df["short_exit_signal"] = ((df["close"] > exit_upper.shift(1)) | ch_flip_up).astype(int)
    return df

def add_f07_ichimoku_donchian(df):
    df = df.copy()
    don_upper = df["high"].rolling(20).max()
    don_lower = df["low"].rolling(20).min()
    exit_lower = df["low"].rolling(10).min()
    exit_upper = df["high"].rolling(10).max()
    tenkan = (df["high"].rolling(9).max() + df["low"].rolling(9).min()) / 2
    kijun = (df["high"].rolling(26).max() + df["low"].rolling(26).min()) / 2
    senkou_a = ((tenkan + kijun) / 2).shift(26)
    senkou_b = ((df["high"].rolling(52).max() + df["low"].rolling(52).min()) / 2).shift(26)
    tk_cross_up = (tenkan > kijun) & (tenkan.shift(1) <= kijun.shift(1))
    tk_cross_down = (tenkan < kijun) & (tenkan.shift(1) >= kijun.shift(1))
    above_cloud = (df["close"] > senkou_a) & (df["close"] > senkou_b)
    df["entry_signal"] = ((df["close"] > don_upper.shift(1)) | (tk_cross_up & above_cloud)).astype(int) & (df["close"] > df["ema50"]).astype(int) & (df["adx"] > 18).astype(int)
    df["short_entry_signal"] = ((df["close"] < don_lower.shift(1)) | tk_cross_down).astype(int) & (df["close"] < df["ema50"]).astype(int) & (df["adx"] > 18).astype(int)
    df["exit_signal"] = ((df["close"] < exit_lower.shift(1)) | tk_cross_down).astype(int)
    df["short_exit_signal"] = ((df["close"] > exit_upper.shift(1)) | tk_cross_up).astype(int)
    return df

def add_f08_bb_squeeze_donchian(df):
    df = df.copy()
    don_upper = df["high"].rolling(20).max()
    don_lower = df["low"].rolling(20).min()
    exit_lower = df["low"].rolling(10).min()
    exit_upper = df["high"].rolling(10).max()
    bb_mid = df["close"].rolling(20).mean()
    bb_std = df["close"].rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std
    kc_mid = df["close"].ewm(span=20).mean()
    kc_atr = df["atr"]
    kc_upper = kc_mid + 1.5 * kc_atr
    kc_lower = kc_mid - 1.5 * kc_atr
    squeeze_on = (bb_lower > kc_lower) & (bb_upper < kc_upper)
    squeeze_off = ~squeeze_on
    squeeze_release = squeeze_off & squeeze_on.shift(1)
    mom = df["close"] - bb_mid
    squeeze_bull = squeeze_release & (mom > 0)
    squeeze_bear = squeeze_release & (mom < 0)
    df["entry_signal"] = ((df["close"] > don_upper.shift(1)) | squeeze_bull).astype(int) & (df["close"] > df["ema50"]).astype(int) & (df["adx"] > 18).astype(int)
    df["short_entry_signal"] = ((df["close"] < don_lower.shift(1)) | squeeze_bear).astype(int) & (df["close"] < df["ema50"]).astype(int) & (df["adx"] > 18).astype(int)
    df["exit_signal"] = ((df["close"] < exit_lower.shift(1)) | ((mom < 0) & (mom.shift(1) >= 0))).astype(int)
    df["short_exit_signal"] = ((df["close"] > exit_upper.shift(1)) | ((mom > 0) & (mom.shift(1) <= 0))).astype(int)
    return df

STRATEGIES = [
    ("F01_PSAR_Donchian_Wide", add_f01_psar_donchian, "F01_PSAR_Donchian_Wide.pine"),
    ("F02_ADX_DI_Donchian_Wide", add_f02_adx_di_donchian, "F02_ADX_DI_Donchian_Wide.pine"),
    ("F03_SuperTrend_Donchian_Wide", add_f03_supertrend_donchian, "F03_SuperTrend_Donchian_Wide.pine"),
    ("F04_TRIX_Donchian_Wide", add_f04_trix_donchian, "F04_TRIX_Donchian_Wide.pine"),
    ("F05_Williams_Donchian_Wide", add_f05_williams_donchian, "F05_Williams_Donchian_Wide.pine"),
    ("F06_Chandelier_Donchian_Wide", add_f06_chandelier_donchian, "F06_Chandelier_Donchian_Wide.pine"),
    ("F07_Ichimoku_Donchian_Wide", add_f07_ichimoku_donchian, "F07_Ichimoku_Donchian_Wide.pine"),
    ("F08_BB_Squeeze_Donchian_Wide", add_f08_bb_squeeze_donchian, "F08_BB_Squeeze_Donchian_Wide.pine"),
]

df = load_data("ETHUSDT_4h")
df = calculate_indicators(df)

results = []
for name, fn, pine in STRATEGIES:
    try:
        df_s = fn(df)
        oos = run_backtest_oos(df_s, {"strategy": name}, oos_ratio=0.30,
            stop_loss=0.015, take_profit=0.12, trailing_stop=0.04, side="both",
            slippage_pct=0.001, sizing_mode="fixed_notional", fixed_notional_usd=500)
        is_m, oos_m = oos["is"], oos["oos"]
        passed = oos_m["roi_pct"] > 0 and oos_m["pf"] >= 1.0
        status = "PASS" if passed else "FAIL"
        print(f"  {name:35s} IS={is_m['roi_pct']:>7.2f}% OOS={oos_m['roi_pct']:>7.2f}% PF={oos_m['pf']:.2f} WR={oos_m['win_rate']:.1f}% [{status}]")
        results.append({"strategy": name, "pine": pine, "oos_roi": oos_m["roi_pct"], "oos_pf": oos_m["pf"], "oos_wr": oos_m["win_rate"], "oos_gdd": oos_m["gdd"], "oos_trades": oos_m["trades"], "status": status})
    except Exception as e:
        print(f"  {name:35s} ERROR: {e}")

results.sort(key=lambda x: x["oos_roi"], reverse=True)
passed = [r for r in results if r["status"] == "PASS"]
print(f"\n{len(passed)}/{len(results)} PASSED")
json.dump(results, open(os.path.join(ROOT, "reports", "FIXED_BATCH_RESULTS.json"), "w"), indent=2)
