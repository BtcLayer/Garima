# Trading Bot - Binance API Setup

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Get Binance API Keys
1. Go to [Binance.com](https://www.binance.com)
2. Create an account or login
3. Go to **Settings** → **Account** → **API Management**
4. Create a new key with the following permissions:
   - **Read** access for querying data
   - **Trade** access if you want to place orders
   - **Restricted IP** (recommended for security)

### 3. Configure Environment Variables
1. Copy `.env.example` to `.env`:
   ```bash
   copy .env.example .env
   ```
2. Open `.env` and add your API credentials:
   ```
   BINANCE_API_KEY=your_actual_api_key_here
   BINANCE_API_SECRET=your_actual_api_secret_here
   BINANCE_TESTNET=False
   ```

### 4. Test Connection
```bash
python binance_client.py
```

You should see:
```
✓ Successfully connected to Binance
✓ Account connected: X assets
✓ USDT Balance: 1234.56
```

## Files Overview

- **binance_client.py** - Main Binance API client class with common functions
- **example_usage.py** - Example showing how to use the client
- **.env.example** - Template for environment variables
- **.env** - Your actual credentials (create from .env.example, never commit)
- **storage/jsonl_queue.py** - Thread-safe JSONL storage for orders/trades
- **core/order_manager.py** - Order creation with deterministic `client_order_id`
- **core/executor.py** - Idempotent order executor (prevents duplicate exchange orders)
- **core/event_logger.py** - Centralized audit trail for all trading events
- **core/alert_router.py** - Alert routing for incidents
- **core/reconciler.py** - 15s interval position reconciliation monitor

## Storage: JSONL Queue

Thread-safe JSON Lines storage with file locking for reliable data persistence.

### append_jsonl Usage

Append records atomically with exclusive file locking (uses `fcntl.flock` on Unix/Linux/macOS, threading locks on Windows):

```python
from storage.jsonl_queue import append_jsonl, read_jsonl

# Append an order record
append_jsonl('orders.jsonl', {
    'order_id': '12345',
    'symbol': 'BTCUSDT',
    'side': 'BUY',
    'quantity': 0.001,
    'price': 50000,
    'timestamp': 1645123456
})

# Append from multiple threads safely - file locking ensures atomicity
# Verified: 100 concurrent threads produce 100 parseable JSON lines
```

### read_jsonl Usage

Read all records safely:

```python
records = read_jsonl('orders.jsonl')
for record in records:
    print(f"Order {record['order_id']}: {record['quantity']} {record['symbol']}")
```

### Features

- ✅ **Thread-safe**: File locking (`fcntl.flock` or threading.Lock)
- ✅ **Atomic writes**: Each `append_jsonl` call is atomic with `fsync()`
- ✅ **Cross-platform**: Works on Windows, Linux, macOS
- ✅ **Verified**: Unit test with 100 concurrent threads (all 100 records written successfully)

### Run Tests

```bash
python -m pytest storage/test_jsonl_queue.py -v
```

## Order Execution: Idempotent Executor

Prevents duplicate exchange orders on retries with deterministic `client_order_id` and idempotent execution.

### How It Works

**Deterministic `client_order_id`:**
```
Format: "{signal_id}:{venue}:{leg}:{attempt}"
Example: "sig_123:binance:entry:0" → retry becomes "sig_123:binance:entry:1"
```

**Idempotency Algorithm:**
1. Check if `client_order_id` already acknowledged from exchange
2. If yes → return cached `exchange_order_id` (skip re-submission) ✅ **Prevents duplicates**
3. If no → submit to exchange and cache the result

### Example Usage

```python
from core.order_manager import OrderManager, OrderSide
from core.executor import IdempotentExecutor
from binance_client import BinanceClient

manager = OrderManager()
executor = IdempotentExecutor(binance_adapter)

# Create order with deterministic client_order_id
order = manager.create_order(
    signal_id="sig_123",
    venue="binance",
    leg="entry",
    symbol="BTCUSDT",
    side=OrderSide.BUY,
    quantity=0.001,
    price=50000,
)

print(order.client_order_id)  # "sig_123:binance:entry:0"

# Attempt 1: Submit to exchange
result = executor.execute(order)  # Submits, gets exch_id_1

# Attempt 2: Retry (network timeout)
result = executor.execute(order)  # Returns cached exch_id_1 (no duplicate!)

# Attempt 3: Retry again
result = executor.execute(order)  # Returns cached exch_id_1 (still no duplicate!)
```

### Features

- ✅ **Retry-safe**: Same order submitted multiple times = 1 exchange order
- ✅ **Deterministic**: Same inputs always produce same `client_order_id`
- ✅ **Cached**: Idempotent lookup prevents redundant exchange calls
- ✅ **Verified**: Acceptance test confirms single exchange order with repeated retries

### Retry Scenario Test

```bash
python -m pytest core/test_executor.py::TestExecutorIdempotency::test_retry_scenario_network_failure -v
```

**Result:** Network failure + retry + retry again = Only 2 exchange submissions (fail + success), not 3  
✅ **Acceptance:** Zero duplicate orders

## Event Logger & Reconciler

Complete audit trail and automated drift detection for all trading events.

### EventLogger: Full Audit Trail

Logs all trading events across the system in chronological order:

**Event Types:**
- `signal_received` - Trading signal from webhook/strategy
- `order_submitted` - Order sent to exchange
- `order_ack` - Exchange acknowledgment received
- `fill_received` - Trade execution
- `position_snapshot` - Current position state
- `recon_incident` - Position mismatch detected
- `alert_triggered` - Alert generated

### Example: Complete Signal Event Chain

```python
from core.event_logger import EventLogger, EventType

logger = EventLogger()

# Log events as they occur during signal execution
logger.log_signal_received(signal_id="sig_001", symbol="BTCUSDT", side="BUY", quantity=0.001)
logger.log_order_submitted(signal_id="sig_001", client_order_id="sig_001:binance:entry:0", 
                          symbol="BTCUSDT", side="BUY", quantity=0.001, price=45000)
logger.log_order_ack(signal_id="sig_001", client_order_id="sig_001:binance:entry:0", 
                    exchange_order_id="exch_123")
logger.log_fill_received(signal_id="sig_001", exchange_order_id="exch_123", 
                        symbol="BTCUSDT", side="BUY", quantity=0.001, fill_price=45050)

# Get complete event chain for signal (for debugging/audit)
chain = logger.get_signal_event_chain("sig_001")
for event in chain:
    print(f"{event.timestamp}: {event.event_type.value}")
    # Results in: 4 events - signal_received → order_submitted → order_ack → fill_received
```

### Reconciler: 15s Interval Position Monitoring

Automatically detects position mismatches between derived (from fills) and exchange positions.

**What It Does:**
1. Every 15 seconds: calculates derived position from fill events
2. Queries exchange for current position via API
3. Compares: if mismatch > threshold → creates incident
4. Triggers alert and logs incident to EventLogger

### Example: Position Mismatch Detection

```python
from core.reconciler import Reconciler
from core.alert_router import AlertRouter
from core.event_logger import EventLogger

logger = EventLogger()
router = AlertRouter()
reconciler = Reconciler(check_interval=15, mismatch_threshold=0.0001)

# Setup callbacks
derived_position = lambda symbol: 1.0  # Calculate from fills
exchange_position = lambda symbol: 0.9  # Query exchange API

def on_mismatch(incident):
    """Handle mismatch incident."""
    alert = router.trigger_recon_incident_alert(
        incident_id=incident.incident_id,
        message=f"Position drift for {incident.symbol}: {incident.mismatch} units"
    )
    logger.log_recon_incident(
        symbol=incident.symbol,
        derived_position=incident.derived_position,
        exchange_position=incident.exchange_position,
        mismatch=incident.mismatch,
    )

reconciler.set_derive_position_callback(derived_position)
reconciler.set_query_exchange_position_callback(exchange_position)
reconciler.set_incident_callback(on_mismatch)

# Start monitoring in background (15s intervals)
reconciler.start(symbols=["BTCUSDT", "ETHUSDT"])

# Mismatch detected automatically → incident created → alert triggered
```

### Features

- ✅ **Complete Audit Trail**: Every event logged with timestamp and metadata
- ✅ **Signal Chain Query**: Get all events for a signal for debugging
- ✅ **Continuous Monitoring**: 15s interval reconciliation checks
- ✅ **Automated Alerts**: Critical alerts on position mismatch
- ✅ **Verified**: Acceptance test confirms event chain + incident + alert

### Run Tests

```bash
python -m pytest core/test_event_and_recon.py -v
```

### Run Example

```bash
python example_event_and_recon.py
```

Output shows:
- Event chains for multiple signals
- Recon incidents detected
- Alerts generated
- Full statistics

## Common Operations

### Get Account Balance
```python
from binance_client import BinanceClient
client = BinanceClient()
balance = client.get_balance('USDT')
print(f"USDT: {balance['free']}")
```

### Get Market Price
```python
ticker = client.client.get_symbol_ticker(symbol='BTCUSDT')
print(f"BTC Price: ${ticker['price']}")
```

### Place an Order
```python
order = client.place_order('BTCUSDT', 'BUY', 'LIMIT', quantity=0.001, price=50000)
```

## Security Best Practices

⚠️ **Important:**
- Never commit `.env` file to git
- Use API keys with minimal required permissions
- Enable IP whitelist
- Use testnet for development

## Troubleshooting

- **Invalid API Key**: Check your `.env` file has correct keys
- **Permission Denied**: Ensure your API key has required permissions
- **Orders failing**: Use testnet first to test without real money

## Next Steps

1. Test with the example script
2. Build your trading strategy
3. Use the BinanceClient class in your bot
