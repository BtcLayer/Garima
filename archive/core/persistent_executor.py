"""
Production-Grade Persistent Executor
Addresses weaknesses: restart-safe, network-timeout-safe, multi-instance-safe, exchange-safe.

Architecture:
1. SQLite persistent cache (survives restarts)
2. Exchange-level idempotency (Binance newClientOrderId)
3. Timeout handling (query exchange if network fails)
4. State machine (INIT → SUBMITTING → ACKNOWLEDGED → FILLED)
"""

import sqlite3
import threading
from typing import Optional, Dict, List
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass
from core.order_manager import Order, OrderStatus


class ExecutorState(Enum):
    """Order execution state machine."""
    INIT = "INIT"                   # Order created, not submitted
    SUBMITTING = "SUBMITTING"       # Request sent to exchange
    ACKNOWLEDGED = "ACKNOWLEDGED"   # Exchange confirmed with order ID
    FAILED = "FAILED"               # Permanent failure
    SUBMITTED = "SUBMITTED"         # Legacy (for compatibility)


@dataclass
class PersistentOrderRecord:
    """Persistent order record in DB."""
    order_id: int
    client_order_id: str
    exchange_order_id: Optional[str]
    state: ExecutorState
    attempt_count: int
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime


class PersistentExecutorDB:
    """SQLite-backed persistent executor storage."""
    
    def __init__(self, db_path: str = "executor_state.db"):
        """Initialize DB connection."""
        self.db_path = db_path
        self.lock = threading.Lock()
        # Keep persistent connection for in-memory DBs (each connection = separate DB)
        self._conn = sqlite3.connect(db_path, check_same_thread=False) if db_path == ":memory:" else None
        self._init_db()
    
    def _get_conn(self):
        """Get DB connection (persistent for :memory:, fresh for files)."""
        if self._conn:
            return self._conn
        return sqlite3.connect(self.db_path)
    
    def _init_db(self):
        """Initialize DB schema."""
        if self._conn:
            conn = self._conn
        else:
            conn = sqlite3.connect(self.db_path)
        
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS executor_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_order_id TEXT UNIQUE NOT NULL,
                    exchange_order_id TEXT,
                    state TEXT NOT NULL DEFAULT 'INIT',
                    attempt_count INTEGER DEFAULT 0,
                    last_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(client_order_id)
                )
            """)
            conn.commit()
        finally:
            if not self._conn:
                conn.close()
    
    def save_order(
        self,
        client_order_id: str,
        exchange_order_id: Optional[str] = None,
        state: ExecutorState = ExecutorState.INIT,
        error: Optional[str] = None,
        increment_attempt: bool = True,
    ) -> None:
        """Save/update order in persistent storage."""
        now = datetime.now(timezone.utc).isoformat()
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                # Try update first
                if increment_attempt:
                    cursor = conn.execute(
                        """
                        UPDATE executor_orders 
                        SET exchange_order_id=?, state=?, attempt_count=attempt_count+1, 
                            last_error=?, updated_at=?
                        WHERE client_order_id=?
                        """,
                        (exchange_order_id, state.value, error, now, client_order_id)
                    )
                else:
                    cursor = conn.execute(
                        """
                        UPDATE executor_orders 
                        SET exchange_order_id=?, state=?, last_error=?, updated_at=?
                        WHERE client_order_id=?
                        """,
                        (exchange_order_id, state.value, error, now, client_order_id)
                    )
                
                # If no rows updated, insert
                if cursor.rowcount == 0:
                    # Start with 1 if we're incrementing (successful attempt), else 0
                    initial_count = 1 if increment_attempt else 0
                    conn.execute(
                        """
                        INSERT INTO executor_orders 
                        (client_order_id, exchange_order_id, state, attempt_count, last_error, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (client_order_id, exchange_order_id, state.value, initial_count, error, now, now)
                    )
                
                conn.commit()
    
    def get_order(self, client_order_id: str) -> Optional[PersistentOrderRecord]:
        """Retrieve order from persistent storage."""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT id, client_order_id, exchange_order_id, state, attempt_count, last_error, created_at, updated_at
                    FROM executor_orders
                    WHERE client_order_id=?
                    """,
                    (client_order_id,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return PersistentOrderRecord(
                    order_id=row[0],
                    client_order_id=row[1],
                    exchange_order_id=row[2],
                    state=ExecutorState(row[3]),
                    attempt_count=row[4],
                    last_error=row[5],
                    created_at=datetime.fromisoformat(row[6]),
                    updated_at=datetime.fromisoformat(row[7]),
                )
    
    def get_all_orders(self) -> List[PersistentOrderRecord]:
        """Get all persisted orders."""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT id, client_order_id, exchange_order_id, state, attempt_count, last_error, created_at, updated_at
                    FROM executor_orders
                    ORDER BY created_at DESC
                    """
                )
                return [
                    PersistentOrderRecord(
                        order_id=row[0],
                        client_order_id=row[1],
                        exchange_order_id=row[2],
                        state=ExecutorState(row[3]),
                        attempt_count=row[4],
                        last_error=row[5],
                        created_at=datetime.fromisoformat(row[6]),
                        updated_at=datetime.fromisoformat(row[7]),
                    )
                    for row in cursor.fetchall()
                ]
    
    def clear(self):
        """Clear all records (for testing)."""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM executor_orders")
                conn.commit()
    
    def close(self):
        """Close DB connections (for testing cleanup)."""
        # SQLite auto-closes with context manager, but force any open transactions to close
        pass


