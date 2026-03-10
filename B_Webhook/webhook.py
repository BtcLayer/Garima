# webhook.py
from fastapi import FastAPI, Request, HTTPException, Header
from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import sessionmaker
from db.models import Base, EventRaw
import datetime
import json
import hashlib
import logging

# ---------------------------
# Logging
# ---------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------
# Config
# ---------------------------
DATABASE_URL = "sqlite:///C:/Users/hp/Desktop/trial/db.sqlite3"
SECRET_TOKEN = "supersecret123"  # TradingView webhook must send this in X-Webhook-Token

# ---------------------------
# Database setup
# ---------------------------
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)

# ---------------------------
# FastAPI app
# ---------------------------
app = FastAPI(title="TradingView Webhook API")

# ---------------------------
# Helper: Idempotency
# ---------------------------
def get_idempotency_key(payload: dict) -> str:
    """Create SHA256 hash of payload for deduplication"""
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

# ---------------------------
# Webhook endpoint
# ---------------------------
@app.post("/tv/webhook")
async def tradingview_webhook(request: Request, x_webhook_token: str = Header(None)):
    # 1️⃣ Check token
    if x_webhook_token != SECRET_TOKEN:
        logger.warning("Invalid token: %s", x_webhook_token)
        raise HTTPException(status_code=401, detail="Invalid token")

    # 2️⃣ Parse JSON payload
    try:
        payload = await request.json()
        logger.info("Received payload: %s", payload)
    except Exception as e:
        logger.exception("Invalid JSON")
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    # 3️⃣ Generate idempotency key
    key = get_idempotency_key(payload)

    # 4️⃣ Insert into DB
    session = SessionLocal()
    try:
        # Check duplicate using idempotency key
        existing = session.query(EventRaw).filter(EventRaw.payload_json == key).first()
        if existing:
            return {"status": "ignored", "reason": "duplicate"}

        event = EventRaw(
            received_at=datetime.datetime.utcnow(),
            payload_json=json.dumps(payload, sort_keys=True),
            source="tradingview"
        )
        session.add(event)
        session.commit()
        logger.info("Event saved with key: %s", key)
        return {"status": "ok", "idempotency_key": key}

    except Exception as e:
        session.rollback()
        logger.exception("Failed to save event")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()