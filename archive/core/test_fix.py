# test_fix.py
from unittest.mock import MagicMock
from core.event_logger import EventLogger, EventType
from core.executor import OrderExecutor  # Adjust based on your actual class name
from core.order_manager import generate_client_order_id

def test_idempotency_scenario():
    print("=" * 80)
    print("TEST 4.3: MOCK EXCHANGE RETRY SCENARIO")
    print("=" * 80)

    # 1. Setup Components
    logger = EventLogger()
    # Mock the Binance Client so it doesn't actually place trades
    mock_binance = MagicMock()
    
    # Initialize your executor with the logger and mock client
    # Note: Adjust the initialization parameters to match your executor.py
    executor = OrderExecutor(binance_client=mock_binance, logger=logger)

    # 2. Define Order Parameters
    signal_id = "SIG_RETRY_101"
    venue = "BINANCE"
    leg = 1
    attempt = 0
    
    # 3. FIRST ATTEMPT (Normal Flow)
    print("\n[Attempt 1] Sending order to exchange...")
    executor.execute_trade(signal_id, venue, leg, attempt, {"symbol": "BTCUSDT", "qty": 0.1})
    
    # Manually log an ACK to simulate a successful exchange receipt
    cl_id = f"{signal_id}:{venue}:{leg}:{attempt}"
    logger.log_order_ack(signal_id=signal_id, client_order_id=cl_id, exchange_order_id="EXCH_999")
    print("  ✓ Attempt 1 completed and Acknowledged in logs.")

    # 4. SECOND ATTEMPT (The Retry Scenario)
    print(f"\n[Attempt 2] Retrying same order ID: {cl_id}")
    executor.execute_trade(signal_id, venue, leg, attempt, {"symbol": "BTCUSDT", "qty": 0.1})

    # 5. VERIFICATION (Acceptance Criteria)
    # The binance_client.create_order should have been called ONLY ONCE
    actual_calls = mock_binance.create_order.call_count
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Exchange Order Calls: {actual_calls}")
    
    if actual_calls == 1:
        print("\n✅ AC MET: Retry test shows one exchange order only.")
        print("✅ SUCCESS: Duplicate execution prevented.")
    else:
        print("\n❌ AC FAILED: Multiple orders were sent to the exchange!")
    print("=" * 80)

if __name__ == "__main__":
    test_idempotency_scenario()
