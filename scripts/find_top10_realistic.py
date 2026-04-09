#!/usr/bin/env python3
"""Find 10 best strategies using realistic backtesting.
Tests top TV-validated candidates with $500 fixed, 0.1% slippage, 30% OOS.
"""
import sys, os, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ["BACKTEST_SIZING_MODE"] = "fixed_notional"
os.environ["BACKTEST_FIXED_NOTIONAL_USD"] = "500"
os.environ["BACKTEST_SLIPPAGE_PCT"] = "0.001"

from run_strategies_batch import load_data, calculate_indicators, run_backtest_oos
import numpy as np

REPORTS = os.path.join(ROOT, "reports")

# ═══════════════════════════════════════════════════════════════
# TOP 20 TV-VALIDATED CANDIDATES — from profitable_results_sheet
# Each has: signal function, SL/TP/TS params, assets to test
# ═══════════════════════════════════════════════════════════════

def add_donchian_trend(df, dc_len=20, dc_exit=10):
    df = df.copy()
    don_upper = df["high"].rolling(dc_len).max()
    don_lower = df["low"].rolling(dc_len).min()
    exit_lower = df["low"].rolling(dc_exit).min()
    exit_upper = df["high"].rolling(dc_exit).max()
    df["entry_signal"] = ((df["close"] > don_upper.shift(1)) & (df["close"] > df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = ((df["close"] < don_lower.shift(1)) & (df["close"] < df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = (df["close"] < exit_lower.shift(1)).astype(int)
    df["short_exit_signal"] = (df["close"] > exit_upper.shift(1)).astype(int)
    return df

def add_cci_trend(df):
    df = df.copy()
    cci = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    df["entry_signal"] = ((cci > 100) & (cci.shift(1) <= 100) & (df["close"] > df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = ((cci < -100) & (cci.shift(1) >= -100) & (df["close"] < df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = ((cci < 0) & (cci.shift(1) >= 0)).astype(int)
    df["short_exit_signal"] = ((cci > 0) & (cci.shift(1) <= 0)).astype(int)
    return df

def add_kc_breakout(df):
    df = df.copy()
    kc_mid = df["close"].ewm(span=20).mean()
    kc_upper = kc_mid + 1.5 * df["atr"]
    kc_lower = kc_mid - 1.5 * df["atr"]
    df["entry_signal"] = ((df["close"] > kc_upper) & (df["close"].shift(1) <= kc_upper.shift(1)) & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = ((df["close"] < kc_lower) & (df["close"].shift(1) >= kc_lower.shift(1)) & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = (df["close"] < kc_mid).astype(int)
    df["short_exit_signal"] = (df["close"] > kc_mid).astype(int)
    return df

def add_ha_trend(df):
    df = df.copy()
    ha_close = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_open = df["open"].copy()
    for i in range(1, len(df)):
        ha_open.iloc[i] = (ha_open.iloc[i-1] + ha_close.iloc[i-1]) / 2
    ha_bull = ha_close > ha_open
    ha_bear = ha_close < ha_open
    bull_cross = ha_bull & ~ha_bull.shift(1).fillna(False)
    bear_cross = ha_bear & ~ha_bear.shift(1).fillna(False)
    df["entry_signal"] = (bull_cross & (df["close"] > df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = (bear_cross & (df["close"] < df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = bear_cross.astype(int)
    df["short_exit_signal"] = bull_cross.astype(int)
    return df

def add_aroon_oscillator(df):
    df = df.copy()
    n = 25
    aroon_up = df["high"].rolling(n+1).apply(lambda x: x.argmax(), raw=True) / n * 100
    aroon_dn = df["low"].rolling(n+1).apply(lambda x: x.argmin(), raw=True) / n * 100
    osc = aroon_up - aroon_dn
    osc_cross_up = (osc > 50) & (osc.shift(1) <= 50)
    osc_cross_dn = (osc < -50) & (osc.shift(1) >= -50)
    df["entry_signal"] = (osc_cross_up & (df["close"] > df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = (osc_cross_dn & (df["close"] < df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = (osc < 0).astype(int)
    df["short_exit_signal"] = (osc > 0).astype(int)
    return df

def add_engulfing_v2(df):
    df = df.copy()
    bull_eng = (df["close"] > df["open"]) & (df["close"].shift(1) < df["open"].shift(1)) & (df["close"] > df["open"].shift(1)) & (df["open"] < df["close"].shift(1))
    bear_eng = (df["close"] < df["open"]) & (df["close"].shift(1) > df["open"].shift(1)) & (df["close"] < df["open"].shift(1)) & (df["open"] > df["close"].shift(1))
    df["entry_signal"] = (bull_eng & (df["close"] > df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = (bear_eng & (df["close"] < df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = bear_eng.astype(int)
    df["short_exit_signal"] = bull_eng.astype(int)
    return df

def add_momentum_v2(df):
    df = df.copy()
    roc = (df["close"] / df["close"].shift(10) - 1) * 100
    roc_up = (roc > 2) & (roc.shift(1) <= 2)
    roc_dn = (roc < -2) & (roc.shift(1) >= -2)
    df["entry_signal"] = (roc_up & (df["close"] > df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = (roc_dn & (df["close"] < df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = (roc < 0).astype(int)
    df["short_exit_signal"] = (roc > 0).astype(int)
    return df

def add_breakout_retest(df):
    df = df.copy()
    high20 = df["high"].rolling(20).max()
    low20 = df["low"].rolling(20).min()
    broke_up = df["close"] > high20.shift(1)
    retested = (df["low"] <= high20.shift(1)) & broke_up.shift(1).rolling(5).sum().fillna(0) > 0
    broke_dn = df["close"] < low20.shift(1)
    df["entry_signal"] = (broke_up & (df["close"] > df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = (broke_dn & (df["close"] < df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = (df["close"] < df["low"].rolling(10).min().shift(1)).astype(int)
    df["short_exit_signal"] = (df["close"] > df["high"].rolling(10).max().shift(1)).astype(int)
    return df

def add_donchian_cci_power(df):
    """G11: Donchian + CCI combined."""
    df = df.copy()
    don_upper = df["high"].rolling(20).max()
    don_lower = df["low"].rolling(20).min()
    exit_lower = df["low"].rolling(10).min()
    exit_upper = df["high"].rolling(10).max()
    cci = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    df["entry_signal"] = ((df["close"] > don_upper.shift(1)) & (cci > 50) & (df["close"] > df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = ((df["close"] < don_lower.shift(1)) & (cci < -50) & (df["close"] < df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = ((df["close"] < exit_lower.shift(1)) | (cci < 0)).astype(int)
    df["short_exit_signal"] = ((df["close"] > exit_upper.shift(1)) | (cci > 0)).astype(int)
    return df

def add_donchian_adx_aggro(df):
    """G26: Aggressive Donchian with lower ADX threshold."""
    df = df.copy()
    don_upper = df["high"].rolling(20).max()
    don_lower = df["low"].rolling(20).min()
    exit_lower = df["low"].rolling(10).min()
    exit_upper = df["high"].rolling(10).max()
    df["entry_signal"] = ((df["close"] > don_upper.shift(1)) & (df["close"] > df["ema50"]) & (df["adx"] > 15)).astype(int)
    df["short_entry_signal"] = ((df["close"] < don_lower.shift(1)) & (df["close"] < df["ema50"]) & (df["adx"] > 15)).astype(int)
    df["exit_signal"] = (df["close"] < exit_lower.shift(1)).astype(int)
    df["short_exit_signal"] = (df["close"] > exit_upper.shift(1)).astype(int)
    return df

def add_donchian_short14(df):
    """G28: Donchian with shorter 14-period channel."""
    df = df.copy()
    don_upper = df["high"].rolling(14).max()
    don_lower = df["low"].rolling(14).min()
    exit_lower = df["low"].rolling(7).min()
    exit_upper = df["high"].rolling(7).max()
    df["entry_signal"] = ((df["close"] > don_upper.shift(1)) & (df["close"] > df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = ((df["close"] < don_lower.shift(1)) & (df["close"] < df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = (df["close"] < exit_lower.shift(1)).astype(int)
    df["short_exit_signal"] = (df["close"] > exit_upper.shift(1)).astype(int)
    return df

def add_cci_donchian_wide(df):
    """G27: CCI + wide Donchian (30-period)."""
    df = df.copy()
    don_upper = df["high"].rolling(30).max()
    don_lower = df["low"].rolling(30).min()
    cci = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    df["entry_signal"] = ((cci > 100) & (df["close"] > don_upper.shift(1)) & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = ((cci < -100) & (df["close"] < don_lower.shift(1)) & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = ((cci < 0) | (df["close"] < df["low"].rolling(15).min().shift(1))).astype(int)
    df["short_exit_signal"] = ((cci > 0) | (df["close"] > df["high"].rolling(15).max().shift(1))).astype(int)
    return df

def add_cci_pure_hightp(df):
    """G25: Pure CCI with higher TP target."""
    df = df.copy()
    cci = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    df["entry_signal"] = ((cci > 100) & (cci.shift(1) <= 100) & (df["close"] > df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = ((cci < -100) & (cci.shift(1) >= -100) & (df["close"] < df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = ((cci < -50) & (cci.shift(1) >= -50)).astype(int)
    df["short_exit_signal"] = ((cci > 50) & (cci.shift(1) <= 50)).astype(int)
    return df

def add_donchian_cci_lite(df):
    """G23: Lighter CCI threshold with Donchian."""
    df = df.copy()
    don_upper = df["high"].rolling(20).max()
    don_lower = df["low"].rolling(20).min()
    cci = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    df["entry_signal"] = ((df["close"] > don_upper.shift(1)) & (cci > 0) & (df["close"] > df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = ((df["close"] < don_lower.shift(1)) & (cci < 0) & (df["close"] < df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = ((cci < -50) | (df["close"] < df["low"].rolling(10).min().shift(1))).astype(int)
    df["short_exit_signal"] = ((cci > 50) | (df["close"] > df["high"].rolling(10).max().shift(1))).astype(int)
    return df

def add_aroon_donchian(df):
    """G15: Aroon + Donchian breakout."""
    df = df.copy()
    n = 25
    aroon_up = df["high"].rolling(n+1).apply(lambda x: x.argmax(), raw=True) / n * 100
    aroon_dn = df["low"].rolling(n+1).apply(lambda x: x.argmin(), raw=True) / n * 100
    don_upper = df["high"].rolling(20).max()
    don_lower = df["low"].rolling(20).min()
    df["entry_signal"] = ((aroon_up > 80) & (df["close"] > don_upper.shift(1)) & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = ((aroon_dn > 80) & (df["close"] < don_lower.shift(1)) & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = ((aroon_dn > aroon_up) | (df["close"] < df["low"].rolling(10).min().shift(1))).astype(int)
    df["short_exit_signal"] = ((aroon_up > aroon_dn) | (df["close"] > df["high"].rolling(10).max().shift(1))).astype(int)
    return df

def add_donchian_volume_surge(df):
    """G19: Donchian + volume surge."""
    df = df.copy()
    don_upper = df["high"].rolling(20).max()
    don_lower = df["low"].rolling(20).min()
    vol_sma = df["volume"].rolling(20).mean()
    vol_surge = df["volume"] > vol_sma * 1.5
    df["entry_signal"] = ((df["close"] > don_upper.shift(1)) & vol_surge & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = ((df["close"] < don_lower.shift(1)) & vol_surge & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = (df["close"] < df["low"].rolling(10).min().shift(1)).astype(int)
    df["short_exit_signal"] = (df["close"] > df["high"].rolling(10).max().shift(1)).astype(int)
    return df


# ═══════════════════════════════════════════════════════════════
# CANDIDATES — top 20 from TV results, each with best asset
# ═══════════════════════════════════════════════════════════════

CANDIDATES = [
    # (name, signal_fn, assets, sl, tp, ts, pine_file)
    ("Donchian_Trend", add_donchian_trend, ["ETHUSDT_4h", "SUIUSDT_4h", "BTCUSDT_4h", "LINKUSDT_4h", "AVAXUSDT_4h"], 0.015, 0.12, 0.04, "tv_first_35_Donchian_Trend.pine"),
    ("CCI_Trend", add_cci_trend, ["ETHUSDT_4h", "LDOUSDT_4h", "BTCUSDT_4h", "SOLUSDT_4h"], 0.015, 0.12, 0.04, "tv_first_40_CCI_Trend.pine"),
    ("KC_Breakout", add_kc_breakout, ["ETHUSDT_4h", "BTCUSDT_4h", "LINKUSDT_4h"], 0.015, 0.12, 0.04, "tv_first_42_Keltner_Breakout.pine"),
    ("HA_Trend", add_ha_trend, ["AVAXUSDT_4h", "ETHUSDT_4h", "SUIUSDT_4h"], 0.015, 0.12, 0.04, "tv_first_36_Heikin_Ashi_Trend.pine"),
    ("Aroon_Oscillator", add_aroon_oscillator, ["LINKUSDT_4h", "AVAXUSDT_4h", "ETHUSDT_4h"], 0.015, 0.12, 0.04, "aroon_oscillator_fusion.pine"),
    ("Engulfing_V2", add_engulfing_v2, ["ETHUSDT_4h", "AVAXUSDT_4h", "BTCUSDT_4h"], 0.015, 0.12, 0.04, "tv_first_28b_Engulfing_V2.pine"),
    ("Momentum_V2", add_momentum_v2, ["SUIUSDT_4h", "ETHUSDT_4h", "LINKUSDT_4h"], 0.015, 0.12, 0.04, "tv_first_27b_Momentum_V2.pine"),
    ("Breakout_Retest", add_breakout_retest, ["ETHUSDT_4h", "BTCUSDT_4h", "SUIUSDT_4h"], 0.015, 0.12, 0.04, "tv_first_33_Breakout_Retest.pine"),
    ("G11_Donchian_CCI_Power", add_donchian_cci_power, ["ETHUSDT_4h", "BTCUSDT_4h"], 0.015, 0.12, 0.04, "G11_Donchian_CCI_Power.pine"),
    ("G26_Donchian_ADX_Aggro", add_donchian_adx_aggro, ["ETHUSDT_4h", "SUIUSDT_4h", "BTCUSDT_4h"], 0.015, 0.12, 0.04, "G26_Donchian_ADX_Aggro.pine"),
    ("G28_Donchian_Short14", add_donchian_short14, ["ETHUSDT_4h", "BTCUSDT_4h", "LINKUSDT_4h"], 0.015, 0.12, 0.04, "G28_Donchian_Short14.pine"),
    ("G27_CCI_Donchian_Wide", add_cci_donchian_wide, ["AVAXUSDT_4h", "ETHUSDT_4h", "BTCUSDT_4h"], 0.015, 0.12, 0.04, "G27_CCI_Donchian_Wide.pine"),
    ("G25_CCI_Pure_HighTP", add_cci_pure_hightp, ["AVAXUSDT_4h", "SUIUSDT_4h", "ETHUSDT_4h"], 0.015, 0.15, 0.04, "G25_CCI_Pure_HighTP.pine"),
    ("G23_Donchian_CCI_Lite", add_donchian_cci_lite, ["ETHUSDT_4h", "BTCUSDT_4h", "LINKUSDT_4h"], 0.015, 0.12, 0.04, "G23_Donchian_CCI_Lite.pine"),
    ("G15_Aroon_Donchian", add_aroon_donchian, ["ETHUSDT_4h", "BTCUSDT_4h"], 0.015, 0.12, 0.04, "G15_Aroon_Donchian_Breakout.pine"),
    ("G19_Donchian_Vol_Surge", add_donchian_volume_surge, ["ETHUSDT_4h", "BTCUSDT_4h", "LINKUSDT_4h"], 0.015, 0.12, 0.04, "G19_Donchian_Volume_Surge.pine"),
]


def run():
    results = []
    total = sum(len(c[2]) for c in CANDIDATES)
    done = 0

    print("=" * 80)
    print(f"REALISTIC BACKTEST — TOP TV-VALIDATED STRATEGIES ({total} combos)")
    print(f"$500 fixed | 0.1% slippage | 30% OOS | SL/TP/TS per strategy")
    print("=" * 80)

    for name, signal_fn, assets, sl, tp, ts, pine in CANDIDATES:
        for asset_key in assets:
            done += 1
            df = load_data(asset_key)
            if df is None:
                continue

            df = calculate_indicators(df)
            try:
                df = signal_fn(df)
            except Exception as e:
                print(f"  [{done}/{total}] ERROR {name} {asset_key}: {e}")
                continue

            try:
                oos = run_backtest_oos(
                    df, {"strategy": name},
                    oos_ratio=0.30,
                    stop_loss=sl, take_profit=tp, trailing_stop=ts,
                    side="both",
                    slippage_pct=0.001,
                    sizing_mode="fixed_notional",
                    fixed_notional_usd=500,
                )
            except Exception as e:
                print(f"  [{done}/{total}] ERROR {name} {asset_key}: {e}")
                continue

            is_m = oos["is"]
            oos_m = oos["oos"]
            is_roi = is_m["roi_pct"] if is_m["roi_pct"] != 0 else 0.001
            retention = oos_m["roi_pct"] / is_roi if is_roi > 0 else 0

            asset = asset_key.split("_")[0]
            passed = oos_m["roi_pct"] > 0 and oos_m["pf"] >= 1.0

            status = "PASS" if passed else "FAIL"
            print(f"  [{done}/{total}] {name:30s} {asset:10s} IS={is_m['roi_pct']:>7.2f}% OOS={oos_m['roi_pct']:>7.2f}% PF={oos_m['pf']:.2f} WR={oos_m['win_rate']:.1f}% DD={oos_m['gdd']:.1f}% [{status}]")

            results.append({
                "strategy": name, "asset": asset, "tf": "4h",
                "pine_file": pine,
                "is_roi": is_m["roi_pct"], "is_pf": is_m["pf"], "is_wr": is_m["win_rate"],
                "oos_roi": oos_m["roi_pct"], "oos_pf": oos_m["pf"], "oos_wr": oos_m["win_rate"],
                "oos_gdd": oos_m["gdd"], "oos_trades": oos_m["trades"], "oos_sharpe": oos_m["sharpe"],
                "retention": round(retention * 100, 1), "status": status,
                "sl": sl, "tp": tp, "ts": ts,
            })

    # Sort by OOS ROI
    results.sort(key=lambda x: x["oos_roi"], reverse=True)
    passed = [r for r in results if r["status"] == "PASS"]

    print(f"\n{'='*80}")
    print(f"RESULTS: {len(passed)} PASSED / {len(results)} tested")
    print(f"{'='*80}")

    # Top 10
    print(f"\n{'='*80}")
    print("TOP 10 STRATEGIES FOR TV VALIDATION")
    print(f"{'='*80}")
    for i, r in enumerate(passed[:10]):
        print(f"\n  #{i+1}  {r['strategy']} on {r['asset']} 4h")
        print(f"      OOS: ROI={r['oos_roi']:.2f}% PF={r['oos_pf']:.2f} WR={r['oos_wr']:.1f}% DD={r['oos_gdd']:.1f}% Trades={r['oos_trades']}")
        print(f"      IS:  ROI={r['is_roi']:.2f}% PF={r['is_pf']:.2f}")
        print(f"      Pine: all_strategies/{r['pine_file']}")
        print(f"      Params: SL={r['sl']*100}% TP={r['tp']*100}% TS={r['ts']*100}%")

    # Save
    out = os.path.join(REPORTS, "TOP10_REALISTIC_STRATEGIES.json")
    with open(out, "w") as f:
        json.dump(passed[:10], f, indent=2)

    all_out = os.path.join(REPORTS, "ALL_REALISTIC_BACKTEST_RESULTS.json")
    with open(all_out, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nSaved: {out}")
    print(f"Saved: {all_out}")


if __name__ == "__main__":
    run()
