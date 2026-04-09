# Range-Bound Research Lane - April 9, 2026

**Status:** RESEARCH ONLY - NOT part of the frozen paper manifest

## Why This Lane Exists
Most recent winning DNA is trend-breakout heavy:
- Donchian
- CCI trend
- Aroon / ADX breakout
- wide breakout-confirm structures

That leaves one gap: sideways / mean-reverting behavior. This lane explores that gap without disturbing the active paper window.

## Existing Repo Clues Used As Base
- `all_strategies/tv_first_19_BB_Squeeze_V2.pine`
- `all_strategies/tv_first_33_Breakout_Retest.pine`
- `scripts/generate_squeeze_variations.py`
- `scripts/test_squeeze.py`
- `scripts/squeeze_screener.py`
- `scripts/paper_trade_squeeze.py`

## First Range-Bound Families
1. **BB RSI Range Revert**
- mean reversion near outer Bollinger bands
- RSI oversold / overbought confirmation
- soft trend filter instead of strict breakout trend alignment

2. **Donchian Midline Fade**
- fade stretched moves back toward the Donchian midline
- use RSI extremes plus rejection candles
- best for sideways 4h conditions

3. **Squeeze Fade Retest**
- do not chase the first squeeze release
- wait for squeeze expansion, then fade exhaustion back toward the basis

## Parameter Template For First Pass
- timeframe: `4h`
- SL: `1.5%`
- TP: `8%` to `10%`
- trail: `2%` to `3%` only when the setup benefits from a soft lock-in
- max trades/day: `3`
- cooldown after `3` consecutive losses
- daily breaker near `-3%`

## First-Pass Assets
Priority 1:
- `ETHUSDT`
- `LINKUSDT`
- `DOTUSDT`
- `BNBUSDT`
- `SOLUSDT`

Priority 2:
- `AVAXUSDT`
- `ADAUSDT`
- `LDOUSDT`
- `SUIUSDT`

Avoid first-pass focus on:
- `15m`
- very low-liquidity names
- anything outside the existing 4h validation habit

## First Batch Added Today
- `RB01_BB_RSI_Range_Revert.pine`
- `RB02_Donchian_Midline_Fade.pine`
- `RB03_Squeeze_Fade_Retest.pine`

## Success Criteria
- keep this lane fully separate from the paper manifest
- produce TV-testable range-bound scripts
- decide which assets show the cleanest range behavior
- collect research evidence, not deployment claims
