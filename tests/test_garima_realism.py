import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _make_trade_df():
    rows = []
    price = 100.0
    for i in range(12):
        rows.append(
            {
                "timestamp": f"2026-01-01 00:{i:02d}:00",
                "open": price,
                "high": price * 1.02,
                "low": price * 0.99,
                "close": price * (1.01 if i % 2 == 0 else 1.0),
                "entry_signal": 1 if i in {0, 4, 8} else 0,
                "exit_signal": 1 if i in {2, 6, 10} else 0,
                "short_entry_signal": 0,
                "short_exit_signal": 0,
            }
        )
        price *= 1.01
    return pd.DataFrame(rows)


def test_run_backtest_uses_capped_notional_by_default():
    from run_strategies_batch import BACKTEST_FIXED_NOTIONAL_USD, run_backtest

    _, trades = run_backtest(
        _make_trade_df(),
        side="long",
        slippage_pct=0.0,
        sizing_mode="fixed_notional",
        fixed_notional_usd=BACKTEST_FIXED_NOTIONAL_USD,
        max_position_pct=0.10,
    )

    assert trades
    assert max(t["notional_usd"] for t in trades) <= BACKTEST_FIXED_NOTIONAL_USD + 1


def test_freeze_paper_candidates_prefers_validated_4h_rows():
    from src.garima_realism import freeze_paper_candidates

    frame = pd.DataFrame(
        [
            {
                "source_file": "combo_strategy_results_good.csv",
                "strategy_display": "Donchian Trend BINANCEUSDT.P 2026-04-03",
                "strategy": "Donchian Trend",
                "asset": "SUI",
                "timeframe": "4h",
                "annualization_metric": "ROI_Annual_Percent",
                "annualized_return_pct": 785.55,
                "roi_per_day_pct": 2.1522,
                "win_rate_percent": 84.66,
                "profit_factor": 9.86,
                "gross_drawdown_percent": 11.27,
                "total_trades": 378,
                "deployment_status": "TIER_1",
                "status_group": "PAPER_STRONG",
                "credibility_score": 110.0,
                "flags": "",
                "eligible_for_paper": True,
                "promotion_gate": "BLOCKED_PENDING_OOS",
                "oos_status": "PENDING_WALK_FORWARD",
                "paper_trade_recommendation": "YES",
            },
            {
                "source_file": "combo_strategy_results_cagr.csv",
                "strategy_display": "Aroon Oscillator Fusion BINANCEUSDT.P 2026-04-06",
                "strategy": "Aroon Oscillator Fusion",
                "asset": "MAGIC",
                "timeframe": "15m",
                "annualization_metric": "CAGR_Percent",
                "annualized_return_pct": 19088.14,
                "roi_per_day_pct": 1.4497,
                "win_rate_percent": 91.9,
                "profit_factor": 8.0,
                "gross_drawdown_percent": 91.83,
                "total_trades": 500,
                "deployment_status": "IGNORE",
                "status_group": "REJECT",
                "credibility_score": 5.0,
                "flags": "NON_4H,BAD_STATUS,HIGH_DRAWDOWN",
                "eligible_for_paper": False,
                "promotion_gate": "NOT_SHORTLISTED",
                "oos_status": "NOT_APPLICABLE",
                "paper_trade_recommendation": "NO",
            },
        ]
    )

    shortlist = freeze_paper_candidates(frame, limit=5)

    assert len(shortlist) == 1
    assert shortlist.iloc[0]["strategy"] == "Donchian Trend"
    assert shortlist.iloc[0]["promotion_gate"] == "BLOCKED_PENDING_OOS"
