"""
Signal Server — TradingView webhook → validation → execution pipeline.

Wires together:
  - FastAPI webhook endpoint (from archive/webhook_v2)
  - Pydantic signal validation (new)
  - Idempotency / dedup (from archive/webhook_v2)
  - Metrics tracking (from archive/core_server)
  - Event logging (replaces SQLAlchemy)
  - Order execution (src/manager.py)

Run: uvicorn src.signal_server:app --host 0.0.0.0 --port 8000
"""

import hmac
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.metrics import Metrics
from src.event_log import log_event
from src.signal_queue import SignalQueue
from src import manager
from src.strategy_promotion import is_strategy_approved

# ── Config ────────────────────────────────────────────────────────────

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change-me-in-production")
MAX_IDEMPOTENCY_CACHE = 10_000  # Max dedup keys in memory
SIGNATURE_TTL_SECONDS = int(os.getenv("WEBHOOK_SIGNATURE_TTL_SECONDS", "300"))

# ── App ───────────────────────────────────────────────────────────────

app = FastAPI(title="Garima Signal Server", version="1.0")
metrics = Metrics()
queue = SignalQueue()
_seen_keys: dict[str, float] = {}  # idempotency_key → timestamp


# ── Pydantic Schemas (P1 #6: signal validation) ──────────────────────

class SignalSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    buy = "buy"
    sell = "sell"


class TradingViewSignal(BaseModel):
    """Schema for TradingView webhook payloads."""
    strategy: str = Field(..., min_length=1, max_length=100, description="Strategy name")
    symbol: str = Field(..., min_length=1, max_length=20, description="e.g. BTCUSDT")
    side: SignalSide = Field(..., description="BUY or SELL")
    price: float = Field(..., gt=0, description="Signal price")
    sl_pct: float = Field(default=0.02, ge=0, le=0.5, description="Stop loss %")
    tp_pct: float = Field(default=0.04, ge=0, le=1.0, description="Take profit %")
    ts_pct: float = Field(default=0.0, ge=0, le=0.5, description="Trailing stop %")
    timeframe: str = Field(default="4h", description="Candle timeframe")
    alert_message: Optional[str] = Field(default=None, description="Raw TradingView alert text")

    @field_validator("symbol")
    @classmethod
    def symbol_uppercase(cls, v):
        return v.upper().strip()

    @field_validator("side")
    @classmethod
    def side_uppercase(cls, v):
        return SignalSide(v.value.upper())


class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    kill_switch: bool
    paper_trading: bool
    open_positions: int
    metrics: dict


# ── Helpers ───────────────────────────────────────────────────────────

_start_time = time.time()


def _idempotency_key(payload: dict) -> str:
    """SHA256 hash for deduplication."""
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def _is_duplicate(key: str) -> bool:
    """Check if signal was already processed (within cache window)."""
    if key in _seen_keys:
        return True
    # Prune old keys if cache is full
    if len(_seen_keys) >= MAX_IDEMPOTENCY_CACHE:
        oldest = sorted(_seen_keys, key=_seen_keys.get)[:MAX_IDEMPOTENCY_CACHE // 2]
        for k in oldest:
            del _seen_keys[k]
    _seen_keys[key] = time.time()
    return False


def _require_configured_secret() -> str:
    secret = (WEBHOOK_SECRET or "").strip()
    if not secret or secret == "change-me-in-production":
        raise HTTPException(status_code=500, detail="Webhook secret is not configured")
    return secret


def _parse_signature_timestamp(raw_timestamp: str) -> datetime:
    try:
        timestamp = datetime.fromtimestamp(int(raw_timestamp), tz=timezone.utc)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid signature timestamp")

    now = datetime.now(timezone.utc)
    if abs((now - timestamp).total_seconds()) > SIGNATURE_TTL_SECONDS:
        raise HTTPException(status_code=401, detail="Stale signature timestamp")
    return timestamp


def _signature_payload(raw_timestamp: str, nonce: str, body: bytes) -> bytes:
    return raw_timestamp.encode() + b"." + nonce.encode() + b"." + body


def _compute_signature(secret: str, raw_timestamp: str, nonce: str, body: bytes) -> str:
    return hmac.new(
        secret.encode(),
        _signature_payload(raw_timestamp, nonce, body),
        hashlib.sha256,
    ).hexdigest()


def _verify_webhook_signature(secret: str, raw_timestamp: str, nonce: str, signature: str, body: bytes) -> None:
    if not raw_timestamp or not nonce or not signature:
        raise HTTPException(status_code=401, detail="Missing signature headers")

    _parse_signature_timestamp(raw_timestamp)
    expected = _compute_signature(secret, raw_timestamp, nonce, body)
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")


def _register_nonce(nonce: str, raw_timestamp: str) -> None:
    if not nonce.strip():
        raise HTTPException(status_code=401, detail="Missing nonce")

    timestamp = _parse_signature_timestamp(raw_timestamp)
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=SIGNATURE_TTL_SECONDS)).isoformat()
    queue.purge_nonces_older_than(cutoff)
    if not queue.register_nonce(nonce=nonce, created_at=timestamp.isoformat()):
        raise HTTPException(status_code=409, detail="Replay detected")


def _enforce_strategy_approval(signal: TradingViewSignal) -> None:
    """
    In live mode, only approved strategies should reach execution.

    Paper mode remains open for research/testing, but live trading should only
    run strategies that have passed Garima's offline review artifact.
    """
    if manager.PAPER_TRADING:
        return

    if is_strategy_approved(signal.strategy, asset=signal.symbol, timeframe=signal.timeframe):
        return

    raise HTTPException(
        status_code=403,
        detail=f"Strategy '{signal.strategy}' is not approved for live execution",
    )


# ── Endpoints ─────────────────────────────────────────────────────────

