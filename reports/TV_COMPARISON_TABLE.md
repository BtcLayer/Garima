# TradingView vs Bot — Comparison Table

**Criteria used:** ROI >= 40%/yr, GrossDD < 60%, WinRate > 20%, Trades > 50, PF > 1.0
**Passing:** 29 out of 410 strategies

Instructions: Run each Pine Script on TradingView with the specified Asset + Timeframe. Fill in the TV columns. Discard if Bot vs TV ROI differs by >20%.

## Top 20 Candidates

| # | Pine Script | Asset | TF | Bot ROI%/yr | Bot Trades | Bot Win% | Bot GDD% | Bot NDD% | Cap@NDD | TV ROI% | TV Trades | TV Win% | Match? |
|---|------------|-------|-----|------------|-----------|---------|---------|---------|---------|---------|-----------|---------|--------|
| 1 | 03_EMA_Break_Momentum | BNB | 4h | 65.3 | 413 | 32.2 | 50.2 | 1.5 | $9,846 | | | | |
| 2 | 07_MACD_Breakout | BNB | 4h | 62.9 | 430 | 40.5 | 42.2 | 21.3 | $7,869 | | | | |
| 3 | 02_Volume_Stochastic_MACD_ADX | ETH | 4h | 56.6 | 226 | 26.1 | 44.1 | 2.0 | $9,796 | | | | |
| 4 | 08_ADX_Volume_Break | BNB | 4h | 55.6 | 568 | 25.4 | 55.8 | 3.1 | $9,694 | | | | |
| 5 | 09_Breakout_Cluster | ADA | 4h | 53.5 | 364 | 25.3 | 41.8 | 0.1 | $9,988 | | | | |
| 6 | 10_Aggressive_Entry | LINK | 4h | 52.9 | 562 | 25.6 | 40.4 | 1.0 | $9,896 | | | | |
| 7 | 14_MACD_Trend_Strength | BNB | 4h | 52.8 | 400 | 34.3 | 57.2 | 1.5 | $9,846 | | | | |
| 8 | 09_Breakout_Cluster | ETH | 1h | 49.0 | 996 | 31.9 | 48.9 | 0.0 | $10,000 | | | | |
| 9 | 10_Aggressive_Entry | ETH | 4h | 48.3 | 507 | 29.0 | 32.1 | 1.8 | $9,817 | | | | |
| 10 | 20_Stochastic_Trend_MACD | ETH | 4h | 47.6 | 531 | 23.0 | 43.4 | 0.9 | $9,910 | | | | |
| 11 | 07_MACD_Breakout | ETH | 4h | 47.5 | 450 | 36.9 | 43.0 | 1.8 | $9,820 | | | | |
| 12 | 02_Volume_Stochastic_MACD_ADX | BNB | 4h | 45.1 | 201 | 24.9 | 39.9 | 0.0 | $10,000 | | | | |
| 13 | 10_Aggressive_Entry | BNB | 4h | 45.1 | 504 | 29.0 | 44.1 | 3.3 | $9,670 | | | | |

## Strategies NOT in Pine Scripts (need Pine Script or test via bot)

| # | Strategy | Asset | TF | Bot ROI%/yr | Trades | Win% | GDD% | NDD% | Note |
|---|----------|-------|-----|------------|--------|------|------|------|------|
| 14 | High_Momentum_Entry | ETH | 1h | 68.1 | 690 | 32.0 | 39.9 | 0.0 | No Pine Script yet |
| 15 | Breakout_ADX_Pro | ETH | 1h | 68.1 | 690 | 32.0 | 39.9 | 0.0 | No Pine Script yet |
| 16 | Volume_Trend_ADX | BNB | 4h | 47.6 | 332 | 31.3 | 57.2 | 1.5 | No Pine Script yet |

## How to Test

1. Open TradingView → Chart → select Asset (e.g. BNBUSDT) + Timeframe (e.g. 4h)
2. Pine Editor → paste script from pine/ folder
3. Add to Chart → Strategy Tester tab shows results
4. Record: Net Profit %, Total Trades, Win Rate in the TV columns above
5. Mark "Match?" as YES if TV ROI is within 20% of Bot ROI

## Selection Target

Pick **10 strategies** from the "Match? = YES" rows ensuring:
- At least 3 different assets
- At least 2 different timeframes
- No more than 3 strategies on same asset
- All have GrossDD < 60% and WinRate > 20%
