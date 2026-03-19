# INCIDENT RUNBOOK

## 1. Webhook Not Receiving Alerts
1. Check webhook server process is running.
2. Verify port is open and accessible.
3. Inspect logs/audit_trail.log.
4. Test using curl POST request.
5. Restart service if required.

---

## 2. Binance Order Not Executed
1. Check API key validity.
2. Confirm sufficient balance.
3. Inspect order response logs.
4. Validate symbol precision.
5. Retry manually via CLI.

---

## 3. Duplicate Orders Triggered
1. Check deterministic order ID logic.
2. Inspect get_id.py.
3. Confirm no retry loop bug.
4. Validate network timeout handling.
5. Monitor logs for repeated IDs.

---

## 4. Alerts Not Sent to Telegram
1. Confirm TELEGRAM_BOT_TOKEN in .env.
2. Confirm TELEGRAM_CHAT_ID in .env.
3. Check internet connectivity.
4. Inspect logs/alerts.jsonl.
5. Verify rate limit not blocking.

---

## 5. Bot Crashes Unexpectedly
1. Check stack trace in logs.
2. Validate environment variables.
3. Ensure dependencies installed.
4. Run test suite (pytest).
5. Restart service and monitor.