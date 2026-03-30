# Garima — Project Context for LLM Sessions

## What This Is
Crypto trading bot with Telegram interface. Backtests 230+ strategies across 10 assets (BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, LINK, LTC) on 3 timeframes (15m, 1h, 4h) using 6 years of Binance Spot data. Generates Pine Scripts for TradingView verification. Uses Gemini AI for analysis.

## Repo Structure
```
src/
  telegram_backtest_bot.py  — Main bot (3900+ lines, all commands)
  brain.py                  — Gemini AI integration
  data_fetcher.py           — Binance data downloader
  binance_client.py         — Binance API wrapper
  manager.py                — Live trade execution (minimal, NOT production-ready)
  pine_generator.py         — Pine Script generator
  comprehensive_backtest.py — Full backtest engine with Sharpe/Sortino/Calmar
  auto_optimizer.py         — SL/TP/TS parameter optimizer
  backtest_optimizer.py     — Trade analyzer

run_strategies_batch.py     — Core backtesting engine (indicators, signals, backtest loop)
strategies/                 — 20 batch files (batch_01.py - batch_20.py), 230+ strategies
storage/historical_data/    — 30 parquet files, 6yr data (gitignored, ~80MB)
storage/checkpoints/        — Auto-save progress for long-running commands
storage/elite_ranking.json  — Saved optimized strategy params (gitignored)
scripts/                    — fetch_6yr_data.py, generate_pine.py, asset_status.py
reports/                    — Day reports, audit report, old result CSVs
archive/                    — Unused but preserved: webhook, core executor, migrations, old runners
deploy/                     — systemd service file, SSH key (gitignored)
pine/                       — TradingView Pine Script references
```

## Bot Commands (Telegram)
```
Step 1: Backtest
  /auto all 4h        — Full pipeline: backtest all 230 strats → filter top 20 → optimize SL/TP/TS → validate
  /auto all 1h        — Same for 1h timeframe
  /backtest ETHUSDT_4h 1-5  — Run specific batches on specific asset
  /comprehensive      — All assets × all timeframes

Step 2: Results & Analysis
  /results             — Last run results (all timeframes)
  /results 4h          — Filter by timeframe
  /results 1h
  /elite               — Show/run elite strategies
  /analyze             — Gemini AI analysis (uses API quota)
  /ask <question>      — Ask AI about results

Step 3: Pine Script & Verification
  /pinescript top 5    — Generate Pine Scripts for top 5 strategies
  /pinescript <name>   — Generate for specific strategy

Step 4: Management
  /status              — Bot status, running jobs, config
  /stop                — Stop current job (checkpoint saved for /auto)
  /restart             — Reset bot internal state (NOT code reload)
  /setdefault BTCUSDT_4h — Change default symbol
  /help                — Command guide
```

## Server Deployment
```
Server: ubuntu@15.207.152.119 (AWS EC2, ap-south-1)
SSH key: deploy/harsh_server/harsh-key-ap-south-1.pem
Service: telegram_bot.service (systemd, auto-restart)
Python: 3.10, venv at /home/ubuntu/Garima/.venv
Bot runs: python -m src.telegram_backtest_bot

# Deploy updated code:
scp -i "deploy/harsh_server/harsh-key-ap-south-1.pem" src/telegram_backtest_bot.py ubuntu@15.207.152.119:/home/ubuntu/Garima/src/telegram_backtest_bot.py

# Deploy multiple files:
scp -i "deploy/harsh_server/harsh-key-ap-south-1.pem" run_strategies_batch.py ubuntu@15.207.152.119:/home/ubuntu/Garima/

# Restart bot (must run on server, not local):
ssh -i "deploy/harsh_server/harsh-key-ap-south-1.pem" ubuntu@15.207.152.119 "sudo systemctl restart telegram_bot"

# Check logs:
ssh -i "deploy/harsh_server/harsh-key-ap-south-1.pem" ubuntu@15.207.152.119 "sudo journalctl -u telegram_bot -n 30 --no-pager"

# Check if running:
ssh -i "deploy/harsh_server/harsh-key-ap-south-1.pem" ubuntu@15.207.152.119 "sudo systemctl status telegram_bot"
```

