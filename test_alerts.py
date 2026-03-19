import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.alerts.router import AlertRouter


def run_test():
    router = AlertRouter(rate_limit_seconds=10)

    print("--- Starting Requirement 6.3 Test ---")

    print("\n[Test 1] Sending primary alert...")
    router.send("CRITICAL", "SYSTEM_CHECK: Requirement 6.3 testing active.", event_key="system")

    print("\n[Test 2] Sending immediate second alert (same key)...")
    router.send("WARNING", "This should be rate-limited", event_key="system")

    print("\n--- Test Complete ---")
    print("Expected:")
    print("• Telegram → Only 1 message")
    print("• logs/alerts.jsonl → Only 1 message")


if __name__ == "__main__":
    run_test()