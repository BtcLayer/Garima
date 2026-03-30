# COMPLETE STRATEGY HISTORY — All Days, All Parameters, All Metrics

Generated: 2026-03-29 EOD

---

## Day 0: March 24 — Audit Only

No strategies tested. Codebase audit performed.
- Audit score: 3.5/10 (prototype grade)
- 16 priority items identified (P0/P1/P2)
- Backtester had bugs: trailing stop not tracking peak, SL/TP checked at close only, fees only on exit

---

## Day 1: March 25

**Backtester:** FEE=0.1% per side (0.2% round-trip) | Initial=$10,000 | Data=6yr (2020-2026) | 0.1% commission on entry+exit

### Auto 4h — Top 10 (server optimized SL/TP/TS)

| # | Strategy | Asset | TF | ROI%/yr | Daily% | WR% | PF | Sharpe | GrossDD% | NetDD% | Cap@NDD | Trades | SL | TP | TS | min_ag | Indicators | TV Status |
|---|----------|-------|----|---------|--------|-----|-----|--------|----------|--------|---------|--------|----|----|-----|--------|-----------|-----------|
| 1 | VWAP_Momentum_Pro | SOL | 4h | 68.9 | 0.189 | 30.1 | 1.08 | 0.95 | 63.3 | 50.6 | $4,941 | 670 | 1.5% | 9% | 1.5% | 2 | VWAP, EMA_Cross, MACD_Cross, Volume_Spike | IGNORE |
| 2 | EMA_Break_Momentum | BNB | 4h | 65.3 | 0.179 | 32.2 | 1.26 | 0.14 | 50.2 | 1.5 | $9,846 | 413 | 2% | 15% | 2.5% | 2 | EMA_Cross, Breakout_20, MACD_Cross, ADX_Trend | IGNORE |
| 3 | MACD_Breakout | BNB | 4h | 62.9 | 0.172 | 40.5 | 1.42 | 0.18 | 42.2 | 21.3 | $7,869 | 430 | 4% | 15% | 1.5% | 2 | MACD_Cross, Breakout_20, Volume_Spike, ADX_Trend | IGNORE |
| 4 | Volume_Stochastic_MACD_ADX | ETH | 4h | 56.6 | 0.155 | 26.1 | 1.26 | 0.32 | 44.1 | 2.0 | $9,796 | 226 | 2% | 12% | 2% | 4 | Volume_Spike, Stochastic, MACD_Cross, ADX_Trend, Trend_MA50, Supertrend | TIER_2_TEST |
| 5 | ADX_Volume_Break | BNB | 4h | 55.6 | 0.152 | 25.4 | 1.23 | — | 55.8 | 3.1 | $9,694 | 568 | 2% | 12% | 2% | 2 | ADX_Trend, Volume_Spike, Breakout_20, EMA_Cross | IGNORE |
| 6 | Breakout_Cluster | ADA | 4h | 53.5 | 0.147 | 25.3 | 1.21 | — | 41.8 | 0.1 | $9,988 | 364 | 2.5% | 15% | 1.5% | 2 | Breakout_20, Volume_Spike, EMA_Cross, MACD_Cross | IGNORE |
| 7 | Aggressive_Entry | LINK | 4h | 52.9 | 0.145 | 25.6 | 1.25 | — | 40.4 | 1.0 | $9,896 | 562 | 4% | 15% | 0.5% | 2 | Breakout_20, Volume_Spike, MACD_Cross, ADX_Trend | IGNORE |
| 8 | MACD_Trend_Strength | BNB | 4h | 52.8 | 0.145 | 34.2 | 1.19 | — | 57.2 | 1.5 | $9,846 | 400 | 1.8% | 10% | 1.8% | 3 | MACD_Cross, Trend_MA50, ADX_Trend, EMA_Cross, Volume_Spike | IGNORE |
| 9 | High_Profit_Trade | ETH | 4h | 53.2 | 0.146 | 27.8 | — | — | 66.7 | 0.9 | $9,910 | 299 | 2.5% | 15% | 2.5% | 4 | EMA_Cross, MACD_Cross, ADX_Trend, Supertrend, VWAP, Trend_MA50 | IGNORE |
| 10 | Aggressive_Entry | ETH | 4h | 48.3 | 0.132 | 29.0 | 1.33 | — | 32.0 | 1.8 | $9,817 | 507 | 4% | 15% | 0.5% | 2 | Breakout_20, Volume_Spike, MACD_Cross, ADX_Trend | PAPER_TRADE |

