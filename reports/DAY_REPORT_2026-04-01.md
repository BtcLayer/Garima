# Day Report — April 1, 2026

## Executive Summary
Major discovery day. Read Harsh's tournament backtester code — found it uses `signal × bar_return` model (theoretical, not real trades). TV validation of all strategies confirmed this — 0 of 14 profitable on TV. Rewrote our backtester twice. Tested 25+ different strategy approaches. ML scored approach found **0.366%/day on LTCUSDT** (best honest result). Built persistent ML system that remembers everything. Running overnight.

**LLM Time**: ~8 hours | **Human Time**: ~6 hours

---

## Key Discoveries

### 1. Tournament Backtester is Theoretical
Read `strategy_tournament.py` — uses `signal × bar_return` (multiply direction by each bar's % change). No actual trades. TV validation: **0 of 14 strategies profitable** (-90% to -100% loss).

### 2. Our Backtester Rewritten
- Crossover signals (fire once, not every bar)
- Signal-based exits (adaptive, not fixed SL/TP)
- Long + Short with instant position flipping
- Fee matched to 0.1%

### 3. Best ML Result: 0.366%/day LTCUSDT
ML Scored approach (quality score 0-100) found:
- 0.366%/day LTC (PF=1.80, WR=53.3%, 90 trades, TP=6%, SL=3%)
- 8 strategies above 0.1%/day total

---

## All Approaches Tested Today

| # | Approach | Best Result | Asset |
|---|----------|-------------|-------|
| 1 | Tournament-matched backtester | 1.5%/day (FAKE — failed TV) | NEAR |
| 2 | TV validation 15m (14 strategies) | 0 profitable | All |
| 3 | TV validation 1h (14 strategies) | 1 barely profitable | FIL |
| 4 | 5 TV-first Pine Scripts on 15m | 0 profitable | All |
| 5 | Basic ML (RF+GBM) | 0.178%/day | ADA |
| 6 | Neural Network ensemble | 0.101%/day | ADA |
| 7 | Rule-based ML features | 0.089%/day | ADA |
| 8 | Archive enhanced ML | 0.048%/day | BTC |
| 9 | **ML Scored labels** | **0.366%/day** | **LTC** |
| 10 | ML Improve Winners | 0.062%/day | ADA |
| 11 | ML Full Ensemble (16 sig + 9 combo) | 0.068%/day | SOL |
| 12 | 10 rule-based strategies (4h) | 0.078%/day | ETH |
| 13 | 15 NEW strategies | 0.168%/day | ETH |

---

## Best 10 Strategies Found (Honest, 4h)

| # | ROI/day | Asset | Strategy | PF | WR% | Trades |
|---|---------|-------|----------|-----|-----|--------|
| 1 | **0.366%** | LTC | ML Scored T60 TP=6% | 1.80 | 53.3% | 90 |
| 2 | **0.241%** | LTC | ML Scored T60 TP=8% | 1.44 | 48.1% | 81 |
| 3 | **0.201%** | LTC | ML Scored T60 TP=4% | 1.74 | 51.5% | 99 |
| 4 | **0.181%** | LTC | ML Scored T60 TP=10% | 1.34 | 50.7% | 75 |
| 5 | **0.168%** | ETH | InsideBar Breakout | 1.40 | 52.5% | 556 |
| 6 | **0.128%** | LTC | ML Scored T60 TP=3% | 1.71 | 50.5% | 105 |
| 7 | **0.087%** | LTC | ML Scored T60 TP=2% | 1.79 | 52.3% | 109 |
| 8 | **0.080%** | SOL | EMA Ribbon Expansion | 1.19 | 41.9% | 339 |
| 9 | **0.078%** | ETH | Regime Adaptive | 1.32 | 48.1% | 212 |
| 10 | **0.077%** | ETH | Fibonacci Pullback | 1.20 | 50.5% | 277 |

---

## Infrastructure Updates

| Component | Change |
|-----------|--------|
| `/autohunt` | Removed (replaced by `/ml`) |
| "ALPHA" keyword | Replaced with "TIER" everywhere |
| ML results | GDD added to bot display |
| Auto-notify | GDD + TP/SL added to notifications |
| Persistent ML | Built — saves models, remembers tested combos, never repeats |
| ML Generate Hybrid | Built — ATR-adaptive + High-TP + Trend+Dip |
| 15 new strategies | InsideBar, Engulfing, Hammer, Squeeze, Triple Flip, Fib, ADX Explosion, etc. |
| 3 level-based Pine Scripts | OBV Momentum, Lookback Momentum, Supertrend Level |
| 2 advanced Pine Scripts | Regime Adaptive, Multi Dip Trend |

---

## Running Overnight on Server

| Process | What |
|---------|------|
| Persistent ML | 16 signals × 8 params × 10 assets, saves models + memory |
| ML Generate Hybrid | ATR-adaptive + High-TP + Trend+Dip + ML filter |
| Auto-notify | Messages Telegram on new results |
| Bot | Active |
| Dashboard | Active |

---

## AlgoEdge Platform Explored
- Trading dashboard with backtester, signals, kill switch, order manager
- 6 live signals: IV, OI, Price Action, Put-Call Ratio, Volume, VWAP Deviation
- 5 strategy types: Pairs L/S, Sector Rotation, ORB Breakout, Crossover, RSI Reversion
- Data API for stock/options data (equity-focused, not crypto)
- Useful strategy TYPES (ORB Breakout, Pairs) but not directly applicable to our crypto work

---

## End of Day Activities

### 1. Visiting Top Strategy in TradingView
- Testing ML Scored LTC 0.366%/day strategy directly on TV
- Validating InsideBar Breakout ETH 0.168%/day
- Checking Regime Adaptive and Triple Flip strategies

### 2. Sharing Optimization Process with Harsh
- Explained tournament backtester vs TV gap (signal×return vs real trades)
- Shared 1h vs 15m TV validation comparison
- Key finding: tournament's risk filters work on return stream, not on actual trades
- Recommendation: TV-first approach for all future strategies

### 3. AlgoEdge Platform (edgeconnect-new.algoedge.io)
- Explored trading dashboard with Harsh
- Found 6 live signals: IV, OI, Price Action, Put-Call Ratio, Volume, VWAP Deviation
- 5 strategy types: Pairs L/S, Sector Rotation, ORB Breakout, Crossover, RSI Reversion
- Data API available for stock/options (equity-focused, not crypto)
- Useful strategy concepts (ORB Breakout, Pairs) to implement for crypto tomorrow

---

## Tomorrow's Plan
1. Check overnight ML results (persistent + hybrid)
2. TV validate LTC 0.366%/day strategy
3. Implement ORB Breakout for crypto (from AlgoEdge concept)
4. Implement Pairs trading (long ETH / short BTC)
5. Compile best 10 strategies for senior presentation
6. Push to main branch
