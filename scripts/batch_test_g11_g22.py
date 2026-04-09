#!/usr/bin/env python3
"""Batch backtest all 12 new G11-G22 strategies across top 5 assets.
Uses realistic settings: $500 fixed, 0.1% slippage, 30% OOS.
Outputs ranked results + sends Telegram notification for winners.
"""
import sys, os, json, datetime, requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault("BACKTEST_SIZING_MODE", "fixed_notional")
os.environ.setdefault("BACKTEST_FIXED_NOTIONAL_USD", "500")
os.environ.setdefault("BACKTEST_SLIPPAGE_PCT", "0.001")

from run_strategies_batch import load_data, calculate_indicators, run_backtest_oos

REPORTS = os.path.join(ROOT, "reports")
STORAGE = os.path.join(ROOT, "storage")

# ── Telegram ──
BOT_TOKEN = ""
CHAT_ID = ""
env_path = os.path.join(ROOT, ".env")
try:
    for line in open(env_path):
        line = line.strip()
        if "BOT_TOKEN" in line and "=" in line and not line.startswith("#"):
            BOT_TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
        if "CHAT_ID" in line and "=" in line and not line.startswith("#"):
            CHAT_ID = line.split("=", 1)[1].strip().strip('"').strip("'").split(",")[0]
except Exception:
    pass


def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
    except Exception:
        pass


# ── G11-G22 strategy signal definitions ──
# Each uses proven Donchian/CCI winning DNA with tiered entry

def add_g11_donchian_cci_power(df):
    """G11: Donchian breakout + CCI momentum confirmation."""
    df = df.copy()
    don_upper = df["high"].rolling(20).max()
    don_lower = df["low"].rolling(20).min()
    exit_lower = df["low"].rolling(10).min()
    exit_upper = df["high"].rolling(10).max()
    cci = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())

    long_strong = (df["close"] > don_upper.shift(1)) & (cci > 100) & (df["close"] > df["ema50"]) & (df["adx"] > 25)
    long_medium = (df["close"] > don_upper.shift(1)) & (cci > 50) & (df["close"] > df["ema50"]) & (df["adx"] > 20)
    df["entry_signal"] = (long_strong | long_medium).astype(int)

    short_strong = (df["close"] < don_lower.shift(1)) & (cci < -100) & (df["close"] < df["ema50"]) & (df["adx"] > 25)
    short_medium = (df["close"] < don_lower.shift(1)) & (cci < -50) & (df["close"] < df["ema50"]) & (df["adx"] > 20)
    df["short_entry_signal"] = (short_strong | short_medium).astype(int)

    df["exit_signal"] = ((df["close"] < exit_lower.shift(1)) | (cci < 0)).astype(int)
    df["short_exit_signal"] = ((df["close"] > exit_upper.shift(1)) | (cci > 0)).astype(int)
    return df


