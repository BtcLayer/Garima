"""
Event Logger Module
Centralized audit trail for all trading bot events.

Events:
- signal_received: Trading signal from webhook
- order_submitted: Order sent to exchange
- order_ack: Order acknowledged by exchange
- fill_received: Trade execution
- position_snapshot: Current position state
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any, Dict, List
from datetime import datetime, timezone
import json


class EventType(Enum):
    """Event type enumeration."""
    SIGNAL_RECEIVED = "signal_received"
    ORDER_SUBMITTED = "order_submitted"
    ORDER_ACK = "order_ack"
    FILL_RECEIVED = "fill_received"
    POSITION_SNAPSHOT = "position_snapshot"
    RECON_INCIDENT = "recon_incident"
    ALERT_TRIGGERED = "alert_triggered"


@dataclass
class Event:
    """
    Immutable event record for audit trail.
    
    Attributes:
        event_type: Type of event
        timestamp: Event creation time (UTC)
        signal_id: Related trading signal ID (if applicable)
        data: Event-specific data dictionary
        metadata: Optional metadata (source, user, etc.)
    """
    event_type: EventType
    data: Dict[str, Any]
    signal_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        """Convert event to dictionary for storage."""
        return {
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'signal_id': self.signal_id,
            'data': self.data,
            'metadata': self.metadata or {},
        }
    
    def __repr__(self) -> str:
        return f"Event({self.event_type.value}, {self.signal_id}, {self.timestamp.isoformat()[:19]}Z)"


class EventLogger:
    """
    Centralized event logger with in-memory buffer.
    
    Wires together events from:
    - Webhook handlers (signal_received)
    - Order manager (order_submitted, order_ack)
    - Fill handlers (fill_received)
    - Position tracker (position_snapshot)
    - Reconciler (recon_incident)
    - AlertRouter (alert_triggered)
    """
    
    def __init__(self, buffer_size: int = 10000):
        """
        Initialize event logger.
        
        Args:
            buffer_size: Max events to keep in memory (circular buffer)
        """
        self.buffer_size = buffer_size
        self.events: List[Event] = []
        self.event_count = 0
    
    def log_event(self, event: Event) -> None:
        """
        Log an event.
        
        Args:
            event: Event to log
        """
        self.events.append(event)
        self.event_count += 1
        
        # Maintain circular buffer
        if len(self.events) > self.buffer_size:
            self.events.pop(0)
    
    def log_signal_received(self, signal_id: str, symbol: str, side: str, quantity: float, **kwargs) -> Event:
        """
        Log signal received event.
        
        Args:
            signal_id: Trading signal ID
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Order quantity
            **kwargs: Additional signal data
        
        Returns:
            Event logged
        """
        event = Event(
            event_type=EventType.SIGNAL_RECEIVED,
            signal_id=signal_id,
            data={
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                **kwargs,
            },
            metadata={'source': 'webhook'},
        )
        self.log_event(event)
        return event
    
    def log_order_submitted(self, signal_id: str, client_order_id: str, symbol: str, side: str, quantity: float, price: Optional[float] = None, **kwargs) -> Event:
        """
        Log order submitted event.
        
        Args:
            signal_id: Trading signal ID
            client_order_id: Client-generated order ID
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Order quantity
            price: Limit price (None for market)
            **kwargs: Additional order data
        
        Returns:
            Event logged
        """
        event = Event(
            event_type=EventType.ORDER_SUBMITTED,
            signal_id=signal_id,
            data={
                'client_order_id': client_order_id,
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': price,
                **kwargs,
            },
            metadata={'source': 'order_manager'},
        )
        self.log_event(event)
        return event
    
    def log_order_ack(self, signal_id: str, client_order_id: str, exchange_order_id: str, **kwargs) -> Event:
        """
        Log order acknowledged event.
        
        Args:
            signal_id: Trading signal ID
            client_order_id: Client-generated order ID
            exchange_order_id: Exchange-assigned order ID
            **kwargs: Additional data
        
        Returns:
            Event logged
        """
        event = Event(
            event_type=EventType.ORDER_ACK,
            signal_id=signal_id,
            data={
                'client_order_id': client_order_id,
                'exchange_order_id': exchange_order_id,
                **kwargs,
            },
            metadata={'source': 'exchange'},
        )
        self.log_event(event)
        return event
    
    def log_fill_received(self, signal_id: str, exchange_order_id: str, symbol: str, side: str, quantity: float, fill_price: float, **kwargs) -> Event:
        """
        Log fill received event.
        
        Args:
            signal_id: Trading signal ID
            exchange_order_id: Exchange order ID
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Filled quantity
            fill_price: Fill price
            **kwargs: Additional fill data
        
        Returns:
            Event logged
        """
        event = Event(
            event_type=EventType.FILL_RECEIVED,
            signal_id=signal_id,
            data={
                'exchange_order_id': exchange_order_id,
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'fill_price': fill_price,
                **kwargs,
            },
            metadata={'source': 'exchange'},
        )
        self.log_event(event)
        return event
    
    def log_position_snapshot(self, symbol: str, position: float, entry_price: float, current_price: float, pnl: float, **kwargs) -> Event:
        """
        Log position snapshot event.
        
        Args:
            symbol: Trading symbol
            position: Current position size
            entry_price: Average entry price
            current_price: Current market price
            pnl: Profit/loss
            **kwargs: Additional position data
        
        Returns:
            Event logged
        """
        event = Event(
            event_type=EventType.POSITION_SNAPSHOT,
            data={
                'symbol': symbol,
                'position': position,
                'entry_price': entry_price,
                'current_price': current_price,
                'pnl': pnl,
                **kwargs,
            },
            metadata={'source': 'position_tracker'},
        )
        self.log_event(event)
        return event
    
    def log_recon_incident(self, symbol: str, derived_position: float, exchange_position: float, mismatch: float, **kwargs) -> Event:
        """
        Log reconciliation incident (mismatch detected).
        
        Args:
            symbol: Trading symbol
            derived_position: Position calculated from events
            exchange_position: Position from exchange API
            mismatch: Difference (derived - exchange)
            **kwargs: Additional incident data
        
        Returns:
            Event logged
        """
        event = Event(
            event_type=EventType.RECON_INCIDENT,
            data={
                'symbol': symbol,
                'derived_position': derived_position,
                'exchange_position': exchange_position,
                'mismatch': mismatch,
                'mismatch_pct': abs(mismatch / exchange_position * 100) if exchange_position != 0 else 0,
                **kwargs,
            },
            metadata={'source': 'reconciler', 'severity': 'HIGH'},
        )
        self.log_event(event)
        return event
    
    def log_alert_triggered(self, alert_type: str, message: str, incident_id: Optional[str] = None, **kwargs) -> Event:
        """
        Log alert triggered event.
        
        Args:
            alert_type: Type of alert
            message: Alert message
            incident_id: Related incident ID (if any)
            **kwargs: Additional alert data
        
        Returns:
            Event logged
        """
        event = Event(
            event_type=EventType.ALERT_TRIGGERED,
            data={
                'alert_type': alert_type,
                'message': message,
                'incident_id': incident_id,
                **kwargs,
            },
            metadata={'source': 'alert_router'},
        )
        self.log_event(event)
        return event
    
    def get_events(self, event_type: Optional[EventType] = None, signal_id: Optional[str] = None, limit: int = 100) -> List[Event]:
        """
        Query events with optional filtering.
        
        Args:
            event_type: Filter by event type
            signal_id: Filter by signal ID
            limit: Max events to return
        
        Returns:
            List of matching events (most recent first)
        """
        filtered = self.events
        
        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]
        
        if signal_id:
            filtered = [e for e in filtered if e.signal_id == signal_id]
        
        # Return most recent first
        return list(reversed(filtered[-limit:]))
    
    def get_signal_event_chain(self, signal_id: str) -> List[Event]:
        """
        Get all events for a signal in chronological order.
        
        Useful for: audit trail, debugging signal execution flow.
        
        Args:
            signal_id: Trading signal ID
        
        Returns:
            All events for this signal (oldest first)
        """
        signal_events = [e for e in self.events if e.signal_id == signal_id]
        return signal_events  # Already in order
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event logger statistics."""
        event_counts = {}
        for event_type in EventType:
            count = len([e for e in self.events if e.event_type == event_type])
            if count > 0:
                event_counts[event_type.value] = count
        
        return {
            'total_events': self.event_count,
            'buffered_events': len(self.events),
            'buffer_size': self.buffer_size,
            'event_counts': event_counts,
        }