### Auto 1h — Top 5 (server optimized)

| # | Strategy | Asset | TF | ROI%/yr | Daily% | WR% | PF | Sharpe | GrossDD% | NetDD% | Cap@NDD | Trades | SL | TP | TS | min_ag | Indicators |
|---|----------|-------|----|---------|--------|-----|-----|--------|----------|--------|---------|--------|----|----|-----|--------|-----------|
| 1 | High_Momentum_Entry | ETH | 1h | 68.1 | 0.187 | 32.0 | 1.23 | — | 39.9 | 0.0 | $10,000 | 690 | 1.5% | 15% | 1.5% | 3 | EMA_Cross, MACD_Cross, Volume_Spike, ADX_Trend, Breakout_20 |
| 2 | Breakout_ADX_Pro | ETH | 1h | 68.1 | 0.187 | 32.0 | 1.23 | — | 39.9 | 0.0 | $10,000 | 690 | 1.5% | 15% | 1.5% | 3 | Breakout_20, ADX_Trend, Volume_Spike, EMA_Cross, MACD_Cross |
| 3 | Trend_All_Confirm | BNB | 1h | 76.2 | 0.209 | 26.4 | 1.16 | — | 64.3 | 3.6 | $9,636 | 413 | 5% | 15% | 3% | 3 | Trend_MA50, EMA_Cross, ADX_Trend, Supertrend, MACD_Cross |
| 4 | Golden_Cross_Pro | BNB | 1h | 64.5 | 0.177 | 31.3 | — | — | 69.0 | 0.5 | $9,953 | — | 1.5% | 9% | 1.5% | 2 | EMA_Cross, MACD_Cross, ADX_Trend, Trend_MA50 |
| 5 | EMA_Break_Momentum | BNB | 1h | 57.4 | 0.157 | 35.4 | — | — | 69.3 | 0.6 | $9,944 | — | 2% | 15% | 2.5% | 2 | EMA_Cross, Breakout_20, MACD_Cross, ADX_Trend |

### Walk-Forward Validation (5 windows per strategy)

| Strategy | Asset | W1 ROI% | W2 ROI% | W3 ROI% | W4 ROI% | W5 ROI% | Avg OOS | Consistency | Verdict |
|----------|-------|---------|---------|---------|---------|---------|---------|-------------|---------|
| Aggressive_Entry | SOL 4h | -27.4 | -13.9 | -28.9 | +25.1 | -8.7 | -10.7% | 1/5 | OVERFIT |
| Aggressive_Entry | BNB 4h | -8.5 | +5.8 | -18.9 | +8.4 | +9.5 | -0.7% | 3/5 | FAIL |
| MACD_Breakout | SOL 4h | -14.5 | -36.9 | -19.9 | +25.2 | -9.3 | -11.1% | 1/5 | OVERFIT |
| Ichimoku_Trend_Pro | BNB 4h | +294.8 | +14.6 | -28.0 | +17.9 | -8.7 | +58.1% | 3/5 | DEGRADED |
| Aggressive_Entry | ETH 4h | -28.2 | -20.6 | +4.8 | +23.2 | +22.2 | +0.3% | 3/5 | DEGRADED |
| MACD_Breakout | ETH 4h | +142.8 | +12.6 | +34.1 | +65.9 | +17.2 | +54.5% | **5/5** | **PASS** |
| Full_Momentum | BNB 4h | +185.1 | +60.9 | -17.1 | +27.7 | -22.1 | +46.9% | 3/5 | PASS |
| EMA_Break_Momentum | BNB 4h | +87.3 | +34.0 | -10.5 | +104.8 | +13.1 | +45.7% | **4/5** | **PASS** |
| Ichimoku_MACD_Pro | BTC 4h | +143.6 | -16.7 | +6.6 | +70.7 | -47.2 | +31.4% | 3/5 | PASS |
| MACD_Breakout | BNB 4h | +54.1 | -19.2 | -4.4 | +43.7 | +6.3 | +16.1% | 3/5 | PASS |

---

## Day 2: March 26

