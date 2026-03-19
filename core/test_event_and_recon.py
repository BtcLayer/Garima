"""
Unit tests for EventLogger, AlertRouter, and Reconciler.

Acceptance Criteria (5.3):
- Event chain present for sample trade
- Recon incident + alert created in simulated mismatch
- All events logged and queryable
"""

import unittest
import time
from core.event_logger import EventLogger, EventType
from core.alert_router import AlertRouter, AlertSeverity
from core.reconciler import Reconciler, MockExchangePositionProvider, MockDerivedPositionProvider


class TestEventLogger(unittest.TestCase):
    """Test event logger functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.logger = EventLogger()
    
    def test_log_signal_received(self):
        """Test logging signal received event."""
        event = self.logger.log_signal_received(
            signal_id="sig_123",
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.001,
            threshold=100,
        )
        
        self.assertEqual(event.event_type, EventType.SIGNAL_RECEIVED)
        self.assertEqual(event.signal_id, "sig_123")
        self.assertEqual(event.data['symbol'], "BTCUSDT")
        self.assertEqual(event.data['side'], "BUY")
    
    def test_log_order_submitted(self):
        """Test logging order submitted event."""
        event = self.logger.log_order_submitted(
            signal_id="sig_123",
            client_order_id="sig_123:binance:entry:0",
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.001,
            price=45000,
        )
        
        self.assertEqual(event.event_type, EventType.ORDER_SUBMITTED)
        self.assertEqual(event.data['client_order_id'], "sig_123:binance:entry:0")
        self.assertEqual(event.data['price'], 45000)
    
    def test_log_order_ack(self):
        """Test logging order acknowledged event."""
        event = self.logger.log_order_ack(
            signal_id="sig_123",
            client_order_id="sig_123:binance:entry:0",
            exchange_order_id="exch_999",
        )
        
        self.assertEqual(event.event_type, EventType.ORDER_ACK)
        self.assertEqual(event.data['exchange_order_id'], "exch_999")
    
    def test_log_fill_received(self):
        """Test logging fill event."""
        event = self.logger.log_fill_received(
            signal_id="sig_123",
            exchange_order_id="exch_999",
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.001,
            fill_price=45100,
            commission=0.00001,
        )
        
        self.assertEqual(event.event_type, EventType.FILL_RECEIVED)
        self.assertEqual(event.data['fill_price'], 45100)
        self.assertEqual(event.data['commission'], 0.00001)
    
    def test_log_position_snapshot(self):
        """Test logging position snapshot."""
        event = self.logger.log_position_snapshot(
            symbol="BTCUSDT",
            position=0.001,
            entry_price=45000,
            current_price=45500,
            pnl=0.5,
        )
        
        self.assertEqual(event.event_type, EventType.POSITION_SNAPSHOT)
        self.assertEqual(event.data['position'], 0.001)
        self.assertEqual(event.data['pnl'], 0.5)
    
    def test_get_signal_event_chain(self):
        """
        ACCEPTANCE TEST: Event chain present for sample trade.
        
        Scenario: Complete trade lifecycle for one signal.
        Expected: All events for signal in order.
        """
        signal_id = "sig_trade_001"
        
        # 1. Signal received
        self.logger.log_signal_received(
            signal_id=signal_id,
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.001,
        )
        
        # 2. Order submitted
        self.logger.log_order_submitted(
            signal_id=signal_id,
            client_order_id="sig_trade_001:binance:entry:0",
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.001,
            price=45000,
        )
        
        # 3. Order acknowledged
        self.logger.log_order_ack(
            signal_id=signal_id,
            client_order_id="sig_trade_001:binance:entry:0",
            exchange_order_id="exch_123",
        )
        
        # 4. Fill received
        self.logger.log_fill_received(
            signal_id=signal_id,
            exchange_order_id="exch_123",
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.001,
            fill_price=45050,
        )
        
        # 5. Position snapshot
        self.logger.log_position_snapshot(
            symbol="BTCUSDT",
            position=0.001,
            entry_price=45050,
            current_price=45500,
            pnl=0.45,
        )
        
        # Get event chain
        chain = self.logger.get_signal_event_chain(signal_id)
        
        # Acceptance: Event chain present
        self.assertEqual(len(chain), 4, "Should have signal_received, order_submitted, order_ack, fill_received")
        
        # Verify order
        self.assertEqual(chain[0].event_type, EventType.SIGNAL_RECEIVED)
        self.assertEqual(chain[1].event_type, EventType.ORDER_SUBMITTED)
        self.assertEqual(chain[2].event_type, EventType.ORDER_ACK)
        self.assertEqual(chain[3].event_type, EventType.FILL_RECEIVED)
    
    def test_query_events_by_type(self):
        """Test querying events by type."""
        self.logger.log_signal_received("sig_1", "BTCUSDT", "BUY", 0.001)
        self.logger.log_signal_received("sig_2", "ETHUSDT", "SELL", 1.0)
        self.logger.log_order_submitted("sig_1", "client_1", "BTCUSDT", "BUY", 0.001)
        
        # Query signal_received events
        signals = self.logger.get_events(EventType.SIGNAL_RECEIVED)
        self.assertEqual(len(signals), 2)
        
        # Query order_submitted events
        orders = self.logger.get_events(EventType.ORDER_SUBMITTED)
        self.assertEqual(len(orders), 1)
    
    def test_event_logger_stats(self):
        """Test event logger statistics."""
        self.logger.log_signal_received("sig_1", "BTCUSDT", "BUY", 0.001)
        self.logger.log_order_submitted("sig_1", "client_1", "BTCUSDT", "BUY", 0.001)
        self.logger.log_order_ack("sig_1", "client_1", "exch_1")
        
        stats = self.logger.get_stats()
        
        self.assertEqual(stats['total_events'], 3)
        self.assertEqual(stats['buffered_events'], 3)
        self.assertEqual(len(stats['event_counts']), 3)


class TestAlertRouter(unittest.TestCase):
    """Test alert router functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.router = AlertRouter()
        self.received_alerts = []
    
    def test_trigger_alert(self):
        """Test triggering an alert."""
        alert = self.router.trigger_alert(
            alert_type="test_alert",
            message="Test message",
            severity=AlertSeverity.WARNING,
        )
        
        self.assertIsNotNone(alert.alert_id)
        self.assertEqual(alert.alert_type, "test_alert")
        self.assertEqual(alert.severity, AlertSeverity.WARNING)
        self.assertFalse(alert.acknowledged)
    
    def test_alert_handler_called(self):
        """Test that alert handlers are called."""
        def handler(alert):
            self.received_alerts.append(alert)
        
        self.router.add_handler(handler)
        
        alert = self.router.trigger_alert(
            alert_type="test_alert",
            message="Test message",
        )
        
        self.assertEqual(len(self.received_alerts), 1)
        self.assertEqual(self.received_alerts[0].alert_id, alert.alert_id)
    
    def test_trigger_position_mismatch_alert(self):
        """Test position mismatch alert."""
        alert = self.router.trigger_position_mismatch_alert(
            symbol="BTCUSDT",
            derived_position=1.0,
            exchange_position=0.8,
            mismatch=0.2,
        )
        
        self.assertEqual(alert.alert_type, "position_mismatch")
        self.assertEqual(alert.severity, AlertSeverity.CRITICAL)
        self.assertIn("BTCUSDT", alert.message)
    
    def test_acknowledge_alert(self):
        """Test acknowledging an alert."""
        alert = self.router.trigger_alert(
            alert_type="test_alert",
            message="Test message",
        )
        
        self.assertFalse(alert.acknowledged)
        
        # Acknowledge
        acknowledged = self.router.acknowledge_alert(alert.alert_id)
        
        self.assertTrue(acknowledged.acknowledged)
    
    def test_alert_router_stats(self):
        """Test alert router statistics."""
        self.router.trigger_alert("alert_1", "Message 1", AlertSeverity.INFO)
        self.router.trigger_alert("alert_2", "Message 2", AlertSeverity.CRITICAL)
        self.router.trigger_alert("alert_3", "Message 3", AlertSeverity.CRITICAL)
        
        stats = self.router.get_stats()
        
        self.assertEqual(stats['total_alerts'], 3)
        self.assertEqual(stats['unacknowledged'], 3)
        self.assertEqual(stats['severity_counts']['CRITICAL'], 2)
        self.assertEqual(stats['severity_counts']['INFO'], 1)


