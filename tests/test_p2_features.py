"""Tests for P2 features: walk-forward, short selling, slippage."""

import os
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Helper: create fake OHLCV data ──────────────────────────────────

def _make_df(n=500, trend="up"):
    """Create synthetic OHLCV dataframe for testing."""
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=n, freq="4h")
    if trend == "up":
        close = 100 + np.cumsum(np.random.randn(n) * 0.5 + 0.05)
    elif trend == "down":
        close = 200 + np.cumsum(np.random.randn(n) * 0.5 - 0.05)
    else:
        close = 100 + np.cumsum(np.random.randn(n) * 0.5)

    close = np.maximum(close, 10)  # no negative prices
    high = close * (1 + np.abs(np.random.randn(n) * 0.005))
    low = close * (1 - np.abs(np.random.randn(n) * 0.005))
    volume = np.random.randint(100, 10000, n).astype(float)

    df = pd.DataFrame({
        "timestamp": dates,
        "open": close * (1 + np.random.randn(n) * 0.001),
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })
    return df


def _add_signals(df, entry_every=20):
    """Add entry/exit signals to dataframe."""
    df = df.copy()
    df["entry_signal"] = 0
    df["exit_signal"] = 0
    for i in range(0, len(df), entry_every):
        df.loc[df.index[i], "entry_signal"] = 1
        if i + entry_every // 2 < len(df):
            df.loc[df.index[i + entry_every // 2], "exit_signal"] = 1
    return df


# ── Short Selling Tests ──────────────────────────────────────────────

class TestShortSelling:
    def test_long_profits_in_uptrend(self):
        from run_strategies_batch import run_backtest, INITIAL_CAPITAL
        df = _add_signals(_make_df(500, trend="up"))
        cap, trades = run_backtest(df, 0.05, 0.10, 0.03, side="long")
        assert cap > INITIAL_CAPITAL  # should profit in uptrend
        assert len(trades) > 0
        assert all(t["side"] == "long" for t in trades)

    def test_short_profits_in_downtrend(self):
        from run_strategies_batch import run_backtest, INITIAL_CAPITAL
        df = _add_signals(_make_df(500, trend="down"))
        cap, trades = run_backtest(df, 0.05, 0.10, 0.03, side="short")
        assert len(trades) > 0
        assert all(t["side"] == "short" for t in trades)
        # At least some shorts should profit in downtrend
        profitable = [t for t in trades if t["pnl"] > 0]
        assert len(profitable) > 0

    def test_short_return_pct_inverted(self):
        from run_strategies_batch import run_backtest
        df = _add_signals(_make_df(200, trend="down"))
        _, trades = run_backtest(df, 0.05, 0.10, 0.03, side="short")
        if trades:
            for t in trades:
                if t["entry"] > t["exit"]:
                    # Price dropped → short should show positive return
                    assert t["return_pct"] > 0

    def test_default_side_is_long(self):
        from run_strategies_batch import run_backtest
        df = _add_signals(_make_df(200))
        _, trades = run_backtest(df, 0.05, 0.10, 0.03)
        if trades:
            assert trades[0]["side"] == "long"


# ── Slippage Tests ───────────────────────────────────────────────────

class TestSlippage:
    def test_slippage_reduces_profits(self):
        from run_strategies_batch import run_backtest
        df = _add_signals(_make_df(500, trend="up"))

        cap_no_slip, _ = run_backtest(df, 0.05, 0.10, 0.03, slippage_pct=0.0)
        cap_with_slip, _ = run_backtest(df, 0.05, 0.10, 0.03, slippage_pct=0.001)

        assert cap_with_slip < cap_no_slip  # slippage should reduce returns

    def test_zero_slippage_unchanged(self):
        from run_strategies_batch import run_backtest
        df = _add_signals(_make_df(200))
        cap1, trades1 = run_backtest(df, 0.05, 0.10, 0.03, slippage_pct=0.0)
        cap2, trades2 = run_backtest(df, 0.05, 0.10, 0.03)
        assert cap1 == cap2
        assert len(trades1) == len(trades2)

    def test_high_slippage_significant_impact(self):
        from run_strategies_batch import run_backtest, INITIAL_CAPITAL
        df = _add_signals(_make_df(500, trend="up"))
        cap_low, _ = run_backtest(df, 0.05, 0.10, 0.03, slippage_pct=0.0005)
        cap_high, _ = run_backtest(df, 0.05, 0.10, 0.03, slippage_pct=0.005)
        assert cap_high < cap_low  # higher slippage = worse


# ── Walk-Forward Tests ───────────────────────────────────────────────

class TestWalkForward:
    def test_split_windows(self):
        from src.walk_forward import _split_windows
        df = _make_df(600)
        splits = _split_windows(df, n_windows=6)
        assert len(splits) == 5  # n-1 windows (first is train-only)
        for train, test in splits:
            assert len(test) == 100
            assert len(train) > 0

    def test_split_preserves_data(self):
        from src.walk_forward import _split_windows
        df = _make_df(300)
        splits = _split_windows(df, n_windows=3)
        for train, test in splits:
            # No overlap between train and test
            assert train.index[-1] < test.index[0]

    def test_run_single(self):
        from src.walk_forward import _run_single
        from run_strategies_batch import calculate_indicators
        df = _make_df(500, trend="up")
        df = calculate_indicators(df)
        result = _run_single(df, ["EMA_Cross", "MACD_Cross"], 1, 0.02, 0.04, 0.02)
        assert "roi" in result
        assert "trades" in result
        assert "win_rate" in result
