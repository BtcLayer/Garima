# Weekly Goal Achievement and Planning

**Week: March 23-30, 2026**
**Project: Garima — Crypto Trading Bot**
**Team: Garima (Intern) + Claude (LLM)**

---

## PART 1: LAST WEEK'S PERFORMANCE (REFLECTION)

---

### Day 0: March 23 — Bot Enhancement & Baseline

- **Owner:** Garima
- **Status:** Complete — 100%

**Work done:**
- Added `/restart`, fixed `/results` and `/stats` (CSV fallback)
- Process tracking in `/status`, `/help` restructured
- Wrapped 6 workers in try/except, removed auto Gemini calls
- Fixed SSH .pem key permissions

**Backtests:** `/backtest ETHUSDT 1h` (31 strats), `/auto 4h` (100 results, 10 assets)

**Baseline numbers:**

| Metric | Value |
|--------|-------|
| Best strategy | EMA_Cloud_Strength (score 44.46) |
| Best avg ROI/yr | 20.8% |
| Assets profitable (4h) | 8/10 |
| Deployment-ready | 0 (all grade C/D) |

**Issues found:**
- LTC and AVAX — no profitable strategy on any timeframe
- NetDD >> GrossDD on all strategies (high profit volatility)
- AI (Claude) unavailability slowed progress
- 0 strategies met deployment criteria

---

### Day 1: March 24 — Audit

- **Owner:** Claude, Garima
- **Status:** Complete — 100%

**Work done:** Full codebase audit by quant systems architect review

**Numbers:**

| Metric | Value |
|--------|-------|
| Audit score | 3.5/10 (prototype grade) |
| Critical issues (P0) | 4 (kill switch, position sizing, circuit breaker, SL/TP monitor) |
| High issues (P1) | 6 (signal server, validation, paper trading, tests, queue, logging) |
| Medium issues (P2) | 6 (walk-forward, short selling, slippage, Docker, Prometheus, migrations) |
| Live execution readiness | DANGEROUS — hardcoded 0.01 qty, no safety controls |

**Issues found:**
- 3 separate webhook implementations in archive, none integrated
- manager.py only 126 lines, hardcoded everything
- CI passes with zero tests (fallback echo)
- File-based signal queue (fragile)
- No kill switch, no circuit breaker

---

### Day 2: March 25 — P0/P1 Implementation + First Backtests

- **Owner:** Claude (code) + Garima (testing, bot commands)
- **Status:** Complete — 100%
- **LLM time:** ~6 hrs | **Human time:** ~3 hrs

**Work done:**
- All P0 safety: kill switch, position sizing (2%/trade), circuit breaker ($500/day), SL/TP monitor (10s)
- All P1 MVP: signal server, Pydantic validation, SQLite queue, structured logging, 51 tests
- P2 partial: walk-forward, short selling, slippage modeling
- First Pine Scripts (5 strategies)
- 4h backtest (200 results), 1h backtest (210 results), 15m started overnight

**Numbers:**

| Metric | Before (Mar 24) | After (Mar 25) |
|--------|-----------------|----------------|
| Audit score | 3.5/10 | 6.5/10 |
| Safety features | 0 | 4 (all P0 done) |
| Unit tests | 0 | 51 |
| Bot commands | ~20 | ~25 |
| Strategies backtested | 100 | 410 |

**Issues found:**
- `/results 4h` returned empty — bot only searched root directory, not `reports/`
- Reports CSVs not on server — had to upload
- 15m backtest extremely slow (217k candles per asset)

---

### Day 3: March 26 — TV Validation + New Indicators

- **Owner:** Garima (TV testing) + Claude (indicators, scripts)
- **Status:** Complete — 100%
- **LLM time:** ~6 hrs | **Human time:** ~4 hrs

**Work done:**
- 7 new indicators (OBV, CCI, Ichimoku, PSAR, MFI, Keltner, Williams %R)
- 12 new strategies (batch_21)
- 20 Pine Scripts generated, tested on TV
- Short selling analysis (2 of 5 strategies benefit)
- 15m officially dropped (all negative)

**Numbers:**

| Metric | Value |
|--------|-------|
| TV strategies tested | 30+ combinations |
| TV-validated profitable | 22 (all 4h) |
| Best TV ROI | Aggressive_Entry SOL 282%/yr |
| New indicators | 7 |
| Short selling useful | 2 of 5 strategies |