class TestReconciler(unittest.TestCase):
    """Test reconciliation monitoring."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.reconciler = Reconciler(check_interval=1, mismatch_threshold=0.0001)
        self.derived_provider = MockDerivedPositionProvider()
        self.exchange_provider = MockExchangePositionProvider()
        self.incidents_detected = []
    
    def test_no_mismatch_when_positions_match(self):
        """Test no incident when positions match."""
        self.derived_provider.set_position("BTCUSDT", 1.0)
        self.exchange_provider.set_position("BTCUSDT", 1.0)
        
        self.reconciler.set_derive_position_callback(self.derived_provider.get_position)
        self.reconciler.set_query_exchange_position_callback(self.exchange_provider.get_position)
        
        incident = self.reconciler.check_symbol("BTCUSDT")
        
        self.assertIsNone(incident)
    
    def test_incident_created_on_mismatch(self):
        """
        ACCEPTANCE TEST: Recon incident created in simulated mismatch.
        
        Scenario: Derived position != exchange position
        Expected: Incident created with details
        """
        self.derived_provider.set_position("BTCUSDT", 1.0)
        self.exchange_provider.set_position("BTCUSDT", 0.8)  # Mismatch!
        
        self.reconciler.set_derive_position_callback(self.derived_provider.get_position)
        self.reconciler.set_query_exchange_position_callback(self.exchange_provider.get_position)
        
        incident = self.reconciler.check_symbol("BTCUSDT")
        
        # Acceptance: Incident created
        self.assertIsNotNone(incident)
        self.assertEqual(incident.symbol, "BTCUSDT")
        self.assertEqual(incident.derived_position, 1.0)
        self.assertEqual(incident.exchange_position, 0.8)
        self.assertAlmostEqual(incident.mismatch, 0.2, places=5)
    """
    ACCEPTANCE TEST: Full integration
    - Event chain for sample trade
    - Recon incident + alert created on mismatch
    """
    
    def test_complete_trade_with_recon_and_alert(self):
        """
        Complete scenario: Signal → Order → Fill → Recon detected mismatch → Alert.
        """
        logger = EventLogger()
        router = AlertRouter()
        reconciler = Reconciler(check_interval=1, mismatch_threshold=0.0001)
        
        derived_provider = MockDerivedPositionProvider()
        exchange_provider = MockExchangePositionProvider()
        
        # Track alerts from incidents
        alerts_from_incidents = []
        
        def incident_callback(incident):
            """When incident detected, trigger alert."""
            alert = router.trigger_recon_incident_alert(
                incident_id=incident.incident_id,
                message=f"Position mismatch: {incident.symbol}",
            )
            alerts_from_incidents.append(alert)
            
            # Log incident in event logger
            logger.log_recon_incident(
                symbol=incident.symbol,
                derived_position=incident.derived_position,
                exchange_position=incident.exchange_position,
                mismatch=incident.mismatch,
            )
        
        # Setup reconciler
        reconciler.set_derive_position_callback(derived_provider.get_position)
        reconciler.set_query_exchange_position_callback(exchange_provider.get_position)
        reconciler.set_incident_callback(incident_callback)
        
        # --- Scenario: Complete trade flow ---
        signal_id = "sig_integration_001"
        
        # 1. Signal received
        logger.log_signal_received(
            signal_id=signal_id,
            symbol="BTCUSDT",
            side="BUY",
            quantity=1.0,
        )
        
        # 2. Order submitted
        logger.log_order_submitted(
            signal_id=signal_id,
            client_order_id="sig_integration_001:binance:entry:0",
            symbol="BTCUSDT",
            side="BUY",
            quantity=1.0,
            price=45000,
        )
        
        # 3. Order acknowledged
        logger.log_order_ack(
            signal_id=signal_id,
            client_order_id="sig_integration_001:binance:entry:0",
            exchange_order_id="exch_777",
        )
        
        # 4. Fill received - we filled 1.0
        logger.log_fill_received(
            signal_id=signal_id,
            exchange_order_id="exch_777",
            symbol="BTCUSDT",
            side="BUY",
            quantity=1.0,
            fill_price=45050,
        )
        
        # Update derived position (from fills)
        derived_provider.set_position("BTCUSDT", 1.0)
        
        # 5. We think we have 1.0, but exchange has 0.9 (drift!)
        exchange_provider.set_position("BTCUSDT", 0.9)
        
        # 6. Reconciler detects mismatch
        incident = reconciler.check_symbol("BTCUSDT")
        
        # --- ACCEPTANCE CHECKS ---
        
        # 1. Event chain present
        chain = logger.get_signal_event_chain(signal_id)
        self.assertEqual(len(chain), 4)
        self.assertEqual(chain[0].event_type, EventType.SIGNAL_RECEIVED)
        self.assertEqual(chain[1].event_type, EventType.ORDER_SUBMITTED)
        self.assertEqual(chain[2].event_type, EventType.ORDER_ACK)
        self.assertEqual(chain[3].event_type, EventType.FILL_RECEIVED)
        
        # 2. Recon incident created
        self.assertIsNotNone(incident)
        self.assertEqual(incident.symbol, "BTCUSDT")
        self.assertEqual(incident.derived_position, 1.0)
        self.assertEqual(incident.exchange_position, 0.9)
        self.assertAlmostEqual(incident.mismatch, 0.1, places=5)
        
        # 3. Alert triggered
        self.assertEqual(len(alerts_from_incidents), 1)
        alert = alerts_from_incidents[0]
        self.assertEqual(alert.alert_type, "recon_incident")
        self.assertEqual(alert.severity, AlertSeverity.CRITICAL)
        
        # 4. Incident logged in EventLogger
        recon_events = logger.get_events(EventType.RECON_INCIDENT)
        self.assertEqual(len(recon_events), 1)
        
        # All conditions met
        print("\n✅ ACCEPTANCE TEST PASSED:")
        print(f"  - Event chain: {len(chain)} events logged")
        print(f"  - Recon incident: {incident.incident_id} detected")
        print(f"  - Alert: {alert.alert_id} triggered")
        print(f"  - Full audit trail available")


if __name__ == '__main__':
    unittest.main()
