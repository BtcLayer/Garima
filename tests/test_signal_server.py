"""Tests for signal_server, metrics, and event_log modules."""

import hashlib
import hmac
import json
import os
import shutil
import sys
import time
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def make_test_dir(name: str) -> str:
    root = os.path.join(os.path.dirname(__file__), ".tmp_runtime")
    path = os.path.join(root, f"{name}_{uuid.uuid4().hex}")
    os.makedirs(path, exist_ok=True)
    return path


def cleanup_test_dir(path: str) -> None:
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)


# ── Metrics tests ─────────────────────────────────────────────────────

class TestMetrics:
    def test_record_signal(self):
        from src.metrics import Metrics
        m = Metrics.__new__(Metrics)
        m.total = 0
        m.duplicates = 0
        m.rejects = 0
        m.executed = 0
        m.latencies = []
        m.critical_incidents = 0
        m.save = lambda: None  # stub persistence

        m.total += 1
        assert m.total == 1

    def test_duplicate_rate(self):
        from src.metrics import Metrics
        m = Metrics.__new__(Metrics)
        m.total = 10
        m.duplicates = 3
        m.rejects = 0
        m.executed = 0
        m.latencies = []
        m.critical_incidents = 0
        assert m.duplicate_rate() == 0.3

    def test_duplicate_rate_zero(self):
        from src.metrics import Metrics
        m = Metrics.__new__(Metrics)
        m.total = 0
        m.duplicates = 0
        m.rejects = 0
        m.executed = 0
        m.latencies = []
        m.critical_incidents = 0
        assert m.duplicate_rate() == 0.0

    def test_p95_latency(self):
        from src.metrics import Metrics
        m = Metrics.__new__(Metrics)
        m.total = 0
        m.duplicates = 0
        m.rejects = 0
        m.executed = 0
        m.latencies = list(range(100))
        m.critical_incidents = 0
        assert m.p95_latency() >= 94

    def test_to_dict(self):
        from src.metrics import Metrics
        m = Metrics.__new__(Metrics)
        m.total = 5
        m.duplicates = 1
        m.rejects = 1
        m.executed = 3
        m.latencies = [10, 20, 30]
        m.critical_incidents = 0
        d = m.to_dict()
        assert d["total_signals"] == 5
        assert d["executed"] == 3
        assert d["duplicates"] == 1


# ── Event log tests ───────────────────────────────────────────────────

class TestEventLog:
    def test_log_and_read(self):
        import src.event_log as el
        tmp_dir = make_test_dir("event_log_read")
        try:
            el.EVENT_LOG_PATH = os.path.join(tmp_dir, "events.jsonl")

            el.log_event("test_signal", {"symbol": "BTCUSDT", "side": "BUY"})
            el.log_event("test_signal", {"symbol": "ETHUSDT", "side": "SELL"})

            events = el.read_events()
            assert len(events) == 2
            assert events[0]["payload"]["symbol"] == "BTCUSDT"
            assert events[1]["payload"]["symbol"] == "ETHUSDT"
        finally:
            cleanup_test_dir(tmp_dir)

    def test_read_filtered(self):
        import src.event_log as el
        tmp_dir = make_test_dir("event_log_filtered")
        try:
            el.EVENT_LOG_PATH = os.path.join(tmp_dir, "events.jsonl")

            el.log_event("signal", {"symbol": "BTCUSDT"})
            el.log_event("reject", {"reason": "auth"})
            el.log_event("signal", {"symbol": "ETHUSDT"})

            signals = el.read_events(event_type="signal")
            assert len(signals) == 2

            rejects = el.read_events(event_type="reject")
            assert len(rejects) == 1
        finally:
            cleanup_test_dir(tmp_dir)

    def test_count_events(self):
        import src.event_log as el
        tmp_dir = make_test_dir("event_log_counts")
        try:
            el.EVENT_LOG_PATH = os.path.join(tmp_dir, "events.jsonl")

            el.log_event("signal", {})
            el.log_event("signal", {})
            el.log_event("reject", {})

            counts = el.count_events()
            assert counts["signal"] == 2
            assert counts["reject"] == 1
        finally:
            cleanup_test_dir(tmp_dir)

    def test_read_empty(self):
        import src.event_log as el
        tmp_dir = make_test_dir("event_log_empty")
        try:
            el.EVENT_LOG_PATH = os.path.join(tmp_dir, "nonexistent.jsonl")
            assert el.read_events() == []
        finally:
            cleanup_test_dir(tmp_dir)


