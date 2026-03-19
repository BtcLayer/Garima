"""
Order Executor Module
Handles order execution with idempotent retry support.

Key Concept:
- If we see a client_order_id we've already acknowledged from exchange,
  skip re-submitting and return the cached exchange_order_id
- This ensures retries don't create duplicate exchange orders
"""

from typing import Optional, Dict, List
from dataclasses import dataclass
from core.order_manager import Order, OrderStatus


@dataclass
class ExecutionResult:
    """Result of order execution."""
    success: bool
    exchange_order_id: Optional[str] = None
    error: Optional[str] = None
    was_cached: bool = False  # True if order already acknowledged
    
    def __repr__(self):
        if self.success:
            cached_note = " (cached)" if self.was_cached else ""
            return f"ExecutionResult(success=True, exchange_order_id={self.exchange_order_id}{cached_note})"
        else:
            return f"ExecutionResult(success=False, error={self.error})"


class ExchangeAdapter:
    """Base interface for exchange operations."""
    
    def submit_order(self, order: Order) -> ExecutionResult:
        """
        Submit order to exchange.
        
        Args:
            order: Order to submit
        
        Returns:
            ExecutionResult with exchange_order_id on success
        """
        raise NotImplementedError()


class IdempotentExecutor:
    """
    Executes orders idempotently using client_order_id.
    
    Idempotency Strategy:
    1. Before submitting order: check if we already have exchange_order_id for this client_order_id
    2. If yes: return cached exchange_order_id (don't re-submit)
    3. If no: submit to exchange, store exchange_order_id mapping
    
    This ensures retries don't create duplicate orders.
    """
    
    def __init__(self, exchange: ExchangeAdapter):
        """
        Initialize executor.
        
        Args:
            exchange: ExchangeAdapter implementation
        """
        self.exchange = exchange
        # Map of client_order_id -> exchange_order_id for acknowledged orders
        self.acknowledged_orders: Dict[str, str] = {}
    
    def execute(self, order: Order) -> ExecutionResult:
        """
        Execute order with idempotency.
        
        Algorithm:
        1. Check if client_order_id already acknowledged
        2. If yes → return cached exchange_order_id (idempotent)
        3. If no → submit to exchange
        4. On success → store mapping and return result
        
        Args:
            order: Order to execute
        
        Returns:
            ExecutionResult with success flag and exchange_order_id
        """
        client_order_id = order.client_order_id
        
        # Step 1: Check cache for acknowledgment
        if client_order_id in self.acknowledged_orders:
            cached_exchange_id = self.acknowledged_orders[client_order_id]
            return ExecutionResult(
                success=True,
                exchange_order_id=cached_exchange_id,
                was_cached=True,  # Signal that this was cached
            )
        
        # Step 2: Submit to exchange (not cached)
        result = self.exchange.submit_order(order)
        
        # Step 3: On success, cache the mapping
        if result.success and result.exchange_order_id:
            self.acknowledged_orders[client_order_id] = result.exchange_order_id
            order.mark_acknowledged(result.exchange_order_id)
            result.was_cached = False
        
        return result
    
    def get_acknowledged_exchange_id(self, client_order_id: str) -> Optional[str]:
        """Get exchange_order_id if acknowledged, else None."""
        return self.acknowledged_orders.get(client_order_id)
    
    def get_all_acknowledged_orders(self) -> Dict[str, str]:
        """Get all acknowledged orders mapping."""
        return self.acknowledged_orders.copy()


class MockExchange(ExchangeAdapter):
    """Mock exchange for testing."""
    
    def __init__(self):
        """Initialize mock exchange."""
        self.submitted_orders = []  # Track all submissions
        self.fail_count = 0  # Fail first N attempts
        self.next_exchange_id = 1
    
    def submit_order(self, order: Order) -> ExecutionResult:
        """Mock submit - can be configured to fail."""
        self.submitted_orders.append(order.client_order_id)
        
        # Simulate failures
        if self.fail_count > 0:
            self.fail_count -= 1
            return ExecutionResult(
                success=False,
                error="Network timeout",
            )
        
        # Success
        exchange_order_id = f"exch_{self.next_exchange_id}"
        self.next_exchange_id += 1
        
        return ExecutionResult(
            success=True,
            exchange_order_id=exchange_order_id,
        )
    
    def reset(self):
        """Reset mock exchange state."""
        self.submitted_orders = []
        self.fail_count = 0
        self.next_exchange_id = 1
    
    def get_submission_count(self, client_order_id: str) -> int:
        """Get how many times a client_order_id was submitted."""
        return self.submitted_orders.count(client_order_id)

    def execute_trade(self, signal_id, venue, leg, attempt, params):
    # 1. Generate the ID
        cl_id = self.order_manager.generate_client_order_id(signal_id, venue, leg, attempt)
        
        # 2. Requirement 4.2: Check if clinical ack exists in EventLogger/Recon
        # We look for any 'ORDER_ACK' or 'FILL' events for this specific ID
        history = self.logger.get_events_by_client_id(cl_id) 
        
        if any(e.event_type in [EventType.ORDER_ACK, EventType.FILL_RECEIVED] for e in history):
            print(f"⚠️ Skipping duplicate execution: {cl_id} already exists in logs.")
            return None # Exit early

        # 3. Proceed only if no previous record found
        return self.binance_client.create_order(params, client_id=cl_id)