# TV Validation Comparison — 1h vs 15m

## Summary
Tested Harsh's top 14 tournament strategies on TradingView on both 1h and 15m timeframes. Both failed — but 1h was slightly less catastrophic.

---

## 1h Results (TV Validated)

| # | Strategy | Asset | Net Profit | ROI% | WR% | PF | Sharpe | Trades | Verdict |
|---|----------|-------|-----------|------|-----|-----|--------|--------|---------|
| 1 | MACD_Breakout | FIL | +$2,871 | +28.7% | 83.3% | 1.11 | 0.27 | 582 | **ONLY WINNER** (barely) |
| 2 | Ichimoku_Trend_Pro | FIL | -$215,996 | -2,160% | 76.4% | 1.06 | -0.01 | 854 | LOSS |
| 3 | Keltner_Breakout | FIL | -$209,410 | -2,094% | 68.4% | 1.00 | -0.01 | 1045 | LOSS |
| 4 | Ichimoku_MACD_Pro | OP | -$160,080 | -1,601% | 28.8% | 0.14 | — | — | LOSS |
| 5 | MACD_Breakout | OP | -$473,283 | -4,733% | 29.9% | 0.16 | — | — | LOSS |
| 6 | Aggressive_Entry | FIL | -$483,210 | -4,832% | -92.1% | 0.08 | — | — | LOSS |
| 7 | MACD_Breakout | LDO | -$559,697 | -5,597% | 32.1% | 0.14 | — | — | LOSS |
| 8 | Ichimoku_MACD_Pro | LDO | -$718,688 | -7,187% | 30.4% | 0.13 | — | 846 | LOSS |
| 9 | Aggressive_Entry | LDO | -$811,986 | -8,120% | 26.2% | 0.06 | — | — | LOSS |
| 10 | Ichimoku_Trend_Pro | LDO | -$963,206 | -9,632% | 33.3% | 0.06 | — | 2033 | LOSS |
| 11 | Full_Momentum | OP | -$930,088 | -9,301% | 27.3% | 0.05 | — | — | LOSS |
| 12 | Ichimoku_Trend_Pro | UNI | -$995,035 | -9,950% | 31.7% | 0.07 | — | — | LOSS |
| 13 | Full_Momentum | LDO | -$999,713 | -9,997% | 27.4% | 0.02 | — | — | LOSS |

**1h Result: 1 of 14 profitable (MACD_Breakout FIL, +28.7% but PF=1.11 — barely)**

---

## 15m Results (TV Validated)

| # | Strategy | Asset | Net Profit | ROI% | WR% | PF | Sharpe | Trades | Verdict |
|---|----------|-------|-----------|------|-----|-----|--------|--------|---------|
| 1 | SMC_LuxAlgo | OP | -$9,487 | -94.9% | 34.2% | 0.77 | -1.79 | 1267 | LOSS |
| 2 | SMC_LuxAlgo | FIL | -$9,624 | -96.2% | 23.2% | 0.74 | -1.66 | 1550 | LOSS |
| 3 | Aggressive_Entry | FIL | -$9,207 | -92.1% | 23.2% | 0.67 | — | — | LOSS |
| 4 | MACD_Breakout | OP | -$9,338 | -93.4% | 26.6% | 0.66 | -1.97 | 1212 | LOSS |
| 5 | MACD_Breakout | LDO | -$9,621 | -96.2% | 27.8% | 0.58 | -2.6 | — | LOSS |
| 6 | Keltner_Breakout | FIL | -$9,728 | -97.3% | 30.5% | 0.61 | -2.45 | 1524 | LOSS |
| 7 | Aggressive_Entry | LDO | -$9,844 | -98.4% | 24.3% | 0.60 | -1.97 | — | LOSS |
| 8 | Ichimoku_Trend_Pro | UNI | -$9,966 | -99.7% | 30.2% | 0.56 | -2.61 | — | LOSS |
| 9 | Ichimoku_Trend_Pro | FIL | -$9,971 | -99.7% | 31.5% | 0.56 | -2.61 | 3120 | LOSS |
| 10 | Ichimoku_MACD_Pro | OP | -$9,882 | -98.8% | 24.4% | 0.69 | -2.69 | — | LOSS |
| 11 | Ichimoku_Trend_Pro | LDO | -$9,997 | -100% | 30.9% | 0.59 | -3.48 | — | LOSS |
| 12 | Ichimoku_MACD_Pro | LDO | -$9,970 | -99.7% | 23.8% | 0.43 | -3.08 | — | LOSS |
| 13 | Full_Momentum | FIL | -$10,000 | -100% | 23.7% | 0.42 | -3.08 | — | TOTAL LOSS |
| 14 | Full_Momentum | LDO | -$9,999 | -100% | 23.7% | — | — | — | TOTAL LOSS |

**15m Result: 0 of 14 profitable. All lost 92-100% of capital.**

---

## Direct Comparison: 1h vs 15m

| Metric | 1h | 15m |
|--------|-----|------|
| Profitable strategies | 1/14 (7%) | 0/14 (0%) |
| Best result | +28.7% (MACD FIL) | -92.1% (best was least bad) |
| Worst result | -99.97% (Full_Momentum LDO) | -100% (Full_Momentum LDO) |
| Average WR on TV | 26-83% (wide range) | 23-34% (consistently bad) |
| Average PF on TV | 0.02-1.11 | 0.42-0.77 |
| Avg loss | -$500k+ per strategy | -$9,700 per strategy |
| Trades | 582-2033 | 1212-3120 |

### Key Difference
- **1h has fewer trades** but each trade has bigger impact (both positive and negative)
- **15m has more trades** but ALL lose — the noise kills every strategy
- **MACD_Breakout on FIL 1h** is the only survivor across both timeframes — this signal works on 1h but not 15m

---

## Kya Problem Hai (Hinglish)

**Seedhi baat:** 14 mein se 14 strategies TV pe FAIL hui. 1h pe sirf 1 barely profitable, 15m pe 0.

**Tournament backtester aur TradingView bilkul alag kaam karte hain:**
- Tournament sirf `signal × bar_return` multiply karta hai — koi actual trade nahi hota. Ye **math formula** hai, real trading nahi.
- TradingView actual mein position open karta hai, fees lagta hai, compound hota hai. Ye **real execution** hai.
- Tournament mein jo cooldown, circuit breaker, ADX filter hai — wo sab **return stream pe lagta hai**, actual trade pe nahi. Isliye tournament dikhata hai +1%/day lekin TV dikhata hai -95%.

**15m vs 1h ka fark:**
- 15m pe **bohot zyada noise** hai — har 15 min mein signal aata hai, zyada false signals
- 1h pe **kam noise** — isliye MACD_Breakout FIL survive kiya
- Dono pe tournament ke numbers FAKE hain — real results -92% to -100% loss

**Ye gap fix nahi ho sakta** Pine Script mein filters add karke. Kyunki dono systems fundamentally alag hain — ek theoretical hai, ek practical.

**Bottom line:** Tournament ke 225 ALPHA strategies ka 1%/day — ye sirf **paper pe hai**. Real mein 0 kaam ke hain. Ab se sirf **TV-first approach** — jo TV pe chalega wahi final.

---

## Recommendation for Senior
1. **Don't trust backtester numbers** without TV validation
2. **15m is unusable** for these strategies — too noisy
3. **1h might work** but only MACD_Breakout on FIL showed any promise
4. **Focus on 4h timeframe** — less noise, more reliable signals
5. **Add risk management filters to Pine Scripts** before trusting any strategy
6. **TV-first approach** — build on TV, validate on TV, deploy from TV