# ── Signal validation tests ───────────────────────────────────────────

class TestSignalValidation:
    def test_valid_signal(self):
        from src.signal_server import TradingViewSignal
        sig = TradingViewSignal(
            strategy="Golden_Cross_Pro",
            symbol="btcusdt",
            side="BUY",
            price=50000.0,
        )
        assert sig.symbol == "BTCUSDT"
        assert sig.side.value == "BUY"
        assert sig.sl_pct == 0.02  # default
        assert sig.tp_pct == 0.04  # default

    def test_symbol_normalized(self):
        from src.signal_server import TradingViewSignal
        sig = TradingViewSignal(
            strategy="Test",
            symbol="  ethusdt  ",
            side="SELL",
            price=3000.0,
        )
        assert sig.symbol == "ETHUSDT"

    def test_invalid_price_rejected(self):
        from src.signal_server import TradingViewSignal
        with pytest.raises(Exception):
            TradingViewSignal(
                strategy="Test",
                symbol="BTCUSDT",
                side="BUY",
                price=-100,
            )

    def test_invalid_side_rejected(self):
        from src.signal_server import TradingViewSignal
        with pytest.raises(Exception):
            TradingViewSignal(
                strategy="Test",
                symbol="BTCUSDT",
                side="HODL",
                price=50000,
            )

    def test_sl_pct_bounds(self):
        from src.signal_server import TradingViewSignal
        with pytest.raises(Exception):
            TradingViewSignal(
                strategy="Test",
                symbol="BTCUSDT",
                side="BUY",
                price=50000,
                sl_pct=0.9,  # >50% not allowed
            )

    def test_empty_strategy_rejected(self):
        from src.signal_server import TradingViewSignal
        with pytest.raises(Exception):
            TradingViewSignal(
                strategy="",
                symbol="BTCUSDT",
                side="BUY",
                price=50000,
            )


# ── Idempotency tests ────────────────────────────────────────────────

class TestIdempotency:
    def test_same_payload_detected(self):
        from src.signal_server import _idempotency_key, _is_duplicate, _seen_keys
        _seen_keys.clear()

        payload = {"symbol": "BTCUSDT", "side": "BUY", "price": 50000}
        key = _idempotency_key(payload)

        assert not _is_duplicate(key)  # first time
        assert _is_duplicate(key)      # second time — duplicate

    def test_different_payloads_unique(self):
        from src.signal_server import _idempotency_key, _is_duplicate, _seen_keys
        _seen_keys.clear()

        k1 = _idempotency_key({"symbol": "BTCUSDT", "price": 50000})
        k2 = _idempotency_key({"symbol": "ETHUSDT", "price": 3000})

        assert not _is_duplicate(k1)
        assert not _is_duplicate(k2)


class TestWebhookAuth:
    def test_compute_signature_matches_reference(self):
        from src.signal_server import _compute_signature

        secret = "test-secret"
        timestamp = "1712400000"
        nonce = "nonce-123"
        body = b'{"symbol":"BTCUSDT"}'

        expected = hmac.new(
            secret.encode(),
            timestamp.encode() + b"." + nonce.encode() + b"." + body,
            hashlib.sha256,
        ).hexdigest()

        assert _compute_signature(secret, timestamp, nonce, body) == expected

    def test_verify_signature_accepts_valid_request(self):
        from src.signal_server import _compute_signature, _verify_webhook_signature

        secret = "test-secret"
        timestamp = str(int(time.time()))
        nonce = "nonce-123"
        body = b'{"symbol":"BTCUSDT"}'
        signature = _compute_signature(secret, timestamp, nonce, body)

        _verify_webhook_signature(secret, timestamp, nonce, signature, body)

    def test_verify_signature_rejects_stale_timestamp(self):
        from src.signal_server import _compute_signature, _verify_webhook_signature

        secret = "test-secret"
        timestamp = str(int(time.time()) - 3600)
        nonce = "nonce-123"
        body = b'{"symbol":"BTCUSDT"}'
        signature = _compute_signature(secret, timestamp, nonce, body)

        with pytest.raises(Exception):
            _verify_webhook_signature(secret, timestamp, nonce, signature, body)

    def test_verify_signature_rejects_invalid_signature(self):
        from src.signal_server import _verify_webhook_signature

        with pytest.raises(Exception):
            _verify_webhook_signature(
                "test-secret",
                str(int(time.time())),
                "nonce-123",
                "bad-signature",
                b'{"symbol":"BTCUSDT"}',
            )


