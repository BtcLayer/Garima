# Garima — Project Context for LLM Sessions

## What This Is
Crypto trading bot with Telegram interface. Backtests 260+ strategies across 10 assets (BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, LINK, LTC) on 3 timeframes (15m, 1h, 4h) using 6 years of Binance Spot data. Generates Pine Scripts for TradingView verification. Uses Gemini AI for analysis. Integrated with alert bot tournament tier system (TIER_1/TIER_2/PAPER).

## Repo Structure
```
src/
  telegram_backtest_bot.py  — Main bot (4600+ lines, all commands incl. autohunt)
  brain.py                  — Gemini AI integration
  data_fetcher.py           — Binance data downloader
  binance_client.py         — Binance API wrapper
  manager.py                — Live trade execution (~400 lines, kill switch, 2% risk, circuit breaker)
  signal_server.py          — FastAPI webhook server (Pydantic validation)
  signal_queue.py           — SQLite signal queue (WAL mode, idempotency)
  pine_generator.py         — Pine Script generator
  comprehensive_backtest.py — Full backtest engine with Sharpe/Sortino/Calmar
  auto_optimizer.py         — SL/TP/TS parameter optimizer
  backtest_optimizer.py     — Trade analyzer
  walk_forward.py           — Walk-forward validation (rolling train/test)
  metrics.py                — Signal processing metrics
  event_log.py              — JSONL event logger
  logger.py                 — Structured JSON logging with rotation

run_strategies_batch.py     — Core backtesting engine (19 indicators, 19 signals, TV-matched execution)
strategies/                 — 22 batch files (batch_01.py - batch_22.py), 260+ strategies
storage/historical_data/    — 30 parquet files, 6yr data (gitignored, ~80MB)
storage/checkpoints/        — Auto-save progress for long-running commands
storage/elite_ranking.json  — Saved optimized strategy params (gitignored)
storage/autohunt_results.json — Auto-hunt found strategies
scripts/                    — find_high_trade_strategies.py, optimize_pf.py, param_sweep_engine.py, etc.
reports/                    — Day reports, weekly report, audit report, CSVs
archive/                    — Unused but preserved: webhook, core executor, migrations, old runners
deploy/                     — systemd service file, SSH key (gitignored)
pine/                       — 65+ TradingView Pine Script files (TV-validated)
```

## Bot Commands (Telegram)
```
Step 1: Backtest
  /auto all 4h        — Full pipeline: backtest all strats → filter top 20 → optimize → validate
  /auto all 1h        — Same for 1h timeframe
  /backtest ETHUSDT_4h 1-5  — Run specific batches on specific asset
  /comprehensive      — All assets x all timeframes
  /autohunt           — Auto-find ALPHA/ALPHA++ strategies (Phase 0 proven + Phase 1 brute force)
  /autohunt stop      — Pause hunt (saves checkpoint)
  /autohunt resume    — Resume from checkpoint
  /autohunt status    — Show progress

Step 2: Results & Analysis
  /results             — Last run results (all timeframes)
  /results 4h          — Filter by timeframe
  /elite               — Show/run elite strategies (with NDD, Cap@NDD)
  /analyze             — Gemini AI analysis (uses API quota)
  /ask <question>      — Ask AI about results

Step 3: Pine Script & Verification
  /pinescript top 5    — Generate Pine Scripts for top 5 strategies
  /pinescript <name>   — Generate for specific strategy

Step 4: Management
  /status              — Bot status, running jobs, config
  /stop                — Stop current job (checkpoint saved)
  /restart             — Reset bot internal state
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

# Restart bot:
ssh -i "deploy/harsh_server/harsh-key-ap-south-1.pem" ubuntu@15.207.152.119 "sudo systemctl restart telegram_bot"

# Check logs:
ssh -i "deploy/harsh_server/harsh-key-ap-south-1.pem" ubuntu@15.207.152.119 "sudo journalctl -u telegram_bot -n 30 --no-pager"
```

## Key Technical Details

