import threading
import time

class AlertRouter:
    def send_alert(self, level, message):
        print(f"\n--- [ALERT {level.upper()}] ---")
        print(f"Message: {message}\n")

class Reconciler:
    def __init__(self, client, internal_state, alert_router, event_logger):
        self.client = client
        self.internal_state = internal_state
        self.alert_router = alert_router
        self.event_logger = event_logger
        self.is_running = False

    def start_monitoring(self, interval=15):
        self.is_running = True
        thread = threading.Thread(target=self._run, args=(interval,), daemon=True)
        thread.start()

    def _run(self, interval):
        while self.is_running:
            self.reconcile()
            time.sleep(interval)

    def reconcile(self):
        try:
            account = self.client.get_account()
            # Get real balance (default to 0.0 if not found)
            balances = {b['asset']: float(b['free']) for b in account['balances'] if float(b['free']) > 0}
            
            # Check BTC as the test case
            exchange_val = balances.get('BTC', 0.0)
            derived_val = self.internal_state.get('BTC', 0.0)

            # 5.1 Log Snapshot
            self.event_logger.log_event("position_snapshot", {
                "exchange": exchange_val,
                "internal": derived_val
            })

            # 5.3 Mismatch detection
            if exchange_val != derived_val:
                msg = f"DRIFT DETECTED! Exchange: {exchange_val}, Internal: {derived_val}"
                self.alert_router.send_alert("critical", msg)
                
        except Exception as e:
            self.alert_router.send_alert("error", f"Reconciler failed: {str(e)}")