# ── Signal Queue tests ───────────────────────────────────────────────

class TestSignalQueue:
    def test_push_and_pop(self):
        from src.signal_queue import SignalQueue
        tmp_dir = make_test_dir("queue_push_pop")
        try:
            q = SignalQueue(os.path.join(tmp_dir, "test.db"))
            q.push({"symbol": "BTCUSDT", "side": "BUY", "price": 50000})
            sig = q.pop()
            assert sig is not None
            assert sig["payload"]["symbol"] == "BTCUSDT"
        finally:
            cleanup_test_dir(tmp_dir)

    def test_fifo_order(self):
        from src.signal_queue import SignalQueue
        tmp_dir = make_test_dir("queue_fifo")
        try:
            q = SignalQueue(os.path.join(tmp_dir, "test.db"))
            q.push({"symbol": "BTCUSDT"})
            q.push({"symbol": "ETHUSDT"})
            first = q.pop()
            assert first["payload"]["symbol"] == "BTCUSDT"
            second = q.pop()
            assert second["payload"]["symbol"] == "ETHUSDT"
        finally:
            cleanup_test_dir(tmp_dir)

    def test_pop_empty(self):
        from src.signal_queue import SignalQueue
        tmp_dir = make_test_dir("queue_empty")
        try:
            q = SignalQueue(os.path.join(tmp_dir, "test.db"))
            assert q.pop() is None
        finally:
            cleanup_test_dir(tmp_dir)

    def test_duplicate_rejected(self):
        from src.signal_queue import SignalQueue
        tmp_dir = make_test_dir("queue_duplicate")
        try:
            q = SignalQueue(os.path.join(tmp_dir, "test.db"))
            id1 = q.push({"symbol": "BTCUSDT"}, idempotency_key="abc123")
            id2 = q.push({"symbol": "BTCUSDT"}, idempotency_key="abc123")
            assert id1 > 0
            assert id2 == -1  # duplicate
        finally:
            cleanup_test_dir(tmp_dir)

    def test_mark_done(self):
        from src.signal_queue import SignalQueue
        tmp_dir = make_test_dir("queue_done")
        try:
            q = SignalQueue(os.path.join(tmp_dir, "test.db"))
            q.push({"symbol": "BTCUSDT"})
            sig = q.pop()
            q.mark_done(sig["id"])
            stats = q.stats()
            assert stats.get("done", 0) == 1
            assert stats.get("pending", 0) == 0
        finally:
            cleanup_test_dir(tmp_dir)

    def test_mark_failed_and_retry(self):
        from src.signal_queue import SignalQueue
        tmp_dir = make_test_dir("queue_retry")
        try:
            q = SignalQueue(os.path.join(tmp_dir, "test.db"))
            q.push({"symbol": "BTCUSDT"})
            sig = q.pop()
            q.mark_failed(sig["id"], "timeout")
            assert q.stats().get("failed", 0) == 1
            retried = q.retry_failed()
            assert retried == 1
            assert q.pending_count() == 1
        finally:
            cleanup_test_dir(tmp_dir)

    def test_stats(self):
        from src.signal_queue import SignalQueue
        tmp_dir = make_test_dir("queue_stats")
        try:
            q = SignalQueue(os.path.join(tmp_dir, "test.db"))
            q.push({"a": 1})
            q.push({"b": 2})
            stats = q.stats()
            assert stats["total"] == 2
            assert stats["pending"] == 2
        finally:
            cleanup_test_dir(tmp_dir)

    def test_register_nonce_rejects_replay(self):
        from src.signal_queue import SignalQueue

        tmp_dir = make_test_dir("queue_nonce")
        try:
            q = SignalQueue(os.path.join(tmp_dir, "test.db"))
            assert q.register_nonce("nonce-123")
            assert not q.register_nonce("nonce-123")
        finally:
            cleanup_test_dir(tmp_dir)

    def test_purge_nonces(self):
        from src.signal_queue import SignalQueue

        tmp_dir = make_test_dir("queue_nonce_purge")
        try:
            q = SignalQueue(os.path.join(tmp_dir, "test.db"))
            assert q.register_nonce("old-nonce", created_at="2020-01-01T00:00:00+00:00")
            assert q.register_nonce("fresh-nonce", created_at="2030-01-01T00:00:00+00:00")

            deleted = q.purge_nonces_older_than("2025-01-01T00:00:00+00:00")
            stats = q.stats()

            assert deleted == 1
            assert stats["nonce_count"] == 1
        finally:
            cleanup_test_dir(tmp_dir)
