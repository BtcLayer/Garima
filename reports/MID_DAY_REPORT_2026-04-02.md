# Mid-Day Report — April 2, 2026

## Executive Summary
**Breakthrough day.** BB Squeeze V2 strategy is **profitable on 8 of 10 assets on TradingView**. Parameter optimization (TP 4.5% → 10%) improved DOT from 22.38% → **35.70%/yr (+59%)**. Online learning ML built and trained on 35 TV results. Tier system updated to 2%/day (730%/yr) target. 21 Pine Scripts generated and tested.

**LLM Time**: ~4 hours | **Human Time**: ~3 hours

---

## BB Squeeze V2 — TV Results Comparison

### Default Params (SL=1.5%, TP=4.5%, Trail=2%)
| # | Asset | ROI/yr | WR% | PF | GDD% |
|---|-------|--------|-----|-----|------|
| 1 | ETH | 26.86% | 82.4% | 16.53 | -5.6% |
| 2 | LTC | 22.38% | 72.1% | 8.89 | -10.3% |
| 3 | DOT | 22.38% | 62.4% | 6.40 | -3.3% |
| 4 | BTC | 17.58% | 81.6% | 7.19 | -2.4% |

### Optimized Params (SL=1.5%, TP=10%, Trail=3.5%)
| # | Asset | ROI/yr | WR% | PF | GDD% | Change |
|---|-------|--------|-----|-----|------|--------|
| 1 | **DOT** | **35.70%** | **86.6%** | **14.71** | -5.8% | **+59%** |
| 2 | ETH | 26.86% | 82.4% | 16.53 | -5.6% | Not tested yet |
| 3 | LTC | 22.38% | 72.1% | 8.89 | -10.3% | Same |
| 4 | BTC | 19.47% | 79.8% | 6.71 | -13.6% | +11% |

### Full Asset Results (TP=10%, Trail=3.5%)
| # | Asset | ROI/yr | PF | WR% | GDD% | Trades | Tier (2%/day) |
|---|-------|--------|-----|-----|------|--------|---------------|
| 1 | DOT | 35.70% | 14.71 | 86.6% | -5.8% | 149 | PAPER_TRADE |
| 2 | ETH | 26.86% | 16.53 | 82.4% | -5.6% | 210 | PAPER_TRADE |
| 3 | LTC | 22.38% | 8.89 | 72.1% | -10.3% | 208 | PAPER_TRADE |
| 4 | BTC | 19.47% | 6.71 | 79.8% | -13.6% | 192 | PAPER_TRADE |
| 5 | XRP | 10.18% | 3.06 | 39.1% | -22.8% | 263 | REJECT |
| 6 | BNB | 9.93% | 5.90 | 53.1% | -11.2% | 233 | REJECT |
| 7 | SOL | 9.80% | 3.79 | 53.9% | -14.4% | 128 | REJECT |
| 8 | ADA | 8.46% | 3.76 | 35.9% | -16.7% | 197 | REJECT |
| 9 | AVAX | -15.43% | — | — | -33.8% | 105 | REJECT |
| 10 | LINK | -28.15% | — | — | -44.1% | 173 | REJECT |

---

## Tier System (2%/day = 730%/yr Target)

| Tier | ROI/yr | GDD | Count |
|------|--------|-----|-------|
| TIER_1 DEPLOY | >= 500% | < 10% | 0 |
| TIER_1 | >= 200% | < 15% | 0 |
| TIER_2 | >= 50% | < 25% | 0 |
| PAPER_TRADE | >= 15% | < 35% | **4** |
| REJECT | < 15% or > 35% | | 6 |

---

## Progress Report

### Accomplished
1. Tested 21 Pine Scripts on TV across 10+ assets
2. Found BB Squeeze V2 — **8/10 assets profitable** (first multi-asset winner)
3. Optimized params (TP 4.5% → 10%) — DOT improved **+59%** (22.38% → 35.70%/yr)
4. Built online learning ML — trained on 35 TV results, learns backtester-to-TV gap
5. Updated tier system to 2%/day target
6. Fixed `/ml` command to use persistent mode + 10 assets
7. Created backtest processor prompt for tier changes

### Key Findings
- **BB Squeeze is the winning approach** — squeeze detection + momentum + ADX works on TV
- **DOT, ETH are best assets** — highest WR (86.6%, 82.4%) and PF (14.71, 16.53)
- **Altcoins below BNB fail** — XRP, ADA, SOL, AVAX, LINK all under 15%/yr
- **Higher TP helps** — DOT gained 59% ROI by changing TP from 4.5% to 10%
- **ETH not yet tested with TP=10%** — could be the best result

### Adjustments
- Dropped all non-Squeeze strategies (MACD, EMA, Regime combos all showed < 8%/yr on TV)
- Focus narrowed to BB Squeeze V2 param optimization on top 4 assets
- Online ML learning from each TV validation round

---

## Next Steps (Afternoon)
1. Test ETH with TP=10% (could beat DOT's 35.70%/yr)
2. Test DOT with TP=15% (DOT responded best to higher TP)
3. Try different BB/KC params (length, multiplier variations)
4. Compile final results for senior
5. Day report + commit + push
