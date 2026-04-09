# Developing Personality Evaluation - April 9, 2026

## Purpose
Check whether a person behaves like a developer-builder under practical project conditions.

## What To Look For
- writes reusable code instead of hardcoded one-offs
- states assumptions clearly
- handles failure cases and dirty data
- keeps research, paper, and live lanes separate
- proposes validation, not just generation

## Test 1: Messy Results Cleanup
Prompt:
`Given multiple messy CSV outputs with overlapping strategy rows, build a clean ranking utility and explain your cleanup rules.`

What this reveals:
- structure thinking
- data hygiene
- practical judgment

## Test 2: Improve Weak Strategy Ideas
Prompt:
`Given 3 weak strategy ideas, improve them into testable versions and justify the changes.`

What this reveals:
- whether the person can refine instead of only invent
- whether they reuse proven patterns

## Test 3: Webhook Payload Validation
Prompt:
`Given several Pine scripts with inconsistent alert payloads, build a validator and add test cases for malformed fields.`

What this reveals:
- defensive engineering
- ability to build tools, not only outputs

## Test 4: Conflicting Evidence Decision
Prompt:
`A strategy looks strong in internal backtests but weak on TradingView. Recommend the correct next step and explain why.`

What this reveals:
- realism mindset
- evidence hierarchy
- discipline under ambiguity

## Scoring Lens
- **Ownership:** do they clarify the real problem?
- **Code quality:** do they produce maintainable work?
- **Validation instinct:** do they ask how to trust the result?
- **Separation discipline:** do they keep research away from live?
- **Communication:** do they explain tradeoffs without overclaiming?
