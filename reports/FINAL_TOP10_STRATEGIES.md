
# FINAL STRATEGIES FOR LIVE TRADING

Updated: 2026-03-26
All TV-validated on Binance data | 0.1% commission | 4h timeframe (except #2)

## Top 14 TV-Validated Strategies

| # | Script | Asset | TF | TV ROI%/yr | TV Win% | TV PF | Type |
|---|--------|-------|----|-----------|---------|-------|------|
| 1 | 10_Aggressive_Entry | SOL | 4h | 282% | 57.7% | 1.34 | Original |
| 2 | 10_Aggressive_Entry | LINK | 1h | 205% | 58.3% | 1.40 | Original |
| 3 | 07_MACD_Breakout | SOL | 4h | 199% | 48.2% | 1.17 | Original |
| 4 | 10_Aggressive_Entry | ADA | 4h | 164% | 56.4% | 1.33 | Original |
| 5 | 10_Aggressive_Entry | BNB | 4h | 164% | 55.2% | 1.33 | Original |
| 6 | 22_Ichimoku_Trend_Pro | BNB | 4h | 136% | 41.0% | 1.05 | New (Ichimoku) |
| 7 | 23_Ichimoku_MACD_Pro | BNB | 4h | 133% | 38.8% | 1.04 | New (Ichimoku) |
| 8 | 21_Full_Momentum | BNB | 4h | 132% | 41.2% | 1.04 | New (PSAR+Ichimoku) |
| 9 | 10_Aggressive_Entry | ETH | 4h | 131% | 57.0% | 1.39 | Original |
| 10 | 03_EMA_Break_Momentum | SOL | 4h | 127% | 39.4% | 1.01 | Original |
| 11 | 22_Ichimoku_Trend_Pro | ETH | 4h | 95% | 40.6% | 1.02 | New |
| 12 | 07_MACD_Breakout | LINK | 4h | 86% | 46.6% | 1.06 | Original |
| 13 | 21_Full_Momentum | ETH | 4h | 85% | 40.5% | 1.01 | New |
| 14 | 03_EMA_Break_Momentum | BNB | 4h | 79% | 40.1% | 1.03 | Original |

## Also Profitable (lower priority)

| # | Script | Asset | TF | TV ROI%/yr | TV Win% |
|---|--------|-------|----|-----------|---------|
| 15 | 22_Ichimoku_Trend_Pro | BTC | 4h | 74% | 40.1% |
| 16 | 21_Full_Momentum | BTC | 4h | 72% | 38.6% |
| 17 | 23_Ichimoku_MACD_Pro | BTC | 4h | 65% | 37.0% |
| 18 | 07_MACD_Breakout | ETH | 4h | 61% | 47.0% |
| 19 | 24_Keltner_Breakout | BTC | 4h | 57% | 40.6% |
| 20 | 03_EMA_Break_Momentum | BTC | 4h | 52% | 39.2% |
| 21 | 07_MACD_Breakout | BTC | 4h | 45% | 41.5% |
| 22 | 24_Keltner_Breakout | ETH | 4h | 19% | 41.9% |

## Portfolio Summary

- **Total TV-validated profitable:** 22 strategy-asset combos
- **Scripts needed:** 7 Pine Scripts
- **Assets:** SOL (3), BNB (5), ETH (5), LINK (2), ADA (1), BTC (5)
- **Timeframes:** 4h (21), 1h (1)
- **Avg ROI%/yr (top 14):** 144%
- **Best performer:** Aggressive_Entry on SOL 4h — 282%/yr

## Scripts Reference

| Script | SL | TP | TS | Indicators |
|--------|----|----|-----|-----------|
| 10_Aggressive_Entry | 4% | 15% | 0.5% | Breakout_20, Volume_Spike, MACD_Cross, ADX_Trend |
| 07_MACD_Breakout | 4% | 15% | 1.5% | MACD_Cross, Breakout_20, Volume_Spike, ADX_Trend |
| 03_EMA_Break_Momentum | 2% | 15% | 2.5% | EMA_Cross, Breakout_20, MACD_Cross, ADX_Trend |
| 22_Ichimoku_Trend_Pro | 2% | 12% | 2% | Ichimoku_Bull, EMA_Cross, ADX_Trend, OBV_Rising |
| 23_Ichimoku_MACD_Pro | 2% | 15% | 2% | Ichimoku_Bull, MACD_Cross, OBV_Rising, Volume_Spike |
| 21_Full_Momentum | 2.5% | 15% | 2.5% | PSAR_Bull, Ichimoku_Bull, MACD_Cross, ADX_Trend, OBV_Rising |
| 24_Keltner_Breakout | 1.5% | 10% | 1.5% | Keltner_Lower, RSI_Oversold, Volume_Spike, OBV_Rising |

## Failed on TV (DO NOT USE)

- All 1h strategies except Aggressive_Entry LINK: -98.6% ROI
- Keltner_Breakout on BNB: -12%
- All 15m strategies: negative
- CCI, Williams %R, MFI as primary signals: all negative

## Risk Warnings
- Expect 40-60% of TV backtest ROI in live trading
- Realistic live expectation: 50-90%/yr from top strategies
- Paper trade 2 weeks before real money
- Start small ($100-500)
- Circuit breaker: $500/day loss limit
