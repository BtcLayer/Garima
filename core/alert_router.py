"""
Alert Router Module
Routes reconciliation and other incidents to appropriate alerting channels.

Supported alert types:
- position_mismatch: Derived vs exchange position divergence
- recon_incident: General reconciliation anomaly
- execution_failure: Order execution failed
- critical: Critical system issue
"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, List, Optional
from datetime import datetime, timezone
import uuid


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class Alert:
    """
    Alert record.
    
    Attributes:
        alert_id: Unique alert identifier
        alert_type: Type of alert
        severity: Severity level
        message: Alert message
        incident_id: Related incident ID (if any)
        created_at: Creation timestamp
        acknowledged: Whether alert has been acknowledged
    """
    alert_type: str
    severity: AlertSeverity
    message: str
    incident_id: Optional[str] = None
    alert_id: str = None
    created_at: datetime = None
    acknowledged: bool = False
    
    def __post_init__(self):
        """Initialize defaults."""
        if not self.alert_id:
            self.alert_id = f"alert_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'alert_id': self.alert_id,
            'alert_type': self.alert_type,
            'severity': self.severity.value,
            'message': self.message,
            'incident_id': self.incident_id,
            'created_at': self.created_at.isoformat(),
            'acknowledged': self.acknowledged,
        }
    
    def __repr__(self) -> str:
        return f"Alert({self.alert_type}, {self.severity.value}, {self.alert_id})"


class AlertRouter:
    """
    Routes alerts to handlers/channels.
    
    Can send to:
    - Event logger
    - Email
    - Slack
    - PagerDuty
    - Custom handlers
    """
    
    def __init__(self):
        """Initialize alert router."""
        self.alerts: List[Alert] = []
        self.handlers: List[Callable[[Alert], None]] = []
    
    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        """
        Add an alert handler.
        
        Args:
            handler: Function that receives Alert and handles it
        """
        self.handlers.append(handler)
    
    def trigger_alert(
        self,
        alert_type: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.WARNING,
        incident_id: Optional[str] = None,
    ) -> Alert:
        """
        Trigger an alert.
        
        Calls all registered handlers with the alert.
        
        Args:
            alert_type: Type of alert
            message: Alert message
            severity: Alert severity
            incident_id: Related incident ID
        
        Returns:
            Alert created and dispatched
        """
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            incident_id=incident_id,
        )
        
        # Store alert
        self.alerts.append(alert)
        
        # Dispatch to all handlers
        for handler in self.handlers:
            try:
                handler(alert)
            except Exception as e:
                print(f"Error in alert handler: {e}")
        
        return alert
    
    def trigger_position_mismatch_alert(
        self,
        symbol: str,
        derived_position: float,
        exchange_position: float,
        mismatch: float,
    ) -> Alert:
        """
        Trigger a position mismatch alert.
        
        Args:
            symbol: Trading symbol
            derived_position: Position from events
            exchange_position: Position from exchange
            mismatch: Difference
        
        Returns:
            Alert created
        """
        message = (
            f"Position mismatch detected for {symbol}: "
            f"Derived={derived_position}, Exchange={exchange_position}, "
            f"Diff={mismatch}"
        )
        return self.trigger_alert(
            alert_type="position_mismatch",
            message=message,
            severity=AlertSeverity.CRITICAL,
        )
    
    def trigger_recon_incident_alert(self, incident_id: str, message: str) -> Alert:
        """
        Trigger a reconciliation incident alert.
        
        Args:
            incident_id: Incident ID
            message: Incident message
        
        Returns:
            Alert created
        """
        return self.trigger_alert(
            alert_type="recon_incident",
            message=message,
            severity=AlertSeverity.CRITICAL,
            incident_id=incident_id,
        )
    
    def get_alerts(self, alert_type: Optional[str] = None, limit: int = 100) -> List[Alert]:
        """
        Get alerts with optional filtering.
        
        Args:
            alert_type: Filter by alert type
            limit: Max alerts to return
        
        Returns:
            List of alerts (most recent first)
        """
        filtered = self.alerts
        
        if alert_type:
            filtered = [a for a in filtered if a.alert_type == alert_type]
        
        return list(reversed(filtered[-limit:]))
    
    def acknowledge_alert(self, alert_id: str) -> Optional[Alert]:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: Alert ID to acknowledge
        
        Returns:
            Updated alert if found, else None
        """
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return alert
        return None
    
    def get_stats(self) -> dict:
        """Get alert statistics."""
        total = len(self.alerts)
        unacknowledged = len([a for a in self.alerts if not a.acknowledged])
        
        severity_counts = {}
        for alert in self.alerts:
            severity = alert.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            'total_alerts': total,
            'unacknowledged': unacknowledged,
            'severity_counts': severity_counts,
        }