**Issues found:**
- **ALL 1h strategies failed on TV** (-98.6% ROI) — min_agreement=3 too strict for 1h noise
- Only exception: Aggressive_Entry on LINK 1h works (58.3% WR)
- 15m all negative — best was -25%/yr
- Old CSVs in reports/ used 0.01% fees (unrealistic) — moved to archive
- Pine Script position sizing was 10% (should be 95%) — fixed

---

### Day 4: March 29 AM — Walk-Forward + Autohunt

- **Owner:** Claude (validation, autohunt) + Garima (TV testing)
- **Status:** Complete — 100%
- **LLM time:** ~5 hrs | **Human time:** ~3 hrs

**Work done:**
- Walk-forward validation on 15 strategy-asset combos
- Portfolio stacking model (5 strategies × $2k each)
- ALPHA optimization (340 combos)
- Autohunt v1 (99,330 combos tested)
- 30 new Pine Scripts (25-55)

**Numbers:**

| Metric | Value |
|--------|-------|
| Walk-forward tested | 15 combos × 5 windows = 75 tests |
| Walk-forward PASS | 5 (MACD_Breakout ETH 5/5 best) |
| Walk-forward FAIL/OVERFIT | 10 (Aggressive_Entry SOL -10.7% OOS) |
| Autohunt combos | 99,330 |
| Autohunt ALPHA found | 0 |
| Stacking portfolio result | $10k → $11,849 (3.1%/yr) — failed |

**Issues found:**
- **Walk-forward killed top strategies:** Aggressive_Entry SOL (282%/yr on TV) scored -10.7%/yr out-of-sample — OVERFIT
- **Autohunt found 0 ALPHA** — targeting wrong criteria (Sharpe-based, not PF-based)
- **Stacking doesn't work** — SOL strategies lost money, dragged portfolio down
- **SOL strategies all overfit** — great on TV backtest, fail on walk-forward

---

### Day 4: March 29 PM — Key Discovery + Param Sweep

- **Owner:** Claude (optimization) + Garima (TV testing, CSV analysis)
- **Status:** Complete — 100%
- **LLM time:** ~5 hrs | **Human time:** ~3 hrs

**Work done:**
- Discovered alert bot uses **PF + WR** for deployment, NOT Sharpe
- Fixed bot fees (0.1% → 0.03% per side = 0.06% round-trip, matches TV)
- Fixed Sharpe to TV-style (daily returns × sqrt(252))
- Param sweep engine with configurable indicator params
- PF optimizer (54,600 backtests)
- 38,372 results from param sweep

**Numbers:**

| Metric | Value |
|--------|-------|
| PF optimizer backtests | 54,600 |
| Param sweep backtests | 576,000 |
| Param sweep results (PF ≥ 1.2) | 38,372 |
| TIER_2_DEPLOY found (param sweep) | 21 |
| Best PF found | 1.82 (PSAR_EMA_ST_ADX_OBV on ADA) |

**Issues found:**
- **Bot Sharpe ≠ TV Sharpe** — bot used per-trade (inflated 2-4), TV uses daily (realistic 0.4-1.8)
- **Bot fees were 3x higher than TV** — 0.2% vs 0.06% round-trip, killing PF
- **Param sweep ADA strategies failed on TV** — bot showed PF 1.82 but TV showed PF 0.97
- **Only ETH strategies reliably match between bot and TV**

---

### Day 5: March 30 — TV-Matched Backtester + Final Strategies

- **Owner:** Claude (backtester fix) + Garima (TV validation, alerts)
- **Status:** Complete — 100%
- **LLM time:** ~4 hrs | **Human time:** ~3 hrs

**Work done:**
- Rewrote backtester to match TV execution exactly (entry at next bar open, compound sizing, exit at SL/TP level)
- Generated 10 TV-first Pine Scripts with TP sweep (4-8%)
- TV validated all strategies
- Improved grading logic (PF + WR + DD + Sharpe + min trades)
- Fixed autohunt with proven combos + TV-matched params

**Numbers:**