### Backtester (run_strategies_batch.py) — TV-Matched (Mar 29-30)
- **19 indicators**: EMA8/21/50, SMA20, BB, RSI14, MACD, Stochastic, VWAP, ADX, ATR, Supertrend, Volume, OBV, CCI, Ichimoku, PSAR, MFI, Keltner, Williams %R
- **19 signal functions**: EMA_Cross, RSI_Oversold, MACD_Cross, BB_Lower, BB_Upper, Volume_Spike, Breakout_20, Stochastic, Supertrend, VWAP, ADX_Trend, Trend_MA50, OBV_Rising, CCI_Oversold, Ichimoku_Bull, PSAR_Bull, MFI_Oversold, Keltner_Lower, Williams_Oversold
- **Entry**: Next bar open (pending_entry flag) — matches TradingView
- **Position sizing**: Compounds at 95% of current equity (not fixed) — matches TradingView
- **Exit**: At actual SL/TP price level, not bar close — matches TradingView
- **Peak tracking**: From bar high, not close — matches TradingView
- **Fees**: 0.03% per side (0.06% round-trip) — matches TradingView (FEE=0.0003)
- **Sharpe**: TV-style daily Sharpe = (mean_daily_return / std_daily_return) x sqrt(252)
- **Initial capital**: $10,000
- **min_agreement**: N-of-M signals must fire simultaneously for entry

### Autohunt System (Mar 29-30)
- **Phase 0**: Tests proven signal combos (PSAR+EMA+Supertrend core) on all assets/TFs
- **Phase 1**: Brute force all N-choose-K combinations (sizes 2-6) with min_ag sweep
- **TF-specific params**: 4h uses SL 0.8-2% TP 3-12%; 1h uses SL 0.4-1% TP 1.2-6%
- **TF-specific criteria**: 4h strict (PF>=1.6 for TIER_2), 1h relaxed (PF>=1.35 for TIER_2)
- **Checkpoints**: Every 50 combos, resumes from where it left off
- **Searches 1h + 4h** (15m disabled for now)

### Alert Bot Grading (User's Live System)
```
TIER_1_DEPLOY:   PF >= 2.0, WR >= 50%, MDD < 30%, ROI >= 20%, Sharpe > 0
TIER_1_MONITOR:  PF >= 1.8, WR >= 50%, Sharpe >= 0.5, ROI >= 15%, MDD < 50%
TIER_2_DEPLOY:   PF >= 1.6, WR >= 50%, MDD < 40%, ROI >= 10%
TIER_2_TEST:     PF >= 1.4, WR >= 50%, MDD < 50%, ROI >= 5%
PAPER_TRADE:     PF >= 1.2, WR >= 45%, ROI >= 2%, MDD < 60%
```
Key insight: **PF + WR determine tier, not Sharpe**.

### Winning Signal Combo
- **PSAR_Bull + EMA_Cross + Supertrend + Trend_MA50 + Volume_Spike** (5/5 agree)
- TP sweet spot: 4-8% for 4h (balances PF vs ROI)
- Only ETH, ADA, BTC produce reliable TV-matched results
- BNB, SOL, LINK, XRP, DOT, AVAX, LTC fail PF/WR thresholds on 4h

### Checkpoint System
- /auto saves progress after each asset (Phase 1) and each strategy (Phase 3)
- /autohunt saves every 50 combos
- Saved to storage/checkpoints/ and storage/autohunt_checkpoint.json
- If stopped, re-running resumes from checkpoint

### Results Storage
- /auto saves to auto_results_{timeframe}.csv and auto_optimization_results.csv
- /autohunt saves to storage/autohunt_results.json
- /results loads from all CSV files + reports/ directory + in-memory results
- /results {timeframe} filters by 15m/1h/4h

### Pine Script Generator
- Generates TradingView-compatible Pine Script v5
- Includes JSON webhook alert_message for live trading
- Uses strategy.cash qty type
- min_agreement mapped correctly (>= N, not AND)
- Position sizing 95% of equity (matching backtester)
- 65+ pine scripts in pine/ directory, TV-validated

## Bugs Fixed

### Mar 24 (Day 1)
1. Trailing stop never tracked peak — CRITICAL
2. SL/TP checked at close only — now uses high/low for intrabar stops
3. Fees only on exit — now both entry + exit
4. Bollinger Bands wrong stdev — ddof=1 to ddof=0
5. Breakout_20 included current bar — now uses [1:] for lookback
6. Exit threshold hardcoded to 0 — now matches min_agreement
7. VWAP fallback assumed 15m — now timeframe-aware

