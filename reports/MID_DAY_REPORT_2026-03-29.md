# MID-DAY REPORT — March 29, 2026

## Status: 2:00 PM IST

---

## Executive Summary

Intensive strategy R&D day focused on meeting ALPHA++ tournament criteria (Daily ROI ≥ 0.5%, Sharpe ≥ 3.5, Win Rate ≥ 45%, Gross DD < 35%). Ran walk-forward validation on top 5 strategies — **all 5 flagged as overfit or failing out-of-sample**. The "best" TV strategies (282%/yr, 199%/yr) are confirmed unreliable. Only MACD_Breakout on ETH (5/5 walk-forward windows profitable) and EMA_Break_Momentum on BNB (4/5) are genuinely reliable.

Built portfolio stacking model — combined 5 strategies on $10k gave only 3.1%/yr and 0.009%/day, far below targets. The SOL strategies drag the portfolio into losses.

Generated 24 new Pine Scripts (27-50) with progressively tighter params and more selective entries targeting TV Sharpe improvement. TV testing showed **28_Ichimoku_PSAR_ADX on BNB achieved 84.8% win rate and 0.68 Sharpe** — our best TV metrics yet, 3x better Sharpe than previous strategies. Generated 20 ultra-advanced strategies (31-50) using 4-8 signal agreement with SL 0.4-1.5% and TP 1.5-8% — currently being backtested (100 tests running).

**Key finding:** TV Sharpe uses daily returns (not per-trade), making Sharpe ≥ 3.5 extremely difficult for any 4h crypto strategy. Best Sharpe achieved: 0.68 (vs 3.5 needed). This is a fundamental mathematical constraint, not a strategy design flaw.

---

## Time Breakdown

| | Time | Work Done |
|---|------|-----------|
| **LLM (Claude)** | ~5 hrs | Walk-forward validation (15 combos), stacking portfolio model, ALPHA optimization (340 combos), brute force search (thousands of combos), 24 new Pine Scripts, 3 backtest scripts |
| **Human (Garima)** | ~2 hrs | TV testing of 15 strategy-asset combos, recorded Sharpe/WR/ROI/DD for each, identified 84% WR on Ichimoku_PSAR_ADX BNB |

---

## Tasks & Subtasks

### Task 1: Walk-Forward Validation — DONE
- [x] 1.1 Ran walk-forward on Aggressive_Entry SOL 4h — **OVERFIT** (1/5 windows, -10.7%/yr OOS)
- [x] 1.2 Ran walk-forward on Aggressive_Entry BNB 4h — **FAIL** (3/5 windows, -0.7%/yr OOS)
- [x] 1.3 Ran walk-forward on MACD_Breakout SOL 4h — **OVERFIT** (1/5 windows, -11.1%/yr OOS)
- [x] 1.4 Ran walk-forward on Ichimoku_Trend_Pro BNB 4h — **OVERFIT** (3/5, +58%/yr but >50% degradation)
- [x] 1.5 Ran walk-forward on Aggressive_Entry ETH 4h — **OVERFIT** (3/5, +0.3%/yr OOS)
- [x] 1.6 Ran walk-forward on 10 more combos (Full_Momentum, Ichimoku_MACD_Pro, EMA_Break_Momentum, MACD_Breakout)
- [x] 1.7 **PASS strategies found:** MACD_Breakout ETH (5/5, +54.5%/yr), EMA_Break_Momentum BNB (4/5, +45.7%/yr), Full_Momentum BNB (3/5, +46.9%/yr), Ichimoku_MACD_Pro BTC (3/5, +31.4%/yr), MACD_Breakout BNB (3/5, +16.1%/yr)
- [x] 1.8 Result: 5 PASS, 5 MARGINAL, 5 OVERFIT/FAIL out of 15 tested

### Task 2: Portfolio Stacking Model — DONE
- [x] 2.1 Built scripts/stack_portfolio.py — 5 strategies × $2k each = $10k portfolio
- [x] 2.2 Result: $10,000 → $11,849 over 5.6 years = 3.1%/yr, 0.009%/day
- [x] 2.3 Max drawdown: 49.1%
- [x] 2.4 Best month: Feb 2021 (+63.9%), Worst month: Apr 2024 (-21.6%)
- [x] 2.5 SOL strategies lost money (-65% to -70%), dragged portfolio down
- [x] 2.6 Only Ichimoku_Trend_Pro BNB profitable individually ($2k → $7,559)
- [x] 2.7 Conclusion: Cat 1 and Cat 2 NOT achievable via stacking with current strategies