| Metric | Value |
|--------|-------|
| Bot PF vs TV PF accuracy | Within 2% (was 50%+ off before) |
| TV strategies tested | 27 combinations |
| TIER_1 found | **2** (tv_04 ETH, 44_PSAR BTC) |
| TIER_2_DEPLOY found | **7** |
| TIER_2_TEST found | **5** |
| Total deployable | **14** |
| Alerts set on TV | **11** |

**Issues found:**
- **Bot backtester was fundamentally different from TV** — entry at close (should be next bar open), fixed capital (should compound), exit at close (should exit at SL/TP level)
- **Trade count low (~300-500)** for 6yr period — Volume_Spike > 2x filter too strict, but loosening it drops PF
- **BNB, SOL strategies fail on TV** even when bot shows TIER_2 — only ETH, ADA, BTC reliable
- **1h timeframe confirmed dead again** — tested with TV-matched backtester, still only PAPER tier

---

## Issues & Bugs Log (Chronological)

| Date | Issue | Impact | Resolution | Status |
|------|-------|--------|-----------|--------|
| Mar 23 | AI unavailability | Slowed work | Manual coding | Resolved |
| Mar 23 | LTC/AVAX no profitable strategy | 2 assets excluded | Dropped from pool | Accepted |
| Mar 24 | No kill switch/safety controls | CRITICAL for live | Implemented P0 Day 2 | Fixed |
| Mar 24 | CI passes with 0 tests | False confidence | Added 51 real tests | Fixed |
| Mar 25 | `/results 4h` empty | Can't view results | Added reports/ scan | Fixed |
| Mar 25 | Reports CSVs missing on server | Bot can't load data | Uploaded via SCP | Fixed |
| Mar 25 | Test suite spamming Telegram | Annoying | Mocked send_telegram() | Fixed |
| Mar 26 | 1h strategies -98.6% on TV | Entire 1h timeframe dead | Dropped 1h (except LINK) | Accepted |
| Mar 26 | 15m all negative | Entire 15m dead | Dropped 15m | Accepted |
| Mar 26 | Old CSVs had 0.01% fees | Inflated ROI numbers | Moved to archive | Fixed |
| Mar 26 | Pine Script sizing 10% | Wrong position size | Changed to 95% | Fixed |
| Mar 29 | Walk-forward: SOL strategies overfit | 282%/yr TV, -10.7% OOS | Dropped SOL for live | Accepted |
| Mar 29 | Autohunt 0 results (99k combos) | Wrong criteria (Sharpe) | Switched to PF-based | Fixed |
| Mar 29 | Bot Sharpe inflated 5-10x | Wrong tier classification | Fixed to daily Sharpe | Fixed |
| Mar 29 | Bot fees 3x higher than TV | PF killed in bot | Fixed to 0.06% RT | Fixed |
| Mar 29 | Param sweep ADA fails on TV | Bot shows 1.82 PF, TV 0.97 | ETH only reliable | Accepted |
| Mar 30 | Bot entry at close, TV at next open | All metrics off | Rewrote backtester | Fixed |
| Mar 30 | Bot fixed capital, TV compounds | ROI mismatch | Fixed compound sizing | Fixed |
| Mar 30 | Bot exit at close, TV at SL level | PF mismatch | Fixed exit logic | Fixed |
| Mar 30 | Low trade count (~300) | Alert bot wants more | Volume filter too strict | Accepted tradeoff |
| Mar 30 | 1h dead with TV-matched backtester | No 1h strategies | 4h only | Accepted |

---

## Numerical Summary — Full Week (March 23-30)

### Backtesting

| Metric | Mar 23 | Mar 24 | Mar 25 | Mar 26 | Mar 29 | Mar 30 | Total |
|--------|--------|--------|--------|--------|--------|--------|-------|
| Backtests run | 100 | 0 | 410 | 285 | 255,000+ | 50,000+ | **500,000+** |
| Pine Scripts | 0 | 0 | 5 | 20 | 36 | 10 | **60+** |
| TV tests | 0 | 0 | 0 | 30+ | 15+ | 27 | **70+** |
| TIER_1 found | 0 | 0 | 0 | 0 | 0 | **2** | **2** |
| TIER_2 found | 0 | 0 | 0 | 0 | 3 | **7** | **9** |
| Deployable total | 0 | 0 | 0 | 0 | 3 | **14** | **14** |

### TV-Validated Strategies (Final — March 30)