## Key Technical Details

### Backtester (run_strategies_batch.py)
- 12 indicators: EMA8/21/50, SMA20, BB, RSI14, MACD, Stochastic, VWAP, ADX, ATR, Supertrend, Volume
- Entry: min_agreement signals must be active (1, 2, or 3 depending on strategy)
- Exit: signal count drops below min_agreement, OR SL/TP/TS hit
- SL/TP checked against HIGH/LOW (not just close) — fixed Mar 24
- Trailing stop tracks actual peak price per bar — fixed Mar 24
- Fees: 0.1% on both entry AND exit — fixed Mar 24
- Initial capital: $10,000
- Net DD = (10k - lowest capital) / 10k × 100%, capped at 100%
- Gross DD = peak-to-trough equity drawdown %

### Checkpoint System
- `/auto` saves progress after each asset (Phase 1) and each strategy (Phase 3)
- Saved to storage/checkpoints/auto_{timeframe}.json
- If stopped, re-running `/auto` resumes from checkpoint
- Checkpoint cleared on successful completion

### Results Storage
- /auto saves to auto_results_{timeframe}.csv and auto_optimization_results.csv
- /results loads from all CSV files + in-memory results
- /results {timeframe} filters by 15m/1h/4h

### Pine Script Generator
- Generates TradingView-compatible Pine Script v5
- Includes JSON webhook alert_message for live trading
- Uses strategy.cash qty type to avoid negative equity errors
- min_agreement mapped correctly (>= N, not AND)

## Bugs Fixed (Mar 24, 2026)
1. Trailing stop never tracked peak — CRITICAL (was checking entry price, not rolling peak)
2. SL/TP checked at close only — HIGH (now uses high/low for intrabar stops)
3. Fees only on exit — MEDIUM (now both entry + exit)
4. Bollinger Bands wrong stdev — MEDIUM (ddof=1 → ddof=0)
5. Breakout_20 included current bar — MEDIUM (now uses [1:] for lookback)
6. Exit threshold hardcoded to 0 — MEDIUM (now matches min_agreement)
7. VWAP fallback assumed 15m — LOW (now timeframe-aware)

## Data
- 10 assets × 3 timeframes = 30 parquet files
- Period: 2020-01-01 to 2026-03-20 (~6 years)
- Downloaded via scripts/fetch_6yr_data.py (paginated Binance API, 1000 candles/batch)
- SOL/AVAX/DOT start later (Aug-Sep 2020)
- Data lives locally + on server, NOT in git (gitignored)

## Known Issues / Limitations
1. Live execution (manager.py) is toy-grade: hardcoded 0.01 qty, no position sizing, no kill-switch
2. No paper trading mode
3. Webhook pipeline exists in archive/ but is NOT connected to anything active
4. Bot processes commands sequentially — don't use two Telegram chats simultaneously
5. /restart only resets internal state, does NOT reload Python code (need systemctl restart)
6. Gemini AI free tier has quota limits — only called on /analyze and /ask
7. 15m backtests are slow (~217k candles × 230 strats) — run overnight
8. All strategies are LONG only — no short selling

## Current Status (as of Mar 25, 2026)
- /auto all 1h: COMPLETED — 200 results across 10 assets, saved to auto_optimization_results.csv
- /auto all 4h: needs to be run with fixed code
- /auto all 15m: needs to be run (slow, do overnight)
- Top strategy (1h): Golden_Cross_Pro on BNBUSDT — 75.7%/yr ROI, 73% GrossDD
- All results need TradingView cross-verification before trusting
- Audit score: 3.5/10 (prototype grade, strong backtesting, weak execution)

## ROI Definitions
- ROI% in /results = ROI per annum (annualized compound return)
- ROI_Percent in CSV = total return over entire backtest period
- Daily ROI = ROI_per_annum / 365
- For 1%/day target, need 365%/yr — very aggressive, few strategies hit this honestly

## What NOT to Do
- Don't run /auto without "all" — it only tests default symbol
- Don't SCP from the server SSH session — run from local PowerShell
- Don't run systemctl commands locally — they're for the server
- Don't trust results without TV cross-verification
- Don't deploy to live trading — execution path has no risk controls