class ProductionExecutor:
    """
    Production-grade executor with:
    - Persistent cache (SQLite)
    - Exchange-level idempotency (newClientOrderId)
    - Timeout handling (query exchange)
    - State machine tracking
    """
    
    def __init__(self, exchange, db_path: str = "executor_state.db"):
        """
        Initialize production executor.
        
        Args:
            exchange: Exchange adapter with submit_order(order) and query_order(client_order_id)
            db_path: SQLite DB path
        """
        self.exchange = exchange
        self.db = PersistentExecutorDB(db_path)
    
    def execute(self, order: Order) -> tuple[bool, str, Optional[str]]:
        """
        Execute order with production-grade safety.
        
        Algorithm:
        1. Check persistent DB for client_order_id
        2. If ACKNOWLEDGED → return cached exchange_order_id (restart safe)
        3. If SUBMITTING → query exchange (timeout safe)
        4. If INIT/FAILED → submit with deterministic ID (exchange safe)
        
        Returns:
            (success, message, exchange_order_id)
        """
        client_order_id = order.client_order_id
        
        # Step 1: Check persistent cache
        persistent = self.db.get_order(client_order_id)
        
        if persistent and persistent.state == ExecutorState.ACKNOWLEDGED:
            # **Restart Safe**: Already acknowledged, return cached ID
            return (True, "Order already acknowledged (cached)", persistent.exchange_order_id)
        
        if persistent and persistent.state == ExecutorState.SUBMITTING:
            # **Timeout Safe**: Was submitting, query exchange to check if it went through
            exchange_id = self._query_exchange_order(client_order_id)
            if exchange_id:
                # Order was accepted, save state
                self.db.save_order(
                    client_order_id=client_order_id,
                    exchange_order_id=exchange_id,
                    state=ExecutorState.ACKNOWLEDGED,
                )
                return (True, "Order found on exchange (recovered from timeout)", exchange_id)
            else:
                # Not on exchange yet, will retry below
                pass
        
        # Step 2: Submit order (mark as SUBMITTING first)
        self.db.save_order(
            client_order_id=client_order_id,
            state=ExecutorState.SUBMITTING,
            increment_attempt=False,  # Don't increment here, only on actual exchange interaction
        )
        
        try:
            # **Exchange-level idempotency**: Pass deterministic client_order_id
            result = self.exchange.submit_order(order, client_order_id=client_order_id)
            
            if result['success']:
                exchange_order_id = result.get('exchange_order_id')
                
                # **Save ACKNOWLEDGED state**
                self.db.save_order(
                    client_order_id=client_order_id,
                    exchange_order_id=exchange_order_id,
                    state=ExecutorState.ACKNOWLEDGED,
                    increment_attempt=True,  # Count successful submission
                )
                
                return (True, "Order submitted and acknowledged", exchange_order_id)
            else:
                # Check if duplicate
                error = result.get('error', '')
                
                if 'duplicate' in error.lower() or 'already' in error.lower():
                    # **Exchange rejected duplicate**: Fetch existing order
                    exchange_id = self._query_exchange_order(client_order_id)
                    if exchange_id:
                        self.db.save_order(
                            client_order_id=client_order_id,
                            exchange_order_id=exchange_id,
                            state=ExecutorState.ACKNOWLEDGED,
                        )
                        return (True, "Duplicate detected, fetched existing order", exchange_id)
                
                # Permanent failure
                self.db.save_order(
                    client_order_id=client_order_id,
                    state=ExecutorState.FAILED,
                    error=error,
                )
                return (False, f"Exchange rejected: {error}", None)
        
        except TimeoutError:
            # **Timeout Safe**: Query exchange to check if order went through
            exchange_id = self._query_exchange_order(client_order_id)
            
            if exchange_id:
                self.db.save_order(
                    client_order_id=client_order_id,
                    exchange_order_id=exchange_id,
                    state=ExecutorState.ACKNOWLEDGED,
                )
                return (True, "Order submitted (confirmed after timeout)", exchange_id)
            else:
                # Unclear state, mark as retryable
                self.db.save_order(
                    client_order_id=client_order_id,
                    state=ExecutorState.INIT,
                    error="Network timeout",
                )
                return (False, "Network timeout - retry from persistent state", None)
        
        except Exception as e:
            self.db.save_order(
                client_order_id=client_order_id,
                state=ExecutorState.FAILED,
                error=str(e),
            )
            return (False, f"Error: {str(e)}", None)
    
    def _query_exchange_order(self, client_order_id: str) -> Optional[str]:
        """
        Query exchange for order by client_order_id.
        
        Returns:
            Exchange order ID if found, else None
        """
        try:
            result = self.exchange.query_order(client_order_id=client_order_id)
            return result.get('exchange_order_id') if result else None
        except Exception:
            return None
    
    def get_persisted_state(self, client_order_id: str) -> Optional[PersistentOrderRecord]:
        """Get persisted state of order."""
        return self.db.get_order(client_order_id)
    
    def get_stats(self) -> dict:
        """Get executor statistics."""
        orders = self.db.get_all_orders()
        
        states = {}
        for order in orders:
            state = order.state.value
            states[state] = states.get(state, 0) + 1
        
        return {
            'total_orders': len(orders),
            'states': states,
            'db_path': self.db.db_path,
        }