### Mar 26 (Day 2)
8. `/results 4h` showing no results — bot only searched root dir, added reports/ scanning
9. Column name normalization for different CSV formats

### Mar 29 (Day 3)
10. Bot Sharpe inflated 5-10x vs TV — was per-trade, fixed to daily Sharpe
11. Walk-forward showed SOL overfit (282%/yr on TV, -10.7% OOS) — dropped SOL
12. Kill switch test sending real Telegram messages — fixed with mocking
13. Gross DD dividing by initial_capital instead of peak_equity — fixed
14. Net DD returning 0 for negative results — fixed

### Mar 30 (Day 4) — MAJOR REWRITE
15. Bot entry at current close, TV at next bar open — rewrote with pending_entry flag
16. Bot fixed capital sizing, TV compounds — changed to 95% equity / entry_price
17. Bot exit at close price, TV at SL/TP level — exit at actual sl_price/tp_price
18. Peak tracking from close instead of high — changed to track from high
19. Fee 0.1% per side (3x TV) — changed to 0.03% per side (FEE=0.0003)
20. Cap@NDD showing $10,000 for all — key mismatch `Net_DD_Capital` vs `Capital_At_Net_DD` fixed
21. Pine Script position sizing was 10% — changed to 95%
22. Autohunt Phase 1 using undefined `PARAMS` variable — fixed to `PARAMS_BY_TF`
23. Autohunt only searching 4h — added 1h with TF-specific params and relaxed criteria
24. `pine_backtest` import crash — changed to optional import with graceful fallback

## 14 Deployed Strategies (TV-Validated, as of Mar 30)
| # | Strategy | Asset | TF | PF | WR% | ROI%/yr | Tier |
|---|----------|-------|----|----|-----|---------|------|
| 1 | tv_04_TP8 | ETH | 4h | 1.87 | 62.4 | 112.3 | TIER_1_MONITOR |
| 2 | 44_PSAR_Vol_Surge | BTC | 4h | 1.87 | 46.1 | 107.7 | TIER_1_MONITOR |
| 3 | tv_03_TP6 | ETH | 4h | 1.73 | 52.4 | 109.6 | TIER_2_DEPLOY |
| 4 | tv_12_PSAR_EMA_Vol | ADA | 4h | 1.72 | 52.5 | 102.4 | TIER_2_DEPLOY |
| 5 | tv_02_TP5 | ETH | 4h | 1.73 | — | — | TIER_2_DEPLOY |
| 6 | tv_01_TP4 | ETH | 4h | 1.73 | — | — | TIER_2_DEPLOY |
| 7 | tv_04_TP8 | ADA | 4h | 1.73 | — | — | TIER_2_DEPLOY |
| 8 | 56_PSAR_Vol_Tight | ETH | 4h | 1.68 | 61.1 | 93.0 | TIER_2_DEPLOY |
| 9 | 57_PSAR_Vol_Ultra | ETH | 4h | 1.63 | 63.4 | 69.1 | TIER_2_DEPLOY |
| 10 | tv_11_ADA_TP9 | ADA | 4h | 1.50 | 52.3 | 112.1 | TIER_2_TEST |
| 11 | alpha_04_Ichi_PSAR | ETH | 4h | 1.56 | ~55 | 55.8 | TIER_2_TEST |
| 12 | 56_PSAR_Vol_Tight | BTC | 4h | 1.51 | 50.8 | — | TIER_2_TEST |
| 13 | tv_04_TP8 | LINK | 4h | 1.25 | 48.9 | — | TIER_2_TEST |
| 14 | tv_03_TP6 | BTC | 4h | — | — | — | TIER_2_TEST |

## Work Completed by Day

### Day 1 — Mar 24-25: Foundation & Bug Fixes
- Fixed 7 critical backtester bugs (trailing stop, SL/TP, fees, etc.)
- `/results 4h` bug fixed (was not scanning reports/ directory)
- Ran full `/auto all 1h` — 200 results across 10 assets
- Ran backtests on 15m (locally) and 1h (on bot)
- Created mid-day report with executive summary
- Completed P0 audit items (data integrity, fee accuracy)

