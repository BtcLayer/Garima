# Day Report — March 29, 2026

## Executive Summary

Full-stack strategy optimization day. Three major breakthroughs: (1) Discovered that **Profit Factor + Win Rate** — not Sharpe — determines alert bot deployment tier, (2) Fixed bot calculations to match TradingView exactly (fees 0.1% → 0.06% round-trip, daily Sharpe instead of per-trade), (3) Launched massive parallel optimization — 150,000+ backtests running on local + server sweeping indicator parameters AND SL/TP/TS combinations.

**Current deployable strategies: 3** (56_PSAR_Volume_Tight ETH = TIER_2_DEPLOY, 57_PSAR_Volume_Ultra ETH = TIER_2_TEST, 44_PSAR_Volume_Surge BTC = TIER_2_TEST). Walk-forward validation confirmed only 5 of 15 strategies are reliable. Autohunt v1 tested 99,330 combos finding 0 ALPHA (wrong criteria). Autohunt v2 deployed with correct PF-based criteria. 30 Pine Scripts generated (25-55), 8 modified for TIER_2 params. Counter/short trades tested — weak on crypto (best PF 1.51 on ADA shorts). Two massive optimizations running overnight — PF optimizer (54,600 backtests) + param sweep engine (100,000+ backtests with variable indicator parameters).

**From combo_strategy_results.csv — 191 strategies tested on TradingView:**
- TIER_1_DEPLOY: 1 (Volume_Stoch_MACD_ADX SOL)
- TIER_2_DEPLOY: 4 (56_PSAR, AI Supertrend, AI SOLUSDT Alpha variants)
- TIER_2_TEST: 3 (44_PSAR BTC, 57_PSAR ETH, Volume_Stoch ETH)
- PAPER_TRADE: 7 (10_Aggressive on 5 assets, EMA_RSI_Quant, EMA+RSI Optimized)
- IGNORE/WEAK: 40+
- UNPROFITABLE: 100+

---

## Time Breakdown

| | Time | Work Done |
|---|------|-----------|
| **LLM (Claude)** | ~10 hrs | Walk-forward (15 combos), stacking model, ALPHA optimization (340 combos), 30 Pine Scripts, autohunt v1 (99,330 combos) + v2 with checkpoints, batch_22 (16 strategies), TV-matched fee/Sharpe fix, PF optimizer (54,600 backtests running), param sweep engine (100,000+ running), counter trades (576 tests), 8 strategy modifications, tier classification in bot, 7 deployments |
| **Human (Garima)** | ~6 hrs | TV validation of 30+ combos, identified PF as key metric (not Sharpe), tested modified strategies, managed alert bot, compiled combo_strategy_results.csv with 191 entries, directed strategy modifications |

---

## Tasks & Subtasks

### Task 1: Walk-Forward Validation — DONE
- [x] 1.1 Tested top 5 TV strategies — **0/5 pass** (Aggressive_Entry SOL/BNB/ETH overfit, Ichimoku_Trend_Pro BNB degraded)
- [x] 1.2 Tested 10 more combos — **5 PASS**: MACD_Breakout ETH (5/5, +54.5%/yr OOS), EMA_Break_Momentum BNB (4/5, +45.7%/yr), Full_Momentum BNB (3/5, +46.9%/yr), Ichimoku_MACD_Pro BTC (3/5, +31.4%/yr), MACD_Breakout BNB (3/5, +16.1%/yr)
- [x] 1.3 Total: 75 walk-forward tests (15 combos × 5 windows)

### Task 2: Portfolio Stacking Model — DONE
- [x] 2.1 5 strategies × $2k each = $10k portfolio
- [x] 2.2 Result: $10,000 → $11,849 over 5.6yr = 3.1%/yr, 0.009%/day
- [x] 2.3 Only Ichimoku_Trend_Pro BNB profitable ($2k → $7,559)
- [x] 2.4 Cat 1 and Cat 2 NOT achievable via stacking

### Task 3: ALPHA Optimization (Old Criteria) — DONE
- [x] 3.1 Tested 340 param combos targeting Sharpe ≥ 2.5, WR ≥ 45%
- [x] 3.2 Result: 0 ALPHA, 0 ALPHA++ — Sharpe ≥ 2.5 on TV is unreachable
- [x] 3.3 Best: MACD_Breakout ETH — Sharpe 1.55, WR 42.8%, PF 1.27

