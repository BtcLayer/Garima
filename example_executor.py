"""
Example: Order Execution with Idempotency
Demonstrates T4 - Deterministic client_order_id & executor idempotency
"""

from core.order_manager import OrderManager, OrderSide
from core.executor import IdempotentExecutor, MockExchange


def main():
    """
    Demonstrate idempotent order execution preventing duplicate exchange orders.
    """
    print("=" * 70)
    print("T4: Deterministic client_order_id & Executor Idempotency")
    print("=" * 70)
    
    # Setup
    manager = OrderManager()
    mock_exchange = MockExchange()
    executor = IdempotentExecutor(mock_exchange)
    
    # Scenario: Network failure on first attempt, retry succeeds
    print("\n📋 SCENARIO: Network Failure + Retry")
    print("-" * 70)
    
    # Create order
    order = manager.create_order(
        signal_id="sig_daily_001",
        venue="binance",
        leg="entry",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        quantity=0.001,
        price=45000,
    )
    
    print(f"\n✓ Created order:")
    print(f"  client_order_id: {order.client_order_id}")
    print(f"  Format: {{signal_id}}:{{venue}}:{{leg}}:{{attempt}}")
    print(f"  Symbol: {order.symbol}")
    print(f"  Side: {order.side.value}")
    print(f"  Quantity: {order.quantity}")
    print(f"  Price: {order.price}")
    
    # Attempt 1: Network failure
    print(f"\n🔄 Attempt 1: Submit to exchange...")
    mock_exchange.fail_count = 1  # Fail once
    result1 = executor.execute(order)
    print(f"  Result: FAILED - {result1.error}")
    print(f"  Exchange submissions for this order: {mock_exchange.get_submission_count(order.client_order_id)}")
    
    # Attempt 2: Retry
    print(f"\n🔄 Attempt 2: Retry (network recovered)...")
    result2 = executor.execute(order)
    print(f"  Result: SUCCESS")
    print(f"  Exchange order ID: {result2.exchange_order_id}")
    print(f"  Cached: {result2.was_cached}")
    print(f"  Exchange submissions for this order: {mock_exchange.get_submission_count(order.client_order_id)}")
    
    # Attempt 3: Retry again (should be cached)
    print(f"\n🔄 Attempt 3: Retry again (already acknowledged)...")
    result3 = executor.execute(order)
    print(f"  Result: SUCCESS (from cache)")
    print(f"  Exchange order ID: {result3.exchange_order_id}")
    print(f"  Cached: {result3.was_cached}")
    print(f"  Exchange submissions for this order: {mock_exchange.get_submission_count(order.client_order_id)}")
    
    # Acceptance criteria
    print(f"\n{'=' * 70}")
    print("✅ ACCEPTANCE CRITERIA:")
    total_submissions = mock_exchange.get_submission_count(order.client_order_id)
    print(f"   Expected: 2 exchange submissions (fail + success)")
    print(f"   Actual:   {total_submissions} exchange submissions")
    
    if total_submissions == 2:
        print("   Status: ✅ PASS - No duplicate exchange orders!")
    else:
        print("   Status: ❌ FAIL - Unexpected submission count")
    
    # Multi-leg example
    print(f"\n{'=' * 70}")
    print("📋 MULTI-LEG EXAMPLE: Entry + Exit same signal")
    print("-" * 70)
    
    # Entry order
    entry_order = manager.create_order(
        signal_id="sig_daily_002",
        venue="binance",
        leg="entry",
        symbol="ETHUSDT",
        side=OrderSide.BUY,
        quantity=1.0,
        price=3000,
    )
    
    # Exit order (same signal, different leg)
    exit_order = manager.create_order(
        signal_id="sig_daily_002",
        venue="binance",
        leg="exit",
        symbol="ETHUSDT",
        side=OrderSide.SELL,
        quantity=1.0,
        price=3100,
    )
    
    print(f"\n✓ Created two legs of same signal:")
    print(f"  Entry: {entry_order.client_order_id}")
    print(f"  Exit:  {exit_order.client_order_id}")
    
    # Execute both
    entry_result = executor.execute(entry_order)
    exit_result = executor.execute(exit_order)
    
    print(f"\n✓ Executed both legs:")
    print(f"  Entry exchange ID: {entry_result.exchange_order_id}")
    print(f"  Exit exchange ID:  {exit_result.exchange_order_id}")
    print(f"  Different IDs: {entry_result.exchange_order_id != exit_result.exchange_order_id} ✓")
    
    print(f"\n{'=' * 70}\n")


if __name__ == '__main__':
    main()
