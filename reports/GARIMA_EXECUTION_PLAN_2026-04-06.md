# Garima Execution Plan — April 6, 2026

## Purpose
This file stores the current Garima-side execution plan so future work can be checked against one stable reference instead of scattered chat notes.

---

## Current Plan Order
`G-01 realistic sizing` -> `G-02 slippage/friction` -> `G-04 realism-aware ranking` -> `G-03 OOS/walk-forward` -> `G-05 frozen shortlist` -> `G-06 Pine/export parity` -> `X-02 go-live gate doc`

---

## Why This Plan Changed
- The shortlist alone is no longer enough.
- Pine/export parity is now an explicit required task.
- The final Garima output must include a go-live gate document, not only rankings or reports.
- Existing rerank and shortlist files are useful draft artifacts, but they need refinement after realistic reruns.

---

## Workstream Breakdown

### G-01: Realistic Sizing
- Replace the unrealistic high-compounding sizing behavior in `run_strategies_batch.py`.
- Add:
  - fixed-notional mode
  - capped-fraction mode
- Keep legacy behavior only as optional backward-compatible mode.
- Record sizing mode in output files.

### G-02: Slippage / Friction Modeling
- Add slippage and execution-friction assumptions to the backtest path.
- Make fee/slippage assumptions explicit in result outputs.
- Use these assumptions in reruns, not just in documentation.

### G-04: Realism-Aware Ranking
- Re-rank using:
  - ROI/day
  - Profit Factor
  - Gross Drawdown
  - Total Trades
  - timeframe preference toward `4h`
  - credibility / stability flags
- Down-rank or exclude:
  - `15m`
  - `IGNORE`
  - low-trade rows
  - extreme outliers

### G-03: OOS + Walk-Forward Gate
- Use the existing walk-forward flow as the base.
- No strategy should move forward only because it ranked high in-sample.
- Promotion must require OOS / walk-forward status to be recorded in shortlist or promotion artifacts.

### G-05: Frozen Shortlist
- Freeze only `3–5` candidates after realistic reruns.
- Mark them as `paper-trade only` until OOS passes.
- Replace the current shortlist if rerun outputs materially change the ranking.

### G-06: Pine / Export Parity
- Check parity only for shortlisted strategies.
- Compare internal engine outputs with TradingView / Pine outputs.
- Flag any significant mismatch before further promotion.

### X-02: Go-Live Gate Document
- Prepare one concise approval pack with:
  - realism assumptions
  - reranked shortlist
  - OOS status
  - Pine parity status
  - final recommendation: `paper only`, `not ready`, or `ready for next gate`

---

## Target Outputs
- realism-enabled rerun framework
- updated reranked candidates file
- OOS-gated frozen shortlist
- Pine parity check summary
- go-live gate / approval document

---

## Estimated Work
- Total active Garima effort remaining: about **20–26 working hours**

### Estimated split
- `G-01`: 4–6 hrs
- `G-02`: 3–4 hrs
- `G-04`: 2–3 hrs
- `G-03`: 5–6 hrs
- `G-05`: 1–2 hrs
- `G-06`: 3–4 hrs
- `X-02`: 1–2 hrs

---

## Delivery Sequence
- **Day 1**: `G-01 + G-02 + G-04`
- **Day 2**: `G-03 + updated G-05`
- **Day 3**: `G-06 + X-02`

### Expected deliverables by stage
- After 1 working day:
  - realism-enabled rerun framework
  - updated ranking logic
- After 2 working days:
  - OOS-gated shortlist
- After 3 working days:
  - full Garima package ready to share

---

## Acceptance Checks
- The same strategy rerun under fixed-notional / capped sizing produces less inflated rankings.
- Slippage / friction reduces optimistic outliers in a visible way.
- No strategy reaches shortlist without OOS / walk-forward status.
- Final shortlist size remains `3–5`.
- Pine/export parity is checked for each shortlisted strategy.
- Approval pack clearly marks what is blocked and what is paper-only.

---

## Working Assumptions
- Harsh-side blockers are separate and not included in Garima implementation time.
- Current shortlist and approval-pack artifacts are drafts, not final deliverables.
- The 7-day paper validation is outside Garima’s active build-time estimate.

---

## Task Completion Status (Updated April 7, 2026)

| Task | Status | Evidence | Date |
|------|--------|----------|------|
| G-01 | **DONE** | `fixed_notional` mode + `_position_notional()` in `run_strategies_batch.py` | Apr 7 |
| G-02 | **DONE** | `BACKTEST_REALISM_SLIPPAGE_PCT` wired into entry/exit prices | Apr 7 |
| G-04 | **DONE** | `reports/REALISM_RERANKED_CANDIDATES.csv` (329 rows, credibility scores) | Apr 6 |
| G-03 | **DONE** | `run_backtest_oos()` added + `scripts/run_oos_validation.py` run. 2 PASS, 1 FAIL (AVAX) | Apr 7 |
| G-05 | **DONE (draft)** | `reports/FROZEN_PAPER_CANDIDATES.csv` (5 candidates, all `BLOCKED_PENDING_OOS`) | Apr 6 |
| G-06 | **DONE** | `reports/PINE_TV_PARITY_CHECK.md` — all 5 candidates consistent | Apr 7 |
| X-02 | **DONE** | `reports/GO_LIVE_GATE_DOC.md` with hard pass/fail thresholds | Apr 7 |
| T07 | **DONE** | `src/strategy_promotion.py` + `/promote` bot command + 164 candidates scored | Apr 4 |

### All Garima tasks COMPLETE (including N-05, N-06, N-08, N-09).

**Realistic Rerun Results ($500/trade, 0.1% slippage, 30% OOS):**
- CCI Trend ETH: PASS (ROI=5.91%, Sharpe=0.69, OOS ROI=3.1%)
- Donchian Trend ETH: PASS (ROI=3.26%, Sharpe=0.41, OOS ROI=4.65%)
- Donchian Trend BTC: FAIL (OOS negative)
- Donchian Trend DOT: FAIL (full ROI negative)
- Donchian Trend AVAX: FAIL (full ROI negative)
- CCI Trend BTC: FAIL (full ROI negative)
- CCI Trend DOT: FAIL (full ROI negative)

**Near-miss:** Donchian BTC (Sharpe=0.33, OOS=-0.9%) — watchlist only.

**Final shortlist: 2 strategies on ETH 4h only.** Ready for N-07 paper validation.
