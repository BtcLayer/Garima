from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import sqlite3
import datetime

app = FastAPI(title="TradingView Forward Test Listener")

# Schema for incoming TradingView Alert
class TVAlert(BaseModel):
    strategy_name: str
    symbol: str
    action: str  # buy/sell
    price: float
    order_id: str
    alert_message: str

@app.post("/webhook")
async def receive_alert(alert: TVAlert):
    try:
        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()
        
        # Log the live trade into a 'trades' table
        cursor.execute('''
            INSERT INTO trades (timestamp, strategy_name, symbol, action, price, order_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (datetime.datetime.now(), alert.strategy_name, alert.symbol, 
              alert.action, alert.price, alert.order_id))
        
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Trade Logged"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "alive"}