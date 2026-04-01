# Mid-Day Report — April 1, 2026

## Executive Summary
Discovered that Harsh's backtester uses a theoretical `signal × bar_return` model that doesn't produce real trades — TV validation of all 14 ALPHA++ strategies showed -95% to -100% loss. Rewrote our backtester to match tournament logic, found 29 strategies at 1%+/day in that model, but TV validation confirmed these don't translate to real trading either. Pivoted to ML-based approach — using archive ensemble strategies as training data for ML to learn which entries actually win vs lose.

**LLM Time**: ~5 hours | **Human Time**: ~4 hours

---

## Morning Session

### Task 1: Read Tournament Backtester (Completed)
Read `strategy_tournament.py` line by line. Found critical difference:
- **Tournament**: `signal × bar_return` — no actual trades, just math
- **TradingView**: actual position open/close with fees
- This is why tournament shows +0.3%/day but TV shows -95%

### Task 2: TV Validation on 15m (User — Completed)
User validated Harsh's top 14 strategies on TradingView 15m:
- **0 of 14 profitable** — all showed -90% to -100% loss
- Confirmed: tournament model results don't transfer to TV

### Task 3: TV Validation of Our Scripts (User — Completed)
User tested 5 TV-first Pine Scripts on 15m:
- All 5 UNPROFITABLE (-70% to -100%)
- **Decision: abandon 15m, focus on 4h only**

### Task 4: ML Approaches Tried (6 different methods)

| # | Approach | Best Result | Status |
|---|----------|-------------|--------|
| 1 | Basic ML (RF+GBM) | 0.178%/day ADA | Completed |
| 2 | Neural Network + Sequence features + BTC lead | 0.101%/day ADA | Completed |
| 3 | Rule-based binary features | 0.089%/day ADA | Completed |
| 4 | Archive enhanced (squeeze + mean reversion) | 0.048%/day BTC | Completed |
| 5 | Scored labels (quality score 0-100) | Running | In Progress |
| 6 | ML Improve Winners (filter fake-profit strategies) | Running | In Progress |
| 7 | Full Ensemble (16 signals + 9 combos + ML filter) | Running | In Progress |

### Task 5: Level-Based Pine Scripts (3 created)
Created Pine Scripts matching the logic that showed 1%+ in backtester:
- OBV Momentum (always-in, level-based)
- Lookback Momentum (close > close[9])
- Supertrend Level (band direction)
All include 5 anti-overtrading rules: max 3 trades/day, cooldown, circuit breaker, gap, ADX+ATR filter

---

## Currently Running on Server

| Process | What | Status |
|---------|------|--------|
| ML Improve Winners | Takes OBV/Lookback/Supertrend signals → ML learns which entries actually win → filters bad trades | Running |
| ML Full Ensemble | 16 signals + 9 archive combos → ML filter for realistic wins | Running |
| Auto-notify | Sends Telegram message when new results found | Running |
| Dashboard | Live at server/dashboard/ | Active |
| Telegram Bot | All commands | Active |

---

## Key Findings Today

1. **Tournament backtester is theoretical** — `signal × return` model doesn't produce real trades
2. **15m timeframe doesn't work** on TV for any strategy type
3. **ML ceiling on 4h with basic approach: ~0.1%/day** — regardless of feature engineering
4. **Archive ensemble combos** are the most promising — 9 pre-built combos with proven profit history
5. **ML as filter** (not signal generator) is the right approach — keep the winning signals, remove losing entries

---

## Afternoon Plan

1. Wait for ML Improve Winners + Full Ensemble results
2. Take best ML-filtered strategies, test on our backtester
3. Generate Pine Scripts only for those that pass our backtest
4. Give to user for TV validation
5. End-of-day report + git commit
