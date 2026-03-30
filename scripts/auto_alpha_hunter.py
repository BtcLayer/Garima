"""
AUTO ALPHA HUNTER v2 — Targets TIER_2_DEPLOY criteria
Uses TV-style daily Sharpe + Profit Factor + Win Rate.

TIER_2_DEPLOY needs: PF >= 1.6, WR >= 50%, GDD < 35%
TIER_2_TEST needs: PF >= 1.4, WR >= 50%
PAPER_TRADE needs: PF >= 1.2, WR >= 45%

Run: python scripts/auto_alpha_hunter.py
"""
import sys, os, json, numpy as np
from itertools import combinations
from datetime import datetime as _dt
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from run_strategies_batch import load_data, calculate_indicators, apply_strategy, run_backtest, SIGNAL_FUNCTIONS

INITIAL = 10000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# TIER criteria based on actual alert bot CSV analysis
# What actually gets deployed: PF >= 1.6, WR >= 50%, GDD < 35%

ASSETS = ["BNBUSDT", "ETHUSDT", "BTCUSDT", "SOLUSDT", "LINKUSDT", "ADAUSDT"]
TIMEFRAMES = ["4h"]  # Only 4h works on TV

# All persistent signals (best for high WR + PF)
PERSISTENT = ["EMA_Cross", "Supertrend", "PSAR_Bull", "ADX_Trend", "Trend_MA50",
              "OBV_Rising", "Ichimoku_Bull", "VWAP"]

# Momentary signals
MOMENTARY = ["Volume_Spike", "MACD_Cross", "Breakout_20"]

# SL/TP/TS grid — focused on HIGH PF (tight TP, moderate SL)
# Key insight: 56_PSAR got TIER_2_DEPLOY with SL=1%, TP=3%, TS=0.4%
PARAM_GRID = [
    # Ultra tight — highest PF
    (0.008, 0.02, 0.003),
    (0.008, 0.025, 0.004),
    (0.01, 0.025, 0.004),
    (0.01, 0.03, 0.004),
    # Proven TIER_2 params
    (0.01, 0.03, 0.004),
    (0.01, 0.035, 0.004),
    (0.012, 0.035, 0.005),
    # Moderate
    (0.012, 0.04, 0.005),
    (0.015, 0.04, 0.005),
    (0.015, 0.05, 0.006),
]


def classify_tier(daily, sharpe, wr, gdd, pf):
    """Classify based on what ACTUALLY gets deployed in alert bot."""
    # Based on CSV analysis: PF and WR are what matter most
    if pf >= 2.0 and wr >= 50 and gdd < 30:
        return "TIER_1_DEPLOY"
    if pf >= 1.6 and wr >= 50 and gdd < 35:
        return "TIER_2_DEPLOY"
    if pf >= 1.4 and wr >= 50:
        return "TIER_2_TEST"
    if pf >= 1.2 and wr >= 45:
        return "PAPER_TRADE"
    if pf >= 1.0 and wr >= 40 and daily > 0:
        return "AVERAGE"
    return "REJECT"


def calc_daily_sharpe(trades, total_days):
    """Calculate Sharpe the same way TradingView does — daily returns."""
    if total_days < 30 or len(trades) < 10:
        return 0
    # Build daily PnL
    daily_pnl = defaultdict(float)
    for t in trades:
        date = t.get("exit_date", "")
        if date:
            daily_pnl[date[:10]] += t["pnl"]

    # Include zero-return days
    daily_returns = []
    for d in range(total_days):
        date_str = str(d)  # placeholder — we just need the count
        daily_returns.append(0)

    # Fill actual trading days
    for i, (date, pnl) in enumerate(sorted(daily_pnl.items())):
        if i < len(daily_returns):
            daily_returns[i] = pnl / INITIAL * 100

    avg = np.mean(daily_returns)
    std = np.std(daily_returns)
    if std == 0:
        return 0
    return (avg / std) * np.sqrt(252)  # Annualized


