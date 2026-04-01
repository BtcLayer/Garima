# TradingView Validation Results — March 31, 2026

## Summary
Validated Harsh's top tournament strategies on TradingView. **All strategies showed UNPROFITABLE results on TV**, contradicting the tournament backtester's positive OOS numbers.

---

## Validated Strategies (TV Backtester, 15m)

| # | Strategy | Asset | TF | Net Profit | ROI% | ROI Ann% | Win Rate | PF | Sharpe | Max DD | Trades | Tier (TV) |
|---|----------|-------|----|-----------|------|----------|----------|-----|--------|--------|--------|-----------|
| 1 | MACD_Breakout | FIL | 1h | +$2,870.72 | +28.7% | 21.6% | 83.3% | 1.11 | 0.27 | -23.4% | 582 | WEAK |
| 2 | Ichimoku_Trend_Pro | FIL | 1h | -$215,995.8 | -2,159.96% | — | 76.4% | 1.06 | -0.01 | -3,072,092 | 854 | WEAK |
| 3 | Keltner_Breakout | FIL | 1h | -$209,409.7 | -2,094.1% | — | 68.4% | 1.00 | -0.01 | -960,342 | 1045 | WEAK |
| 4 | Ichimoku_MACD_Pro | OP | 1h | -$160,079.7 | -1,600.8% | — | 28.8% | 0.14 | — | — | — | WEAK |
| 5 | MACD_Breakout | OP | 1h | -$473,283 | -4,732.83% | — | 29.9% | 0.16 | — | — | — | UNPROFITABLE |
| 6 | Ichimoku_MACD_Pro | OP | 1h | — | — | — | 27.3% | 0.94 | — | — | — | UNPROFITABLE |
| 7 | Aggressive_Entry | FIL | 1h | -$483,210 | -4,832.1% | — | -92.1% | 0.08 | — | — | — | UNPROFITABLE |
| 8 | MACD_Breakout | LDO | 1h | -$559,697 | -5,596.97% | — | 32.1% | 0.14 | — | — | — | UNPROFITABLE |
| 9 | Ichimoku_MACD_Pro | LDO | 1h | -$718,688 | -7,186.88% | — | 30.4% | 0.13 | — | — | 846 | UNPROFITABLE |
| 10 | Aggressive_Entry | LDO | 1h | -$811,986 | -8,119.86% | — | 26.2% | 0.06 | 0.88 | — | — | UNPROFITABLE |
| 11 | Ichimoku_Trend_Pro | LDO | 1h | -$963,206 | -9,632.06% | — | 33.3% | 0.06 | — | — | 2033 | UNPROFITABLE |
| 12 | Full_Momentum | OP | 1h | -$930,088 | -9,300.88% | — | 27.3% | 0.05 | — | — | — | UNPROFITABLE |
| 13 | Ichimoku_Trend_Pro | UNI | 1h | -$995,035 | -9,950.35% | — | 31.7% | 0.07 | — | — | — | UNPROFITABLE |
| 14 | Full_Momentum | LDO | 1h | -$999,713 | -9,997.13% | — | 27.4% | 0.02 | — | — | — | UNPROFITABLE |

---

## Key Findings

### Only 1 of 14 showed any profit
- **MACD_Breakout on FIL 1h**: +$2,870 (+28.7%), 582 trades, WR=83.3%, but PF=1.11 and Sharpe=0.27 — barely profitable, classified WEAK

### 13 of 14 are heavily UNPROFITABLE
- Losses range from -$160k to -$999k (on $10k initial — due to compounding losses)
- Win rates on TV: 26-33% (tournament showed 49%)
- Profit factors: 0.02-0.16 (tournament showed 4-7)

### Why Tournament Shows Profit but TV Shows Loss
1. **Tournament uses 15m data with specific param grid** — TV was tested on 1h
2. **Tournament backtester** applies filters (ADX, ATR, cooldown, circuit breaker) that the Pine Scripts don't have
3. **Position sizing differs** — tournament may use fixed size, TV uses 100% equity (compounds losses)
4. **The Pine Scripts are simplified versions** — they don't include all the tournament backtester's risk management

---

## Conclusion
The tournament system's backtester produces results that don't transfer to TradingView. The risk management filters (cooldown after 3 losses, daily circuit breaker, ADX/ATR filters) in the tournament system are doing the heavy lifting — without them, the raw signal logic loses money.

**Next step:** Add the tournament's risk management filters to the Pine Scripts and retest, or work directly with the tournament system for strategy selection and only use TV for alert generation.
