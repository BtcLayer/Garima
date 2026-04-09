# Profitable Strategy Blueprint
> Patterns extracted from 300+ backtested strategy-asset combos across cagr, cagr2, cagr3, cagr4, good, good2 result sheets.

---

## 1. WINNING RISK FRAMEWORK (Non-Negotiable)

Every profitable strategy shares this exact risk skeleton:

| Parameter | Value | Why |
|-----------|-------|-----|
| **SL** | 1.5% | Tight enough to cut losses fast, wide enough to avoid noise stops |
| **TP** | 12-18% | Lets winners run. 15%+ performs better on volatile assets |
| **Trailing Stop** | 3.0-4.0% | Locks in profit without exiting too early. 3.5% is sweet spot |
| **Anti-Overtrading** | Max 3 trades/day | Prevents overexposure and revenge trading |
| **Consecutive Loss Cooldown** | 6 bars after 3 losses | Avoids drawdown spirals |
| **Daily Circuit Breaker** | -3% equity = stop trading | Hard stop for bad days |
| **ATR Volatility Filter** | ATR < SMA(ATR,100) × 2 | Avoids entry during extreme volatility spikes |
| **Position Sizing** | 95% equity (backtest) / $500 fixed (live) | Backtest uses compounding, live uses fixed notional |
| **Commission** | 0.1% per trade | Accounts for exchange fees + slippage |

**Without this framework**: Same indicators produce WEAK/IGNORE results (0.1-0.4%/day)
**With this framework**: Same indicators produce TIER_1 results (0.4-0.96%/day, WR 80-85%, PF 9-18)

---

## 2. BEST ENTRY SIGNALS (Ranked by Performance)

### Tier A — Breakout Signals (Best Performers)

| Signal | How It Works | Best CAGR Achieved |
|--------|-------------|-------------------|
| **Donchian Channel Breakout** | Close > 20-bar high (or < 20-bar low) | 2.15%/day on SUI |
| **CCI Cross ±100** | CCI crosses above +100 (buy) or below -100 (sell) | 1.42%/day on LDO |
| **Donchian + CCI combo** | Either Donchian break OR CCI cross triggers entry | 0.96%/day on AVAX |

### Tier B — Confirmation Signals (Good as secondary)

| Signal | Role | Typical Boost |
|--------|------|---------------|
| **ADX > 20** | Confirms real trend exists | Required — without it PF drops 50%+ |
| **EMA50 direction** | Price above EMA50 for longs | Required — prevents counter-trend trades |
| **Volume > SMA(20) × 1.2** | Confirms institutional participation | +10-20% WR improvement for strong tier |

### Tier C — Enhancer Signals (Optional, add if needed)

| Signal | When to Use |
|--------|-------------|
| **SuperTrend direction** | Good trend filter, doesn't reduce trades much |
| **PSAR direction** | Clean trend confirmation |
| **Stochastic K > D** | Momentum timing |
| **MACD histogram > 0** | Growing momentum |
| **Aroon Up > 70** | New highs forming |
| **Ichimoku above cloud** | Multi-timeframe trend strength |

### AVOID — These Signals Fail Consistently

| Signal | Why It Fails |
|--------|-------------|
| **VWAP Mean Reversion** | Counter-trend = gets destroyed in crypto trends. ALL 5 assets negative |
| **OBV EMA Trend** | WR 25-32% = too many false signals |
| **Chaikin Money Flow** | Barely PF 1.0, inconsistent across assets |
| **ROC MACD Momentum** | Redundant oscillators, 3/5 assets negative |
| **Elder Impulse** | Too many conditions = misses entries |
| **EMA crossover alone** | Without breakout channel = too many whipsaws |

---

## 3. BEST ASSETS (Ranked by Profitability)

| Rank | Asset | Why It Works | Best Daily CAGR |
|------|-------|-------------|-----------------|
| 1 | **SUI** | Highest volatility, strong trends, newer token | 2.15%/day |
| 2 | **LDO** | High volatility, strong DeFi narrative moves | 1.75%/day |
| 3 | **AVAX** | Good volatility, clean breakouts | 0.96%/day |
| 4 | **DOT** | Moderate volatility, trend-friendly | 0.86%/day |
| 5 | **ETH** | Most liquid, consistent but lower CAGR | 0.73%/day |
| 6 | **SOL** | Good but inconsistent across strategies | 0.38%/day |
| 7 | **BTC** | Too stable for breakout strategies, low CAGR | 0.25%/day |
| 8 | **LINK** | Worst performer — most strategies go negative | AVOID |

**Pattern**: Higher volatility = higher CAGR. Breakout strategies need price movement.
**LINK is a trap**: Looks good on paper but majority of strategies lose money on it.

---

## 4. BEST TIMEFRAME

| Timeframe | Verdict |
|-----------|---------|
| **4h** | ONLY timeframe that works. All TIER_1 results are 4h |
| 15m | Too noisy, false signals, high fees eat profits |
| 1h | Marginally OK but 4h is strictly better |
| 1d | Too few trades, low CAGR |

---

## 5. OPTIMAL ENTRY STRUCTURE

### Simple > Complex

