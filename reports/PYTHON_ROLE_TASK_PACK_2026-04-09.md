# Python Role Task Pack - April 9, 2026

## Goal
Test real engineering behavior, not just coding speed.

## Task 1: Reusable Range-Bound Backtest Runner
Build a reusable runner for range-bound strategies that can:
- accept multiple strategy functions
- run across a chosen asset list and timeframe list
- return a normalized result table

Expected qualities:
- functions are reusable
- no hardcoded asset-only branches
- clear inputs / outputs

## Task 2: Result Merge + Clean Summary Utility
Build a small utility that:
- merges multiple range-bound result files
- standardizes columns
- removes duplicate rows cleanly
- produces one compact quality summary

Expected qualities:
- handles missing columns
- handles mixed schemas
- produces readable output

## Task 3: Pine Webhook Payload Validator
Build a validator that checks Pine files for:
- presence of webhook secret
- valid action labels
- expected JSON fields
- consistent strategy names across alert payloads

Expected qualities:
- catches malformed payload strings
- reports file-level failures clearly
- easy to run again on future scripts

## Task 4: Strategy Quality Report Generator
Build a report utility that summarizes:
- ROI/day
- Profit Factor
- Gross Drawdown
- Total Trades
- timeframe quality
- shortlist eligibility

Expected qualities:
- simple output
- practical interpretation
- easy to plug into reports/

## Evaluation Rubric
- **Code clarity:** easy to read, sensible naming
- **Modularity:** reusable pieces, not one giant script
- **Testability:** functions can be checked in isolation
- **Edge cases:** handles missing/dirty data
- **Builder mindset:** improves structure instead of adding clutter