**Backtester:** Same as Day 1 (FEE=0.1%, 6yr)

### New Indicators Added (hardcoded parameters)

| Indicator | Parameters | Signal Name | Signal Logic |
|-----------|-----------|-------------|-------------|
| OBV | cumulative, SMA20 | OBV_Rising | OBV > SMA20(OBV) |
| CCI | period=20 | CCI_Oversold | CCI < -100 AND rising |
| Ichimoku | tenkan=9, kijun=26, senkou_b=52 | Ichimoku_Bull | close > span_a AND close > span_b |
| PSAR | af=0.02, max=0.2 | PSAR_Bull | close > PSAR |
| MFI | period=14 | MFI_Oversold | MFI < 20 AND rising |
| Keltner | EMA20 ± 2×ATR10 | Keltner_Lower | close < lower band |
| Williams %R | period=14 | Williams_Oversold | %R < -80 AND rising |

### TV-Validated Results (original params)

| # | Strategy | Asset | TF | ROI%/yr | Daily% | WR% | PF | Sharpe | GrossDD% | Trades | SL | TP | TS | min_ag | Indicators | TV Status |
|---|----------|-------|----|---------|--------|-----|-----|--------|----------|--------|----|----|-----|--------|-----------|-----------|
| 1 | 10_Aggressive_Entry | SOL | 4h | 282.2 | 0.773 | 57.7 | 1.34 | 1.13 | 62.7 | 822 | 4% | 15% | 0.5% | 2 | Breakout_20, Volume_Spike, MACD_Cross, ADX_Trend | PAPER_TRADE |
| 2 | 10_Aggressive_Entry | LINK | 1h | 204.5 | 0.560 | 58.3 | 1.40 | 1.13 | 19.3 | 999 | 4% | 15% | 0.5% | 2 | Breakout_20, Volume_Spike, MACD_Cross, ADX_Trend | PAPER_TRADE |
| 3 | 07_MACD_Breakout | SOL | 4h | 198.6 | 0.544 | 48.2 | 1.17 | 0.64 | 41.3 | 768 | 4% | 15% | 1.5% | 2 | MACD_Cross, Breakout_20, Volume_Spike, ADX_Trend | IGNORE |
| 4 | 10_Aggressive_Entry | ADA | 4h | 164.2 | 0.450 | 56.4 | 1.33 | 0.81 | 21.3 | 1060 | 4% | 15% | 0.5% | 2 | Breakout_20, Volume_Spike, MACD_Cross, ADX_Trend | PAPER_TRADE |
| 5 | 10_Aggressive_Entry | BNB | 4h | 163.9 | 0.449 | 55.2 | 1.33 | 0.95 | 35.5 | 1063 | 4% | 15% | 0.5% | 2 | Breakout_20, Volume_Spike, MACD_Cross, ADX_Trend | PAPER_TRADE |
| 6 | 22_Ichimoku_Trend_Pro | BNB | 4h | 136.3 | 0.373 | 41.0 | 1.05 | 0.26 | 65.0 | 2220 | 2% | 12% | 2% | 3 | Ichimoku_Bull, EMA_Cross, ADX_Trend, OBV_Rising | IGNORE |
| 7 | 23_Ichimoku_MACD_Pro | BNB | 4h | 132.7 | 0.364 | 38.8 | 1.04 | 0.22 | 71.1 | 2305 | 2% | 15% | 2% | 2 | Ichimoku_Bull, MACD_Cross, OBV_Rising, Volume_Spike | IGNORE |
| 8 | 21_Full_Momentum | BNB | 4h | 132.0 | 0.362 | 41.2 | 1.04 | 0.22 | 61.8 | 1886 | 2.5% | 15% | 2.5% | 3 | PSAR_Bull, Ichimoku_Bull, MACD_Cross, ADX_Trend, OBV_Rising | IGNORE |
| 9 | 10_Aggressive_Entry | ETH | 4h | 131.3 | 0.360 | 57.0 | 1.39 | 1.11 | 15.6 | 1175 | 4% | 15% | 0.5% | 2 | Breakout_20, Volume_Spike, MACD_Cross, ADX_Trend | PAPER_TRADE |
| 10 | 03_EMA_Break_Momentum | SOL | 4h | 127.2 | 0.349 | 39.4 | 1.01 | 0.08 | 86.2 | 1471 | 2% | 15% | 2.5% | 2 | EMA_Cross, Breakout_20, MACD_Cross, ADX_Trend | IGNORE |

