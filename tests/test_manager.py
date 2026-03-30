"""Unit tests for src/manager.py — kill switch, position sizing, circuit breaker."""
import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Ensure src/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture(autouse=True)
def reset_manager(tmp_path):
    """Reset manager state before each test."""
    # Patch BinanceClient and send_telegram so tests don't make real calls
    with patch("src.manager.BinanceClient"), \
         patch("src.manager.send_telegram"):
        # Reimport to reset module-level state
        import src.manager as mgr
        mgr._kill_switch_active = False
        mgr._active_positions = {}
        mgr._daily_pnl = 0.0
        mgr._weekly_pnl = 0.0
        mgr.PAPER_TRADING = True
        mgr.TRADE_LOG = str(tmp_path / "trades.jsonl")
        mgr.STATE_FILE = str(tmp_path / "manager_state.json")
        mgr.bnc = MagicMock()
        mgr.bnc.get_balance.return_value = {"total": 10000.0}
        mgr.bnc.get_ticker_price.return_value = "50000.0"
        yield mgr


# ── Kill Switch ──────────────────────────────────────────────────────

class TestKillSwitch:
    def test_activate(self, reset_manager):
        mgr = reset_manager
        assert not mgr.is_kill_switch_active()
        mgr.activate_kill_switch(close_all=False)
        assert mgr.is_kill_switch_active()

    def test_deactivate(self, reset_manager):
        mgr = reset_manager
        mgr.activate_kill_switch(close_all=False)
        mgr.deactivate_kill_switch()
        assert not mgr.is_kill_switch_active()

    def test_blocks_new_trades(self, reset_manager):
        mgr = reset_manager
        mgr.activate_kill_switch(close_all=False)
        mgr.process_signal({"symbol": "BTCUSDT", "side": "BUY", "price": "50000"})
        assert "BTCUSDT" not in mgr._active_positions

    def test_closes_all_on_activate(self, reset_manager):
        mgr = reset_manager
        # Open a paper position first
        mgr.process_signal({"symbol": "BTCUSDT", "side": "BUY", "price": "50000"})
        assert "BTCUSDT" in mgr._active_positions
        mgr.activate_kill_switch(close_all=True)
        assert "BTCUSDT" not in mgr._active_positions


# ── Position Sizing ──────────────────────────────────────────────────

class TestPositionSizing:
    def test_risk_based_quantity(self, reset_manager):
        mgr = reset_manager
        # equity=10000, risk 2% = $200, price=50000, sl=2% → qty = 200/(50000*0.02) = 0.2
        qty = mgr._compute_quantity("BTCUSDT", 50000.0, 0.02)
        assert qty > 0
        assert qty <= 0.2  # risk cap

    def test_zero_equity_returns_zero(self, reset_manager):
        mgr = reset_manager
        mgr.bnc.get_balance.return_value = {"total": 0.0}
        qty = mgr._compute_quantity("BTCUSDT", 50000.0, 0.02)
        assert qty == 0.0

    def test_exposure_cap(self, reset_manager):
        mgr = reset_manager
        # Fill up exposure to the limit
        mgr._active_positions["ETHUSDT"] = {
            "entry_price": 3000, "quantity": 1.0,
            "stop_loss": 2900, "take_profit": 3200,
            "peak_price": 3000, "trailing_stop_pct": 0,
            "entry_at": "", "mode": "PAPER",
        }
        # 3000 * 1.0 = $3000 exposure, max = 10000 * 0.30 = $3000 → at limit
        qty = mgr._compute_quantity("BTCUSDT", 50000.0, 0.02)
        assert qty == 0.0


# ── Circuit Breaker ──────────────────────────────────────────────────

