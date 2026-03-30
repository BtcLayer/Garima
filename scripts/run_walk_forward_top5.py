"""
Walk-forward validation on the top 5 TV-validated strategies.
Checks for overfitting by testing each strategy on ~1yr rolling windows.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.walk_forward import walk_forward_validate

# ── Top 5 TV-validated strategy-asset combos ─────────────────────

COMBOS = [
    {
        "symbol": "SOLUSDT_4h",
        "tv_roi_yr": "282%",
        "strat": {
            "name": "Aggressive_Entry",
            "strategies": ["Breakout_20", "Volume_Spike", "MACD_Cross", "ADX_Trend"],
            "min_agreement": 2,
            "stop_loss": 0.04,
            "take_profit": 0.15,
            "trailing_stop": 0.005,
        },
    },
    {
        "symbol": "BNBUSDT_4h",
        "tv_roi_yr": "164%",
        "strat": {
            "name": "Aggressive_Entry",
            "strategies": ["Breakout_20", "Volume_Spike", "MACD_Cross", "ADX_Trend"],
            "min_agreement": 2,
            "stop_loss": 0.04,
            "take_profit": 0.15,
            "trailing_stop": 0.005,
        },
    },
    {
        "symbol": "SOLUSDT_4h",
        "tv_roi_yr": "199%",
        "strat": {
            "name": "MACD_Breakout",
            "strategies": ["MACD_Cross", "Breakout_20", "Volume_Spike", "ADX_Trend"],
            "min_agreement": 2,
            "stop_loss": 0.04,
            "take_profit": 0.15,
            "trailing_stop": 0.015,
        },
    },
    {
        "symbol": "BNBUSDT_4h",
        "tv_roi_yr": "136%",
        "strat": {
            "name": "Ichimoku_Trend_Pro",
            "strategies": ["Ichimoku_Bull", "EMA_Cross", "ADX_Trend", "OBV_Rising"],
            "min_agreement": 3,
            "stop_loss": 0.02,
            "take_profit": 0.12,
            "trailing_stop": 0.02,
        },
    },
    {
        "symbol": "ETHUSDT_4h",
        "tv_roi_yr": "131%",
        "strat": {
            "name": "Aggressive_Entry",
            "strategies": ["Breakout_20", "Volume_Spike", "MACD_Cross", "ADX_Trend"],
            "min_agreement": 2,
            "stop_loss": 0.04,
            "take_profit": 0.15,
            "trailing_stop": 0.005,
        },
    },
]


def main():
    print("=" * 80)
    print("WALK-FORWARD VALIDATION — TOP 5 TV-VALIDATED STRATEGIES")
    print("=" * 80)
    print()

    summary_rows = []

    for combo in COMBOS:
        symbol = combo["symbol"]
        strat = combo["strat"]
        tv_roi = combo["tv_roi_yr"]

        print("-" * 80)
        print(f"Strategy: {strat['name']}  |  Asset: {symbol}  |  TV ROI/yr: {tv_roi}")
        print(f"  Signals: {strat['strategies']}")
        print(f"  min_agreement={strat['min_agreement']}  SL={strat['stop_loss']:.0%}  TP={strat['take_profit']:.0%}  TS={strat['trailing_stop']:.1%}")
        print("-" * 80)

        result = walk_forward_validate(symbol, strat, n_windows=6)

        if "error" in result:
            print(f"  ERROR: {result['error']}")
            print()
            continue

        # Per-window table
        print(f"  {'Window':<8} {'Test Rows':<12} {'Test ROI%':<12} {'Test Trades':<14} {'Test WR%':<10}")
        print(f"  {'------':<8} {'---------':<12} {'---------':<12} {'-----------':<14} {'--------':<10}")

        profitable_windows = 0
        for w in result["windows"]:
            roi_str = f"{w['test_roi']:+.1f}%"
            flag = " <-- LOSS" if w["test_roi"] <= 0 else ""
            print(f"  W{w['window']:<6}  {w['test_rows']:<12} {roi_str:<12} {w['test_trades']:<14} {w['test_wr']:.1f}%{flag}")
            if w["test_roi"] > 0:
                profitable_windows += 1

        total_windows = len(result["windows"])
        print()
        print(f"  Avg train ROI:    {result['avg_train_roi']:+.1f}%")
        print(f"  Avg test ROI:     {result['avg_test_roi']:+.1f}%")
        print(f"  Degradation:      {result['degradation_pct']:+.1f}%")
        print(f"  Consistency:      {profitable_windows}/{total_windows} windows profitable ({result['consistency']:.0%})")
        print()

        # Apply user's overfit criterion
        if result["consistency"] < 0.5:
            user_verdict = "OVERFIT (< 50% windows profitable)"
        else:
            user_verdict = result["verdict"]

        print(f"  >>> VERDICT: {user_verdict}")
        print()

        summary_rows.append({
            "strategy": strat["name"],
            "asset": symbol,
            "tv_roi": tv_roi,
            "avg_test_roi": result["avg_test_roi"],
            "consistency": f"{profitable_windows}/{total_windows}",
            "verdict": user_verdict,
        })

    # Final summary table
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  {'Strategy':<22} {'Asset':<16} {'TV ROI':<10} {'Avg Test ROI':<14} {'Consistency':<14} {'Verdict'}")
    print(f"  {'--------':<22} {'-----':<16} {'------':<10} {'------------':<14} {'-----------':<14} {'-------'}")
    for r in summary_rows:
        print(f"  {r['strategy']:<22} {r['asset']:<16} {r['tv_roi']:<10} {r['avg_test_roi']:+.1f}%{'':<9} {r['consistency']:<14} {r['verdict']}")

    print()
    print("=" * 80)
    overfit_count = sum(1 for r in summary_rows if "OVERFIT" in r["verdict"] or "UNSTABLE" in r["verdict"] or "FAIL" in r["verdict"])
    pass_count = len(summary_rows) - overfit_count
    print(f"Result: {pass_count}/{len(summary_rows)} strategies PASS walk-forward,  {overfit_count}/{len(summary_rows)} flagged as problematic")
    print("=" * 80)


if __name__ == "__main__":
    main()