### Failed Experiments

| Experiment | Assets | TF | Best Result | Verdict |
|-----------|--------|-----|-------------|---------|
| All strategies on 1h | ETH, BNB, LINK, ADA, AVAX | 1h | -98.6% ROI | ALL DEAD (except Aggressive_Entry LINK) |
| All strategies on 15m | All 10 | 15m | -25%/yr best | ALL DEAD |
| Short selling (5 strategies) | BNB, ETH, SOL, ADA, LINK | 4h | +17% delta on Vol_Stoch_MACD_ADX | Only 2 of 5 benefit |

---

## Day 3: March 29

### Phase 1 AM — New Pine Scripts with tighter params

**Backtester:** FEE=0.1% (later changed to 0.03%)

| # | Strategy | Asset | TF | ROI%/yr | Daily% | WR% | PF | TV Sharpe | GrossDD% | Trades | SL | TP | TS | min_ag | Indicators | TV Status |
|---|----------|-------|----|---------|--------|-----|-----|-----------|----------|--------|----|----|-----|--------|-----------|-----------|
| 1 | 44_PSAR_Volume_Surge | ETH | 4h | 508.5 | 1.393 | 62.7 | 1.29 | **1.81** | 14.9 | 343 | 1.5% | 6% | 0.7% | 5 of 5 | PSAR, Vol>2x, BullCandle, EMA, Supertrend | PAPER_TRADE |
| 2 | 26_Trend_Confirm_Tight | ETH | 4h | 250.4 | 0.686 | 48.0 | 1.07 | 0.48 | 44.6 | 1182 | 1.2% | 6% | 0.6% | 4 of 6 | EMA, MA50, Ichimoku, PSAR, Supertrend, ADX | IGNORE |
| 3 | 25_High_Sharpe_Scalp | ETH | 4h | 255.8 | 0.701 | 48.9 | 1.05 | 0.45 | 58.4 | 3906 | 1% | 5% | 0.5% | 3 of 5 | EMA, Supertrend, ADX, PSAR, OBV | IGNORE |
| 4 | 28_Ichimoku_PSAR_ADX | BNB | 4h | 101.0 | 0.277 | **84.8** | **1.20** | **0.68** | 48.8 | 3812 | 1.5% | 8% | 0.8% | 5 of 5 | Ichimoku, PSAR, ADX, OBV, Tenkan>Kijun | IGNORE |
| 5 | 54_All_Trend_Align | ETH | 4h | 129.8 | 0.356 | 52.7 | 1.11 | 0.63 | 35.4 | 2731 | 1.5% | 3% | 0.5% | 7 of 8 | EMA, MA50, Ichimoku, TK, PSAR, Supertrend, ADX, OBV | IGNORE |

### Phase 2 PM — TIER_2 discovered (tighter SL/TP)

| # | Strategy | Asset | TF | ROI%/yr | Daily% | WR% | PF | TV Sharpe | GrossDD% | Trades | SL | TP | TS | min_ag | Indicators | TV Status |
|---|----------|-------|----|---------|--------|-----|-----|-----------|----------|--------|----|----|-----|--------|-----------|-----------|
| 1 | **56_PSAR_Volume_Tight** | ETH | 4h | 93.0 | 0.255 | **61.1** | **1.68** | **1.16** | 17.7 | 342 | **1%** | **3%** | **0.4%** | 5 of 5 | PSAR, Vol>2x, EMA, Supertrend, MA50 | **TIER_2_DEPLOY** |
| 2 | **57_PSAR_Volume_Ultra** | ETH | 4h | 64.6 | 0.177 | **61.5** | **1.54** | 0.68 | 39.7 | 161 | 0.8% | 2% | 0.3% | 6 of 6 | PSAR, Vol>2x, EMA, Supertrend, MA50, ADX | **TIER_2_TEST** |
| 3 | **44_PSAR_Volume_Surge** | BTC | 4h | 75.6 | 0.207 | 51.6 | **1.44** | 0.78 | 38.0 | 310 | 1.5% | 6% | 0.7% | 5 of 5 | PSAR, Vol>2x, BullCandle, EMA, Supertrend | **TIER_2_TEST** |
| 4 | 38_Cloud_Momentum | ETH | 4h | 119.5 | 0.327 | 50.4 | 1.24 | 0.90 | 40.7 | 1303 | 1.2% | 5% | 0.6% | 5 of 5 | Ichimoku, TK, PSAR, OBV, Volume | PAPER_TRADE |
| 5 | 51_Cloud_Momentum_v2 | ETH | 4h | 115.5 | 0.317 | 55.3 | 1.28 | 0.99 | 41.6 | 1303 | 2% | 3% | 0.5% | 5 of 5 | Ichimoku, TK, PSAR, OBV, Volume | PAPER_TRADE |
| 6 | 10_Aggressive_Entry | BNB | 4h | 163.9 | 0.449 | 55.2 | 1.33 | 0.95 | 35.5 | 1063 | 4% | 15% | 0.5% | 2 | Breakout_20, Volume_Spike, MACD_Cross, ADX_Trend | PAPER_TRADE |

