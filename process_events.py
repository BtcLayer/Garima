# process_events.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base, EventRaw, Strategy, Run, Trade, Metrics
import json
import datetime

# ---------------------------
# Database config
# ---------------------------
DATABASE_URL = "sqlite:///C:/Users/hp/Desktop/trial/db.sqlite3"
engine = create_engine(DATABASE_URL, echo=True)
Session = sessionmaker(bind=engine)

# ---------------------------
# Helper: insert or get Strategy
# ---------------------------
def get_or_create_strategy(session, strategy_id, version):
    strategy = session.query(Strategy).filter_by(name=strategy_id, version=version).first()
    if not strategy:
        strategy = Strategy(name=strategy_id, version=version, created_at=datetime.datetime.utcnow())
        session.add(strategy)
        session.commit()
    return strategy

# ---------------------------
# Process events
# ---------------------------
def process_events():
    session = Session()
    try:
        events = session.query(EventRaw).all()
        for event in events:
            payload = json.loads(event.payload_json)
            event_type = payload.get("event_type")

            # Strategy
            strategy_id = payload.get("strategy_id", "UNKNOWN")
            strategy_version = payload.get("strategy_version", "1.0")
            strategy = get_or_create_strategy(session, strategy_id, strategy_version)

            # Example: order_fill events → insert into Run/Trade
            if event_type == "order_fill":
                run = Run(
                    strategy_id=strategy.id,
                    symbol=payload.get("payload", {}).get("symbol", "BTCUSD"),
                    timeframe=payload.get("payload", {}).get("timeframe", "1m"),
                    start=datetime.datetime.utcnow(),
                    end=datetime.datetime.utcnow(),
                    tv_settings_hash=payload.get("param_hash", ""),
                    created_at=datetime.datetime.utcnow()
                )
                session.add(run)
                session.commit()

                trade_payload = payload.get("payload", {})
                trade = Trade(
                    run_id=run.id,
                    entry_time=datetime.datetime.utcnow(),
                    exit_time=datetime.datetime.utcnow(),
                    side=trade_payload.get("side"),
                    qty=trade_payload.get("qty"),
                    entry_price=trade_payload.get("entry_price"),
                    exit_price=trade_payload.get("exit_price", trade_payload.get("entry_price")),
                    pnl=trade_payload.get("pnl", 0.0),
                    fees=trade_payload.get("fees", 0.0)
                )
                session.add(trade)
                session.commit()

            # Example: metrics events → insert into Metrics
            elif event_type == "backtest_metrics":
                metrics_payload = payload.get("payload", {})
                run_id = metrics_payload.get("run_id")  # You may need to map this properly
                metrics = Metrics(
                    run_id=run_id,
                    net_profit=metrics_payload.get("net_profit"),
                    pf=metrics_payload.get("pf"),
                    win_rate=metrics_payload.get("win_rate"),
                    max_dd=metrics_payload.get("max_dd"),
                    trades_count=metrics_payload.get("trades_count")
                )
                session.add(metrics)
                session.commit()

        print("✅ All events processed successfully!")

    except Exception as e:
        session.rollback()
        print("Error processing events:", e)
    finally:
        session.close()

# ---------------------------
# Run processing
# ---------------------------
if __name__ == "__main__":
    process_events()