def add_g12_supertrend_donchian(df):
    """G12: SuperTrend trend + Donchian breakout entry."""
    df = df.copy()
    atr = df["atr"]
    hl2 = (df["high"] + df["low"]) / 2
    upper_band = hl2 + 3.0 * atr
    lower_band = hl2 - 3.0 * atr

    st = upper_band.copy()
    for i in range(1, len(df)):
        if df["close"].iloc[i-1] > st.iloc[i-1]:
            st.iloc[i] = max(lower_band.iloc[i], st.iloc[i-1]) if df["close"].iloc[i] > lower_band.iloc[i] else upper_band.iloc[i]
        else:
            st.iloc[i] = min(upper_band.iloc[i], st.iloc[i-1]) if df["close"].iloc[i] < upper_band.iloc[i] else lower_band.iloc[i]

    don_upper = df["high"].rolling(20).max()
    don_lower = df["low"].rolling(20).min()
    trend_up = df["close"] > st
    trend_dn = df["close"] < st

    df["entry_signal"] = (trend_up & (df["close"] > don_upper.shift(1)) & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = (trend_dn & (df["close"] < don_lower.shift(1)) & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = (trend_dn | (df["close"] < df["low"].rolling(10).min().shift(1))).astype(int)
    df["short_exit_signal"] = (trend_up | (df["close"] > df["high"].rolling(10).max().shift(1))).astype(int)
    return df


def add_g13_macd_donchian(df):
    """G13: MACD crossover + Donchian trend confirmation."""
    df = df.copy()
    macd = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
    signal = macd.ewm(span=9).mean()
    don_upper = df["high"].rolling(20).max()
    don_lower = df["low"].rolling(20).min()

    macd_cross_up = (macd > signal) & (macd.shift(1) <= signal.shift(1))
    macd_cross_dn = (macd < signal) & (macd.shift(1) >= signal.shift(1))

    df["entry_signal"] = (macd_cross_up & (df["close"] > don_upper.shift(1)) & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = (macd_cross_dn & (df["close"] < don_lower.shift(1)) & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = (macd_cross_dn | (df["close"] < df["low"].rolling(10).min().shift(1))).astype(int)
    df["short_exit_signal"] = (macd_cross_up | (df["close"] > df["high"].rolling(10).max().shift(1))).astype(int)
    return df


def add_g14_cci_rsi_double(df):
    """G14: CCI + RSI double momentum confirmation."""
    df = df.copy()
    cci = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    rsi = df["rsi"]

    df["entry_signal"] = ((cci > 100) & (rsi > 60) & (df["close"] > df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = ((cci < -100) & (rsi < 40) & (df["close"] < df["ema50"]) & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = ((cci < 0) | (rsi < 40)).astype(int)
    df["short_exit_signal"] = ((cci > 0) | (rsi > 60)).astype(int)
    return df


def add_g15_aroon_donchian(df):
    """G15: Aroon crossover + Donchian breakout."""
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


def add_g16_cci_keltner(df):
    """G16: CCI momentum + Keltner Channel breakout."""
    df = df.copy()
    cci = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    kc_mid = df["close"].ewm(span=20).mean()
    kc_upper = kc_mid + 1.5 * df["atr"]
    kc_lower = kc_mid - 1.5 * df["atr"]

    df["entry_signal"] = ((cci > 100) & (df["close"] > kc_upper) & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = ((cci < -100) & (df["close"] < kc_lower) & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = ((cci < 0) | (df["close"] < kc_mid)).astype(int)
    df["short_exit_signal"] = ((cci > 0) | (df["close"] > kc_mid)).astype(int)
    return df


def add_g17_donchian_psar(df):
    """G17: Donchian breakout + PSAR trend confirmation."""
    df = df.copy()
    don_upper = df["high"].rolling(20).max()
    don_lower = df["low"].rolling(20).min()
    # Simple PSAR approximation
    psar = df["close"].ewm(span=5).mean()

    df["entry_signal"] = ((df["close"] > don_upper.shift(1)) & (df["close"] > psar) & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = ((df["close"] < don_lower.shift(1)) & (df["close"] < psar) & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = ((df["close"] < psar) | (df["close"] < df["low"].rolling(10).min().shift(1))).astype(int)
    df["short_exit_signal"] = ((df["close"] > psar) | (df["close"] > df["high"].rolling(10).max().shift(1))).astype(int)
    return df


def add_g18_cci_adx_power(df):
    """G18: CCI + strong ADX trend power."""
    df = df.copy()
    cci = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())

    df["entry_signal"] = ((cci > 100) & (df["adx"] > 30) & (df["close"] > df["ema50"])).astype(int)
    df["short_entry_signal"] = ((cci < -100) & (df["adx"] > 30) & (df["close"] < df["ema50"])).astype(int)
    df["exit_signal"] = ((cci < 0) | (df["adx"] < 15)).astype(int)
    df["short_exit_signal"] = ((cci > 0) | (df["adx"] < 15)).astype(int)
    return df


def add_g19_donchian_volume(df):
    """G19: Donchian breakout + volume surge confirmation."""
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


def add_g20_stoch_donchian(df):
    """G20: Stochastic + Donchian trend."""
    df = df.copy()
    low14 = df["low"].rolling(14).min()
    high14 = df["high"].rolling(14).max()
    stoch_k = ((df["close"] - low14) / (high14 - low14) * 100).fillna(50)
    stoch_d = stoch_k.rolling(3).mean()
    don_upper = df["high"].rolling(20).max()
    don_lower = df["low"].rolling(20).min()

    df["entry_signal"] = ((stoch_k > 20) & (stoch_k.shift(1) <= 20) & (df["close"] > don_upper.shift(1)) & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = ((stoch_k < 80) & (stoch_k.shift(1) >= 80) & (df["close"] < don_lower.shift(1)) & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = ((stoch_k > 80) | (df["close"] < df["low"].rolling(10).min().shift(1))).astype(int)
    df["short_exit_signal"] = ((stoch_k < 20) | (df["close"] > df["high"].rolling(10).max().shift(1))).astype(int)
    return df


def add_g21_cci_ichimoku(df):
    """G21: CCI + Ichimoku cloud trend."""
    df = df.copy()
    cci = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    tenkan = (df["high"].rolling(9).max() + df["low"].rolling(9).min()) / 2
    kijun = (df["high"].rolling(26).max() + df["low"].rolling(26).min()) / 2
    senkou_a = ((tenkan + kijun) / 2).shift(26)
    senkou_b = ((df["high"].rolling(52).max() + df["low"].rolling(52).min()) / 2).shift(26)
    above_cloud = (df["close"] > senkou_a) & (df["close"] > senkou_b)
    below_cloud = (df["close"] < senkou_a) & (df["close"] < senkou_b)

    df["entry_signal"] = ((cci > 100) & above_cloud & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = ((cci < -100) & below_cloud & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = ((cci < 0) | ~above_cloud).astype(int)
    df["short_exit_signal"] = ((cci > 0) | ~below_cloud).astype(int)
    return df


def add_g22_donchian_ema_ribbon(df):
    """G22: Donchian breakout + EMA ribbon alignment."""
    df = df.copy()
    don_upper = df["high"].rolling(20).max()
    don_lower = df["low"].rolling(20).min()
    ema8 = df["ema8"]
    ema21 = df["ema21"]
    ema50 = df["ema50"]
    ribbon_bull = (ema8 > ema21) & (ema21 > ema50)
    ribbon_bear = (ema8 < ema21) & (ema21 < ema50)

    df["entry_signal"] = ((df["close"] > don_upper.shift(1)) & ribbon_bull & (df["adx"] > 20)).astype(int)
    df["short_entry_signal"] = ((df["close"] < don_lower.shift(1)) & ribbon_bear & (df["adx"] > 20)).astype(int)
    df["exit_signal"] = (~ribbon_bull | (df["close"] < df["low"].rolling(10).min().shift(1))).astype(int)
    df["short_exit_signal"] = (~ribbon_bear | (df["close"] > df["high"].rolling(10).max().shift(1))).astype(int)
    return df


# ── Strategy registry ──
STRATEGIES = {
    "G11_Donchian_CCI_Power": add_g11_donchian_cci_power,
    "G12_SuperTrend_Donchian": add_g12_supertrend_donchian,
    "G13_MACD_Donchian_Trend": add_g13_macd_donchian,
    "G14_CCI_RSI_Double": add_g14_cci_rsi_double,
    "G15_Aroon_Donchian": add_g15_aroon_donchian,
    "G16_CCI_Keltner_Fusion": add_g16_cci_keltner,
    "G17_Donchian_PSAR": add_g17_donchian_psar,
    "G18_CCI_ADX_Power": add_g18_cci_adx_power,
    "G19_Donchian_Volume_Surge": add_g19_donchian_volume,
    "G20_Stoch_Donchian": add_g20_stoch_donchian,
    "G21_CCI_Ichimoku": add_g21_cci_ichimoku,
    "G22_Donchian_EMA_Ribbon": add_g22_donchian_ema_ribbon,
}

ASSETS = ["ETHUSDT_4h", "BTCUSDT_4h", "SOLUSDT_4h", "AVAXUSDT_4h", "LINKUSDT_4h"]
SL, TP, TS = 0.015, 0.12, 0.04


def run():
    results = []
    total = len(STRATEGIES) * len(ASSETS)
    done = 0

    print("=" * 70)
    print(f"G11-G22 BATCH BACKTEST — {total} combos")
    print(f"Settings: $500 fixed, 0.1% slippage, 30% OOS, SL={SL*100}% TP={TP*100}% TS={TS*100}%")
    print("=" * 70)

    for strat_name, signal_fn in STRATEGIES.items():
        for asset_key in ASSETS:
            done += 1
            df = load_data(asset_key)
            if df is None:
                print(f"  [{done}/{total}] SKIP {strat_name} {asset_key} — no data")
                continue

            df = calculate_indicators(df)
            try:
                df = signal_fn(df)
            except Exception as e:
                print(f"  [{done}/{total}] ERROR {strat_name} {asset_key}: {e}")
                continue

            try:
                oos = run_backtest_oos(
                    df, {"strategy": strat_name},
                    oos_ratio=0.30,
                    stop_loss=SL, take_profit=TP, trailing_stop=TS,
                    side="both",
                    slippage_pct=0.001,
                    sizing_mode="fixed_notional",
                    fixed_notional_usd=500,
                )
            except Exception as e:
                print(f"  [{done}/{total}] BACKTEST ERROR {strat_name} {asset_key}: {e}")
                continue

            is_m = oos["is"]
            oos_m = oos["oos"]
            is_roi = is_m["roi_pct"] if is_m["roi_pct"] != 0 else 0.001
            retention = oos_m["roi_pct"] / is_roi if is_roi > 0 else 0
            passed = retention >= 0.5 and oos_m["roi_pct"] > 0 and oos_m["pf"] >= 1.0

            asset = asset_key.replace("_4h", "")
            status = "PASS" if passed else "FAIL"
            print(f"  [{done}/{total}] {strat_name} {asset}: IS={is_m['roi_pct']:>6.1f}% OOS={oos_m['roi_pct']:>6.1f}% PF={oos_m['pf']:.2f} [{status}]")

            results.append({
                "strategy": strat_name, "asset": asset, "tf": "4h",
                "is_roi": is_m["roi_pct"], "is_pf": is_m["pf"], "is_wr": is_m["win_rate"],
                "oos_roi": oos_m["roi_pct"], "oos_pf": oos_m["pf"], "oos_wr": oos_m["win_rate"],
                "oos_gdd": oos_m["gdd"], "oos_trades": oos_m["trades"],
                "retention": round(retention * 100, 1), "status": status,
            })

    # Sort by OOS ROI
    results.sort(key=lambda x: x["oos_roi"], reverse=True)

    # Save
    out_path = os.path.join(REPORTS, "G11_G22_BACKTEST_RESULTS.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    # Summary
    passed = [r for r in results if r["status"] == "PASS"]
    print(f"\n{'='*70}")
    print(f"RESULTS: {len(passed)} PASSED / {len(results)} tested")
    print(f"{'='*70}")

    if passed:
        print("\nTOP PERFORMERS (OOS-validated):")
        for r in passed[:10]:
            print(f"  {r['strategy']} {r['asset']}: OOS ROI={r['oos_roi']:.1f}% PF={r['oos_pf']:.2f} WR={r['oos_wr']:.1f}%")

        # Send Telegram
        msg = f"*G11-G22 Backtest Complete*\n{len(passed)} PASS / {len(results)} tested\n\n"
        for r in passed[:5]:
            msg += f"`{r['strategy']}` {r['asset']}: OOS {r['oos_roi']:.1f}% PF={r['oos_pf']:.2f}\n"
        msg += f"\nUse best performers for TV validation next."
        send_telegram(msg)
    else:
        send_telegram(f"*G11-G22 Backtest*: 0/{len(results)} passed OOS validation.")

    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    run()
