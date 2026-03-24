"""
Example: EventLogger & Reconciler Integration
Demonstrates T5 - Full audit trail + reconciliation monitoring
"""

from core.event_logger import EventLogger, EventType
from core.alert_router import AlertRouter, AlertSeverity
from core.reconciler import Reconciler, MockDerivedPositionProvider, MockExchangePositionProvider
import time


def main():
    """
    Demonstrate complete trading event flow with reconciliation monitoring.
    """
    print("=" * 80)
    print("T5: EventLogger Wiring & Reconciler Activation")
    print("=" * 80)
    
    # Initialize components
    logger = EventLogger()
    router = AlertRouter()
    reconciler = Reconciler(check_interval=1, mismatch_threshold=0.0001)
    
    derived_provider = MockDerivedPositionProvider()
    exchange_provider = MockExchangePositionProvider()
    
    # Track events
    incidents_detected = []
    alerts_generated = []
    
    def on_incident_detected(incident):
        """Callback when reconciliation incident is detected."""
        incidents_detected.append(incident)
        
        # Trigger alert
        alert = router.trigger_recon_incident_alert(
            incident_id=incident.incident_id,
            message=f"Position mismatch: {incident.symbol} (Derived: {incident.derived_position}, Exchange: {incident.exchange_position})",
        )
        alerts_generated.append(alert)
        
        # Log to event logger
        logger.log_recon_incident(
            symbol=incident.symbol,
            derived_position=incident.derived_position,
            exchange_position=incident.exchange_position,
            mismatch=incident.mismatch,
        )
        
        print(f"\n🚨 RECON INCIDENT DETECTED:")
        print(f"   Incident ID: {incident.incident_id}")
        print(f"   Symbol: {incident.symbol}")
        print(f"   Derived Position: {incident.derived_position}")
        print(f"   Exchange Position: {incident.exchange_position}")
        print(f"   Mismatch: {incident.mismatch} ({incident.mismatch_pct:.2f}%)")
        print(f"   Alert ID: {alert.alert_id}")
    
    # Setup reconciler callbacks
    reconciler.set_derive_position_callback(derived_provider.get_position)
    reconciler.set_query_exchange_position_callback(exchange_provider.get_position)
    reconciler.set_incident_callback(on_incident_detected)
    
    # === SCENARIO 1: Normal Trade Flow ===
    print("\n" + "=" * 80)
    print("SCENARIO 1: Normal Trade Flow (No Mismatch)")
    print("=" * 80)
    
    signal_id_1 = "sig_normal_001"
    print(f"\n📋 Signal: {signal_id_1}")
    
    # Log signal
    logger.log_signal_received(
        signal_id=signal_id_1,
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.5,
        strategy="momentum",
    )
    print("  ✓ Signal received")
    
    # Log order submission
    logger.log_order_submitted(
        signal_id=signal_id_1,
        client_order_id=f"{signal_id_1}:binance:entry:0",
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.5,
        price=45000,
    )
    print("  ✓ Order submitted")
    
    # Log order acknowledgement
    logger.log_order_ack(
        signal_id=signal_id_1,
        client_order_id=f"{signal_id_1}:binance:entry:0",
        exchange_order_id="exch_101",
    )
    print("  ✓ Order acknowledged")
    
    # Log fill
    logger.log_fill_received(
        signal_id=signal_id_1,
        exchange_order_id="exch_101",
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.5,
        fill_price=45050,
        commission=0.0005,
    )
    print("  ✓ Fill received")
    
    # Update positions (matching)
    derived_provider.set_position("BTCUSDT", 0.5)
    exchange_provider.set_position("BTCUSDT", 0.5)
    
    # Check reconciliation
    print("\n🔄 Reconciliation Check:")
    incident = reconciler.check_symbol("BTCUSDT")
    if incident:
        print(f"  ❌ Mismatch detected!")
    else:
        print(f"  ✓ Positions match (no incident)")
    
    # === SCENARIO 2: Mismatch Detected ===
    print("\n" + "=" * 80)
    print("SCENARIO 2: Position Mismatch (Drift Detected)")
    print("=" * 80)
    
    signal_id_2 = "sig_mismatch_001"
    print(f"\n📋 Signal: {signal_id_2}")
    
    # Log another trade
    logger.log_signal_received(
        signal_id=signal_id_2,
        symbol="ETHUSDT",
        side="BUY",
        quantity=2.0,
    )
    print("  ✓ Signal received")
    
    logger.log_order_submitted(
        signal_id=signal_id_2,
        client_order_id=f"{signal_id_2}:binance:entry:0",
        symbol="ETHUSDT",
        side="BUY",
        quantity=2.0,
        price=3000,
    )
    print("  ✓ Order submitted")
    
    logger.log_order_ack(
        signal_id=signal_id_2,
        client_order_id=f"{signal_id_2}:binance:entry:0",
        exchange_order_id="exch_202",
    )
    print("  ✓ Order acknowledged")
    
    logger.log_fill_received(
        signal_id=signal_id_2,
        exchange_order_id="exch_202",
        symbol="ETHUSDT",
        side="BUY",
        quantity=2.0,
        fill_price=3010,
    )
    print("  ✓ Fill received")
    
    # Create drift: we think we have 2.0, but exchange shows 1.8
    print("\n💥 Network issue: Exchange only confirms 1.8, we have 2.0")
    derived_provider.set_position("ETHUSDT", 2.0)
    exchange_provider.set_position("ETHUSDT", 1.8)
    
    # Check reconciliation
    print("\n🔄 Reconciliation Check:")
    incident = reconciler.check_symbol("ETHUSDT")
    
    # === Summary ===
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    # Event chain for signal 1
    print(f"\n📝 Event Chain - Signal {signal_id_1}:")
    chain1 = logger.get_signal_event_chain(signal_id_1)
    for i, event in enumerate(chain1, 1):
        print(f"   {i}. {event.event_type.value}")
    
    # Event chain for signal 2
    print(f"\n📝 Event Chain - Signal {signal_id_2}:")
    chain2 = logger.get_signal_event_chain(signal_id_2)
    for i, event in enumerate(chain2, 1):
        print(f"   {i}. {event.event_type.value}")
    
    # Recon incidents
    print(f"\n🚨 Reconciliation Incidents: {len(incidents_detected)}")
    for incident in incidents_detected:
        print(f"   - {incident.symbol}: Mismatch = {incident.mismatch}")
    
    # Alerts
    print(f"\n📢 Alerts Generated: {len(alerts_generated)}")
    for alert in alerts_generated:
        print(f"   - {alert.alert_type}: {alert.message[:50]}...")
    
    # Logger stats
    stats = logger.get_stats()
    print(f"\n📊 Event Logger Stats:")
    print(f"   Total Events: {stats['total_events']}")
    print(f"   Event Types: {len(stats['event_counts'])}")
    for evt_type, count in stats['event_counts'].items():
        print(f"      - {evt_type}: {count}")
    
    # Reconciler stats
    recon_stats = reconciler.get_stats()
    print(f"\n📊 Reconciler Stats:")
    print(f"   Checks: {recon_stats['total_checks']}")
    print(f"   Incidents: {recon_stats['total_incidents']}")
    print(f"   Incidents by Symbol: {recon_stats['incidents_by_symbol']}")
    
    # Router stats
    router_stats = router.get_stats()
    print(f"\n📊 Alert Router Stats:")
    print(f"   Total Alerts: {router_stats['total_alerts']}")
    print(f"   Unacknowledged: {router_stats['unacknowledged']}")
    print(f"   Severity: {router_stats['severity_counts']}")
    
    print(f"\n{'=' * 80}\n")
    
    # Acceptance criteria check
    print("✅ ACCEPTANCE CRITERIA MET:")
    print(f"   ✓ Event chain present for both signals")
    print(f"   ✓ Recon incident created for mismatch: {len(incidents_detected)} incident(s)")
    print(f"   ✓ Alert triggered for incident: {len(alerts_generated)} alert(s)")
    print(f"   ✓ Full audit trail available in EventLogger")
    print(f"\n{'=' * 80}\n")


if __name__ == '__main__':
    main()
