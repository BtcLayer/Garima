# Day Report — March 31, 2026

## Executive Summary
Today's focus was finding strategies that deliver 1%+ per day ROI. Tested 8 different approaches across our backtester — all failed to match TradingView results. Discovered 3 fundamental flaws in our backtester (level signals vs crossovers, fixed SL/TP vs signal exits, long-only vs long+short) and rewrote the entire engine. Testing Harsh's top 14 ALPHA/ALPHA++ strategies from the tournament system for validation and deployment.

**LLM Time**: ~6 hours | **Human Time**: ~5 hours

---

## Harsh's Top 14 Strategies (Testing/Validating)

These are from the tournament backtester (8501 dashboard), ranked by OOS ROI/day:

| # | Symbol | Strategy | OOS ROI/day | IS ROI/day | WR% | OOS GDD | Tier |
|---|--------|----------|-------------|-----------|-----|---------|------|
| 1 | FILUSDT | Ichimoku_Trend_Pro | **0.303%** | 0.988% | 49.4% | -13.8% | ALPHA++ |
| 2 | FILUSDT | Keltner_Breakout | **0.302%** | 0.997% | 49.4% | -12.5% | ALPHA++ |
| 3 | FILUSDT | Aggressive_Entry | **0.294%** | 1.008% | 49.4% | -16.3% | ALPHA++ |
| 4 | OPUSDT | Ichimoku_MACD_Pro | **0.272%** | 1.021% | 49.0% | -17.6% | ALPHA++ |
| 5 | FILUSDT | Full_Momentum | **0.272%** | 0.750% | 48.5% | -13.3% | ALPHA |
| 6 | OPUSDT | MACD_Breakout | **0.270%** | 1.055% | 49.0% | -14.5% | ALPHA++ |
| 7 | UNIUSDT | Aggressive_Entry | **0.268%** | 0.950% | 49.6% | -11.3% | ALPHA |
| 8 | FILUSDT | Hybrid_SMC | **0.267%** | 0.879% | 48.4% | -15.1% | ALPHA++ |
| 9 | LDOUSDT | Ichimoku_Trend_Pro | **0.266%** | 1.528% | 50.1% | -14.3% | ALPHA++ |
| 10 | OPUSDT | Full_Momentum | **0.266%** | 1.014% | 48.9% | -16.7% | ALPHA++ |
| 11 | LDOUSDT | MACD_Breakout | **0.264%** | 1.403% | 49.8% | -13.5% | ALPHA++ |
| 12 | LDOUSDT | Full_Momentum | **0.264%** | 1.351% | 49.7% | -15.1% | ALPHA++ |
| 13 | LDOUSDT | Aggressive_Entry | **0.260%** | 1.561% | 50.2% | -15.7% | ALPHA++ |
| 14 | UNIUSDT | Ichimoku_Trend_Pro | **0.256%** | 0.937% | 49.5% | -18.9% | ALPHA++ |

**Top assets:** FILUSDT (5 strategies), LDOUSDT (4), OPUSDT (3), UNIUSDT (2)
**Top strategies:** Ichimoku_Trend_Pro (3 assets), Aggressive_Entry (3), Full_Momentum (3)

---

## Approaches Tested Today

| # | Approach | Best ROI/day | Outcome |
|---|----------|-------------|---------|
| 1 | Short selling (bearish) | 0.201% | Below target |
| 2 | Recent data only (2024+) | 0.142% | Confirms old data inflates |
| 3 | Long + Short combined | 0.163% | More trades, lower ROI |
| 4 | Fast indicators (EMA5/13, RSI7) | 0.303% | SOL vol-filtered |
| 5 | Volatility filter | 0.303% | SOL PSAR+EMA+ST |
| 6 | ML Scanner (RF + GBM) | 0.178% | ADA GBM, OOS validated |
| 7 | Strategy Generator (5 methods) | Deployed | Bot command /generate |
| 8 | Genetic Algorithm | 2.993% (fake) | **Failed TV validation** — all 3 scripts UNPROFITABLE on TV |

---

## Critical Discovery: Backtester Flaws