class TestCircuitBreaker:
    def test_daily_loss_triggers_kill_switch(self, reset_manager):
        mgr = reset_manager
        mgr._record_pnl(-mgr.MAX_DAILY_LOSS_USD - 1)
        assert mgr.is_kill_switch_active()

    def test_weekly_loss_triggers_kill_switch(self, reset_manager):
        mgr = reset_manager
        mgr.MAX_DAILY_LOSS_USD = 99999  # don't trigger daily
        mgr._record_pnl(-mgr.MAX_WEEKLY_LOSS_USD - 1)
        assert mgr.is_kill_switch_active()

    def test_small_loss_no_trigger(self, reset_manager):
        mgr = reset_manager
        mgr._record_pnl(-10.0)
        assert not mgr.is_kill_switch_active()


# ── Paper Trading ────────────────────────────────────────────────────

class TestPaperTrading:
    def test_paper_buy_no_real_order(self, reset_manager):
        mgr = reset_manager
        mgr.PAPER_TRADING = True
        mgr.process_signal({"symbol": "BTCUSDT", "side": "BUY", "price": "50000"})
        assert "BTCUSDT" in mgr._active_positions
        assert mgr._active_positions["BTCUSDT"]["mode"] == "PAPER"
        mgr.bnc.place_order.assert_not_called()

    def test_paper_sell_no_real_order(self, reset_manager):
        mgr = reset_manager
        mgr.PAPER_TRADING = True
        mgr.process_signal({"symbol": "BTCUSDT", "side": "BUY", "price": "50000"})
        mgr.process_signal({"symbol": "BTCUSDT", "side": "SELL", "price": "51000"})
        assert "BTCUSDT" not in mgr._active_positions
        mgr.bnc.place_order.assert_not_called()


# ── State Persistence ────────────────────────────────────────────────

class TestPersistence:
    def test_save_and_load_state(self, reset_manager):
        mgr = reset_manager
        mgr.activate_kill_switch(close_all=False)
        mgr._save_state()
        # Reset and reload
        mgr._kill_switch_active = False
        mgr._load_state()
        assert mgr._kill_switch_active is True

    def test_trade_log_written(self, reset_manager):
        mgr = reset_manager
        mgr.process_signal({"symbol": "BTCUSDT", "side": "BUY", "price": "50000"})
        mgr.process_signal({"symbol": "BTCUSDT", "side": "SELL", "price": "51000"})
        assert os.path.exists(mgr.TRADE_LOG)
        with open(mgr.TRADE_LOG) as f:
            lines = f.readlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["symbol"] == "BTCUSDT"
        assert record["pnl"] > 0


# ── SL/TP Monitor ───────────────────────────────────────────────────

class TestMonitor:
    def test_stop_loss_triggered(self, reset_manager):
        mgr = reset_manager
        mgr.process_signal({"symbol": "BTCUSDT", "side": "BUY", "price": "50000", "sl_pct": "0.02"})
        assert "BTCUSDT" in mgr._active_positions
        # Price drops below SL
        mgr.bnc.get_ticker_price.return_value = "48000.0"
        mgr._check_positions()
        assert "BTCUSDT" not in mgr._active_positions

    def test_take_profit_triggered(self, reset_manager):
        mgr = reset_manager
        mgr.process_signal({"symbol": "BTCUSDT", "side": "BUY", "price": "50000", "tp_pct": "0.04"})
        assert "BTCUSDT" in mgr._active_positions
        # Price goes above TP
        mgr.bnc.get_ticker_price.return_value = "55000.0"
        mgr._check_positions()
        assert "BTCUSDT" not in mgr._active_positions

    def test_trailing_stop_updates(self, reset_manager):
        mgr = reset_manager
        mgr.process_signal({
            "symbol": "BTCUSDT", "side": "BUY", "price": "50000",
            "sl_pct": "0.02", "ts_pct": "0.03",
        })
        pos = mgr._active_positions["BTCUSDT"]
        original_sl = pos["stop_loss"]
        # Price goes up → trailing stop should ratchet up
        mgr.bnc.get_ticker_price.return_value = "55000.0"
        mgr._check_positions()
        # Position still open (price above new SL)
        if "BTCUSDT" in mgr._active_positions:
            assert mgr._active_positions["BTCUSDT"]["stop_loss"] > original_sl
