# Garima — Project Context for LLM Sessions

## What This Is
Crypto trading bot with Telegram interface, ML strategy scanner, Streamlit dashboard, and Pine Script generator. Backtests strategies across 10+ assets on 4h timeframe using 6 years of Binance data. **Critical discovery: our backtester and TradingView produce fundamentally different results. Only TV-validated strategies should be trusted.**

## Current State (as of April 7, 2026)

### What Works
- Telegram bot with 20+ commands including `/ml learn`, `/ml insights`, `/ml generate`, `/promote` (running on AWS EC2)
- Streamlit dashboard (live at `15.207.152.119:8502`, loads 313 strategies from CSV, auto-refresh)
- ML pipeline (RF + GBM, 50+ features including Donchian/CCI/HA/Aroon/TRIX signals, walk-forward OOS)
- ML trained on 53 TV-validated results — learns what works on TradingView
- Strategy promotion pipeline (T07) — offline approval before live deployment
- 68 Pine Scripts (50 in `pine/` + 18 in `pine_new/`)
- Bot + Dashboard connected: single shared CSV, auto-sync on ML completion
- Backtest processor with CAGR + fixed capital mode + slippage + win rate checks
- 20 assets supported (ETH, BTC, SOL, SUI, LDO, LINK, AVAX, ADA, XRP, DOT + 10 more)

### What Doesn't Work / Known Issues
- **95% equity compounding inflates all results** — $10K → $3T is not real. Fixed-capital mode added but full reruns pending
- **Win rates 80%+ are suspicious** — trailing stop creates many small wins, needs investigation
- **15m timeframe** — too noisy, not recommended for deployment
- **Genetic algorithm** — produced fake results, failed TV validation
- **Our backtester vs TradingView gap** — backtester uses signal×return, TV uses actual trades

### Critical Findings (Updated)
1. **Risk framework > indicator choice** — same risk management (trailing stop + circuit breaker + ADX filter) turned WEAK strategies into TIER_1/TIER_2
2. **Fusion strategies outperform singles** — combining Donchian + CCI or Supertrend + CCI gives 3-10x better results than either alone
3. **CAGR was inflated** — linear ROI/365 gives 2-3x higher daily returns than compound formula
4. **Position sizing is the key blocker** — 95% equity makes backtests unrealistic. Must use 10-15% fixed sizing for live
5. **Realistic expectation after fixes: 40-120%/yr**, not 500-6000%/yr

## Repo Structure
```
src/
  telegram_backtest_bot.py  — Main bot (6000+ lines, /ml /promote /evolve /generate)
  ml_strategy.py            — ML pipeline (RF + GBM, 50+ features, strategy signals, walk-forward OOS)
  ml_online.py              — Online learning ML (trains from TV validation feedback)
  ml_persistent.py          — Persistent ML (saves models, never repeats tested combos)
  strategy_promotion.py     — T07: Offline approval pipeline (generate/approve/reject/revoke)
  genetic_strategy.py       — Genetic algorithm (failed TV — don't trust)
  brain.py                  — Gemini AI integration
  data_fetcher.py           — Binance data downloader

run_strategies_batch.py     — Core backtesting engine (50+ indicators including Donchian, CCI, Aroon, TRIX, HA, Chandelier, DI+/DI-, ROC)
                              Two sizing modes: legacy compounding + fixed_notional (realistic)
dashboard.py                — Streamlit dashboard (loads from storage/tv_cagr_results.csv dynamically)
strategies/                 — 22 batch files (batch_01-22), 260+ strategies
storage/                    — Historical data (86MB parquet), ML models, TV feedback, promotion candidates
scripts/                    — feed_tv_results.py, train_ml_full.py, predict_new_strats.py, etc.
reports/                    — Day reports, execution plan, frozen candidates, approval pack
pine/                       — 50 TV-validated Pine Scripts
pine_new/                   — 18 fusion Pine Scripts (latest generation)
deploy/                     — systemd service, SSH key
```

