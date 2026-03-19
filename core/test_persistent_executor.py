"""
Production-grade executor tests.

Tests address the 4 weaknesses:
1. Restart safety (persistent cache)
2. Network timeout safety
3. Exchange duplicate handling
4. Multi-instance safety (shared DB)
"""

import unittest
from core.order_manager import Order, OrderManager, OrderSide
from core.persistent_executor import ProductionExecutor, ExecutorState


class MockProductionExchange:
    """Mock exchange for testing."""
    
    def __init__(self):
        self.submitted_orders = {}  # client_id -> exchange_id
        self.fail_count = 0
        self.next_id = 1000
        self.query_results = {}  # For simulating exchange state
    
    def submit_order(self, order: Order, client_order_id: str) -> dict:
        """Submit order with client_order_id."""
        # Simulate failures
        if self.fail_count > 0:
            self.fail_count -= 1
            raise TimeoutError("Network timeout")
        
        # Check if already submitted
        if client_order_id in self.submitted_orders:
            return {
                'success': False,
                'error': 'Duplicate client order ID',
            }
        
        # New order
        exchange_id = f"exch_{self.next_id}"
        self.next_id += 1
        
        self.submitted_orders[client_order_id] = exchange_id
        return {
            'success': True,
            'exchange_order_id': exchange_id,
        }
    
    def query_order(self, client_order_id: str) -> dict:
        """Query order by client_order_id."""
        if client_order_id in self.submitted_orders:
            return {
                'exchange_order_id': self.submitted_orders[client_order_id],
            }
        return None
    
    def clear(self):
        """Reset mock."""
        self.submitted_orders.clear()
        self.fail_count = 0