### Phase 3 — Modified strategies (SL=1%, TP=3%, TS=0.4% matching 56)

| # | Strategy | Asset | TF | Original SL/TP/TS | New SL/TP/TS | Original PF | Expected PF | TV Status Target |
|---|----------|-------|----|------------------|-------------|------------|------------|-----------------|
| 1 | 10_Aggressive_Entry | ETH | 4h | 4/15/0.5% | 1/3/0.4% | 1.39 | 1.6+ | TIER_2 |
| 2 | 44_PSAR_Volume_Surge | ETH | 4h | 1.5/6/0.7% | 1/3/0.4% | 1.29 | 1.6+ | TIER_2 |
| 3 | 38_Cloud_Momentum | ETH | 4h | 1.2/5/0.6% | 1/3/0.4% | 1.24 | 1.6+ | TIER_2 |
| 4 | 51_Cloud_Momentum_v2 | ETH | 4h | 2/3/0.5% | 1/3/0.4% | 1.28 | 1.6+ | TIER_2 |
| 5 | 28_Ichimoku_PSAR_ADX | ETH | 4h | 1.5/6/0.7% | 1/3/0.4% | 1.27 | 1.6+ | TIER_2 |
| 6 | 54_All_Trend_Align | ETH | 4h | 1.5/3/0.5% | 1/3/0.4% | 1.11 | 1.6+ | TIER_2 |
| 7 | 07_MACD_Breakout | ETH | 4h | 4/15/1.5% | 1/3/0.4% | 1.05 | 1.6+ | TIER_2 |
| 8 | 57_PSAR_Volume_Ultra | ETH | 4h | 0.8/2/0.3% | 1/2.5/0.3% | 1.54 | 1.6+ | TIER_2 |

### Phase 4 — Fee fix + Param Sweep (Evening)

**Backtester changed:** FEE=0.03% per side (0.06% round-trip)

**Param Sweep — 576,000 backtests on server, custom indicator parameters:**

| Parameter | Default | Values Swept |
|-----------|---------|-------------|
| EMA fast | 8 | 5, 8, 10, 12 |
| EMA slow | 21 | 15, 21, 26, 30 |
| ATR multiplier | 3.0 | 2.0, 2.5, 3.0, 3.5 |
| ADX threshold | 25 | 20, 25, 30, 35 |
| Volume multiplier | 1.5 | 1.2, 1.5, 2.0 |
| PSAR af | 0.02 | 0.01, 0.02, 0.03 |
| PSAR max | 0.2 | 0.1, 0.2, 0.3 |
| Ichimoku tenkan | 9 | 7, 9, 12 |
| Ichimoku kijun | 26 | 22, 26, 30 |
| Ichimoku senkou_b | 52 | 44, 52, 60 |
| SL | — | 0.5, 0.6, 0.7, 0.8, 1.0, 1.2, 1.5, 2.0% |
| TP | — | 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0% |
| TS | — | 0.2, 0.4, 0.6, 0.8% |

**Results: 38,372 strategies with PF ≥ 1.2**

### 21 TIER_2_DEPLOY Strategies Found (PF ≥ 1.6, WR ≥ 50%, GDD < 35%)