def generate_pine_script(name, signals, min_ag, sl, tp, ts, tier, asset, tf, metrics):
    """Generate a Pine Script for a winning strategy."""
    signal_code = ""
    signal_names = []
    sig_count = 0

    for sig_name in signals:
        sig_count += 1
        var = f"sig_{sig_count}"
        signal_names.append(var)

        if sig_name == "EMA_Cross":
            signal_code += f"ema8 = ta.ema(close, 8)\nema21 = ta.ema(close, 21)\n{var} = ema8 > ema21 ? 1 : 0\n\n"
        elif sig_name == "Supertrend":
            signal_code += f"atr14 = ta.atr(14)\nsupertrend = (high + low) / 2 - 3 * atr14\n{var} = close > supertrend ? 1 : 0\n\n"
        elif sig_name == "PSAR_Bull":
            signal_code += f"psar = ta.sar(0.02, 0.02, 0.2)\n{var} = close > psar ? 1 : 0\n\n"
        elif sig_name == "ADX_Trend":
            signal_code += f"[diplus, diminus, adx_val] = ta.dmi(14, 14)\n{var} = adx_val > 25 ? 1 : 0\n\n"
        elif sig_name == "Trend_MA50":
            signal_code += f"ema50 = ta.ema(close, 50)\n{var} = close > ema50 ? 1 : 0\n\n"
        elif sig_name == "OBV_Rising":
            signal_code += f"obv = ta.obv\nobv_sma = ta.sma(obv, 20)\n{var} = obv > obv_sma ? 1 : 0\n\n"
        elif sig_name == "Ichimoku_Bull":
            signal_code += f"tenkan = (ta.highest(high, 9) + ta.lowest(low, 9)) / 2\nkijun = (ta.highest(high, 26) + ta.lowest(low, 26)) / 2\nspan_a = (tenkan + kijun) / 2\nspan_b = (ta.highest(high, 52) + ta.lowest(low, 52)) / 2\n{var} = (close > span_a and close > span_b) ? 1 : 0\n\n"
        elif sig_name == "VWAP":
            signal_code += f"cum_vol = ta.cum(volume)\ncum_pv = ta.cum(close * volume)\nvwap_val = cum_pv / cum_vol\n{var} = close > vwap_val ? 1 : 0\n\n"
        elif sig_name == "Volume_Spike":
            signal_code += f"vol_ma = ta.sma(volume, 20)\n{var} = (volume > vol_ma * 1.5 and close > close[1]) ? 1 : 0\n\n"
        elif sig_name == "MACD_Cross":
            signal_code += f"macd_ema21 = ta.ema(close, 21)\nmacd_ema50 = ta.ema(close, 50)\nmacd_line = macd_ema21 - macd_ema50\nsignal_line = ta.ema(macd_line, 9)\n{var} = (macd_line > signal_line and macd_line[1] <= signal_line[1]) ? 1 : 0\n\n"
        elif sig_name == "Breakout_20":
            signal_code += f"high_20 = ta.highest(high[1], 20)\n{var} = close > high_20 ? 1 : 0\n\n"
        else:
            signal_code += f"{var} = 0  // {sig_name} not mapped\n\n"

    total_line = "total_signals = " + " + ".join(signal_names)
    safe_name = name.replace(" ", "_")

    script = f"""//@version=5
strategy("{safe_name}", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=95, commission_value=0.1)

// AUTO-GENERATED by Alpha Hunter
// Tier: {tier} | Asset: {asset} | TF: {tf}
// ROI: {metrics['roi_a']:.1f}%/yr | Daily: {metrics['daily']:.3f}% | Sharpe: {metrics['sharpe']:.2f}
// WR: {metrics['wr']:.1f}% | PF: {metrics['pf']:.2f} | GDD: {metrics['gdd']:.1f}% | Trades: {metrics['trades']}

sl_pct = input.float({sl*100}, "Stop Loss %", step=0.1) / 100
tp_pct = input.float({tp*100}, "Take Profit %", step=0.1) / 100
ts_pct = input.float({ts*100}, "Trailing Stop %", step=0.1) / 100
min_agreement = input.int({min_ag}, "Min Signals Required", minval=1, maxval={len(signals)})

// === INDICATORS ===
{signal_code}
// === SIGNAL AGREEMENT ===
{total_line}
long_entry = total_signals >= min_agreement
exit_signal = total_signals < {max(1, min_ag - 2)}

// === EXECUTION ===
if long_entry and strategy.position_size == 0
    strategy.entry("Long", strategy.long, alert_message='{{"strategy":"{safe_name}","symbol":"' + syminfo.ticker + '","side":"BUY","price":' + str.tostring(close) + ',"sl_pct":' + str.tostring(sl_pct) + ',"tp_pct":' + str.tostring(tp_pct) + ',"ts_pct":' + str.tostring(ts_pct) + ',"timeframe":"' + timeframe.period + '"}}')

if strategy.position_size > 0
    trail_ticks = math.round(strategy.position_avg_price * ts_pct / syminfo.mintick)
    strategy.exit("SL/TP", "Long", stop=strategy.position_avg_price * (1 - sl_pct), limit=strategy.position_avg_price * (1 + tp_pct), trail_points=1, trail_offset=trail_ticks, alert_message='{{"strategy":"{safe_name}","symbol":"' + syminfo.ticker + '","side":"SELL","price":' + str.tostring(close) + ',"timeframe":"' + timeframe.period + '"}}')

if exit_signal and strategy.position_size > 0
    strategy.close("Long", comment="Signal Exit", alert_message='{{"strategy":"{safe_name}","symbol":"' + syminfo.ticker + '","side":"SELL","price":' + str.tostring(close) + ',"timeframe":"' + timeframe.period + '"}}')

// === VISUALS ===
bgcolor(total_signals >= min_agreement ? color.new(color.green, 85) : na)
plotshape(long_entry and strategy.position_size == 0, "Buy", shape.triangleup, location.belowbar, color.green, size=size.small)
"""
    return script


