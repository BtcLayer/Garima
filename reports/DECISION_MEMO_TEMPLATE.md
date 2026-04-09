# U-09 / P-10: Go-Live Decision Memo

**Date:** April 14, 2026
**Paper Window:** April 7-14, 2026
**Reviewer:** Garima
**Decision:** [ ] NO_GO [ ] PAPER_ONLY [ ] READY_FOR_TINY_CAPITAL

---

## Decision Scope

This memo applies only to the current frozen paper lane:
- CCI Trend on ETHUSDT 4h
- Donchian Trend on ETHUSDT 4h

This memo does not approve or reject:
- research-lane strategies such as G23-G36
- AVAX, SUI, DOT, LDO, LINK, or BTC research winners
- any broader strategy set outside the current ETHUSDT 4h paper pair

Out-of-scope observations must be tracked separately unless they directly affect the current ETH pair or the shared execution plane.

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

| Metric | Shortlist Expected | Paper Actual (Day 1-2) | Match? |
|--------|-------------------|------------------------|--------|
| Trade frequency | ~2-3/week | 4 in 2 days (~14/week) | HIGH - monitor |
| Avg win size | ~5-12% (TP/trail) | Pending - no closes yet | TBD |
| Avg loss size | ~1.5% (SL) | Pending - no closes yet | TBD |
| DD pattern | < 6% | 0% (no closed trades) | OK |
| Signal quality | Both BUY+SELL for current ETH pair | BUY only (4x BUY on approved ETH pair) | SELL not yet observed |
| Last approved-signal timestamp | Recent | Apr 8 00:00 UTC | OK |
| Last bot-visible signal timestamp | Recent | Apr 8 20:00 UTC (BTC PSAR, out of scope) | INFO only |
| Unapproved signals affecting current ETH pair | None | None confirmed on approved ETH pair | OK |

### Separate Research-Lane Note (Do Not Mix Into Verdict Scope)

- Observed separately: `CCI_Trend` signal activity on `AVAXUSDT`
- Classification: research / out-of-scope observation
- Verdict impact: none by itself
- Reason: this memo evaluates only the frozen ETHUSDT 4h paper pair
- Action: track separately under research-lane notes, not as a fail against the current paper pair

---

## Daily Log (fill each day)

| Day | Date | Signals | Trades | Inventory | Drifts | Diff Clean? |
|-----|------|---------|--------|-----------|--------|-------------|
| 1 | Apr 7 | 2 BUY (CCI+Donchian ETH) | 2 | 2/2 READY | 0 | Yes |
| 2 | Apr 8 | 2 BUY (CCI+Donchian ETH) | 2 | 2/2 READY | 0 | Yes |
| 3 | Apr 9 | No new approved-pair signals seen yet in fetched sheet snapshot | 0 | Pending | Pending | Pending |
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

**Scope rule:** the final verdict below must be written for the current approved ETHUSDT 4h pair only.

**READY_FOR_TINY_CAPITAL** - all must be true:
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

**PAPER_ONLY** - if:
- Infra is clean, no hard NO_GO trigger
- But evidence is too thin or too quiet
- Or metrics acceptable but not convincing

**NO_GO** - if:
- Any hard trigger occurs
- Or paper behavior clearly contradicts shortlist

---

## Decision

**Verdict:** _______________

**Verdict scope statement:** This verdict applies only to `CCI Trend ETHUSDT 4h` and `Donchian Trend ETHUSDT 4h` in the frozen Apr 7-14 paper lane.

---

### Branch A: NO_GO

**Trigger(s) observed:**
- [ ] _list specific trigger(s) from NO_GO section above_

**Evidence:**
- Incident log: ___
- Screenshot/log link: ___

**Root cause:** ___

**Scope confirmation:** The NO_GO verdict must state whether the failure was on the approved ETH pair itself or in shared execution infrastructure. Research-only observations do not trigger NO_GO for this memo by themselves.

**Next action:**
1. Fix root cause (owner: ___, ETA: ___)
2. Reset paper window - new 7-day run starts on: ___
3. Re-verify inventory + manifest before restart

---

### Branch B: PAPER_ONLY

**Why not NO_GO:** No hard triggers fired. Infra is clean.

**Why not READY:** ___ (e.g., too few trades, evidence too thin, one metric borderline)

**Evidence gap:**
- Metric(s) that are acceptable but not convincing: ___
- Days with missing/thin data: ___

**Next action:**
1. Extend paper window by ___ days (new end: ___)
2. Specific thing to watch: ___
3. Re-evaluate on new end date with same criteria

**Scope confirmation:** PAPER_ONLY here applies only to the current ETH 4h pair and must not be read as a judgment on the wider research lane.

---

### Branch C: READY_FOR_TINY_CAPITAL

**All criteria met:**
- [ ] 7 full days completed
- [ ] Inventory READY every day
- [ ] No critical reconciler drift
- [ ] No duplicate execution
- [ ] No missing SL/TP
- [ ] No unexplained blocked signals
- [ ] No queue stalls
- [ ] BUY + SELL both observed
- [ ] PF >= 1.5
- [ ] WR >= 50%
- [ ] Max DD < 15%
- [ ] Behavior matches shortlist

**Deployment plan:**
1. Strategy: ___ (start with 1 only)
2. Max position: $100
3. Asset: ETHUSDT 4h
4. Monitor period: 7 days tiny-capital
5. Escalation criteria: DD > 10% = pause, 2+ consecutive losses = reduce size

**Scope confirmation:** READY_FOR_TINY_CAPITAL here means the current ETH 4h pair only. No other manifest or research-lane strategies are included by implication.

**Signed:** Garima | Date: ___
