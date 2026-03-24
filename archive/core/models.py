# db/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
import datetime

Base = declarative_base()

class Strategy(Base):
    __tablename__ = "strategies"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    repo = Column(String)
    version = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Run(Base):
    __tablename__ = "runs"
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    symbol = Column(String)
    timeframe = Column(String)
    start = Column(DateTime)
    end = Column(DateTime)
    tv_settings_hash = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    strategy = relationship("Strategy", backref="runs")

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("runs.id"))
    entry_time = Column(DateTime)
    exit_time = Column(DateTime)
    side = Column(String)
    qty = Column(Float)
    entry_price = Column(Float)
    exit_price = Column(Float)
    pnl = Column(Float)
    fees = Column(Float)

class Metrics(Base):
    __tablename__ = "metrics"
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("runs.id"))
    net_profit = Column(Float)
    pf = Column(Float)
    win_rate = Column(Float)
    max_dd = Column(Float)
    trades_count = Column(Integer)

class EventRaw(Base):
    __tablename__ = "events_raw"
    id = Column(Integer, primary_key=True)
    received_at = Column(DateTime, default=datetime.datetime.utcnow)
    payload_json = Column(String)
    source = Column(String)