### Day 2 — Mar 26: TradingView Cross-Validation & New Indicators
- Generated Pine Scripts for top strategies
- TV cross-validation revealed bot vs TV mismatches
- Added 7 new indicators: OBV, CCI, Ichimoku, PSAR, MFI, Keltner, Williams %R
- Added 14 new signal functions (7 long + 7 short)
- Created strategies batch_21 (12 strategies) and batch_22 (16 TV-validated alpha)
- Categorized strategies into high-return and moderate-return sets

### Day 3 — Mar 29: Walk-Forward Validation & Alpha Hunting
- Walk-forward validation (rolling train/test windows) on all assets
- Discovered SOL overfit: 282%/yr on TV but -10.7% OOS — dropped from deploy list
- Fixed bot Sharpe calculation (was 5-10x inflated vs TV)
- Added NDD date, Cap@NDD columns to /elite and /results
- Fixed gross DD and net DD calculation bugs
- Built autohunt system with Phase 0 (proven combos) + Phase 1 (brute force)
- Identified PF + WR as tier-determining metrics, not Sharpe
- Found TP sweet spot: 4-8% balances PF and ROI
- Identified winning signal combo: PSAR + EMA_Cross + Supertrend + Trend_MA50 + Volume_Spike

### Day 4 — Mar 30: TV-Matched Backtester Rewrite & Live Deployment
- **Major backtester rewrite** to match TradingView execution exactly:
  - Entry at next bar open (pending_entry flag)
  - Compound position sizing (95% equity)
  - Exit at actual SL/TP price level
  - Peak tracking from high
  - Fee changed to 0.03% per side (0.06% round-trip)
- PF accuracy improved from ~50% off to within 2% of TV
- Generated 65+ Pine Scripts for TradingView
- Created 14 deployable strategies (2 TIER_1, 7 TIER_2_DEPLOY, 5 TIER_2_TEST)
- TP sweep on all 9 remaining assets — only ADA showed candidates
- Updated autohunt: added 1h timeframe, TF-specific params, relaxed criteria
- Fixed Phase 1 using undefined PARAMS variable
- Fixed pine_backtest import crash
- Created weekly report (Mar 23-30) with day-by-day breakdown
- Updated PROJECT_CONTEXT.md
- 4 git commits covering all changes
- Running high-trade-count strategy sweep for 4h + 1h

## Data
- 10 assets x 3 timeframes = 30 parquet files
- Period: 2020-01-01 to 2026-03-21 (~6 years)
- Downloaded via scripts/fetch_6yr_data.py (paginated Binance API, 1000 candles/batch)
- SOL/AVAX/DOT start later (Aug-Sep 2020)
- Data lives locally + on server, NOT in git (gitignored)

## Known Issues / Limitations
1. Only ETH, ADA, BTC produce reliable TV-matched results on 4h
2. 1h and 15m strategies have not yet produced TIER_1/TIER_2 results (work in progress)
3. Bot processes commands sequentially — don't use two Telegram chats simultaneously
4. /restart only resets internal state, does NOT reload Python code (need systemctl restart)
5. Gemini AI free tier has quota limits — only called on /analyze and /ask
6. 15m backtests are slow (~217k candles x 260 strats) — run overnight
7. All strategies are LONG only — no short selling
8. Live execution path needs senior approval (API key, capital, server upgrade)
9. Paper trade the 14 deployed strategies for 1 week before going live

## ROI Definitions
- ROI% in /results = ROI per annum (annualized compound return)
- ROI_Percent in CSV = total return over entire backtest period
- Daily ROI = ROI_per_annum / 365
- For 1%/day target, need 365%/yr — very aggressive, few strategies hit this honestly
- TV-style Sharpe = (mean_daily_return / std_daily_return) x sqrt(252)

## What NOT to Do
- Don't run /auto without "all" — it only tests default symbol
- Don't SCP from the server SSH session — run from local PowerShell
- Don't run systemctl commands locally — they're for the server
- Don't trust results without TV cross-verification
- Don't deploy to live trading without senior approval
- Don't use SOL for strategies — overfits badly