### Task 4: Pine Scripts Generation — DONE
- [x] 4.1 Scripts 25-28: High Sharpe Scalp, Trend Confirm Tight, RSI BB Precision (failed), Ichimoku PSAR ADX
- [x] 4.2 Scripts 29-30: Ultra Confirm (8 signals), Ichi Trend Tight
- [x] 4.3 Scripts 31-50: 20 advanced strategies (Groups A-D)
- [x] 4.4 Scripts 51-55: WR-optimized variants (Cloud Momentum v2, PSAR Volume v2, All Trend Align, Safe Trend Entry)
- [x] 4.5 Scripts 56-60: PSAR variants (Tight, Ultra, Relaxed, Trend Flow, 1h version)
- [x] 4.6 Total: 36 Pine Scripts generated (25-60)

### Task 5: Autohunt v1 — DONE
- [x] 5.1 Built `/autohunt` command with checkpoints, pause/resume
- [x] 5.2 Tested 99,330 signal combinations
- [x] 5.3 Result: 0 ALPHA/ALPHA++ — was targeting wrong criteria (Sharpe-based)

### Task 6: Key Discovery — Alert Bot Uses PF, Not Sharpe — DONE
- [x] 6.1 Analyzed combo_strategy_results.csv (191 strategies)
- [x] 6.2 Found: TIER_1 = PF ≥ 2.0 + WR ≥ 50%, TIER_2 = PF ≥ 1.6 + WR ≥ 50%
- [x] 6.3 56_PSAR_Volume_Tight already TIER_2_DEPLOY (PF 1.68, WR 61.1%)
- [x] 6.4 Updated autohunt v2 with PF-based criteria

### Task 7: TV Calculation Matching — DONE
- [x] 7.1 Fixed FEE: 0.1% → 0.03% per side (0.06% round-trip, matches TV)
- [x] 7.2 Fixed Sharpe: per-trade → daily returns × sqrt(252) (matches TV)
- [x] 7.3 Deployed to server

### Task 8: Strategy Modifications for TIER_2 — DONE
- [x] 8.1 Modified 10_Aggressive_Entry: SL 4%→1%, TP 15%→3%, added PSAR+MA50+OBV
- [x] 8.2 Modified 44_PSAR_Volume_Surge: SL 1.5%→1%, TP 6%→3%, volume 2x→1.2x
- [x] 8.3 Modified 38_Cloud_Momentum: SL 1.2%→1%, TP 5%→3%
- [x] 8.4 Modified 51_Cloud_Momentum_v2: SL 2%→1%, TP unchanged
- [x] 8.5 Modified 28_Ichimoku_PSAR_ADX: SL 1.5%→1%, TP 6%→3%
- [x] 8.6 Modified 57_PSAR_Volume_Ultra: SL 0.8%→1%, TP 2%→2.5%
- [x] 8.7 Modified 54_All_Trend_Align: SL 1.5%→1%
- [x] 8.8 Modified 07_MACD_Breakout: SL 4%→1%, TP 15%→3%

### Task 9: Counter/Short Trades — DONE
- [x] 9.1 Tested 4 strategies × 6 assets × 6 param sets = 576 backtests
- [x] 9.2 Result: 2 PAPER_TRADE (ADA shorts PF 1.51), 38 AVERAGE
- [x] 9.3 Conclusion: Shorts weak on crypto (long-term upward bias)

### Task 10: Massive Optimization (Running Overnight) — IN PROGRESS
- [x] 10.1 Built scripts/optimize_pf.py — 910 SL/TP/TS params × 60 combos = 54,600 backtests
- [x] 10.2 Built scripts/param_sweep_engine.py — variable indicator params + SL/TP/TS = 100,000+ backtests
- [ ] 10.3 PF Optimizer running on local + server
- [ ] 10.4 Param Sweep running on local + server
- [ ] 10.5 Results expected in ~2-3 hours

### Task 11: Bot Improvements — DONE
- [x] 11.1 Added tier classification (TIER_1/TIER_2_DEPLOY/TIER_2_TEST/PAPER_TRADE/AVERAGE/REJECT) to `/elite` and `/results`
- [x] 11.2 Built `/autohunt` v1 + v2 with PF-based criteria
- [x] 11.3 Added checkpoints (autohunt_checkpoint.json, autohunt_results.json)
- [x] 11.4 Added auto-pause on command, resume after
- [x] 11.5 Created batch_22.py (16 TV-validated strategies)
- [x] 11.6 Fixed Sharpe calculation to TV-style daily
- [x] 11.7 Fixed fee to 0.06% round-trip
- [x] 11.8 Deployed 7 updates to server