```
BEST:  Breakout + EMA50 + ADX > 18-20              (0.6-2.15%/day)
GOOD:  Breakout + EMA50 + ADX > 20 + Volume        (0.4-0.96%/day)  
OK:    Breakout + Indicator + EMA50 + ADX + Volume  (0.3-0.4%/day)
BAD:   Breakout + 2 Indicators + EMA + ADX + Vol    (0.2-0.3%/day)
```

**Every added filter reduces trades → reduces CAGR.** Keep entries simple, let the risk framework do the work.

### Tiered Entry (Proven Pattern)

```pine
// Strong entry: high conviction
long_strong = breakout_up and close > ema50 and adx > 25 and vol_confirm

// Medium entry: catch more trades
long_medium = breakout_up and close > ema50 and adx > 18

long_entry = long_strong or long_medium
```

---

## 6. OPTIMAL EXIT STRUCTURE

| Exit Type | Condition | Priority |
|-----------|-----------|----------|
| **Trailing Stop** | 3.0-3.5% trail | Primary — captures most profit |
| **Take Profit** | 15-18% | Secondary — caps extreme winners |
| **Stop Loss** | 1.5% | Safety net — limits downside |
| **Channel Exit** | Close < exit_lower (10-bar) | Turtle-style exit |
| **RSI Extreme** | RSI > 80 (overbought exit) | Prevents holding into reversal |
| **Indicator Flip** | CCI crosses 0, PSAR flips | Strategy-specific exit |

---

## 7. PARAMETER SENSITIVITY

### What to Increase for Higher CAGR

| Parameter | Change | Effect | Risk |
|-----------|--------|--------|------|
| TP | 12% → 15-18% | +30-50% CAGR | Fewer TP hits, more trail exits |
| Trail | 4.0% → 3.0-3.5% | +10-20% CAGR | Tighter = exits earlier on pullbacks |
| ADX threshold | 20 → 15 | +20-40% more trades | Some weak-trend entries |
| ATR filter | × 2.0 → × 2.5 | +10% more trades | Allows some volatile entries |
| Channel | 20-bar → 14-bar | +30% more trades | More false breakouts |

### What NOT to Change

| Parameter | Keep At | Why |
|-----------|---------|-----|
| SL | 1.5% | Lower = too many stops. Higher = big losses |
| Max trades/day | 3 | More = overtrading, less = missing opportunities |
| Cooldown | 6 bars after 3 losses | Proven to prevent drawdown spirals |
| Circuit breaker | -3% | Hard floor, non-negotiable |
| EMA | 50-period | Best balance of trend detection vs lag |

---

## 8. STRATEGY-ASSET MATRIX (What Works Where)

| Strategy Type | SUI | LDO | AVAX | DOT | ETH | BTC | LINK |
|---------------|-----|-----|------|-----|-----|-----|------|
| Donchian Breakout | ★★★ | ★★★ | ★★★ | ★★☆ | ★★☆ | ★☆☆ | ★☆☆ |
| CCI Cross | ★★★ | ★★★ | ★★☆ | ★★☆ | ★★☆ | ★☆☆ | ★☆☆ |
| CCI + Donchian Wide | — | — | ★★★ | ★★☆ | ★★★ | — | — |
| Donchian ADX Aggro | ★★★ | ★★☆ | ★★☆ | ★★☆ | ★★★ | — | — |
| SuperTrend + Donchian | — | — | — | — | ★★☆ | — | — |
| Mean Reversion | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

★★★ = TIER_1_DEPLOY, ★★☆ = TIER_1/TIER_2, ★☆☆ = WEAK, ✗ = DO_NOT_USE

---

## 9. QUICK RECIPE: Building a Profitable Strategy

```
1. Pick entry signal    → Donchian breakout OR CCI cross ±100
2. Add trend filter     → close > EMA50
3. Add strength filter  → ADX > 18 (minimum), 25 for strong tier
4. Set risk params      → SL 1.5%, TP 15%, Trail 3.5%
5. Add anti-overtrading → 3/day max, 6-bar cooldown, -3% breaker
6. Add ATR filter       → ATR < SMA(ATR,100) × 2
7. Pick asset           → SUI, LDO, or AVAX (not LINK, not BTC)
8. Set timeframe        → 4h only
9. Add webhook secret   → squeeze_tradingview_cluster_2026_secure
10. Backtest on TV      → expect WR 80-85%, PF 5-18
```

---

## 10. RED FLAGS (When a Strategy Will Fail)

| Red Flag | What It Means |
|----------|---------------|
| WR < 40% | Entry signal has no edge |
| PF < 1.0 | Losing money per trade on average |
| Sharpe < 0 | Risk-adjusted returns are negative |
| Works on 1 asset only | Likely overfit, not a real edge |
| LINK is the only winner | Unreliable — LINK is inconsistent |
| Mean reversion logic | Counter-trend doesn't work in crypto |
| 3+ indicator confirmations | Over-filtered = too few trades |
| No SL/TP/trailing | No risk management = guaranteed blowup |
| ADX not used | Enters in ranging markets = whipsaw city |

---

*Last updated: April 8, 2026*
*Based on: combo_strategy_results_good, cagr, cagr2, cagr3, cagr4, cagr_good2*