### 3 Fundamental Problems Found

**1. Level signals vs Crossover signals**
- Our signals fired every bar (EMA8 > EMA21 = ON for 500 bars)
- Working strategies fire once on crossover (1 bar only)
- Inflated our trade counts by 10-50x

**2. Fixed SL/TP vs Signal-based exits**
- Our exits: rigid 1.5% SL, 8% TP regardless of market
- Working strategies: exit when signal reverses (adaptive to market)

**3. Long-only vs Long+Short with flipping**
- We only traded long
- Working strategies instantly flip long→short on reversal, never miss a move

### Fix Applied
Rewrote `run_strategies_batch.py`:
- All 19 signals now use crossover detection
- Added `LONG_EXIT_FUNCTIONS` — signal reversal exits for each signal
- Added `SHORT_ENTRY_FUNCTIONS` — bearish crossovers
- `run_backtest()` supports long+short with instant position flipping
- Fee changed to 0.1% (matching working strategies)

### Result After Fix
Tested 3 proven strategies (Ichimoku, Keltner, Aggressive) on all assets — all showed negative returns on our backtester. This confirms our backtester still differs from the tournament system. The tournament system's backtester is the source of truth.

---

## Genetic Algorithm — Failed Experiment

- Built genetic algorithm: 100 strategies × 50 generations, breeding + mutation
- Gen 1 showed 984%/day — obviously fake (compound sizing artifact)
- Added OOS validation + GDD<30% cap — still showed 2.99%/day
- **TV validation: all 3 generated Pine Scripts were UNPROFITABLE (-12% to -65%)**
- Root cause: genetic algo optimized for our backtester's quirks, not real market behavior
- Killed the process, cleared results

---

## Infrastructure Built Today

| Component | Status |
|-----------|--------|
| ML Pipeline (src/ml_strategy.py) | Deployed, 7 results |
| Genetic Algorithm (src/genetic_strategy.py) | Built, failed TV validation |
| Streamlit Dashboard (9 tabs) | Live at server:8502 |
| /ml bot command | Active |
| /evolve bot command | Active |
| /generate bot command | Active |
| Pine Script Gen (dashboard) | 10 pre-built scripts |
| Monte Carlo Simulation | Active in dashboard |
| Parameter Heatmap | Active in dashboard |
| Backtester rewrite (crossover + L/S) | Deployed |
| Tournament strategy names cleaned | 42 unique names |

---

## Progress Report

### Accomplished
1. Tested 8 strategy approaches — identified ceiling at ~0.3%/day for our backtester
2. Built ML pipeline with walk-forward OOS validation
3. Built and ran genetic algorithm (50 generations, 100 population)
4. TV-validated genetic results — caught fake results, saved from bad deployment
5. Discovered and fixed 3 fundamental backtester flaws
6. Built advanced dashboard with 9 tabs including Pine Script generator, Monte Carlo, heatmap
7. Analyzed tournament system (8501) — identified top 14 strategies with real OOS results
8. Cleaned 42 strategy names on tournament dashboard

### Adjustments to Plan
- **Dropped genetic algorithm** — produces fake results that fail TV validation
- **Shifted to tournament system strategies** — these have real OOS validation
- **Backtester rewrite** — crossovers + signal exits + L/S flipping, but still doesn't match tournament results
- **Accepted honest numbers** — real OOS ROI is 0.25-0.30%/day, not 1%+

---

## Key Lessons

1. **Any strategy that shows > 1%/day on a backtester is almost certainly overfit** — TV validation always brings it down
2. **Crossover signals vs level signals** is the single biggest difference between working and non-working strategies
3. **Signal-based exits** (exit on reversal) beat fixed SL/TP exits every time
4. **Long+Short with flipping** doubles opportunities and prevents missing reversals
5. **The tournament backtester and our backtester produce different results** for the same strategy — need to align or use one system only

---

## Open Items

1. Validate top 14 tournament strategies on TradingView
2. Generate Pine Scripts for all 14 for TV alerts
3. Align our backtester with tournament system or use tournament system only
4. Test on testnet (not real money)
5. Git commit all changes
