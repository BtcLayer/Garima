from fastapi import FastAPI, Request, Header, HTTPException
from sqlalchemy.orm import Session
from db.models import Base, EventRaw
import hashlib, json
from datetime import datetime

app = FastAPI()
SECRET_TOKEN = "YOUR_SECRET_KEY"

def compute_idempotency_key(payload: str) -> str:
    return hashlib.sha256(payload.encode()).hexdigest()

@app.post("/tv/webhook")
async def tv_webhook(request: Request, x_tv_token: str = Header(None), db: Session = None):
    if x_tv_token != SECRET_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    payload = await request.body()
    payload_str = payload.decode()
    key = compute_idempotency_key(payload_str)
    
    # check idempotency (pseudo)
    existing = db.query(EventRaw).filter(EventRaw.payload_json == key).first()
    if existing:
        return {"status": "ignored", "reason": "duplicate"}
    
    # store raw event
    event = EventRaw(payload_json=payload_str, source="TradingView")
    db.add(event)
    db.commit()
    
    return {"status": "ok"}