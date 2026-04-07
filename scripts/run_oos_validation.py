"""G-03: Run OOS/walk-forward validation on frozen shortlist candidates."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run_strategies_batch import (
    load_data, calculate_indicators, run_backtest_oos,
    BACKTEST_SIZING_MODE, BACKTEST_FIXED_NOTIONAL_USD, BACKTEST_REALISM_SLIPPAGE_PCT,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Frozen shortlist from GARIMA_EXECUTION_PLAN
SHORTLIST = [
    {"strategy": "Donchian_Trend", "asset": "ETHUSDT", "tf": "4h", "signal": "donchian_breakout", "sl": 0.015, "tp": 0.12, "ts": 0.04},
    {"strategy": "Donchian_Trend", "asset": "SUIUSDT", "tf": "4h", "signal": "donchian_breakout", "sl": 0.015, "tp": 0.12, "ts": 0.04},
    {"strategy": "CCI_Trend", "asset": "LDOUSDT", "tf": "4h", "signal": "cci_breakout", "sl": 0.015, "tp": 0.12, "ts": 0.04},
    {"strategy": "CCI_Trend", "asset": "ETHUSDT", "tf": "4h", "signal": "cci_breakout", "sl": 0.015, "tp": 0.12, "ts": 0.04},
    {"strategy": "Donchian_Trend", "asset": "AVAXUSDT", "tf": "4h", "signal": "donchian_breakout", "sl": 0.015, "tp": 0.12, "ts": 0.04},
]

OOS_RATIO = 0.30  # 70% train, 30% test
OOS_PASS_THRESHOLD = 0.5  # OOS must retain at least 50% of IS performance


def add_strategy_signals(df, signal_type):
    """Add entry/exit signals based on strategy type."""
    df = df.copy()

    if signal_type == "donchian_breakout":
        don_upper = df["high"].rolling(20).max()
        don_lower = df["low"].rolling(20).min()
        exit_lower = df["low"].rolling(10).min()
        df["entry_signal"] = (df["close"] > don_upper.shift(1)).astype(int) & (df["close"] > df["ema50"]).astype(int) & (df["adx"] > 20).astype(int)
        df["short_entry_signal"] = (df["close"] < don_lower.shift(1)).astype(int) & (df["close"] < df["ema50"]).astype(int) & (df["adx"] > 20).astype(int)
        df["exit_signal"] = (df["close"] < exit_lower.shift(1)).astype(int)
        df["short_exit_signal"] = (df["close"] > df["high"].rolling(10).max().shift(1)).astype(int)

    elif signal_type == "cci_breakout":
        cci = df["cci"]
        df["entry_signal"] = ((cci > 100) & (cci.shift(1) <= 100) & (df["close"] > df["ema50"]) & (df["adx"] > 20)).astype(int)
        df["short_entry_signal"] = ((cci < -100) & (cci.shift(1) >= -100) & (df["close"] < df["ema50"]) & (df["adx"] > 20)).astype(int)
        df["exit_signal"] = ((cci < 0) & (cci.shift(1) >= 0)).astype(int)
        df["short_exit_signal"] = ((cci > 0) & (cci.shift(1) <= 0)).astype(int)

    return df


def run_validation():
    results = []
    print("=" * 70)
    print(f"OOS VALIDATION — {OOS_RATIO*100:.0f}% holdout")
    print(f"Sizing: {BACKTEST_SIZING_MODE} | Notional: ${BACKTEST_FIXED_NOTIONAL_USD}")
    print(f"Slippage: {BACKTEST_REALISM_SLIPPAGE_PCT*100:.2f}%")
    print("=" * 70)

    for candidate in SHORTLIST:
        key = f"{candidate['asset']}_{candidate['tf']}"
        df = load_data(key)
        if df is None:
            print(f"\n  SKIP {candidate['strategy']} {candidate['asset']} — no data")
            continue

        df = calculate_indicators(df)
        df = add_strategy_signals(df, candidate["signal"])

        oos_result = run_backtest_oos(
            df, candidate,
            oos_ratio=OOS_RATIO,
            stop_loss=candidate["sl"],
            take_profit=candidate["tp"],
            trailing_stop=candidate["ts"],
            side="both",
            slippage_pct=BACKTEST_REALISM_SLIPPAGE_PCT,
            sizing_mode=BACKTEST_SIZING_MODE,
            fixed_notional_usd=BACKTEST_FIXED_NOTIONAL_USD,
        )

        is_m = oos_result["is"]
        oos_m = oos_result["oos"]

        # Calculate retention ratio
        is_roi = is_m["roi_pct"] if is_m["roi_pct"] != 0 else 0.001
        retention = oos_m["roi_pct"] / is_roi if is_roi > 0 else 0
        passed = retention >= OOS_PASS_THRESHOLD and oos_m["roi_pct"] > 0 and oos_m["pf"] >= 1.0

        status = "PASS" if passed else "FAIL"

        print(f"\n{'='*50}")
        print(f"  {candidate['strategy']} on {candidate['asset']} {candidate['tf']}")
        print(f"  IS  (70%): ROI={is_m['roi_pct']:>7.1f}% WR={is_m['win_rate']:>5.1f}% PF={is_m['pf']:>5.2f} GDD={is_m['gdd']:>5.1f}% Trades={is_m['trades']}")
        print(f"  OOS (30%): ROI={oos_m['roi_pct']:>7.1f}% WR={oos_m['win_rate']:>5.1f}% PF={oos_m['pf']:>5.2f} GDD={oos_m['gdd']:>5.1f}% Trades={oos_m['trades']}")
        print(f"  Retention: {retention*100:.0f}% | OOS Status: {'[PASS] ' + status if passed else '[FAIL] ' + status}")

        results.append({
            "strategy": candidate["strategy"],
            "asset": candidate["asset"],
            "timeframe": candidate["tf"],
            "is_roi": is_m["roi_pct"],
            "is_wr": is_m["win_rate"],
            "is_pf": is_m["pf"],
            "is_gdd": is_m["gdd"],
            "is_trades": is_m["trades"],
            "oos_roi": oos_m["roi_pct"],
            "oos_wr": oos_m["win_rate"],
            "oos_pf": oos_m["pf"],
            "oos_gdd": oos_m["gdd"],
            "oos_trades": oos_m["trades"],
            "retention_pct": round(retention * 100, 1),
            "oos_status": status,
            "sizing_mode": BACKTEST_SIZING_MODE,
            "slippage": BACKTEST_REALISM_SLIPPAGE_PCT,
        })

    # Save results
    out_path = os.path.join(ROOT, "reports", "OOS_VALIDATION_RESULTS.json")
    json.dump(results, open(out_path, "w"), indent=2)

    # Summary
    passed = [r for r in results if r["oos_status"] == "PASS"]
    failed = [r for r in results if r["oos_status"] == "FAIL"]

    print(f"\n{'='*70}")
    print(f"SUMMARY: {len(passed)} PASSED, {len(failed)} FAILED out of {len(results)}")
    print(f"{'='*70}")

    if passed:
        print("\n[PASS] OOS-VALIDATED (ready for paper trade):")
        for r in passed:
            print(f"   {r['strategy']} {r['asset']} — OOS ROI={r['oos_roi']:.1f}% Retention={r['retention_pct']:.0f}%")

    if failed:
        print("\n[FAIL] OOS-FAILED (do not promote):")
        for r in failed:
            print(f"   {r['strategy']} {r['asset']} — OOS ROI={r['oos_roi']:.1f}% Retention={r['retention_pct']:.0f}%")

    return results


if __name__ == "__main__":
    run_validation()