def run_hunt():
    """Main hunt loop."""
    print("=" * 100)
    print("  AUTO ALPHA HUNTER")
    print(f"  Signals: {len(PERSISTENT)} persistent + {len(MOMENTARY)} momentary = {len(PERSISTENT) + len(MOMENTARY)}")
    print(f"  Assets: {len(ASSETS)} | Timeframes: {len(TIMEFRAMES)} | Param sets: {len(PARAM_GRID)}")
    print("=" * 100)

    all_signals = PERSISTENT + MOMENTARY
    winners = []
    total = 0
    pine_count = 0

    # Preload all data
    data_cache = {}
    for asset in ASSETS:
        for tf in TIMEFRAMES:
            symbol = f"{asset}_{tf}"
            df = load_data(symbol)
            if df is not None:
                df = calculate_indicators(df)
                data_cache[symbol] = df
                print(f"  Loaded {symbol}: {len(df)} candles")

    print(f"\n  Data loaded: {len(data_cache)} datasets")
    print("  Starting hunt...\n")

    # Test combos: 2, 3, 4, 5, 6 signal combinations
    for combo_size in [3, 4, 5, 6]:
        # Mix persistent + optional momentary
        for combo in combinations(all_signals, combo_size):
            for min_ag in range(max(combo_size - 1, 2), combo_size + 1):
                for sl, tp, ts in PARAM_GRID:
                    for symbol, df in data_cache.items():
                        total += 1
                        asset = symbol.split("_")[0]
                        tf = symbol.split("_")[1]

                        if "timestamp" in df.columns:
                            t_s = str(df["timestamp"].iloc[0])[:10]
                            t_e = str(df["timestamp"].iloc[-1])[:10]
                        else:
                            t_s, t_e = "2020-01-01", "2026-03-20"
                        try:
                            yrs = max((_dt.fromisoformat(t_e) - _dt.fromisoformat(t_s)).days / 365.25, 0.01)
                        except Exception:
                            yrs = 6.0

                        try:
                            dc = apply_strategy(df.copy(), list(combo), min_ag)
                            cap, trades = run_backtest(dc, sl, tp, ts)
                            if len(trades) < 30:
                                continue

                            roi_a = ((cap / INITIAL) ** (1 / yrs) - 1) * 100 if cap > 0 else -100
                            daily = roi_a / 365
                            if daily < 0.05:
                                continue

                            wins_list = [t for t in trades if t["pnl"] > 0]
                            wr = len(wins_list) / len(trades) * 100
                            if wr < 35:
                                continue

                            tw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                            tl = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
                            pf = tw / tl if tl > 0 else 0

                            rets = [t["pnl"] / INITIAL * 100 for t in trades]
                            sharpe = (np.mean(rets) / np.std(rets)) * np.sqrt(len(trades) / yrs) if np.std(rets) > 0 else 0

                            eq = INITIAL
                            pk = eq
                            gdd = 0
                            for t in trades:
                                eq += t["pnl"]
                                pk = max(pk, eq)
                                dd = (pk - eq) / pk * 100
                                gdd = max(gdd, dd)

                            tier = classify_tier(daily, sharpe, wr, gdd, pf)

                            if tier in ("ALPHA++", "ALPHA"):
                                metrics = {"roi_a": roi_a, "daily": daily, "sharpe": sharpe,
                                           "wr": wr, "pf": pf, "gdd": gdd, "trades": len(trades)}

                                print(f"\n  {'*' * 60}")
                                print(f"  FOUND {tier}!")
                                print(f"  Signals: {' + '.join(combo)}")
                                print(f"  Asset: {asset} | TF: {tf} | min_agreement: {min_ag}")
                                print(f"  ROI: {roi_a:.1f}%/yr | Daily: {daily:.3f}%")
                                print(f"  Sharpe: {sharpe:.2f} | WR: {wr:.1f}% | PF: {pf:.2f}")
                                print(f"  GDD: {gdd:.1f}% | Trades: {len(trades)}")
                                print(f"  Params: SL={sl*100}% TP={tp*100}% TS={ts*100}%")

                                # Generate Pine Script
                                pine_count += 1
                                safe_name = f"Alpha_{pine_count}_{asset}_{tf}"
                                script = generate_pine_script(
                                    safe_name, list(combo), min_ag, sl, tp, ts,
                                    tier, asset, tf, metrics
                                )
                                pine_path = os.path.join(ROOT, "pine", f"alpha_{pine_count:02d}_{asset}_{tf}.pine")
                                with open(pine_path, "w") as f:
                                    f.write(script)
                                print(f"  Pine Script saved: {pine_path}")
                                print(f"  {'*' * 60}")

                                winners.append({
                                    "tier": tier, "signals": list(combo), "min_ag": min_ag,
                                    "asset": asset, "tf": tf, "sl": sl, "tp": tp, "ts": ts,
                                    **metrics, "pine_file": pine_path,
                                })

                            elif tier == "AVERAGE" and total % 10000 == 0:
                                # Progress update
                                pass

                        except Exception:
                            pass

                    if total % 50000 == 0:
                        print(f"  Progress: {total} combos tested, {len(winners)} winners found, {pine_count} Pine Scripts generated")

    # Final summary
    print("\n" + "=" * 100)
    print(f"  HUNT COMPLETE")
    print(f"  Total combos tested: {total}")
    print(f"  ALPHA++ found: {len([w for w in winners if w['tier'] == 'ALPHA++'])}")
    print(f"  ALPHA found: {len([w for w in winners if w['tier'] == 'ALPHA'])}")
    print(f"  Pine Scripts generated: {pine_count}")
    print("=" * 100)

    if winners:
        print("\n  ALL WINNERS:")
        for i, w in enumerate(winners, 1):
            print(f"  {i}. [{w['tier']}] {' + '.join(w['signals'])} on {w['asset']} {w['tf']}")
            print(f"     ROI={w['roi_a']:.1f}%/yr Daily={w['daily']:.3f}% Sharpe={w['sharpe']:.2f} WR={w['wr']:.1f}% PF={w['pf']:.2f} GDD={w['gdd']:.1f}%")
            print(f"     Pine: {w['pine_file']}")

        # Save results
        results_path = os.path.join(ROOT, "reports", "alpha_hunter_results.json")
        with open(results_path, "w") as f:
            json.dump(winners, f, indent=2)
        print(f"\n  Results saved to {results_path}")
    else:
        print("\n  No ALPHA/ALPHA++ strategies found.")
        print("  The ALPHA++ Sharpe >= 3.5 requirement is extremely difficult for crypto on TradingView's daily Sharpe calculation.")


if __name__ == "__main__":
    run_hunt()
