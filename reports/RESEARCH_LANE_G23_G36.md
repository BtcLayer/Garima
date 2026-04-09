# Research Lane: G23-G36 Strategy Wave

**Status:** RESEARCH ONLY - NOT in production paper lane
**Created:** April 8, 2026

---

## Separation Rule

The current production paper lane contains ONLY:
- CCI Trend ETHUSDT 4h (hash: d4ae43d256c0)
- Donchian Trend ETHUSDT 4h (hash: 686adb63d527)

G23-G36 strategies must NOT:
- be added to approved_strategies.json
- be added to top10_strategies.json
- affect the Apr 14 Day-8 decision
- be deployed to the webhook execution pipeline

Apr 14 decision scope rule:
- The Apr 14 verdict is for the current frozen ETHUSDT 4h paper pair only.
- G23-G36 results are evidence for future research prioritization only.
- Even very strong TV results in this lane must not widen the Apr 14 production decision.

---

## Research Strategies - TV Validation Status

### Batch 1 (G23-G28) - TV Validated on ETH

| Strategy | Asset | TV PF | TV WR | TV CAGR% | TV Status |
|----------|-------|-------|-------|----------|-----------|
| G27 CCI Donchian Wide | ETH 4h | 9.93 | 83.8% | 1308 | PASS |
| G28 Donchian Short14 | ETH 4h | 17.43 | 85.0% | 590 | PASS |
| G23 Donchian CCI Lite | ETH 4h | 15.85 | 84.3% | 363 | PASS |
| G25 CCI Pure HighTP | ETH 4h | 15.65 | 83.9% | - | PASS |
| G26 Donchian ADX Aggro | ETH 4h | 17.79 | 85.2% | - | PASS |
| G15 Aroon Donchian | ETH 4h | 15.29 | 84.2% | 347 | PASS |
| G11 Donchian CCI Power | ETH 4h | 15.29 | 84.2% | 347 | PASS |
| G19 Donchian Vol Surge | ETH 4h | 18.97 | 85.0% | 247 | PASS |

### Batch 2 (G29-G36) - TV Validated on ETH

| Strategy | Asset | TV PF | TV WR | TV CAGR% | TV Status |
|----------|-------|-------|-------|----------|-----------|
| G34 Chandelier Donchian Wide | ETH 4h | 10.96 | 83.9% | 894 | PASS |
| G30 ADX DI Donchian Wide | ETH 4h | 20.02 | 84.9% | 728 | PASS |
| G35 Ichimoku Donchian Wide | ETH 4h | 17.37 | 84.6% | 553 | PASS |
| G36 BB Squeeze Donchian Wide | ETH 4h | 14.69 | 83.6% | 499 | PASS |
| G31 SuperTrend Donchian Wide | ETH 4h | 15.22 | 84.8% | 499 | PASS |

### Multi-Asset Validation - IN PROGRESS
User is currently testing top strategies on AVAX, SUI, LINK, DOT, SOL, BTC, etc.

---

## Promotion Path (After Apr 14)

1. Complete multi-asset TV validation
2. Run realistic backtest ($500, 0.1% slippage, 30% OOS) on passing combos
3. If Day-8 verdict = READY_FOR_TINY_CAPITAL or PAPER_ONLY, select at most one research winner for a NEW isolated paper window
4. Do not widen the current manifest from this lane directly
5. Never mix research strategies into an active paper validation window

---

## Top 3 for TV Parity Check (R-07)

Per task R-07, the top 3 research strategies for formal TV parity:

1. **G27 CCI Donchian Wide** - Best overall (PF 9.93, CAGR 1308%)
2. **G30 ADX DI Donchian Wide** - Highest PF (20.02)
3. **G19 Donchian Vol Surge** - Highest signal PF (18.97)

TV parity check = compare our backtester output vs TradingView output on same asset/timeframe.

### Caveat
All TV results use 95% equity compounding. Real deployment will use $500 fixed per trade. Realistic OOS results are 3-6% total ROI, not 500-1300% CAGR.

### Current Interpretation
- This lane can produce exciting winners.
- That does not make it part of the current launch decision.
- The right use of this lane is TV parity, realistic rerun, and later separate paper-window admission.
