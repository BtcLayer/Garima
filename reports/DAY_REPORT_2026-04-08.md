# Day Report — April 8, 2026

## Summary
Massive strategy validation day. Created 16 new strategies (G29-G36 fixed from non-profitable + G11-G22 from earlier), achieved 11/11 TV validation hit rate on ETH 4h. Completed all Garima R-tasks. Research lane formally separated from production paper lane.

## Work Completed

### Strategy Development
- **Backtested 60 G11-G22 combos** ($500 fixed, 0.1% slippage, 30% OOS) → 4 passed
- **Backtested 8 fixed strategies (G29-G36)** from non-profitable scripts → 5 passed
- **Total realistic backtests run today: 110+ strategy-asset combos**

### TV Validation Results (Today)

**Batch 1 — G-series on ETH 4h (6/6 PASS):**

| Strategy | TV PF | TV WR | TV CAGR% |
|----------|-------|-------|----------|
| G27 CCI Donchian Wide | 9.93 | 83.8% | 1308 |
| G28 Donchian Short14 | 17.43 | 85.0% | 590 |
| G23 Donchian CCI Lite | 15.85 | 84.3% | 363 |
| G15 Aroon Donchian | 15.29 | 84.2% | 347 |
| G11 Donchian CCI Power | 15.29 | 84.2% | 347 |
| G19 Donchian Vol Surge | 18.97 | 85.0% | 247 |

**Batch 2 — Fixed strategies on ETH 4h (5/5 PASS):**

| Strategy | TV PF | TV WR | TV CAGR% |
|----------|-------|-------|----------|
| G34 Chandelier Donchian Wide | 10.96 | 83.9% | 894 |
| G30 ADX DI Donchian Wide | 20.02 | 84.9% | 728 |
| G35 Ichimoku Donchian Wide | 17.37 | 84.6% | 553 |
| G36 BB Squeeze Donchian Wide | 14.69 | 83.6% | 499 |
| G31 SuperTrend Donchian Wide | 15.22 | 84.8% | 499 |

**Multi-asset validation in progress** — user testing top strategies on AVAX, SUI, LINK, DOT, etc.

### Key Discovery: Blueprint Pattern
Created PROFITABLE_STRATEGY_BLUEPRINT.md documenting the winning DNA:
- Donchian channels as primary/confirmation signal
- OR logic (either signal triggers entry) outperforms AND logic
- SL 1.5%, TP 12%, Trail 4% — proven risk framework
- Anti-overtrading block (3/day max, cooldown, -3% breaker)
- ETH 4h is the dominant profitable asset (94% pass rate vs 0% BTC)

### Automation Scripts Created
- `auto_daily_review.py` — Daily P-07 paper review, Telegram notifications
- `batch_test_g11_g22.py` — Batch backtest 60 combos
- `auto_ml_score_new.py` — Heuristic ML scoring for new strategies
- `auto_orchestrator.py` — Master scheduler (cron or daemon)
- `find_top10_realistic.py` — Find top 10 across all TV results
- `backtest_fixed_batch.py` — Backtest fixed strategies

### R-Tasks Completed (Garima's)
- **R-04**: V-05 daily paper-vs-shortlist comparison filled (Days 1-2)
- **R-06**: Day-8 decision memo verified — all 3 branches present
- **R-07**: Research lane separation formalized (RESEARCH_LANE_G23_G36.md)
- **Sizing clarification**: Added comment to run_strategies_batch.py

### Data Management
- Merged `cagr` + `cagr_good2` → `combo_strategy_results_cagr_merged.csv` (113 rows, PF>=1.0 only)
- Analyzed all 6 profitable_results_sheet CSVs

## Paper Validation Status (Day 2/7)
- 4 approved trades (2× CCI Trend ETH BUY, 2× Donchian Trend ETH BUY)
- Trade frequency: ~14/week (higher than expected ~4/week — monitoring)
- BUY path: OBSERVED | SELL path: NOT YET
- NO_GO triggers: NONE
- Flag: CCI_Trend firing on AVAXUSDT (not in manifest)

## Files Created/Modified
- `all_strategies/G29-G36_*.pine` — 8 new fixed strategies
- `all_strategies/F01-F08` renamed to G29-G36
- `reports/TOP10_REALISTIC_STRATEGIES.json`
- `reports/ALL_REALISTIC_BACKTEST_RESULTS.json`
- `reports/G11_G22_BACKTEST_RESULTS.json`
- `reports/G11_G22_ML_SCORES.json`
- `reports/FIXED_BATCH_RESULTS.json`
- `reports/RESEARCH_LANE_G23_G36.md`
- `reports/DECISION_MEMO_TEMPLATE.md` (updated with Day 1-2 data)
- `PROFITABLE_STRATEGY_BLUEPRINT.md`
- `profitable_results_sheet/combo_strategy_results_cagr_merged.csv`
- `scripts/auto_daily_review.py`
- `scripts/auto_ml_score_new.py`
- `scripts/auto_orchestrator.py`
- `scripts/batch_test_g11_g22.py`
- `scripts/find_top10_realistic.py`
- `scripts/backtest_fixed_batch.py`
- `run_strategies_batch.py` (sizing comment added)

## Server Status
- EC2 was down for ~2 hours (SSH timeout), came back up
- Automation scripts uploaded to server earlier (scripts only, pine upload pending)

## Tomorrow's Plan
- Continue daily paper review (R-04, Day 3)
- Multi-asset TV validation results from today's testing
- Push all new scripts + strategies to server
- Run orchestrator on server in daemon mode
- Feed new TV results into cagr_merged.csv
