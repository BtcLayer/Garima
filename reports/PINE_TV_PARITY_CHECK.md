# G-06: Pine / TradingView Parity Check

## Purpose
Verify that each shortlisted strategy's Pine Script on TradingView produces results consistent with the backtester engine output.

## Frozen Shortlist Strategies

| # | Strategy | Asset | TF | Pine Script File | TV Tested? | Parity Status |
|---|----------|-------|----|-----------------|------------|---------------|
| 1 | Donchian Trend | ETH | 4h | `pine/tv_first_35_Donchian_Trend.pine` | YES (Apr 3-4) | CONSISTENT — both show TIER_1 |
| 2 | Donchian Trend | SUI | 4h | `pine/tv_first_35_Donchian_Trend.pine` | YES (Apr 3-4) | CONSISTENT — both show TIER_1 |
| 3 | CCI Trend | LDO | 4h | `pine/tv_first_40_CCI_Trend.pine` | YES (Apr 3-4) | CONSISTENT — both show TIER_1 |
| 4 | CCI Trend | ETH | 4h | `pine/tv_first_40_CCI_Trend.pine` | YES (Apr 3-4) | CONSISTENT — both show TIER_1 |
| 5 | Donchian Trend | AVAX | 4h | `pine/tv_first_35_Donchian_Trend.pine` | YES (Apr 3-4) | CONSISTENT — both show TIER_1 |

## Parity Check Method

1. **Same parameters**: SL=1.5%, TP=12%, Trail=4%, ADX>20, volume filter
2. **Same timeframe**: 4h
3. **Same asset**: checked on same BINANCE pair
4. **Both** backtester and TV show the strategy as profitable with similar tier assignment

## Known Differences (Expected)

| Factor | Backtester | TradingView | Impact |
|--------|-----------|-------------|--------|
| Position sizing | Fixed $1K (realistic mode) | 95% equity (default) | TV shows higher absolute returns |
| Slippage | 0.05% modeled | 0% (none) | Backtester slightly more conservative |
| Fee | 0.03% per side | 0.1% per trade | TV charges more |
| Entry timing | Next bar open | Next bar open | Same |
| Compounding | None (fixed notional) | Full (95% equity) | TV compounds, backtester doesn't |

## Conclusion
All 5 frozen shortlist strategies have been validated on TradingView. The **relative ranking** is consistent between backtester and TV — Donchian and CCI are top performers in both systems. Absolute return numbers differ due to position sizing, but the **direction and tier assignment match**.

## Important Caveat
The backtester numbers (with 95% equity) were inflated. After switching to fixed-notional mode, the realistic returns are lower but the ranking order remains the same. This means:
- TV backtester is good for **relative comparison** (which strategy is better)
- Neither TV nor our backtester with 95% equity gives **realistic absolute returns**
- Paper trading with realistic sizing is the only way to get actual expected returns

## Status: G-06 COMPLETE
Parity verified for all 5 frozen shortlist candidates. No Pine/engine mismatch found.
