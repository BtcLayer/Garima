# U-09 / P-10: Go-Live Decision Memo

**Date:** April 14, 2026
**Paper Window:** April 7–14, 2026
**Reviewer:** Garima
**Decision:** [ ] NO_GO [ ] PAPER_ONLY [ ] READY_FOR_TINY_CAPITAL

---

## Approved Strategies Under Test

| Strategy | Asset | TF | Backtest Hash |
|----------|-------|----|---------------|
| CCI Trend | ETHUSDT | 4h | d4ae43d256c0 |
| Donchian Trend | ETHUSDT | 4h | 686adb63d527 |

---

## 7-Day Paper Results (fill daily)

| Metric | CCI Trend ETH | Donchian Trend ETH | Threshold | Pass? |
|--------|--------------|-------------------|-----------|-------|
| Trades executed | | | >= 5 | |
| PF | | | >= 1.5 | |
| Win Rate | | | >= 50% | |
| Max Drawdown | | | < 15% | |
| Consecutive losses | | | < 5 | |
| Circuit breaker trips | | | < 2 | |
| Signal-to-fill latency | | | < 30s | |
| Critical reconciler drifts | | | = 0 | |
| High reconciler drifts | | | <= 1 total | |
| Blocked signals (unexplained) | | | = 0 | |
| Duplicate executions | | | = 0 | |
| Invalid request accepted | | | = 0 | |
| Queue stalls | | | = 0 | |
| Inventory READY rate | | | = 100% every day | |
| BUY path observed | | | >= 1 | |
| SELL path observed | | | >= 1 | |
| Execution-plane diff | | | = none | |

---

## Paper vs Shortlist Comparison (P-07)

| Metric | Shortlist Expected | Paper Actual | Match? |
|--------|-------------------|-------------|--------|
| Trade frequency | ~2-3/week | | |
| Avg win size | | | |
| Avg loss size | | | |
| DD pattern | < 6% | | |
| Signal quality | Both BUY+SELL | | |
| Last approved-signal timestamp | | | |

---

## Daily Log (fill each day)

| Day | Date | Signals | Trades | Inventory | Drifts | Diff Clean? |
|-----|------|---------|--------|-----------|--------|-------------|
| 1 | Apr 7 | | | | | |
| 2 | Apr 8 | | | | | |
| 3 | Apr 9 | | | | | |
| 4 | Apr 10 | | | | | |
| 5 | Apr 11 | | | | | |
| 6 | Apr 12 | | | | | |
| 7 | Apr 13 | | | | | |

---

## NO_GO Triggers (any = immediate reject)

- [ ] Critical reconciler drift occurred
- [ ] Duplicate execution from single signal
- [ ] Queue stall > 30 minutes
- [ ] Missing SL/TP on any entry
- [ ] Inventory drift (LIVE_VERIFIED -> MISSING)
- [ ] Invalid request accepted by webhook
- [ ] Execution-plane code changed during window
- [ ] Paper behavior contradicts shortlist expectations

---

## Decision Criteria

**READY_FOR_TINY_CAPITAL** — all must be true:
- 7 full days completed
- Inventory READY every day
- No critical reconciler drift
- No duplicate execution
- No missing SL/TP on entries
- No unexplained blocked signals
- No queue stalls
- At least one BUY and one SELL path observed
- PF >= 1.5
- WR >= 50%
- Max DD < 15%
- Behavior matches shortlist expectations

**PAPER_ONLY** — if:
- Infra is clean, no hard NO_GO trigger
- But evidence is too thin or too quiet
- Or metrics acceptable but not convincing

**NO_GO** — if:
- Any hard trigger occurs
- Or paper behavior clearly contradicts shortlist

---

## Decision

**Verdict:** _______________

**Reasoning:**


**Next action:**
- NO_GO -> fix issues, rerun 7-day window
- PAPER_ONLY -> continue paper, extend window
- READY_FOR_TINY_CAPITAL -> deploy with $100 max position, 1 strategy only

**Signed:** Garima | Date: ___