| # | Strategy | Asset | PF | WR% | GDD% | ROI% | Sharpe | Trades | SL | TP | TS | EMA_F | EMA_S | ATR_M | PSAR_af | ADX | Ichi_T | Ichi_K |
|---|----------|-------|----|-----|------|------|--------|--------|----|----|-----|-------|-------|-------|---------|-----|--------|--------|
| 1 | PSAR_EMA_ST_ADX_OBV | ADA | **1.82** | 57.9 | 6.7 | 38.9 | 0.85 | 76 | 1.0% | 1.5% | 0.8% | 5 | 30 | 3.5 | 0.010 | >25 | 9 | 26 |
| 2 | PSAR_EMA_ST_ADX_OBV | ADA | **1.80** | 58.1 | 6.7 | 31.1 | 0.82 | 62 | 1.0% | 1.5% | 0.8% | 5 | 26 | 3.0 | 0.010 | >30 | 9 | 26 |
| 3 | PSAR_EMA_ST_ADX_OBV | ADA | **1.76** | 60.3 | 7.3 | 27.3 | 0.78 | 58 | 1.0% | 1.5% | 0.8% | 5 | 30 | 3.5 | 0.010 | >25 | 9 | 26 |
| 4 | PSAR_EMA_ST_ADX_OBV | SOL | **1.68** | 53.3 | 7.4 | 28.8 | 0.64 | 90 | 0.5% | 2.5% | 0.2% | 5 | 15 | 3.5 | 0.030 | >30 | 9 | 26 |
| 5 | PSAR_EMA_ST_ADX_OBV | ADA | **1.68** | 55.8 | 7.5 | 33.4 | 0.81 | 77 | 1.0% | 1.5% | 0.6% | 5 | 30 | 3.5 | 0.010 | >25 | 9 | 26 |
| 6 | PSAR_EMA_ST_ADX_OBV | ADA | **1.68** | 55.6 | 6.7 | 31.2 | 0.80 | 72 | 1.0% | 1.5% | 0.8% | 5 | 26 | 3.5 | 0.010 | >20 | 9 | 26 |
| 7 | PSAR_EMA_ST_ADX_OBV | SOL | **1.67** | 52.8 | 7.4 | 28.9 | 0.63 | 89 | 0.5% | 2.5% | 0.4% | 5 | 15 | 3.5 | 0.030 | >30 | 9 | 26 |
| 8 | Ichi_OBV_Vol_PSAR_Trend | BNB | **1.67** | 53.9 | 8.8 | 50.3 | 0.92 | 128 | 2.0% | 1.5% | 0.8% | 8 | 21 | — | 0.030 | >25 | 12 | 30 |
| 9 | PSAR_EMA_ST_ADX_OBV | ADA | **1.66** | 55.6 | 6.7 | 30.4 | 0.79 | 72 | 1.0% | 1.5% | 0.8% | 8 | 21 | 3.5 | 0.010 | >20 | 9 | 26 |
| 10 | Ichi_OBV_Vol_PSAR_Trend | ETH | **1.66** | 50.0 | 9.6 | 66.7 | 1.02 | 160 | 0.5% | 5.0% | 0.2% | 8 | 21 | — | 0.030 | >25 | 9 | 22 |
| 11 | Ichi_OBV_Vol_PSAR_Trend | ADA | **1.65** | 54.7 | 7.7 | 24.3 | 0.72 | 64 | 1.0% | 1.5% | 0.8% | 8 | 21 | — | 0.030 | >25 | 9 | 22 |
| 12 | Ichi_OBV_Vol_PSAR_Trend | ADA | **1.64** | 53.1 | 7.7 | 23.7 | 0.70 | 64 | 1.0% | 1.5% | 0.4% | 8 | 21 | — | 0.030 | >25 | 9 | 22 |
| 13 | Ichi_OBV_Vol_PSAR_Trend | ADA | **1.64** | 53.1 | 7.7 | 23.7 | 0.70 | 64 | 1.0% | 1.5% | 0.6% | 8 | 21 | — | 0.030 | >25 | 9 | 22 |
| 14 | Ichi_OBV_Vol_PSAR_Trend | ADA | **1.63** | 54.5 | 7.7 | 25.4 | 0.73 | 66 | 1.0% | 1.5% | 0.8% | 8 | 21 | — | 0.030 | >25 | 7 | 22 |
| 15 | Ichi_OBV_Vol_PSAR_Trend | BNB | **1.63** | 50.4 | 8.0 | 50.2 | 0.90 | 137 | 1.0% | 1.5% | 0.8% | 8 | 21 | — | 0.030 | >25 | 9 | 22 |
| 16 | PSAR_EMA_ST_ADX_OBV | ADA | **1.63** | 55.1 | 7.5 | 30.8 | 0.79 | 78 | 1.0% | 1.5% | 0.4% | 5 | 30 | 3.5 | 0.010 | >25 | 9 | 26 |
| 17 | Ichi_OBV_Vol_PSAR_Trend | ADA | **1.63** | 53.0 | 7.7 | 24.8 | 0.71 | 66 | 1.0% | 1.5% | 0.4% | 8 | 21 | — | 0.030 | >25 | 7 | 22 |
| 18 | Ichi_OBV_Vol_PSAR_Trend | ADA | **1.63** | 53.0 | 7.7 | 24.8 | 0.71 | 66 | 1.0% | 1.5% | 0.6% | 8 | 21 | — | 0.030 | >25 | 7 | 22 |
| 19 | Ichi_OBV_Vol_PSAR_Trend | BNB | **1.61** | 52.4 | 10.0 | 46.6 | 0.88 | 126 | 2.0% | 1.5% | 0.8% | 8 | 21 | — | 0.030 | >25 | 9 | 26 |
| 20 | PSAR_EMA_ST_ADX_OBV | ADA | **1.60** | 54.0 | 6.7 | 24.6 | 0.75 | 63 | 1.0% | 1.5% | 0.6% | 5 | 26 | 3.0 | 0.010 | >30 | 9 | 26 |
| 21 | PSAR_EMA_ST_ADX_OBV | ADA | **1.60** | 54.7 | 4.6 | 27.6 | 0.76 | 75 | 1.0% | 1.5% | 0.8% | 5 | 26 | 3.5 | 0.030 | >25 | 9 | 26 |

