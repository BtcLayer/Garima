import logging
import json
import os
from datetime import datetime, timezone

class EventLogger:
    def __init__(self, log_file="logs/audit_trail.log"):
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        self.logger = logging.getLogger("AuditTrail")
        self.logger.setLevel(logging.INFO)
        
        # Clear existing handlers to prevent duplicates
        if not self.logger.handlers:
            handler = logging.FileHandler(log_file)
            self.logger.addHandler(handler)

    def log_event(self, event_type, data):
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            **data
        }
        self.logger.info(json.dumps(event))
        # Also print to console for visibility
        print(f"[LOGGED] {event_type}: {data}")
