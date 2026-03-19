"""
Unit tests for order executor idempotency.

Acceptance Criteria:
- test_retry_scenario: Mock exchange retry scenario → confirm single exchange order
  (even with multiple retries, only ONE exchange order is created)
"""

import unittest
from core.order_manager import Order, OrderManager, OrderSide, OrderStatus
from core.executor import IdempotentExecutor, MockExchange, ExecutionResult


class TestExecutorIdempotency(unittest.TestCase):
    """Test order executor idempotency."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_exchange = MockExchange()
        self.executor = IdempotentExecutor(self.mock_exchange)
        self.order_manager = OrderManager()
    
    def test_client_order_id_format(self):
        """Test deterministic client_order_id format."""
        order = self.order_manager.create_order(
            signal_id="sig_123",
            venue="binance",
            leg="entry",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.001,
            price=50000,
        )
        
        # Verify format: "{signal_id}:{venue}:{leg}:{attempt}"
        expected = "sig_123:binance:entry:0"
        self.assertEqual(order.client_order_id, expected)
    
    def test_single_execution_success(self):
        """Test successful single execution."""
        order = self.order_manager.create_order(
            signal_id="sig_123",
            venue="binance",
            leg="entry",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.001,
            price=50000,
        )
        
        result = self.executor.execute(order)
        
        # Verify success
        self.assertTrue(result.success)
        self.assertIsNotNone(result.exchange_order_id)
        self.assertFalse(result.was_cached)
        
        # Verify order status updated
        self.assertEqual(order.status, OrderStatus.ACKNOWLEDGED)
        self.assertEqual(order.exchange_order_id, result.exchange_order_id)
    
    def test_duplicate_execution_idempotent(self):
        """
        ACCEPTANCE TEST: Idempotency
        
        Same order executed twice returns cached exchange_order_id.
        Ensures no duplicate exchange orders are created.
        """
        order = self.order_manager.create_order(
            signal_id="sig_123",
            venue="binance",
            leg="entry",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.001,
            price=50000,
        )
        
        # First execution
        result1 = self.executor.execute(order)
        exchange_id_1 = result1.exchange_order_id
        submit_count_1 = self.mock_exchange.get_submission_count(order.client_order_id)
        
        self.assertTrue(result1.success)
        self.assertFalse(result1.was_cached)
        self.assertEqual(submit_count_1, 1, "Should be submitted once")
        
        # Second execution (retry)
        result2 = self.executor.execute(order)
        exchange_id_2 = result2.exchange_order_id
        submit_count_2 = self.mock_exchange.get_submission_count(order.client_order_id)
        
        # Acceptance: Same exchange_order_id returned from cache
        self.assertEqual(exchange_id_1, exchange_id_2, "Must return same exchange_order_id")
        self.assertTrue(result2.was_cached, "Second call should use cache")
        self.assertEqual(submit_count_2, 1, "CRITICAL: Still only 1 exchange submission")
    
    def test_retry_scenario_network_failure(self):
        """
        ACCEPTANCE TEST: Retry scenario with network failure
        
        Scenario:
        1. Submit order → network timeout (fail)
        2. Retry submit → success
        3. Retry submit again → cached (no duplicate exchange order)
        
        Expected: Only 2 exchange submissions (fail + success), not 3
        """
        order = self.order_manager.create_order(
            signal_id="sig_456",
            venue="binance",
            leg="entry",
            symbol="ETHUSDT",
            side=OrderSide.BUY,
            quantity=1.0,
            price=3000,
        )
        
        client_order_id = order.client_order_id
        
        # Attempt 1: Network failure
        self.mock_exchange.fail_count = 1
        result1 = self.executor.execute(order)
        self.assertFalse(result1.success, "First attempt should fail")
        self.assertEqual(self.mock_exchange.get_submission_count(client_order_id), 1)
        
        # Attempt 2: Retry after failure → success
        result2 = self.executor.execute(order)
        self.assertTrue(result2.success, "Retry should succeed")
        self.assertFalse(result2.was_cached, "Not cached yet")
        exchange_id = result2.exchange_order_id
        self.assertEqual(self.mock_exchange.get_submission_count(client_order_id), 2,
                        "Should be submitted twice (fail + success)")
        
        # Attempt 3: Retry again → should be cached
        result3 = self.executor.execute(order)
        self.assertTrue(result3.success)
        self.assertTrue(result3.was_cached, "Should return cached result")
        self.assertEqual(result3.exchange_order_id, exchange_id)
        
        # ACCEPTANCE: Still only 2 submissions, not 3
        submission_count = self.mock_exchange.get_submission_count(client_order_id)
        self.assertEqual(submission_count, 2,
                        f"ACCEPTANCE: Only 2 exchange submissions expected, got {submission_count}")
    
    def test_different_attempts_different_client_ids(self):
        """
        Test that retry attempts with incremented attempt number 
        produce different client_order_ids.
        """
        order = self.order_manager.create_order(
            signal_id="sig_789",
            venue="binance",
            leg="entry",
            symbol="LTCUSDT",
            side=OrderSide.SELL,
            quantity=10.0,
            price=200,
        )
        
        # Original attempt 0
        client_id_0 = order.client_order_id
        self.assertEqual(client_id_0, "sig_789:binance:entry:0")
        
        # Create retry order (attempt 1)
        order_retry = order.retry()
        client_id_1 = order_retry.client_order_id
        self.assertEqual(client_id_1, "sig_789:binance:entry:1")
        
        # Different client_order_ids
        self.assertNotEqual(client_id_0, client_id_1)
        
        # Both can be independently tracked
        self.executor.execute(order)
        self.executor.execute(order_retry)
        
        self.assertIn(client_id_0, self.executor.acknowledged_orders)
        self.assertIn(client_id_1, self.executor.acknowledged_orders)
        self.assertEqual(len(self.executor.acknowledged_orders), 2)
    
    def test_multi_leg_orders_independence(self):
        """
        Test that multiple legs (entry, exit) of same signal 
        are tracked independently.
        """
        # Entry order
        entry_order = self.order_manager.create_order(
            signal_id="sig_multi",
            venue="binance",
            leg="entry",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.001,
            price=50000,
        )
        
        # Exit order (same signal, different leg)
        exit_order = self.order_manager.create_order(
            signal_id="sig_multi",
            venue="binance",
            leg="exit",
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            quantity=0.001,
            price=55000,
        )
        
        # Execute both
        result_entry = self.executor.execute(entry_order)
        result_exit = self.executor.execute(exit_order)
        
        # Both should succeed
        self.assertTrue(result_entry.success)
        self.assertTrue(result_exit.success)
        
        # Different exchange IDs
        self.assertNotEqual(result_entry.exchange_order_id, result_exit.exchange_order_id)
        
        # Both tracked independently
        self.assertEqual(len(self.executor.acknowledged_orders), 2)
    
    def test_execution_result_representation(self):
        """Test ExecutionResult string representation."""
        # Success without cache
        result_success = ExecutionResult(
            success=True,
            exchange_order_id="exch_123",
            was_cached=False,
        )
        self.assertIn("success=True", str(result_success))
        self.assertIn("exch_123", str(result_success))
        self.assertNotIn("cached", str(result_success))
        
        # Success with cache
        result_cached = ExecutionResult(
            success=True,
            exchange_order_id="exch_123",
            was_cached=True,
        )
        self.assertIn("cached", str(result_cached))
        
        # Failure
        result_fail = ExecutionResult(
            success=False,
            error="Network timeout",
        )
        self.assertIn("success=False", str(result_fail))
        self.assertIn("Network timeout", str(result_fail))


class TestOrderRetry(unittest.TestCase):
    """Test order retry functionality."""
    
    def test_order_retry_increments_attempt(self):
        """Test that retry() increments attempt number."""
        order = Order(
            signal_id="sig_test",
            venue="binance",
            leg="entry",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.001,
            price=50000,
            attempt=0,
        )
        
        self.assertEqual(order.attempt, 0)
        self.assertEqual(order.client_order_id, "sig_test:binance:entry:0")
        
        # Retry
        order_retry = order.retry()
        self.assertEqual(order_retry.attempt, 1)
        self.assertEqual(order_retry.client_order_id, "sig_test:binance:entry:1")
        self.assertEqual(order_retry.status, OrderStatus.PENDING)
        self.assertIsNone(order_retry.exchange_order_id)
    
    def test_order_retry_preserves_created_at(self):
        """Test that retry preserves original created_at timestamp."""
        order = Order(
            signal_id="sig_test",
            venue="binance",
            leg="entry",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.001,
            price=50000,
        )
        
        original_created = order.created_at
        order_retry = order.retry()
        
        self.assertEqual(order_retry.created_at, original_created)


class TestOrderSerialization(unittest.TestCase):
    """Test order serialization."""
    
    def test_order_to_from_dict(self):
        """Test order serialization to/from dict."""
        order = Order(
            signal_id="sig_123",
            venue="binance",
            leg="entry",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.001,
            price=50000,
            attempt=2,
            status=OrderStatus.ACKNOWLEDGED,
            exchange_order_id="exch_999",
        )
        
        # Serialize
        order_dict = order.to_dict()
        
        self.assertEqual(order_dict['signal_id'], "sig_123")
        self.assertEqual(order_dict['client_order_id'], "sig_123:binance:entry:2")
        self.assertEqual(order_dict['exchange_order_id'], "exch_999")
        self.assertEqual(order_dict['status'], "ACKNOWLEDGED")
        
        # Deserialize
        order_restored = Order.from_dict(order_dict)
        
        self.assertEqual(order_restored.signal_id, order.signal_id)
        self.assertEqual(order_restored.client_order_id, order.client_order_id)
        self.assertEqual(order_restored.exchange_order_id, order.exchange_order_id)


if __name__ == '__main__':
    unittest.main()
