#!/bin/bash

DOMAIN="http://localhost:8000"

echo "Checking health endpoint..."
curl -s -o /dev/null -w "%{http_code}" $DOMAIN/health

echo ""
echo "Sending test webhook..."

curl -X POST $DOMAIN/webhook \
     -H "Content-Type: application/json" \
     -d '{"symbol":"BTCUSDT","action":"BUY"}'

echo ""
echo "Checking queue file..."
ls state/

echo "Smoke test completed."