@app.post("/tv/webhook")
async def tradingview_webhook(
    request: Request,
    x_webhook_timestamp: Optional[str] = Header(None),
    x_webhook_nonce: Optional[str] = Header(None),
    x_webhook_signature: Optional[str] = Header(None),
):
    """
    TradingView webhook endpoint.

    Flow: authenticate → validate → dedup → log → execute → respond
    """
    start = time.time()
    metrics.record_signal()

    # 1. Read raw request for signature verification
    raw_body = await request.body()

    # 2. Mandatory signed request auth
    try:
        secret = _require_configured_secret()
        _verify_webhook_signature(
            secret=secret,
            raw_timestamp=x_webhook_timestamp,
            nonce=x_webhook_nonce,
            signature=x_webhook_signature,
            body=raw_body,
        )
        _register_nonce(x_webhook_nonce, x_webhook_timestamp)
    except HTTPException as exc:
        metrics.record_reject("auth_failed")
        log_event(
            "reject",
            {
                "reason": "auth_failed",
                "detail": exc.detail,
                "nonce": x_webhook_nonce,
                "timestamp": x_webhook_timestamp,
            },
            source="webhook",
        )
        raise

    # 3. Parse JSON
    try:
        raw_payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        metrics.record_reject("invalid_json")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # 4. Validate with Pydantic
    try:
        signal = TradingViewSignal(**raw_payload)
    except Exception as e:
        metrics.record_reject("validation_failed")
        log_event("reject", {"reason": "validation_failed", "error": str(e), "payload": raw_payload}, source="webhook")
        raise HTTPException(status_code=422, detail=f"Validation error: {e}")

    try:
        _enforce_strategy_approval(signal)
    except HTTPException as exc:
        metrics.record_reject("unapproved_strategy")
        log_event(
            "reject",
            {
                "reason": "unapproved_strategy",
                "detail": exc.detail,
                "strategy": signal.strategy,
                "symbol": signal.symbol,
                "timeframe": signal.timeframe,
            },
            source="webhook",
        )
        raise

    # 5. Idempotency check
    idem_key = _idempotency_key(raw_payload)
    if _is_duplicate(idem_key):
        metrics.record_duplicate()
        log_event("duplicate", {"key": idem_key, "symbol": signal.symbol}, source="webhook")
        return {"status": "ignored", "reason": "duplicate", "key": idem_key}

    # 6. Persist to SQLite queue + log event
    signal_payload = {
        "strategy": signal.strategy,
        "symbol": signal.symbol,
        "side": signal.side.value,
        "price": signal.price,
        "sl_pct": signal.sl_pct,
        "tp_pct": signal.tp_pct,
        "ts_pct": signal.ts_pct,
        "timeframe": signal.timeframe,
    }
    queue_id = queue.push(signal_payload, idempotency_key=idem_key)
    log_event("signal_received", {**signal_payload, "idempotency_key": idem_key, "queue_id": queue_id}, source="tradingview")

    # 7. Forward to manager for execution
    try:
        manager.process_signal({
            "symbol": signal.symbol,
            "side": signal.side.value,
            "price": signal.price,
            "sl_pct": signal.sl_pct,
            "tp_pct": signal.tp_pct,
            "ts_pct": signal.ts_pct,
        })
        queue.mark_done(queue_id)
        metrics.record_executed()
        log_event("signal_executed", {
            "symbol": signal.symbol,
            "side": signal.side.value,
            "key": idem_key,
        }, source="manager")
    except Exception as e:
        queue.mark_failed(queue_id, str(e))
        metrics.record_critical()
        log_event("execution_error", {"error": str(e), "symbol": signal.symbol}, source="manager")
        raise HTTPException(status_code=500, detail=f"Execution error: {e}")

    # 8. Record latency
    latency_ms = (time.time() - start) * 1000
    metrics.record_latency(latency_ms)

    return {
        "status": "ok",
        "idempotency_key": idem_key,
        "symbol": signal.symbol,
        "side": signal.side.value,
        "latency_ms": round(latency_ms, 2),
    }


@app.get("/health")
async def health():
    """Health check with system status and metrics."""
    return HealthResponse(
        status="ok",
        uptime_seconds=round(time.time() - _start_time, 1),
        kill_switch=manager.is_kill_switch_active(),
        paper_trading=manager.PAPER_TRADING,
        open_positions=len(manager._active_positions),
        metrics=metrics.to_dict(),
    )


@app.post("/killswitch/{action}")
async def killswitch(action: str, x_webhook_token: Optional[str] = Header(None)):
    """Activate or deactivate the kill switch via API."""
    if x_webhook_token != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid token")

    if action == "on":
        manager.activate_kill_switch(close_all=True)
        return {"status": "kill_switch_activated"}
    elif action == "off":
        manager.deactivate_kill_switch()
        return {"status": "kill_switch_deactivated"}
    else:
        raise HTTPException(status_code=400, detail="Use /killswitch/on or /killswitch/off")


@app.get("/positions")
async def positions():
    """List active positions."""
    return {
        "count": len(manager._active_positions),
        "positions": manager._active_positions,
        "mode": "PAPER" if manager.PAPER_TRADING else "LIVE",
    }


@app.get("/events")
async def events(event_type: Optional[str] = None, limit: int = 50):
    """Recent event log."""
    from src.event_log import read_events
    return {"events": read_events(event_type=event_type, limit=limit)}


@app.get("/queue")
async def queue_status():
    """Signal queue stats and recent signals."""
    return {"stats": queue.stats(), "recent": queue.recent(10)}


# ── Startup ───────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """Start the SL/TP monitor on server boot."""
    manager.start_monitor()
    print(f"Signal server started. Paper={manager.PAPER_TRADING}, Kill={manager.is_kill_switch_active()}")