| # | Strategy | Asset | TF | ROI%/yr | WR% | PF | Trades | Tier |
|---|----------|-------|----|---------|-----|-----|--------|------|
| 1 | tv_04_TP8 | ETH | 4h | 112.3% | 62.4% | 1.87 | 338 | TIER_1_M |
| 2 | 44_PSAR_Vol_Surge | BTC | 4h | 107.7% | 46.1% | 1.87 | 3151 | TIER_1_M |
| 3 | tv_03_TP6 | ETH | 4h | 109.6% | 52.4% | 1.73 | 339 | TIER_2_D |
| 4 | tv_12_PSAR_EMA_Vol | ADA | 4h | 102.4% | 52.5% | 1.72 | 370 | TIER_2_D |
| 5 | tv_02_TP5 | ETH | 4h | — | — | 1.73 | 367 | TIER_2_D |
| 6 | tv_01_TP4 | ETH | 4h | — | — | 1.73 | 340 | TIER_2_D |
| 7 | tv_04_TP8 | ADA | 4h | — | — | 1.73 | 340 | TIER_2_D |
| 8 | 56_PSAR_Vol_Tight | ETH | 4h | 93.0% | 61.1% | 1.68 | 342 | TIER_2_D |
| 9 | 57_PSAR_Vol_Ultra | ETH | 4h | 69.1% | 63.4% | 1.63 | 161 | TIER_2_D |
| 10 | tv_11_ADA_TP9 | ADA | 4h | 112.1% | 52.3% | 1.50 | 367 | TIER_2_TE |
| 11 | alpha_04_Ichi_PSAR | ETH | 4h | 55.8% | ~55% | 1.56 | 346 | TIER_2_TE |
| 12 | 56_PSAR_Vol_Tight | BTC | 4h | — | 50.8% | 1.51 | 315 | TIER_2_TE |
| 13 | tv_04_TP8 | LINK | 4h | — | 48.9% | 1.25 | 321 | TIER_2_TE |
| 14 | tv_03_TP6 | BTC | 4h | — | — | — | 313 | TIER_2_TE |

### Code Changes

| Category | Count | Details |
|----------|-------|---------|
| New files created | 30+ | Pine Scripts, strategies, scripts, reports |
| Files modified | 10+ | manager.py, telegram_backtest_bot.py, run_strategies_batch.py, logger.py |
| New strategies (batch_22) | 16 | TV-validated alpha strategies |
| New indicators | 7 | OBV, CCI, Ichimoku, PSAR, MFI, Keltner, Williams %R |
| New bot commands | 10+ | /autohunt, /killswitch, /paper, /positions, /closeall, /results TF filter |
| Unit tests | 51 | test_manager, test_signal_server, test_p2_features |
| Server deployments | 20+ | Code updates + restarts |
| Backtester rewrites | 2 | Fee fix (Day 4), TV-match rewrite (Day 5) |

### Time Investment

| | Hours | Work |
|---|-------|------|
| **LLM (Claude)** | ~35 hrs | Code, backtesting, optimization, Pine Scripts, reports, deployments |
| **Human (Garima)** | ~22 hrs | TV validation (70+ tests), alert bot setup, direction, bot commands (Day 0), reviews |
| **Total** | ~57 hrs | |

### Key Metrics Progression

| Metric | Mar 23 | Mar 24 | Mar 25 | Mar 26 | Mar 29 | Mar 30 |
|--------|--------|--------|--------|--------|--------|--------|
| Audit score | — | 3.5 | 6.5 | 6.5 | 6.5 | 6.5 |
| Best ROI%/yr | 20.8% | — | 68.1% | 282% (TV) | 508% (TV) | 112% (TIER_1) |
| Best PF | — | — | 1.42 | 1.34 (TV) | 1.68 (TV) | **1.87** (TV) |
| Deployable | 0 | 0 | 0 | 0 | 3 | **14** |
| TV Sharpe (best) | — | — | — | 0.22 | 1.81 | 0.97 |
| Indicators | 12 | 12 | 12 | 19 | 19 | 19 |
| Tests | 0 | 0 | 51 | 51 | 51 | 51 |
| Pine Scripts | 0 | 0 | 5 | 25 | 55 | **65+** |

---

### Team Collaboration Assessment

