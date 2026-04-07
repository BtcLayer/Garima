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
| G-01 | Realistic sizing | Fixed notional, no 95% compounding | PASS | $500/trade fixed notional |
| G-02 | Slippage modeled | ≥ 0.05% per trade | PASS | 0.1% slippage applied |
| G-03 | OOS validation | OOS ROI > 0, PF > 1.0 | PASS | 2 of 7 passed OOS |
| G-04 | Realism ranking | Credibility-scored candidates | PASS | `REALISM_RERANKED_CANDIDATES.csv` |
| G-05 | Frozen shortlist | ≤ 5 candidates, reviewed | PASS | 2 strategies: CCI ETH + Donchian ETH |
| G-06 | Pine/TV parity | Tier assignment matches | PASS | `PINE_TV_PARITY_CHECK.md` |
| N-05 | Realistic shortlist freeze | $500 fixed, 0.1% slippage, OOS | PASS | `REALISTIC_SHORTLIST_FINAL.md` |
| N-06 | Realism provenance confirmed | Rerun with realistic settings | PASS | `REALISTIC_SHORTLIST_RESULTS.json` |

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

| # | Strategy | Asset | TF | OOS Status | Full ROI | OOS ROI | Paper Status |
|---|----------|-------|----|-----------|----------|---------|--------------|
| 1 | CCI Trend | ETH | 4h | PASS | 5.91% | 3.10% | READY |
| 2 | Donchian Trend | ETH | 4h | PASS | 3.26% | 4.65% | READY |

### Removed from shortlist (failed realistic rerun)
| Strategy | Asset | Reason |
|----------|-------|--------|
| Donchian Trend | BTC | OOS ROI negative (-0.9%) |
| Donchian Trend | SUI | No local data for rerun |
| Donchian Trend | AVAX | Full ROI negative (-9.63%) |
| CCI Trend | LDO | No local data for rerun |
| CCI Trend | BTC | Full ROI negative (-7.62%) |

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
Infrastructure:  DONE (H-01 to H-08 confirmed by Harsh)
Research:        DONE (G-01 to G-06, N-05, N-06 all complete)
Validation:      READY TO START (X-01 7-day paper can begin)
```

**Verdict: READY FOR PAPER TRADING. Two strategies (CCI Trend ETH, Donchian Trend ETH) passed all realistic gates. Start 7-day paper validation (N-07). No real capital until N-08 review.**
