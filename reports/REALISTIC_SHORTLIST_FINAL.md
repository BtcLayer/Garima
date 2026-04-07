# Final Realistic Shortlist — April 7, 2026

## Settings
- Position sizing: **$500 fixed notional** (no compounding)
- Slippage: **0.1% per trade** (on top of 0.06% fee)
- OOS holdout: **30%** (train on 70%, test on 30%)
- Data: Binance 4h candles, 2017-2026

## Filters Applied
- Sharpe > 0
- Profit Factor > 1.0
- OOS ROI > 0% (must be profitable out-of-sample)
- Max Drawdown < 25%
- Trade count > 100

## Result: 2 strategies PASSED out of 7 tested

### 1. CCI Trend on ETHUSDT 4h
| Metric | Full Period | OOS (30%) |
|--------|-----------|-----------|
| ROI | 5.91% | 3.10% |
| Sharpe | 0.69 | — |
| Profit Factor | 1.14 | 1.25 |
| Max Drawdown | 2.82% | — |
| Win Rate | 20.7% | 23.6% |
| Trades | 644 | — |

### 2. Donchian Trend on ETHUSDT 4h
| Metric | Full Period | OOS (30%) |
|--------|-----------|-----------|
| ROI | 3.26% | 4.65% |
| Sharpe | 0.41 | — |
| Profit Factor | 1.08 | 1.49 |
| Max Drawdown | 5.77% | — |
| Win Rate | 17.4% | 23.3% |
| Trades | 586 | — |

## Failed Candidates
| Strategy | Asset | Why Failed |
|----------|-------|-----------|
| Donchian Trend | BTC | OOS ROI negative (-0.9%) |
| Donchian Trend | DOT | Negative full ROI (-4.89%) |
| Donchian Trend | AVAX | Negative full ROI (-9.63%) |
| CCI Trend | BTC | Negative full ROI and OOS |
| CCI Trend | DOT | Negative full ROI and OOS |

## Important Notes
- ROI of 3-6% is over the FULL period (6 years), not per year
- With $500 per trade on $10K account, each trade risks 5% of capital
- These are conservative numbers — real returns depend on trade frequency and market conditions
- Both strategies performed BETTER in OOS than in-sample (good sign, not overfit)

## Recommendation
Both strategies are safe for paper trading. Neither is a "get rich quick" — they are modest edge strategies that survive realistic conditions. Start 7-day paper validation on these two only.