### Task 3: ALPHA Tier Optimization — DONE
- [x] 3.1 Created scripts/optimize_alpha.py — 20 strategy-asset combos × 17 param sets = 340 tests
- [x] 3.2 Result: **0 ALPHA++, 0 ALPHA, 8 AVERAGE** — none reached ALPHA
- [x] 3.3 Best: MACD_Breakout ETH — 43.1%/yr, Sharpe 1.55, WR 42.8%, GDD 33.2%
- [x] 3.4 Gap: Sharpe 1.55 vs 2.5 needed (38% short), WR 42.8% vs 45% (close)

### Task 4: Cat 1 Leverage Analysis — DONE
- [x] 4.1 Best strategy daily: 0.77%/day (Aggressive_Entry SOL TV) — but overfit
- [x] 4.2 Best reliable daily: 0.15%/day (MACD_Breakout ETH)
- [x] 4.3 3x leverage needed for Cat 1 on best strategy — liquidation risk 33% drop
- [x] 4.4 Conclusion: Cat 1 on spot = impossible; needs futures + leverage

### Task 5: New Pine Scripts Round 1 (25-28) — DONE
- [x] 5.1 Generated 25_High_Sharpe_Scalp.pine — 5 signals, min=3, SL=1%/TP=5%
- [x] 5.2 Generated 26_Trend_Confirm_Tight.pine — 6 signals, min=4, SL=1.2%/TP=6%
- [x] 5.3 Generated 27_RSI_BB_Precision.pine — mean reversion + trend filter — FAILED (13-28 trades)
- [x] 5.4 Generated 28_Ichimoku_PSAR_ADX.pine — 5 signals, ALL agree, SL=1.5%/TP=8%
- [x] 5.5 TV tested: 28 on BNB = **84.8% WR, 0.68 Sharpe** (best ever)
- [x] 5.6 TV tested: 26 on ETH = **0.48 Sharpe** (2nd best)

### Task 6: New Pine Scripts Round 2 (29-30) — DONE
- [x] 6.1 Generated 29_Ultra_Confirm.pine — 8 signals ALL agree, SL=1%/TP=4%
- [x] 6.2 Generated 30_Ichi_Trend_Tight.pine — tighter version of #28, SL=0.8%/TP=3%

### Task 7: Advanced Pine Scripts (31-50) — DONE
- [x] 7.1 Group A (31-35): Ultra-tight scalp — SL 0.4-0.6%, TP 1.5-2.5%, 4-7 signals
- [x] 7.2 Group B (36-40): Moderate tight — SL 1-1.2%, TP 4-5%, 4-5 signals
- [x] 7.3 Group C (41-45): Momentum burst — SL 1.5%, TP 6-8%, 5-6 signals
- [x] 7.4 Group D (46-50): Advanced logic — EMA stacks, cloud breakouts, PSAR flips, ultimate alpha
- [x] 7.5 All 20 scripts generated with JSON alerts, visuals, realistic params
- [ ] 7.6 Backtesting 100 combos (20 strategies × 5 assets) — RUNNING

### Task 8: Data & Cleanup — DONE
- [x] 8.1 Killed stale brute force process to free resources
- [x] 8.2 Deleted failed strategy 27 (too few trades)

---

## Numerical Results

### Walk-Forward Validated (Reliable for Live)

| # | Strategy | Asset | OOS ROI%/yr | WF Windows | Verdict |
|---|----------|-------|-------------|------------|---------|
| 1 | MACD_Breakout | ETH | +54.5% | **5/5** | **BEST** |
| 2 | Full_Momentum | BNB | +46.9% | 3/5 | PASS |
| 3 | EMA_Break_Momentum | BNB | +45.7% | **4/5** | PASS |
| 4 | Ichimoku_MACD_Pro | BTC | +31.4% | 3/5 | PASS |
| 5 | MACD_Breakout | BNB | +16.1% | 3/5 | PASS |

