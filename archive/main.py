import time
import sys
import os

# Add the current directory to sys.path so imports work
sys.path.append(os.path.dirname(__file__))

from utils import get_binance_client
from logger import EventLogger
from monitor import Reconciler, AlertRouter

def main():
    print("Starting Binance Bot Process...")
    
    # 1. Connect to Binance
    try:
        client = get_binance_client()
        status = client.get_account_status()
        print(f"Connection Successful: {status}")
    except Exception as e:
        print(f"Connection Failed: {e}")
        return

    # 2. Setup Logging
    event_logger = EventLogger()

    # 3. Simulate Signal/Order (Requirement 5.1)
    event_logger.log_event("signal_received", {"symbol": "BTCUSDT", "side": "BUY"})
    event_logger.log_event("order_submitted", {"symbol": "BTCUSDT", "qty": 0.001})

    # 4. Start Reconciler (Requirement 5.2)
    # Simulation: We set internal to 0.99 BTC to force a mismatch with your real account
    internal_state = {"BTC": 0.0} 
    alerts = AlertRouter()
    
    recon = Reconciler(client, internal_state, alerts, event_logger)
    recon.start_monitoring(interval=15)

    print("Monitoring active. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping bot...")

if __name__ == "__main__":
    main()