### Task 12: Reports — DONE
- [x] 12.1 DAY_PLAN_2026-03-29.md
- [x] 12.2 MID_DAY_REPORT_2026-03-29.md
- [x] 12.3 DAY_REPORT_2026-03-29.md — this report

---

## Numerical Results

### combo_strategy_results.csv — Full Breakdown (191 strategies)

**By Deployment Status:**

| Status | Count | Best Strategy | Best PF | Best WR |
|--------|-------|--------------|---------|---------|
| TIER_1_DEPLOY | 1 | Volume_Stoch_MACD_ADX SOL 4h | 5.92 | 52.6% |
| VERY_GOOD / TIER_2_DEPLOY | 5 | 56_PSAR_Volume_Tight ETH 4h | 1.68 | 61.1% |
| GOOD / TIER_2_TEST | 3 | 44_PSAR_Volume_Surge BTC 4h | 1.44 | 51.6% |
| MARGINAL / PAPER_TRADE | 10 | 10_Aggressive_Entry LINK 1h | 1.40 | 58.3% |
| WEAK / IGNORE | 50+ | Various | <1.1 | <45% |
| UNPROFITABLE | 100+ | — | <1.0 | — |

**By Performance Grade:**

| Grade | Count | Criteria Met |
|-------|-------|-------------|
| EXCEPTIONAL | 1 | PF ≥ 5.0, WR > 50% |
| EXCELLENT | 1 | PF ≥ 1.8, Sharpe ≥ 0.75 |
| VERY_GOOD | 5 | PF ≥ 1.6, WR > 50% |
| GOOD | 3 | PF ≥ 1.4, WR > 50% |
| MARGINAL | 10 | PF ≥ 1.2, WR > 45% |
| WEAK | 50+ | PF 1.0-1.1 |
| UNPROFITABLE | 100+ | PF < 1.0 |

### Top 10 from combo_strategy_results.csv

| # | Strategy | Asset | TF | ROI%/yr | WR% | PF | Sharpe | GDD% | Trades | Status |
|---|----------|-------|----|---------|-----|-----|--------|------|--------|--------|
| 1 | 28 Ichimoku PSAR ADX | ETH | 4h | 212% | 49.2% | 1.08 | 0.46 | 40.1% | 3700 | IGNORE |
| 2 | 26 Trend Confirm Tight | ETH | 4h | 185% | 48.9% | 1.07 | 0.41 | 41.5% | 3496 | IGNORE |
| 3 | 44 PSAR Volume Surge | BNB | 4h | 166% | 47.9% | 1.08 | 0.46 | 39.2% | 3293 | IGNORE |
| 4 | **10 Aggressive Entry** | **BNB** | **4h** | **164%** | **55.2%** | **1.33** | **0.95** | **35.5%** | **1063** | **PAPER_TRADE** |
| 5 | 28 Ichimoku PSAR ADX | BNB | 4h | 160% | 48.4% | 1.08 | 0.49 | 40.4% | 3609 | IGNORE |
| 6 | **10 Aggressive Entry** | **LINK** | **1h** | **205%** | **58.3%** | **1.40** | **1.13** | **19.3%** | **999** | **PAPER_TRADE** |
| 7 | **10 Aggressive Entry** | **ADA** | **4h** | **164%** | **56.4%** | **1.33** | **0.81** | **21.3%** | **1060** | **PAPER_TRADE** |
| 8 | **10 Aggressive Entry** | **SOL** | **4h** | **282%** | **57.7%** | **1.34** | **1.13** | **62.7%** | **822** | **PAPER_TRADE** |
| 9 | **10 Aggressive Entry** | **ETH** | **4h** | **131%** | **57.0%** | **1.39** | **1.11** | **15.6%** | **1175** | **PAPER_TRADE** |
| 10 | **56 PSAR Volume Tight** | **ETH** | **4h** | **93%** | **61.1%** | **1.68** | **1.16** | **17.7%** | **342** | **TIER_2_DEPLOY** |

### Strategies Ready for Live Deployment

