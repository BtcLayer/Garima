"""
Reconciler Module
Monitors derived positions vs exchange positions with 15s interval.

Algorithm:
1. Every 15s, calculate derived position from order/fill events
2. Query exchange for current position
3. Compare: if mismatch > threshold, trigger incident & alert
4. Log reconciliation event to EventLogger
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Callable
from datetime import datetime, timezone
import threading
import time
import uuid


@dataclass
class Position:
    """Position snapshot."""
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    pnl: float


@dataclass
class ReconIncident:
    """Reconciliation incident record."""
    incident_id: str = field(default_factory=lambda: f"recon_{uuid.uuid4().hex[:8]}")
    symbol: str = ""
    derived_position: float = 0.0
    exchange_position: float = 0.0
    mismatch: float = 0.0
    mismatch_pct: float = 0.0
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'incident_id': self.incident_id,
            'symbol': self.symbol,
            'derived_position': self.derived_position,
            'exchange_position': self.exchange_position,
            'mismatch': self.mismatch,
            'mismatch_pct': self.mismatch_pct,
            'detected_at': self.detected_at.isoformat(),
        }


class Reconciler:
    """
    Reconciler monitors derived vs exchange positions.
    
    Runs on 15s interval:
    1. Derive position from fills
    2. Query exchange API
    3. Compare
    4. Log incident + trigger alert on mismatch
    """
    
    def __init__(
        self,
        check_interval: int = 15,
        mismatch_threshold: float = 0.0001,
    ):
        """
        Initialize reconciler.
        
        Args:
            check_interval: Check interval in seconds (default 15s)
            mismatch_threshold: Minimum mismatch to trigger incident (in quantity)
        """
        self.check_interval = check_interval
        self.mismatch_threshold = mismatch_threshold
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # Callbacks
        self.derive_position_fn: Optional[Callable[[str], float]] = None
        self.query_exchange_position_fn: Optional[Callable[[str], float]] = None
        self.on_incident_fn: Optional[Callable[[ReconIncident], None]] = None
        
        # State
        self.positions: Dict[str, Position] = {}
        self.incidents: list[ReconIncident] = []
        self.last_check: Dict[str, datetime] = {}
        self.check_count = 0
    
    def set_derive_position_callback(self, fn: Callable[[str], float]) -> None:
        """
        Set callback to derive position from events.
        
        Args:
            fn: Function(symbol) -> float (position quantity)
        """
        self.derive_position_fn = fn
    
    def set_query_exchange_position_callback(self, fn: Callable[[str], float]) -> None:
        """
        Set callback to query exchange for position.
        
        Args:
            fn: Function(symbol) -> float (position quantity)
        """
        self.query_exchange_position_fn = fn
    
    def set_incident_callback(self, fn: Callable[[ReconIncident], None]) -> None:
        """
        Set callback for incidents.
        
        Args:
            fn: Function(incident) -> None
        """
        self.on_incident_fn = fn
    
    def check_symbol(self, symbol: str) -> Optional[ReconIncident]:
        """
        Check position reconciliation for a symbol.
        
        Args:
            symbol: Trading symbol to check
        
        Returns:
            ReconIncident if mismatch detected, else None
        """
        if not self.derive_position_fn or not self.query_exchange_position_fn:
            return None
        
        # Get positions
        try:
            derived = self.derive_position_fn(symbol)
            exchange = self.query_exchange_position_fn(symbol)
        except Exception as e:
            print(f"Error checking {symbol}: {e}")
            return None
        
        # Compare
        mismatch = abs(derived - exchange)
        
        if mismatch > self.mismatch_threshold:
            # Incident detected
            mismatch_pct = abs(mismatch / exchange * 100) if exchange != 0 else 0
            incident = ReconIncident(
                symbol=symbol,
                derived_position=derived,
                exchange_position=exchange,
                mismatch=mismatch,
                mismatch_pct=mismatch_pct,
            )
            
            self.incidents.append(incident)
            
            # Trigger callback
            if self.on_incident_fn:
                self.on_incident_fn(incident)
            
            return incident
        
        return None
    
    def check_all_symbols(self, symbols: list[str]) -> list[ReconIncident]:
        """
        Check all symbols for mismatches.
        
        Args:
            symbols: List of symbols to check
        
        Returns:
            List of incidents detected
        """
        incidents = []
        for symbol in symbols:
            incident = self.check_symbol(symbol)
            if incident:
                incidents.append(incident)
        
        return incidents
    
    def _monitor_loop(self, symbols: list[str]) -> None:
        """
        Monitor loop (runs in background thread).
        
        Args:
            symbols: Symbols to monitor
        """
        while self.running:
            try:
                # Check all symbols
                self.check_all_symbols(symbols)
                self.check_count += 1
                
                # Sleep for interval
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"Error in reconciler loop: {e}")
                time.sleep(1)  # Prevent tight loop on error
    
    def start(self, symbols: list[str]) -> None:
        """
        Start background reconciliation monitor.
        
        Args:
            symbols: List of symbols to monitor
        """
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(
            target=self._monitor_loop,
            args=(symbols,),
            daemon=True,
        )
        self.thread.start()
    
    def stop(self) -> None:
        """Stop background monitor."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
            self.thread = None
    
    def get_incidents(self, symbol: Optional[str] = None) -> list[ReconIncident]:
        """
        Get incidents.
        
        Args:
            symbol: Filter by symbol (optional)
        
        Returns:
            List of incidents
        """
        if symbol:
            return [i for i in self.incidents if i.symbol == symbol]
        return self.incidents
    
    def get_stats(self) -> dict:
        """Get reconciler statistics."""
        incident_counts = {}
        for incident in self.incidents:
            symbol = incident.symbol
            incident_counts[symbol] = incident_counts.get(symbol, 0) + 1
        
        return {
            'running': self.running,
            'check_interval': self.check_interval,
            'total_checks': self.check_count,
            'total_incidents': len(self.incidents),
            'incidents_by_symbol': incident_counts,
        }


class MockExchangePositionProvider:
    """Mock exchange position provider for testing."""
    
    def __init__(self):
        """Initialize mock provider."""
        self.positions: Dict[str, float] = {}
    
    def set_position(self, symbol: str, quantity: float) -> None:
        """Set exchange position."""
        self.positions[symbol] = quantity
    
    def get_position(self, symbol: str) -> float:
        """Get exchange position."""
        return self.positions.get(symbol, 0.0)


class MockDerivedPositionProvider:
    """Mock derived position provider for testing."""
    
    def __init__(self):
        """Initialize mock provider."""
        self.positions: Dict[str, float] = {}
    
    def set_position(self, symbol: str, quantity: float) -> None:
        """Set derived position."""
        self.positions[symbol] = quantity
    
    def get_position(self, symbol: str) -> float:
        """Get derived position."""
        return self.positions.get(symbol, 0.0)
