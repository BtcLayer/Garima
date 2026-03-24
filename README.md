# Garima — Crypto Strategy Backtester & Telegram Bot

Systematic backtesting engine for 230+ trading strategies across 10 crypto assets and 3 timeframes, with a Telegram bot interface for running optimizations, generating TradingView Pine Scripts, and managing results.

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/BtcLayer/Garima.git
cd Garima

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/Mac
# .venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cp .env.example .env             # then edit with your keys
```

Create `.env` with:
```
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
GEMINI_API_KEY=your_gemini_key
```

```bash
# 5. Download 6-year historical data (~80MB)
python scripts/fetch_6yr_data.py

# 6. Run the bot locally
python -m src.telegram_backtest_bot
```

## Server Deployment (24/7)

```bash
# Copy files to server
scp -i "deploy/harsh_server/key.pem" -r src/ strategies/ run_strategies_batch.py requirements.txt ubuntu@server:/home/ubuntu/Garima/

# Copy data files
scp -i "deploy/harsh_server/key.pem" storage/historical_data/*.parquet ubuntu@server:/home/ubuntu/Garima/storage/historical_data/

# SSH into server and start
ssh -i "deploy/harsh_server/key.pem" ubuntu@server
cd /home/ubuntu/Garima
sudo systemctl start telegram_bot
sudo systemctl status telegram_bot   # verify it's running
```

## Bot Commands (Workflow Order)

```
Step 1 — Discover
  /backtest [symbol_tf]     Run all strategies on an asset
  /test [name] [symbol_tf]  Test a single strategy

Step 2 — Filter & Optimize
  /elite                    Filter to top performers
  /optimize                 Tune SL/TP/TS params

Step 3 — Confirm
  /validate                 Re-run with saved params

All-in-One
  /auto [tf]                Backtest + Elite + Optimize + Validate

Analysis
  /results                  Last run summary with Gross DD / Net DD
  /analyze                  AI analysis via Gemini
  /pinescript [name]        Generate TradingView Pine Script

Settings
  /set symbol ETHUSDT_4h    Change default symbol
  /set batches 1-5          Change strategy batches
  /status                   Current bot state
  /help                     Full command guide
```

## Project Structure

```
src/
  telegram_backtest_bot.py  Main Telegram bot (commands, workers, messaging)
  brain.py                  Gemini AI integration for /analyze
  manager.py                Binance trade execution
  data_fetcher.py           Historical data downloader (Binance API)
  binance_client.py         Binance API wrapper

strategies/
  batch_01.py ... batch_20.py   230+ strategy definitions
  __init__.py                   Strategy loader (get_all_strategies, get_by_batch)

scripts/
  fetch_6yr_data.py         Download 6-year historical data (paginated)
  generate_pine.py          Generate TradingView Pine Scripts
  asset_status.py           Track which assets/timeframes are done

run_strategies_batch.py     Core backtesting engine

storage/
  historical_data/          Parquet files (gitignored, ~80MB)
  elite_ranking.json        Optimized strategy params (single source of truth)

deploy/
  systemd/trading_bot.service   Systemd unit for 24/7 server operation

pine/                       TradingView Pine Script references
pine_scripts/               Generated Pine Scripts for verification
reports/                    Day reports and result CSVs
archive/                    Old/unused modules from earlier phases
  webhook/                  Flask webhook receiver (TradingView → bot)
  processor/                Event processor for webhook signals
  migrations/               Alembic DB migrations (PostgreSQL schema)
  core/                     Order manager, executor, reconciler, event logger
  leaderboard/              CSV ingest + HTML report generator
  old_runners/              Per-asset backtest scripts (replaced by batch runner)
  scripts/                  Dashboard export, stress test, Google Sheets sync
  tests/                    Unit tests for queue, idempotency, DLQ, reconciliation
  examples/                 Example usage scripts for executor and events
```

## Assets & Data

10 assets: BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, LINK, LTC
3 timeframes: 15m, 1h, 4h
Period: 2020-01-01 to 2026-03-20 (6 years)
Candles: 217k (15m), 54k (1h), 13.6k (4h) per asset

Download data:
```bash
python scripts/fetch_6yr_data.py
```

## Backtester Details

- Entry: configurable min_agreement (N of M signals must agree)
- Exit: SL, TP, trailing stop checked against high/low (intrabar)
- Fees: 0.1% on both entry and exit
- Capital: $10,000 initial, 95% allocation per trade
- Metrics: ROI/yr, Win Rate, Profit Factor, Sharpe, Gross DD, Net DD

### Drawdown Definitions
- **Gross DD**: (Peak Equity - Trough) / Peak × 100% — equity curve drawdown
- **Net DD**: (Initial Capital - Lowest Capital) / Initial × 100% — only when capital drops below $10k, max 100%

## TradingView Verification

Every strategy can be exported as a Pine Script and cross-verified on TradingView:
```
/pinescript EMA_Cloud_Strength
```
This generates a complete Pine Script with matching indicators, entry/exit logic, and JSON webhook alerts.

## Server Deployment

```bash
scp -i "deploy/harsh_server/key.pem" src/telegram_backtest_bot.py ubuntu@server:/home/ubuntu/Garima/src/
ssh -i "deploy/harsh_server/key.pem" ubuntu@server "sudo systemctl restart telegram_bot"
```

## License

Private repository — internal use only.