| # | Pine Script | Asset | TF | PF | WR% | GDD% | Trades | Alert Bot Status |
|---|------------|-------|----|-----|-----|------|--------|-----------------|
| 1 | `56_PSAR_Volume_Tight.pine` | ETH | 4h | **1.68** | **61.1%** | 17.7% | 342 | **TIER_2_DEPLOY** |
| 2 | `57_PSAR_Volume_Ultra.pine` | ETH | 4h | **1.54** | **61.5%** | 39.7% | 161 | **TIER_2_TEST** |
| 3 | `44_PSAR_Volume_Surge.pine` | BTC | 4h | **1.44** | **51.6%** | 38.0% | 310 | **TIER_2_TEST** |

### TV Sharpe Progression (across all sessions)

| Session | Best TV Sharpe | Strategy | Best PF |
|---------|---------------|----------|---------|
| Mar 25 | 0.04 | MACD_Breakout ETH | 1.05 |
| Mar 26 | 0.22 | Full_Momentum BNB | 1.04 |
| Mar 29 AM | 0.68 | Ichimoku_PSAR_ADX BNB | 1.20 |
| Mar 29 PM | **1.81** | PSAR_Volume_Surge ETH | **1.29** |
| Mar 29 (56) | **1.16** | PSAR_Volume_Tight ETH | **1.68** ← TIER_2 |

### Walk-Forward Validated (Reliable for Live)

| # | Strategy | Asset | OOS ROI%/yr | Windows | Verdict |
|---|----------|-------|-------------|---------|---------|
| 1 | MACD_Breakout | ETH | +54.5% | **5/5** | BEST |
| 2 | Full_Momentum | BNB | +46.9% | 3/5 | PASS |
| 3 | EMA_Break_Momentum | BNB | +45.7% | **4/5** | PASS |
| 4 | Ichimoku_MACD_Pro | BTC | +31.4% | 3/5 | PASS |
| 5 | MACD_Breakout | BNB | +16.1% | 3/5 | PASS |

### Total Backtests Today

| Test | Combos | Result |
|------|--------|--------|
| Walk-forward validation | 75 | 5 PASS |
| Stacking portfolio | 5 | 3.1%/yr combined |
| ALPHA optimization | 340 | 0 ALPHA |
| Batch 31-50 test | 90 | 0 ALPHA, best Sharpe 4.01 |
| Autohunt v1 | 99,330 | 0 ALPHA (wrong criteria) |
| Counter/short trades | 576 | 2 PAPER_TRADE |
| TV-matched recalculation | 60 | 5 PAPER_TRADE |
| PF Optimizer | 54,600 | **RUNNING** |
| Param Sweep | 100,000+ | **RUNNING** |
| **Total** | **~255,000+** | **3 deployable** |

---

## Key Discoveries

1. **Alert bot uses PF + WR for deployment, NOT Sharpe** — PF ≥ 1.6 + WR ≥ 50% = TIER_2_DEPLOY
2. **Our bot had 3x higher fees than TV** (0.2% vs 0.06% round-trip) — killed PF. Now fixed.
3. **TV Sharpe uses daily returns** including non-trading days — fundamentally different from per-trade. Now fixed.
4. **ADA is underexplored** — showed PF 1.45 with WR 48% (closest to TIER_2 in bot tests)
5. **Aggressive_Entry on 5 assets** all got PAPER_TRADE — PF 1.33-1.40, needs 1.6+ for TIER_2
6. **Counter/short trades** don't work well on crypto (long-term upward bias)
7. **Walk-forward kills SOL strategies** — 282%/yr on TV but -10.7%/yr out-of-sample

## Running Overnight

| Process | Location | Backtests | ETA |
|---------|----------|-----------|-----|
| PF Optimizer | Local + Server | 54,600 × 2 | ~1.5 hrs |
| Param Sweep | Local + Server | 100,000+ × 2 | ~2.5 hrs |

Results will include every SL/TP/TS combo AND indicator parameter variation that hits TIER_2+.

## Files Created/Modified Today

| Action | Count | Files |
|--------|-------|-------|
| Pine Scripts created | 36 | pine/25-60 |
| Pine Scripts modified | 8 | pine/10, 07, 28, 38, 44, 51, 54, 57 |
| Strategies created | 16 | strategies/batch_22.py |
| Scripts created | 6 | optimize_pf.py, param_sweep_engine.py, brute_force_alpha.py, optimize_alpha.py, optimize_near_alpha.py, auto_alpha_hunter.py |
| Bot updates | 7 | autohunt, tier classification, TV-matched calcs |
| Reports | 3 | DAY_PLAN, MID_DAY, DAY_REPORT |
| Total deployments | 7 | Server code updates |