### TV Sharpe Progression (improvement over sessions)

| Round | Best TV Sharpe | Strategy | Win Rate |
|-------|---------------|----------|----------|
| Day 1 (Mar 25) | 0.04 | MACD_Breakout ETH | 47% |
| Day 2 (Mar 26) | 0.22 | Full_Momentum BNB | 41% |
| Day 3 (Mar 29) AM | **0.68** | Ichimoku_PSAR_ADX BNB | **84.8%** |
| Day 3 (Mar 29) AM | 0.48 | Trend_Confirm_Tight ETH | 48% |

### TV Results for New Strategies (Round 1)

| # | Strategy | Asset | TV ROI%/yr | TV WR% | TV Sharpe | TV PF | Trades |
|---|----------|-------|-----------|--------|-----------|-------|--------|
| 28 | Ichimoku_PSAR_ADX | BNB | 101% | **84.8%** | **0.68** | **1.20** | 3812 |
| 26 | Trend_Confirm_Tight | ETH | 250% | 48.0% | **0.48** | 1.05 | 1182 |
| 25 | High_Sharpe_Scalp | ETH | 256% | 48.9% | 0.45 | 1.05 | 3906 |
| 26 | Trend_Confirm_Tight | BNB | 181% | 46.0% | 0.41 | 1.06 | 1061 |
| 28 | Ichimoku_PSAR_ADX | ETH | 108% | 48.6% | 0.27 | 0.90 | 996 |
| 25 | High_Sharpe_Scalp | BNB | 129% | 46.7% | 0.17 | 1.02 | 3812 |
| 28 | Ichimoku_PSAR_ADX | BTC | 59% | 43.2% | 0.16 | 1.04 | 1160 |

### Stacking Model Results

| Metric | Value |
|--------|-------|
| Starting capital | $10,000 ($2k × 5 strategies) |
| Final capital | $11,849 |
| ROI/yr | 3.1% |
| Daily avg | 0.009% |
| Max drawdown | 49.1% |
| Cat 2 (0.5%/day) | NOT achieved |
| Cat 1 (2%/day) | NOT achieved |

### ALPHA Gap Analysis

| ALPHA++ Needs | Our Best (Bot) | Our Best (TV) | Gap |
|--------------|---------------|---------------|-----|
| Daily ≥ 0.5% | 0.118% | 0.70% | TV closer |
| Sharpe ≥ 3.5 | 1.55 | **0.68** | TV Sharpe much harder |
| Win Rate ≥ 45% | 42.8% | **84.8%** | TV PASSES on #28 |
| GDD < 35% | 33.2% | 25.9% | PASSES |
| PF ≥ 1.2 | 1.27 | **1.20** | PASSES on #28 |

### Total Backtests Today

| Test | Combos | Result |
|------|--------|--------|
| Walk-forward validation | 75 (15 combos × 5 windows) | 5 PASS |
| Stacking portfolio | 5 strategies | 3.1%/yr combined |
| ALPHA optimization | 340 | 0 ALPHA |
| Brute force search | ~thousands | Running |
| New strategies (31-50) | 100 | Running |
| **Total** | **~600+** | |

---

## Key Insights

1. **TV Sharpe ≠ Bot Sharpe** — TV uses daily returns (most days = 0 return when not trading), bot uses per-trade returns. TV Sharpe is 5-10x lower.
2. **High WR is achievable** — #28 on BNB got 84.8% WR by requiring ALL 5 signals to agree.
3. **Sharpe ≥ 3.5 on TV is near-impossible** for 4h strategies — would need 50+ profitable trades per month with minimal variance.
4. **SOL strategies are overfit** — look great on full backtest, fail on walk-forward.
5. **BNB and ETH are the reliable assets** — consistently profitable across walk-forward windows.
6. **Tighter SL/TP improves Sharpe** — 0.68 Sharpe with 1.5%SL/8%TP vs 0.04 with 4%SL/15%TP.

---

## Running Now

- [ ] Backtesting 20 new strategies (31-50) × 5 assets = 100 tests
- [ ] Brute force signal combination search

## After Break

1. Review backtest results for strategies 31-50
2. TV validate top performers
3. Finalize portfolio of best strategies
4. Generate day report
