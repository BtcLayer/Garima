# Garima — Project Context for LLM Sessions

## What This Is
Crypto trading bot with Telegram interface, ML strategy scanner, Streamlit dashboard, and Pine Script generator. Backtests strategies across 10+ assets on 4h timeframe using 6 years of Binance data. **Critical discovery: our backtester and TradingView produce fundamentally different results. Only TV-validated strategies should be trusted.**

## Current State (as of April 1, 2026)

### What Works
- Telegram bot with 15+ commands (running on AWS EC2)
- Streamlit dashboard (live at server/dashboard/, 9 tabs, auto-refresh)
- ML pipeline (RF + GBM, 40+ features, walk-forward OOS)
- Pine Script generator (dashboard + bot)
- Backtester rewritten with crossover signals + signal-based exits + long/short
- 70+ Pine Scripts generated

### What Doesn't Work
- **Our backtester results DON'T match TradingView** — strategies showing 1%+/day on backtester show -95% on TV
- **Harsh's backtester (strategy_tournament.py) uses signal×return model** — theoretical math, not real trades. Results don't transfer to TV either
- **15m timeframe** — all strategies fail on TV (too noisy)
- **Genetic algorithm** — produced fake 3%/day results that failed TV validation completely

### Critical Finding
The backtester (both ours and Harsh's) uses a different execution model than TradingView:
- **Backtester**: signal × bar_return (no actual trades)
- **TradingView**: actual position open/close with fees and slippage
- **Result gap**: backtester shows +0.3%/day, TV shows -95%
- **Root cause**: Harsh's risk filters (cooldown, circuit breaker, ADX, ATR) are applied to the return stream, not to actual trade execution

## Repo Structure
```
src/
  telegram_backtest_bot.py  — Main bot (5000+ lines, /autohunt /ml /evolve /generate)
  ml_strategy.py            — ML pipeline (RF + GBM, 40+ features, walk-forward OOS)
  genetic_strategy.py       — Genetic algorithm (failed TV validation — don't trust results)
  brain.py                  — Gemini AI integration
  data_fetcher.py           — Binance data downloader
  binance_client.py         — Binance API wrapper
  manager.py                — Live trade execution (~400 lines, kill switch, circuit breaker)
  signal_server.py          — FastAPI webhook server
  signal_queue.py           — SQLite signal queue (WAL mode)
  pine_generator.py         — Pine Script generator
  walk_forward.py           — Walk-forward validation

run_strategies_batch.py     — Core backtesting engine (REWRITTEN Mar 31)
                              Now has: crossover signals, signal-based exits, long+short flipping,
                              tournament-matched backtester (run_tournament_backtest()),
                              LONG_EXIT_FUNCTIONS, SHORT_ENTRY_FUNCTIONS
dashboard.py                — Streamlit dashboard (9 tabs, auto-refresh, Pine Script gen)
strategies/                 — 22 batch files (batch_01-22), 260+ strategies
storage/                    — Historical data, ML results, genetic results, autohunt results
scripts/                    — ml_15m_scan.py, continuous_search.py, run_proven_strategies.py, etc.
reports/                    — Day reports, weekly report, TV validation results
pine/                       — 70+ Pine Scripts (rule-based + genetic + TV-first)
deploy/                     — systemd service, SSH key (gitignored)
```

## Bot Commands (Telegram)
```
Backtesting:
  /auto all 4h        — Full pipeline: backtest → filter → optimize → validate
  /backtest ETHUSDT_4h 1-5 — Run specific batches
  /autohunt           — Auto-find strategies (crossover signals + long/short)
  /autohunt stop/resume/status

Strategy Generation:
  /generate           — 5-method generator (ATR-adaptive, mean reversion, random mutation, high-TP, hybrid)
  /generate stop

ML Scanner:
  /ml                 — Start ML scan (RF + GBM, 40+ features, walk-forward OOS)
  /ml status          — Current progress
  /ml results         — Top 10 ML strategies
  /ml stop

Genetic Evolution:
  /evolve start       — Start genetic evolution
  /evolve status      — Check progress
  /evolve results     — See results

Results & Info:
  /results, /results 4h, /elite, /status, /help
```

## Server
```
Server: ubuntu@15.207.152.119 (AWS EC2, ap-south-1)
SSH key: deploy/harsh_server/harsh-key-ap-south-1.pem
Bot service: telegram_bot.service (systemd)
Dashboard: Streamlit on port 8502, accessible via nginx at /dashboard/
Harsh's system: /home/ubuntu/tradingview_webhook_bot/ (separate project, port 8501)

# Deploy + restart:
scp -i "deploy/harsh_server/harsh-key-ap-south-1.pem" src/telegram_backtest_bot.py ubuntu@15.207.152.119:/home/ubuntu/Garima/src/
ssh -i "deploy/harsh_server/harsh-key-ap-south-1.pem" ubuntu@15.207.152.119 "sudo systemctl restart telegram_bot"
```

## Backtester Details (run_strategies_batch.py)

### Two Modes:
1. **Trade-based backtester** (run_backtest) — crossover entry, signal exits, long+short flipping, 0.1% fee
2. **Tournament-matched backtester** (run_tournament_backtest) — signal×return model matching Harsh's system

### 19 Indicators + 19 Signals (all CROSSOVER-based now)
Signals fire ONCE on crossover, not every bar. Each has matching LONG_EXIT and SHORT_ENTRY functions.

### Key Lesson
Tournament-style backtester produces positive results (0.3-1.5%/day) but these DON'T translate to TradingView. The signal×return model is theoretical — TV uses actual trade execution with fees.

## Harsh's System (strategy_tournament.py)
Located at `/home/ubuntu/tradingview_webhook_bot/`
- Uses `signal × bar_return` model (NOT individual trades)
- Risk filters: ADX>20, ATR<2x, cooldown after 3 losses, -3% daily circuit breaker
- Grading: ALPHA++ (ROI≥0.5%, Sharpe≥3.5, WR≥45%, GDD<35%), ALPHA (ROI≥0.25%, Sharpe≥2.5)
- 902 strategies tested, 119 ALPHA++, 106 ALPHA
- **OOS retention: only 18.9%** (headline 1.5%/day → real 0.2-0.3%/day)
- **TV validation: 0 of 14 strategies profitable on TV**

## ML Pipeline (src/ml_strategy.py)
- **Models**: Random Forest (200 trees) + Gradient Boosting (200 estimators)
- **Features**: 40+ from 19 indicators (returns, distances, slopes, ratios, candle patterns)
- **Validation**: Walk-forward 70/30 train/test split — OOS results only
- **Labels**: 1 if price hits TP before SL within N bars, 0 otherwise
- **Best result**: 0.178%/day on ADA 4h (GBM, PF=2.17, WR=55.9%, Acc=73.2%)
- Currently running 4h scan on server

## Dashboard (dashboard.py)
Live at `http://15.207.152.119/dashboard/` (via nginx reverse proxy)
- 9 tabs: Analytics, ML Scanner, Genetic Evolution, Generator, Strategy Builder, Pine Script Gen, Monte Carlo, Parameter Heatmap, Architecture
- Auto-refreshes every 30 seconds
- Sidebar: metrics + Pine Script dropdown with 10 pre-built scripts
- Interactive strategy builder: select signals → run backtest → equity curve

## TV Validation Results (CRITICAL)
All strategies tested on TradingView showed UNPROFITABLE results:
- 14 Harsh strategies on 15m: 0 profitable (all -90% to -100%)
- 14 Harsh strategies on 1h: 1 barely profitable (MACD_Breakout FIL +28.7%)
- 5 TV-first scripts on 15m: 0 profitable (all -70% to -100%)
- 3 genetic algo scripts on 4h: 0 profitable (all -12% to -65%)

**Only proven approach: build directly on TV, validate there, never trust backtester numbers alone.**

## Bugs Fixed (28 total across 6 days)
Days 1-4: 24 bugs (trailing stop, SL/TP, fees, entry timing, sizing, DD calc, etc.)
Day 5 (Mar 31): Backtester rewrite — crossover signals, signal exits, L/S flipping
Day 6 (Apr 1): Tournament backtester matching, TV validation proving gap

## Work Completed by Day
- **Mar 24-25**: Foundation, 7 bug fixes, first backtests
- **Mar 26**: TV cross-validation, 7 new indicators, 14 signal functions
- **Mar 29**: Walk-forward, SOL overfit caught, autohunt built
- **Mar 30**: TV-match rewrite, 14 strategies deployed, 65+ Pine Scripts
- **Mar 31**: ML pipeline, genetic algo (failed), dashboard (9 tabs), backtester rewrite #2
- **Apr 1**: Read Harsh's tournament code, found signal×return model mismatch, TV validated all strategies (all failed), ML 4h scan running

## Next Steps (Priority Order)
1. **Add risk filters to Pine Scripts** (ADX, ATR, cooldown, circuit breaker) — this is what makes strategies profitable
2. **TV-first approach** — build strategies on TV, validate there, bring back
3. **Funding rate arbitrage** as supplement (0.03-0.15%/day, low risk)
4. **Focus on 4h timeframe only** — 15m and 1h don't work on TV
5. User has Binance testnet API key ready for paper trading

## What NOT to Do
- Don't trust backtester results without TV validation
- Don't use 15m timeframe — all strategies fail on TV
- Don't use genetic algorithm results — they're overfit
- Don't use tournament numbers as-is — they're theoretical (signal×return model)
- Don't use SOL — overfits badly
- Don't run heavy processes locally — use server only (user's machine crashes)