- **What worked well:**
  - LLM handling code, backtesting, deployment while human did TV validation
  - Parallel execution: bot autohunt + human TV testing simultaneously
  - Quick iteration: modify Pine Script → TV test → analyze → repeat
  - CSV data sharing for strategy analysis

- **Bottlenecks:**
  - Bot backtester not matching TV (wasted 2 days optimizing wrong metrics — Days 3-4)
  - Server RAM (914MB) too small for parallel processes
  - TradingView manual testing is slow (1 strategy at a time)
  - AI unavailability on Day 0

- **Support needed:**
  - Senior approval for production API key, capital, go-live
  - Server upgrade for running bot + signal server simultaneously

### Data & Code Backup

| What | Where | Status |
|------|-------|--------|
| Source code | GitHub (branch: Trading_bot) | Committed |
| Strategies (batch 1-22) | `strategies/` directory | 258 strategies |
| Pine Scripts | `pine/` directory (65+ files) | Local |
| Backtest results | Server: `/home/ubuntu/Garima/reports/` | param_sweep (38,372 rows), optimize_pf |
| Historical data | `storage/historical_data/` (30 parquet files, ~80MB) | Local + server |
| Bot state | Server: `storage/` | manager_state.json, autohunt files |
| Reports | `reports/` directory | 20+ reports |
| Server | AWS EC2 ap-south-1 (15.207.152.119) | Running 24/7 |
| Deploy key | `deploy/harsh_server/` (.gitignored) | Local only |
| Combo results | `combo_strategy_results.csv` (191 strategies) | Local |

---

## PART 2: UPCOMING WEEK PLANNING (FORWARD-LOOKING)

### Goal 1: Scale to 20+ Deployable Strategies

- **Goal:** Increase deployable strategies from 14 to 20+
- **Why this matters:** More strategies = more diversification = more consistent daily returns
- **Owner:** Garima (TV validation), Claude (strategy generation)
- **Measurable outcome:** 20+ strategies at TIER_2_DEPLOY or above
- **Deadline:** April 4
- **Key milestones:**
  - Apr 1: Generate more TP variants for ADA, BTC, LINK
  - Apr 2: Test different signal combos with custom indicator params
  - Apr 3: TV validation + alert setup
  - Apr 4: All deployed
- **Potential obstacles:** Only ETH reliably matches bot→TV. Other assets unpredictable.
- **Contingency:** Focus on more ETH variants with different TP/SL combos

### Goal 2: Paper Trade All Deployed Strategies

- **Goal:** Run all 14 deployed strategies in paper trade mode for 1 week
- **Why this matters:** Confirms live signal flow works before real money
- **Owner:** Garima
- **Measurable outcome:** 7 days of paper trades with PnL tracking
- **Deadline:** April 7

### Goal 3: Get Senior Approvals

- **Goal:** Secure approvals for live deployment
- **Owner:** Garima
- **Items pending:**
  1. Production Binance API key
  2. Trading capital amount + risk limits
  3. Go-live approval (3 safety layers)
  4. Server upgrade (914MB → 2GB+)
  5. Secret rotation
  6. Domain + SSL for webhook
- **Deadline:** April 4

### Goal 4: Improve Bot Strategy Generation

- **Goal:** Bot autonomously finds TIER_2+ strategies without manual intervention
- **Owner:** Claude
- **Measurable outcome:** `/autohunt` finds 5+ TIER_2 strategies per run
- **Deadline:** April 2
- **Required:** TV-matched backtester (done), proven combo sweep (done), correct tier criteria (done)

### Coordination Needs

- **Dependencies on senior:** API key, capital approval, server upgrade
- **External dependencies:** TradingView alert uptime, Binance API availability
- **Communication plan:** Daily reports in Telegram, weekly report every Monday

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| TV alerts delayed/missed | Medium | High | Monitor delivery, add redundancy |
| Strategy overfitting | Medium | High | Walk-forward validated top strategies |
| Bot vs TV mismatch | Low (fixed) | High | TV-matched backtester deployed |
| Server downtime | Low | High | Systemd auto-restart |
| API key compromised | Low | Critical | IP whitelist, no withdrawal |
| Market regime change | High | Medium | Diversify ETH, ADA, BTC |
| Low trade count (~300/6yr) | High | Medium | Accept tradeoff — quality > quantity |
