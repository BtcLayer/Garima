"""
Order Manager Module
Manages order creation with deterministic client_order_id generation.

Order Format:
    client_order_id: "{signal_id}:{venue}:{leg}:{attempt}"
    Example: "sig_123:binance:entry:0"
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime, timezone


class OrderSide(Enum):
    """Order side enumeration."""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "PENDING"           # Created, not sent
    SUBMITTED = "SUBMITTED"       # Sent to exchange
    ACKNOWLEDGED = "ACKNOWLEDGED" # Exchange ack received
    FILLED = "FILLED"            # Partially or fully filled
    CANCELLED = "CANCELLED"      # User cancelled
    REJECTED = "REJECTED"        # Exchange rejected


@dataclass
class Order:
    """
    Order object with deterministic client_order_id.
    
    Attributes:
        signal_id: Trading signal identifier (e.g., "sig_123")
        venue: Exchange name (e.g., "binance")
        leg: Order leg name (e.g., "entry", "exit")
        symbol: Trading pair (e.g., "BTCUSDT")
        side: BUY or SELL
        quantity: Order quantity
        price: Limit price (None for market orders)
        attempt: Retry attempt number (0-indexed)
        status: Current order status
        exchange_order_id: Exchange-assigned order ID (filled after submission)
        created_at: Creation timestamp
        submitted_at: Submission timestamp
        
    Properties:
        client_order_id: Deterministic "{signal_id}:{venue}:{leg}:{attempt}"
    """
    signal_id: str
    venue: str
    leg: str
    symbol: str
    side: OrderSide
    quantity: float
    price: Optional[float] = None
    attempt: int = 0
    status: OrderStatus = OrderStatus.PENDING
    exchange_order_id: Optional[str] = None
    created_at: datetime = None
    submitted_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize timestamps if not provided."""
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
    
    @property
    def client_order_id(self) -> str:
        """
        Generate deterministic client_order_id.
        
        Format: "{signal_id}:{venue}:{leg}:{attempt}"
        Example: "sig_123:binance:entry:0"
        
        This ID is globally unique and idempotent - same inputs always 
        produce same ID, enabling retry-safe order handling.
        """
        return f"{self.signal_id}:{self.venue}:{self.leg}:{self.attempt}"
    
    def mark_submitted(self) -> None:
        """Mark order as submitted to exchange."""
        self.status = OrderStatus.SUBMITTED
        self.submitted_at = datetime.now(timezone.utc)
    
    def mark_acknowledged(self, exchange_order_id: str) -> None:
        """Mark order as acknowledged by exchange."""
        self.status = OrderStatus.ACKNOWLEDGED
        self.exchange_order_id = exchange_order_id
    
    def mark_filled(self) -> None:
        """Mark order as filled."""
        self.status = OrderStatus.FILLED
    
    def mark_cancelled(self) -> None:
        """Mark order as cancelled."""
        self.status = OrderStatus.CANCELLED
    
    def mark_rejected(self) -> None:
        """Mark order as rejected."""
        self.status = OrderStatus.REJECTED
    
    def retry(self) -> 'Order':
        """
        Create a retry version of this order with incremented attempt.
        
        Returns:
            New Order with attempt incremented and status reset to PENDING.
            Note: client_order_id will change due to new attempt number.
        """
        return Order(
            signal_id=self.signal_id,
            venue=self.venue,
            leg=self.leg,
            symbol=self.symbol,
            side=self.side,
            quantity=self.quantity,
            price=self.price,
            attempt=self.attempt + 1,
            status=OrderStatus.PENDING,
            exchange_order_id=None,
            created_at=self.created_at,  # Keep original creation time
            submitted_at=None,
        )
    
    def to_dict(self) -> dict:
        """Convert order to dictionary for storage/serialization."""
        return {
            'signal_id': self.signal_id,
            'venue': self.venue,
            'leg': self.leg,
            'symbol': self.symbol,
            'side': self.side.value,
            'quantity': self.quantity,
            'price': self.price,
            'attempt': self.attempt,
            'status': self.status.value,
            'client_order_id': self.client_order_id,
            'exchange_order_id': self.exchange_order_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Order':
        """Create Order from dictionary."""
        return cls(
            signal_id=data['signal_id'],
            venue=data['venue'],
            leg=data['leg'],
            symbol=data['symbol'],
            side=OrderSide(data['side']),
            quantity=data['quantity'],
            price=data.get('price'),
            attempt=data.get('attempt', 0),
            status=OrderStatus(data.get('status', 'PENDING')),
            exchange_order_id=data.get('exchange_order_id'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            submitted_at=datetime.fromisoformat(data['submitted_at']) if data.get('submitted_at') else None,
        )


class OrderManager:
    """Manages order lifecycle and storage."""
    
    def __init__(self):
        """Initialize order manager."""
        self.orders = {}  # Map of client_order_id -> Order
    
    def create_order(
        self,
        signal_id: str,
        venue: str,
        leg: str,
        symbol: str,
        side: OrderSide,
        quantity: float,
        price: Optional[float] = None,
    ) -> Order:
        """
        Create a new order with deterministic client_order_id.
        
        Args:
            signal_id: Trading signal identifier
            venue: Exchange name
            leg: Order leg name (e.g., 'entry', 'exit')
            symbol: Trading pair
            side: BUY or SELL
            quantity: Order quantity
            price: Limit price (None for market orders)
        
        Returns:
            Order instance with client_order_id = "{signal_id}:{venue}:{leg}:0"
        """
        order = Order(
            signal_id=signal_id,
            venue=venue,
            leg=leg,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            attempt=0,
        )
        self.orders[order.client_order_id] = order
        return order
    
    def get_order(self, client_order_id: str) -> Optional[Order]:
        """Retrieve order by client_order_id."""
        return self.orders.get(client_order_id)
    
    def get_orders_by_signal(self, signal_id: str) -> list[Order]:
        """Get all orders for a signal."""
        return [o for o in self.orders.values() if o.signal_id == signal_id]
    
    def update_order_status(
        self,
        client_order_id: str,
        status: OrderStatus,
        exchange_order_id: Optional[str] = None,
    ) -> Optional[Order]:
        """Update order status."""
        order = self.get_order(client_order_id)
        if not order:
            return None
        
        order.status = status
        if exchange_order_id:
            order.exchange_order_id = exchange_order_id
        
        return order

    def generate_client_order_id(signal_id, venue, leg, attempt):
        # Format: "{signal_id}:{venue}:{leg}:{attempt}"
        return f"{signal_id}:{venue}:{leg}:{attempt}"