### 146 TIER_2_TEST + 6,007 PAPER_TRADE also found (in reports/param_sweep_results.csv)

---

## Cumulative Totals

| Metric | Day 0 | Day 1 | Day 2 | Day 3 | Total |
|--------|-------|-------|-------|-------|-------|
| Backtests run | 0 | 410 | 285 | 405,000+ | **405,695+** |
| Pine Scripts | 0 | 5 | 15 | 36 | **56** |
| TIER_1_DEPLOY | 0 | 0 | 0 | 1 | **1** |
| TIER_2_DEPLOY | 0 | 0 | 0 | 22 | **22** |
| TIER_2_TEST | 0 | 0 | 0 | 149 | **149** |
| PAPER_TRADE | 0 | 5 | 7 | 6,010 | **6,022** |
| Indicators | 12 | 12 | 19 | 19 | **19** |
| Strategy batches | 20 | 20 | 21 | 22 | **22** |
| Total strategies | 230 | 230 | 242 | 258 | **258** |
| Audit score | 3.5/10 | 6.5/10 | 6.5/10 | 6.5/10 | **6.5/10** |

### Key Parameter Discoveries (What actually works)

| Discovery | Default | Optimal | Impact |
|-----------|---------|---------|--------|
| **EMA fast period** | 8 | **5** | Faster reaction → better entries on ADA |
| **EMA slow period** | 21 | **26-30** | Wider gap → more selective trend confirmation |
| **ATR multiplier** | 3.0 | **3.5** | Wider Supertrend → fewer false exits |
| **PSAR af** | 0.02 | **0.01** (ADA), **0.03** (BNB/ETH) | Asset-specific tuning matters |
| **ADX threshold** | 25 | **30** for ADA/SOL | Stronger trend filter |
| **Ichimoku kijun** | 26 | **22** for ETH/ADA | Faster momentum detection |
| **Ichimoku tenkan** | 9 | **12** for BNB | Slower, smoother on BNB |
| **SL/TP ratio** | 4%/15% | **1%/1.5%** | Tight TP = higher PF (more wins hit TP) |
| **Trailing stop** | 0.5-2.5% | **0.8%** | Balances profit lock-in vs premature exit |
| **Fee** | 0.1% per side | **0.03% per side** | Matches TV — 3x less drag on PF |
