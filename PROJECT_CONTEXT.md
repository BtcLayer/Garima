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
All results above use 95% equity compounding — **inflated by orders of magnitude**. Realistic fixed-capital reruns pending. Expected realistic range: 40-120%/yr.

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
- **Apr 7**: Continued realism work. Tightened sizing in backtester. Generated 5 new fusion Pine scripts. Created test matrix for pine_new batch. Realism artifacts refreshed

## Current Execution Plan (G-01 through G-06)
```
G-01 Realistic Sizing → G-02 Slippage/Friction → G-04 Realism-Aware Ranking → G-03 OOS/Walk-Forward → G-05 Frozen Shortlist → G-06 Pine/Export Parity → Go-Live Gate
```
Reference: `reports/GARIMA_EXECUTION_PLAN_2026-04-06.md`

## Frozen Paper-Trade Shortlist (draft — NOT live-ready)
1. Donchian Trend / ETH / 4h
2. Donchian Trend / SUI / 4h
3. CCI Trend / LDO / 4h
4. CCI Trend / ETH / 4h
5. Donchian Trend / AVAX / 4h

## Next Steps (Priority Order)
1. **G-01: Finish realistic sizing** in `run_strategies_batch.py` (fixed_notional + capped_equity modes)
2. **G-02: Add slippage** (0.08% per trade on top of 0.06% fee = 0.14% total)
3. **Rerun backtests** with realistic settings and update all numbers
4. **G-03: OOS/walk-forward gate** — no strategy promoted without OOS validation
5. **G-05: Freeze final 3-5 candidates** for paper trading
6. **Paper trade** with realistic position sizing (10% per trade, not 95%)

## What NOT to Do
- Don't trust CAGR numbers from 95% equity compounding ($10K → $3T is not real)
- Don't deploy any strategy as TIER_1_DEPLOY based on current inflated backtests
- Don't use 15m timeframe — too noisy
- Don't use genetic algorithm results — overfit
- Don't generate more strategies until realism is fixed
- Keep `ALLOW_REAL_TRADES=false` until T06/T07 complete
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
  - verified G-01 (realistic sizing) and G-02 (slippage) are already complete:
    - `fixed_notional` mode active: $1,000/trade, max 10% equity
    - slippage: 0.05% per trade, entry delay: 1 bar
    - all metadata visible in outputs (Sizing_Mode, Fixed_Notional_USD, Slippage_Pct, etc.)
  - verified Task 2 (reranking) already complete: 329 candidates reranked with credibility scores, flags, OOS gates
  - verified Task 4 (test matrix) already complete for 5 new pine_new scripts × 3 asset priority tiers
  - updated PROJECT_CONTEXT.md through April 7 (full history Mar 24 → Apr 7)
  - updated all sections: current state, repo structure, bot commands, TV results, execution plan, work log

- **What is going on**
  - G-01 through G-02 are DONE — backtester has realistic sizing + slippage
  - Reranking artifacts exist with credibility scores and promotion gates
  - 5 new fusion scripts ready for first-pass TV testing on Priority 1 assets (BTC, ETH, SOL, AVAX, LINK)
  - Frozen shortlist (Donchian ETH/SUI, CCI LDO/ETH, Donchian AVAX) marked paper-trade only
  - Next steps: run realistic backtests, OOS/walk-forward gate (G-03), then freeze final shortlist (G-05)

- **Current status**
  - G-01 realistic sizing: DONE
  - G-02 slippage/friction: DONE
  - G-04 realism-aware ranking: DONE (329 candidates reranked)
  - G-03 OOS/walk-forward: PENDING
  - G-05 frozen shortlist: DRAFT (5 candidates, paper-trade only)
  - G-06 Pine/export parity: PENDING
  - pine_new scripts: 5 new ready for TV testing
