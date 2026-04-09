# Machine Learning Role Task Pack - April 9, 2026

## Goal
Test research judgment, realism awareness, and explanation quality.

## Task 1: Range-Bound Ranking Score
Design a simple scoring method for range-bound strategies using:
- ROI/day
- Profit Factor
- Gross Drawdown
- Total Trades
- timeframe preference
- stability flags

Expected qualities:
- raw CAGR is not the primary driver
- bad-status and low-trade outliers are down-ranked
- scoring logic is explainable

## Task 2: Regime-Aware Asset Analysis
Identify which assets in the existing universe look more:
- range-bound
- trend-dominant

Expected output:
- a practical classification note
- brief reasoning for each asset group

## Task 3: Fragility / Overfit Flags
Design flags that reduce confidence in weak candidates:
- too few trades
- extreme drawdown
- narrow asset dependence
- unstable performance across files or windows

Expected qualities:
- simple rules
- usable in reports
- avoids false confidence

## Task 4: Trend vs Range Comparison
Compare current trend winners against new range-bound candidates:
- where does each family work better?
- what should be tested on which assets first?

Expected qualities:
- uses evidence from current repo outputs
- does not overclaim from tiny samples

## Evaluation Rubric
- **Feature choice:** uses meaningful factors
- **Realism awareness:** avoids fake alpha traps
- **Explanation quality:** rankings are interpretable
- **Data skepticism:** handles weak / conflicting evidence well
- **Decision usefulness:** helps choose next tests, not just generate scores