## Bot Commands (Telegram)
```
ML Scanner:
  /ml start           — Run ML scan (20 assets, 4h+1h, 50+ features)
  /ml results         — Show CAGR top 10 strategies
  /ml status          — Current progress
  /ml learn <strat> <asset> <cagr> <wr> <pf> <gdd> — Feed TV result to train ML
  /ml insights        — What ML learned (winning signals, best assets)
  /ml generate        — Suggest new strategy combos from learned patterns

Strategy Promotion (T07):
  /promote generate   — Create candidates from TV results
  /promote report     — Show promotion report
  /promote approve <id> — Approve for live
  /promote reject <id>  — Reject strategy
  /promote live       — Show approved live set
  /promote pending    — Show awaiting review

Other:
  /generate, /evolve, /results, /elite, /status, /help
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

## Harsh's System — Execution Repo (`tradingview_webhook_bot`)
Located at `/home/ubuntu/tradingview_webhook_bot/`
Repo: `anythingai-labs/tradingview_webhook_bot`

### Architecture (Production-Hardened)
- **Webhook Server**: Flask with `/webhook/tradingview`, `/health`, `/metrics`, `/kill` endpoints
- **Orchestrator**: Signal handling, gating, execution pipeline with 10-gate TradePolicy
- **Binance Client**: Mainnet mark-price, simulated fills, SL/TP helpers, leverage, kill-all
- **Circuit Breaker**: Persisted state, daily loss / DD / cooldown / consecutive-loss controls
- **Idempotency Store**: SQLite-backed signal deduplication
- **Reconciler**: Compares ledger vs exchange, auto-syncs drift, severity-based alerting
- **PaperBroker**: Dedicated class, fills at real mainnet mark price, persists to `paper_state.json`

### Completed Tasks (T01-T10)
| Task | What | Status |
|------|------|--------|
| T01 | Mandatory signed webhooks (X-Webhook-Secret header, 5min replay protection) | DONE |
| T02 | Body-secret auth removed | DONE |
| T03 | Canonical schema expanded (8 actions: BUY/SELL/LONG/SHORT/EXIT/CLOSE/OFF/TP) | DONE |
| T04 | CI blocking on failure (removed `|| true`) | DONE |
| T05 | 357 pytest tests (auth, parser, idempotency, breaker, execution, schema, integration) | DONE |
| T06 | Research/live separation | PENDING — orchestrator still auto-approves from top10 |
| T07 | Offline approval workflow | PENDING — no human gate between promotion and execution |
| T08 | TradePolicy class (10 gates in single `evaluate()` call) | DONE |
| T09 | PaperBroker class (separate from BinanceClient) | DONE |
| T10 | Alert coverage (7 heartbeat checks + auth spike detection) | DONE |

### TradePolicy Gates (10 gates in order)
1. Idempotency — signal already processed
2. Tournament alpha — non-USDT symbol
3. Dedup — same strategy/symbol/side within 2 min
4. Cooldown — symbol traded within 5 min
5. Candle lock — opposite direction within 1 hr
6. ROI guard — strategy ROI <= 0%
7. Tier average — manual review needed
8. Kill switch — KILL_SWITCH file on disk
9. Circuit breaker — breaker tripped
10. Safety gate — daily loss limit, position conflict

### Strategy Verification (Garima Integration)
- Orchestrator loads `top10_strategies.json` from Garima's storage
- Tier-aware lookup: TIER_1/TIER_1_DEPLOY → execute live, TIER_2 → execute live, PAPER_TRADE → PaperBroker
- File missing → silent USDT open-pass fallback

### Monitoring (auto_injector.py)
7 hourly checks: webhook UP, orchestrator UP, tournament freshness (<36h), DLQ size, circuit breaker state, auth failure count (<20/hr), DLQ growth

### Infrastructure Tasks (H/N/U series)
| Task | What | Status |
|------|------|--------|
| H-01 | Server/GitHub sync | DONE |
| H-02 | Blocking CI (82 expanded tests) | DONE |
| H-03 | Strict TradingView auth modes | DONE |
| H-04 | Manifest-gated live path | DONE in code |
| H-05 | Human approval CLI (`approve_strategy.py`) | DONE in code |
| H-06 | Deterministic safety policy | DONE |
| H-07 | Rich reconciler alerts | DONE |
| H-08 | TV inventory verifier | DONE |
| U-03 | Populate approval manifest | IN PROGRESS (Apr 7) |
| U-04 | Run inventory verification | IN PROGRESS |
| U-08 | 7-day frozen paper validation | STARTING Apr 7 |

### What's Still Missing (Before Real Capital)
1. **T06**: Orchestrator still auto-approves from `top10_strategies.json` — no human gate
2. **T07**: No formal `/approve` command with timestamp/operator/backtest hash
3. **U-08**: 7-day paper validation not yet completed
4. Manifest is being populated now with CCI Trend ETH + Donchian Trend ETH

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

## TV Validation Results

### Failed (Mar 24 - Apr 2)
- 14 Harsh strategies on 15m/1h: 0 profitable
- 5 TV-first scripts: 0 profitable
- 3 genetic algo scripts: 0 profitable

### Succeeded (Apr 2 - Apr 4) — with BB Squeeze V2 risk framework
- **313 strategy-asset combos tested across 20 assets**
- BB Squeeze V2: TIER_2 on LDO (74.53%/yr), SUI (63.54%), ETH (51.76%)
- Donchian Trend: TIER_1 on ETH, BTC, LINK, AVAX, SUI + 8 more assets
- CCI Trend: TIER_1_DEPLOY on LDO, TIER_1 on ETH, BTC, SOL, ADA + more
- Fusion strategies (Apr 4): Supertrend CCI, Triple Confirm, CCI Donchian Fusion, EMA Ribbon

### Caveat
All results above used 95% equity compounding — **inflated by orders of magnitude**.

### Realistic Rerun Results (Apr 7 — $500/trade, 0.1% slippage, 30% OOS)
| Strategy | Asset | Full ROI | OOS ROI | PF | Sharpe | Status |
|----------|-------|---------|---------|-----|--------|--------|
| CCI Trend | ETH 4h | 5.91% | 3.10% | 1.14 | 0.69 | **PASS** |
| Donchian Trend | ETH 4h | 3.26% | 4.65% | 1.08 | 0.41 | **PASS** |
| Donchian Trend | BTC 4h | 2.09% | -0.9% | 1.06 | 0.33 | FAIL |
| Donchian Trend | DOT 4h | -4.89% | 3.55% | 0.89 | -0.62 | FAIL |
| Donchian Trend | AVAX 4h | -9.63% | -2.0% | 0.79 | -1.22 | FAIL |

Only 2 strategies survived realistic conditions. Both on ETH 4h.

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
- **Apr 1**: Read Harsh's tournament code, found signal×return model mismatch, TV validated all strategies (all failed)
- **Apr 2**: BB Squeeze V2 breakthrough — first multi-asset TV-profitable strategy. Parameter optimization (LDO 74.53%/yr)
- **Apr 3**: Cleanup day. Removed 136 failed strategies. Created 16 new strategies with BB Squeeze V2 risk framework. 8 strategies TV-validated (Donchian TIER_1, HA Trend TIER_2). ML trained on 43 TV results. Dashboard deployed on server
- **Apr 4**: Massive expansion. Created strategies #37-50 (fusion strategies). Supertrend CCI ETH 6,431% CAGR. Connected bot+dashboard to shared data. Fixed CAGR formula. Added win rate checks. Strategy promotion pipeline (T07) built. 313 strategies total. **Senior flagged: all results inflated due to 95% equity compounding**
- **Apr 6**: Transition to realism. Stopped generating strategies, focused on fixing backtest engine. Created frozen shortlist (Donchian ETH/SUI, CCI LDO/ETH — paper trade only). Built execution plan (G-01→G-06). 18 new fusion scripts in `pine_new/`
- **Apr 7**: All Garima tasks completed (G-01→G-06, N-05, N-06, U-01, U-02, T07, X-02, P-08). Realistic rerun: 2 strategies PASS (CCI+Donchian ETH), 5 FAIL. Fixed BUY-trade blocking (ema200 gate removed from 9 scripts). Added webhook secret to 4 old pine scripts + 5 pine_new scripts. Harsh confirmed: manifest populated, inventory 2/2 LIVE_VERIFIED, 18/18 go-live gates PASS, 7-day paper validation started (Apr 7-14). Decision memo template created. 3 webhook-ready scripts converted (Aggressive Entry, PSAR Volume Surge, Ichimoku MACD Pro, Full Momentum).

## All Garima Tasks — Completion Status

| Task | Description | Status | Date |
|------|------------|--------|------|
| G-01 | Realistic sizing ($500 fixed notional) | DONE | Apr 7 |
| G-02 | Slippage modeling (0.1%/trade) | DONE | Apr 7 |
| G-03 | OOS/walk-forward validation | DONE | Apr 7 |
| G-04 | Realism-aware ranking (329 candidates) | DONE | Apr 6 |
| G-05 | Frozen shortlist | DONE | Apr 7 |
| G-06 | Pine/TV parity check | DONE | Apr 7 |
| T07 | Strategy promotion pipeline | DONE | Apr 4 |
| X-02 | Go-live gate doc | DONE | Apr 7 |
| N-05 | Realistic shortlist freeze | DONE | Apr 7 |
| N-06 | Realism provenance confirmed | DONE | Apr 7 |
| U-01 | Regenerate shortlist from realistic rerun | DONE | Apr 7 |
| U-02 | Provenance fields + backtest hash | DONE | Apr 7 |
| P-08 | Decision memo template | DONE | Apr 7 |
| U-09 | Final decision memo | PENDING (Apr 14) |
| P-07 | Daily paper review vs shortlist | IN PROGRESS |

## Final Approved Shortlist (Realistic — Paper Trading Active)
| Strategy | Asset | TF | Full ROI | OOS ROI | PF | Hash | Status |
|----------|-------|----|---------|---------|-----|------|--------|
| CCI Trend | ETHUSDT | 4h | 5.91% | 3.10% | 1.14 | d4ae43d256c0 | APPROVED |
| Donchian Trend | ETHUSDT | 4h | 3.26% | 4.65% | 1.08 | 686adb63d527 | APPROVED |

Settings: $500 fixed/trade, 0.1% slippage, 30% OOS, SL=1.5%, TP=12%, Trail=4%

## Current Phase: 7-Day Paper Validation (Apr 7-14)
- Harsh: freeze code, daily reports, inventory/gate snapshots
- Garima: review daily results vs shortlist, prepare Day-8 decision memo
- **No code changes to execution logic during this window**

## What NOT to Do
- Don't change trading logic during 7-day window
- Don't add more strategies to manifest
- Don't tweak thresholds mid-window
- Don't trust old inflated CAGR numbers
- Don't use 15m timeframe
## LLM Work Log

### April 7, 2026 — Codex (Session 1)
- **Worked on**
  - tightened the Garima-side realism path in `run_strategies_batch.py`
  - kept realistic sizing/slippage metadata visible in outputs
  - regenerated realism artifacts:
    - `reports/REALISM_RERANKED_CANDIDATES.csv`
    - `reports/FROZEN_PAPER_CANDIDATES.csv`
    - `reports/GARIMA_APPROVAL_PACK.md`
  - created working docs:
    - `reports/DAY_PLAN_2026-04-07.md`
    - `reports/NEW_SCRIPT_TEST_MATRIX_2026-04-07.md`
  - generated 5 new Pine scripts in `pine_new/`:
    - `donchian_cci_confirm.pine`
    - `ema_ribbon_donchian_pullback.pine`
    - `aroon_donchian_fusion.pine`
    - `cci_supertrend_donchian.pine`
    - `ha_donchian_trend_fusion.pine`
  - added webhook secret payload support to those new scripts
  - targeted tests: 14 passed

### April 7, 2026 — Codex (Session 2)
- **Worked on**
  - Completed ALL remaining Garima tasks: G-03, G-06, N-05, N-06, U-01, U-02, P-08
  - Ran realistic backtest rerun ($500/trade, 0.1% slippage, 30% OOS): 2 PASS, 5 FAIL
  - Added provenance fields + backtest hashes to shortlist
  - Fixed BUY-trade blocking: removed `ema50 > ema200` from 9 Pine scripts
  - Added webhook secret to 4 old pine/ scripts (Donchian, Engulfing V2, Williams R, Stoch RSI)
  - Converted 4 scripts to webhook format (Aggressive Entry, PSAR Volume Surge, Ichimoku MACD Pro, Full Momentum)
  - Created `approved_strategies.json` with 2 approved strategies
  - Tightened decision memo with severity-based drift thresholds, daily log table, explicit verdict criteria
  - Restarted bot on server with latest code

- **Current status**
  - All Garima tasks: DONE (except U-09 waiting for Apr 14)
  - Paper validation: ACTIVE (Apr 7-14)
  - Manifest: 2 strategies approved, enforcement ON
  - Inventory: 2/2 LIVE_VERIFIED
  - Go-live gate: 18/18 PASS
  - Next action: daily P-07 review + U-09 decision memo on Apr 14