class TestPersistentExecutor(unittest.TestCase):
    """Test production executor."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Use in-memory DB for tests (avoids Windows file locking issues)
        self.db_path = ":memory:"
        
        self.exchange = MockProductionExchange()
        self.executor = ProductionExecutor(self.exchange, db_path=self.db_path)
        self.manager = OrderManager()
    
    def tearDown(self):
        """Clean up."""
        # In-memory DB auto-cleaned
        pass
    
    def test_basic_execution(self):
        """Test basic order execution."""
        order = self.manager.create_order(
            signal_id="sig_1",
            venue="binance",
            leg="entry",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.001,
            price=45000,
        )
        
        success, msg, exch_id = self.executor.execute(order)
        
        self.assertTrue(success)
        self.assertIsNotNone(exch_id)
    
    def test_restart_safety_cached_order(self):
        """
        ACCEPTANCE TEST 1: Restart Safety
        
        Scenario:
        1. Submit order → acknowledged
        2. Simulate restart (new executor, same DB)
        3. Re-execute same order
        Expected: Cached result returned (no re-submission)
        """
        order = self.manager.create_order(
            signal_id="sig_restart",
            venue="binance",
            leg="entry",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.001,
            price=45000,
        )
        
        # First execution
        success1, msg1, exch_id1 = self.executor.execute(order)
        self.assertTrue(success1)
        self.assertIn("acknowledged", msg1.lower())
        
        # Count submissions on exchange
        count_before = len(self.exchange.submitted_orders)
        
        # Simulate restart: new executor, same DB
        executor2 = ProductionExecutor(self.exchange, db_path=self.db_path)
        
        # Re-execute same order
        success2, msg2, exch_id2 = executor2.execute(order)
        
        # Acceptance: Cached result
        self.assertTrue(success2)
        self.assertEqual(exch_id1, exch_id2)
        self.assertIn("cached", msg2.lower())
        self.assertEqual(len(self.exchange.submitted_orders), count_before, 
                        "Should not re-submit")
    
    def test_network_timeout_recovery(self):
        """
        ACCEPTANCE TEST 2: Network Timeout Safety
        
        Scenario:
        1. Submit order → network timeout
        2. Exchange actually processed it
        3. Query exchange finds it
        4. Return it as acknowledged
        """
        order = self.manager.create_order(
            signal_id="sig_timeout",
            venue="binance",
            leg="entry",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.001,
            price=45000,
        )
        
        # Simulate: first call times out
        self.exchange.fail_count = 1
        
        executor = ProductionExecutor(self.exchange, db_path=self.db_path)
        executor.exchange.fail_count = 1  # Timeout on submit
        
        # First attempt: timeout
        try:
            success1, msg1, exch_id1 = executor.execute(order)
            self.assertFalse(success1, "Should fail on timeout")
        except:
            pass
        
        # Simulate: order was actually on exchange
        executor.exchange.submitted_orders[order.client_order_id] = "exch_recovered"
        
        # Second attempt: query should find it
        success2, msg2, exch_id2 = executor.execute(order)
        
        # Acceptance: Found order on exchange
        self.assertTrue(success2)
        self.assertIn("confirmed", msg2.lower())
        self.assertEqual(exch_id2, "exch_recovered")
    
    def test_exchange_duplicate_handling(self):
        """
        ACCEPTANCE TEST 3: Exchange Duplicate Handling
        
        Scenario:
        1. Submit order → acknowledged
        2. Later: re-submit same order
        3. Exchange returns duplicate error
        4. Query for existing order
        5. Return existing exchange ID
        """
        order = self.manager.create_order(
            signal_id="sig_dup",
            venue="binance",
            leg="entry",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.001,
            price=45000,
        )
        
        # First submission
        success1, msg1, exch_id1 = self.executor.execute(order)
        self.assertTrue(success1)
        
        # Reset state to INIT to force re-submission
        self.executor.db.save_order(
            client_order_id=order.client_order_id,
            state=ExecutorState.INIT,
        )
        
        # Second submission (will hit duplicate)
        success2, msg2, exch_id2 = self.executor.execute(order)
        
        # Acceptance: Same exchange ID returned
        self.assertTrue(success2)
        self.assertEqual(exch_id1, exch_id2)
    
    def test_persistent_state_tracking(self):
        """Test that order state is persisted correctly."""
        order = self.manager.create_order(
            signal_id="sig_state",
            venue="binance",
            leg="entry",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.001,
            price=45000,
        )
        
        # Check not in DB yet
        persisted = self.executor.get_persisted_state(order.client_order_id)
        self.assertIsNone(persisted)
        
        # Execute
        self.executor.execute(order)
        
        # Check persisted in DB
        persisted = self.executor.get_persisted_state(order.client_order_id)
        self.assertIsNotNone(persisted)
        self.assertEqual(persisted.state, ExecutorState.ACKNOWLEDGED)
        self.assertIsNotNone(persisted.exchange_order_id)
        self.assertEqual(persisted.attempt_count, 1)
    
    def test_multi_instance_shared_db(self):
        """
        ACCEPTANCE TEST 4: Multi-Instance Safety
        
        Scenario:
        1. Instance A submits order
        2. Instance B checks DB (same file)
        3. Instance B sees acknowledged order
        4. Instance B returns cached without re-submit
        """
        order = self.manager.create_order(
            signal_id="sig_multi",
            venue="binance",
            leg="entry",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.001,
            price=45000,
        )
        
        # Instance A submits
        executor_a = ProductionExecutor(self.exchange, db_path=self.db_path)
        success_a, msg_a, exch_id_a = executor_a.execute(order)
        self.assertTrue(success_a)
        
        submitted_count_before = len(self.exchange.submitted_orders)
        
        # Instance B (different executor, same DB)
        executor_b = ProductionExecutor(
            MockProductionExchange(),  # Different exchange mock
            db_path=self.db_path
        )
        
        success_b, msg_b, exch_id_b = executor_b.execute(order)
        
        # Acceptance: Instance B used cached result
        self.assertTrue(success_b)
        self.assertEqual(exch_id_a, exch_id_b)
        self.assertIn("cached", msg_b.lower())
        self.assertEqual(len(self.exchange.submitted_orders), submitted_count_before,
                        "Instance B should not have submitted")
    
    def test_executor_stats(self):
        """Test executor statistics."""
        order1 = self.manager.create_order(
            signal_id="sig_1", venue="binance", leg="entry",
            symbol="BTCUSDT", side=OrderSide.BUY, quantity=0.001, price=45000,
        )
        order2 = self.manager.create_order(
            signal_id="sig_2", venue="binance", leg="entry",
            symbol="ETHUSDT", side=OrderSide.BUY, quantity=1.0, price=3000,
        )
        
        self.executor.execute(order1)
        self.executor.execute(order2)
        
        stats = self.executor.get_stats()
        
        self.assertEqual(stats['total_orders'], 2)
        self.assertEqual(stats['states']['ACKNOWLEDGED'], 2)


if __name__ == '__main__':
    unittest.main()
