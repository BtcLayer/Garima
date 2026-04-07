# New Script Test Matrix — April 7, 2026

## Purpose
This matrix defines the first-pass validation order for the newly added `pine_new` scripts so testing stays focused on the strongest assets first.

---

## Asset Buckets

### Priority 1
- BTC
- ETH
- SOL
- AVAX
- LINK

### Priority 2
- BNB
- DOT
- ADA
- LDO
- SUI

### Priority 3
- XRP
- LTC
- MAGIC

---

## New Script Matrix

| Script | Strategy Family | First-Pass Assets | Expand Next | Notes |
|--------|------------------|------------------|-------------|-------|
| `donchian_cci_confirm.pine` | Donchian + CCI | ETH, LINK, AVAX, BTC | SUI, DOT, LDO | Strongest fit for clean 4h trend assets |
| `ema_ribbon_donchian_pullback.pine` | EMA Ribbon + Donchian | ETH, SOL, AVAX, LINK, BTC | BNB, ADA | Good for established trend assets |
| `aroon_donchian_fusion.pine` | Aroon + Donchian | LINK, AVAX, ETH, SOL | BNB, BTC | Use 4h first; avoid 15m first-pass |
| `cci_supertrend_donchian.pine` | CCI + Supertrend + Donchian | ETH, BTC, AVAX | LDO, DOT, LINK | High-conviction fusion, lower breadth first |
| `ha_donchian_trend_fusion.pine` | HA Trend + Donchian | ETH, AVAX, LINK | LDO, DOT, SOL | Smoother trend family, good on 4h |

---

## Validation Order
1. Run all new scripts on **Priority 1** assets only
2. Keep timeframe at **4h** for first-pass validation
3. Expand to **Priority 2** only if:
   - ROI/day is respectable
   - PF remains strong
   - GDD stays controlled
   - trade count is not too low
4. Use **Priority 3** only after the above pass succeeds

---

## Working Rule
- `pine/` remains the proven base set
- `pine_new/` is the active experimental/fusion set
- Lower-timeframe testing should not come before the 4h pass for these scripts
