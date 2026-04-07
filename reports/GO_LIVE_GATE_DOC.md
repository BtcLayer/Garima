# X-02: Go-Live Gate Document

## Purpose
Hard pass/fail checklist before any real capital is deployed. Every item must PASS — one FAIL blocks live trading.

---

## Gate Checklist

### Infrastructure Gates (Harsh-side)

| # | Gate | Threshold | Status | Evidence |
|---|------|-----------|--------|----------|
| H-01 | Server/repo convergence | All live code in GitHub | PENDING | Harsh to confirm |
| H-02 | CI truly blocking | Tests fail → CI fails | PENDING | Harsh to confirm |
| H-03 | Strict webhook auth | Unsigned requests rejected | PENDING | Harsh to confirm |
| H-04 | Research/live separation | No auto-promotion to live | PENDING | Harsh to confirm |
| H-05 | Human approval workflow | Manifest-based promotion only | DONE (T07) | `src/strategy_promotion.py` |

### Research Gates (Garima-side)

| # | Gate | Threshold | Status | Evidence |
|---|------|-----------|--------|----------|
| G-01 | Realistic sizing | Fixed notional, no 95% compounding | PASS | `run_strategies_batch.py` |
| G-02 | Slippage modeled | ≥ 0.05% per trade | PASS | `BACKTEST_REALISM_SLIPPAGE_PCT` |
| G-03 | OOS validation | Retention ≥ 50%, OOS ROI > 0 | RUN PENDING | `scripts/run_oos_validation.py` ready |
| G-04 | Realism ranking | Credibility-scored candidates | PASS | `REALISM_RERANKED_CANDIDATES.csv` |
| G-05 | Frozen shortlist | ≤ 5 candidates, reviewed | PASS | `FROZEN_PAPER_CANDIDATES.csv` |
| G-06 | Pine/TV parity | Tier assignment matches | PASS | `PINE_TV_PARITY_CHECK.md` |

### Validation Gates (Joint)

| # | Gate | Threshold | Status | Evidence |
|---|------|-----------|--------|----------|
| X-01 | 7-day paper validation | PF ≥ 1.5, WR ≥ 50%, MaxDD < 15% | NOT STARTED | Requires G-03 + H gates first |
| X-02 | This gate doc complete | All gates documented | THIS DOC | — |

---

## Hard Pass/Fail Thresholds for Paper-to-Live Promotion

A strategy can move from paper to live ONLY if ALL of these are met during the 7-day paper validation:

| Metric | Minimum | Maximum |
|--------|---------|---------|
| Profit Factor | ≥ 1.5 | — |
| Win Rate | ≥ 50% | — |
| Max Drawdown | — | < 15% |
| Trades in 7 days | ≥ 5 | — |
| Consecutive losses | — | < 5 |
| Daily circuit breaker trips | — | < 2 |
| Signal-to-fill latency | — | < 30 seconds |
| Reconciliation drift | — | < 0.5% |

---

## Frozen Shortlist (Paper Trade Only)

| # | Strategy | Asset | TF | OOS Status | Paper Status |
|---|----------|-------|----|-----------|--------------|
| 1 | Donchian Trend | ETH | 4h | PENDING | BLOCKED |
| 2 | Donchian Trend | SUI | 4h | PENDING | BLOCKED |
| 3 | CCI Trend | LDO | 4h | PENDING | BLOCKED |
| 4 | CCI Trend | ETH | 4h | PENDING | BLOCKED |
| 5 | Donchian Trend | AVAX | 4h | PENDING | BLOCKED |

---

## Decision Authority

| Decision | Who |
|----------|-----|
| Approve strategy for paper | Garima (via `/promote approve`) |
| Approve strategy for live | Harsh + Garima jointly |
| Emergency kill | Either (via `/kill` or circuit breaker) |
| Add new strategy to shortlist | Requires full G-01→G-06 pipeline |

---

## Current Overall Status

```
Infrastructure:  PARTIALLY READY (H-01 to H-04 pending from Harsh)
Research:        READY (G-01 to G-06 complete, G-03 run pending)
Validation:      NOT STARTED (X-01 blocked by infrastructure gates)
```

**Verdict: NOT READY for live capital. Paper trading can begin once G-03 OOS validation passes and Harsh confirms H-01 through H-04.**
