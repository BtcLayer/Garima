# GARIMA REPOSITORY AUDIT REPORT

Date: 2026-03-24
Repo: https://github.com/BtcLayer/Garima (branch: main)
Auditor: Principal Quant Systems Architect Review

## 1. Executive Summary

This repository is a backtesting-focused Telegram bot that runs 230+ indicator-combination strategies across 10 crypto assets and 3 timeframes, with Gemini AI-powered analysis. It has no functioning TradingView webhook-to-execution pipeline: the webhook, order execution, event processing, reconciliation, and idempotency modules are all in archive/ and are not wired together or used by anything active. The live-money execution path (src/manager.py) is a minimal 126-line file with hardcoded 0.01 BTC quantity, no position sizing, and no kill-switch.

## 2. Repo Maturity Verdict

PROTOTYPE -- strong on backtesting and Telegram UX, hollow on everything required for live trading.

## 3. What Is Already Done

Backtesting engine with 12 technical indicators (run_strategies_batch.py)
230+ strategy combinations across 20 batch files (strategies/batch_01.py - batch_20.py)
6 years of historical data: 10 assets x 3 TFs, 30 parquet files
Telegram bot with ~25 commands: /backtest, /elite, /auto, /optimize, /validate, /pine, /ask
AI analysis layer via Gemini API (src/brain.py)
Comprehensive backtesting with Sharpe, Sortino, Calmar, drawdown (src/comprehensive_backtest.py)
Auto-optimization with random search over SL/TP/TS parameter space
Data fetcher with pagination and caching (src/data_fetcher.py)
Binance client wrapper with testnet capability (src/binance_client.py)
Pine Script generator for TradingView verification (src/pine_generator.py)
Systemd service file for deployment (deploy/systemd/trading_bot.service)
CI pipeline via GitHub Actions (.github/workflows/ci.yml)
Elite strategy ranking with persistence to elite_ranking.json
Counter-strategy auto-generation for negative-ROI strategies
Multi-chat Telegram support and rate-limit handling

## 4. What Is Partially Done

4.1 TradingView Webhook Ingestion
   Observed: Three separate webhook implementations exist in archive/webhook/, B_Webhook/, and src/core/
   Missing: None are integrated with execution path. No schema validation. Idempotency check is buggy.

4.2 Trade Execution (manager.py)
   Observed: process_signal() calls place_order() with hardcoded quantity=0.01
   Missing: No position sizing, no max position limits, no continuous SL/TP monitoring, no trailing stop in live, no kill-switch, no paper trading toggle, no retry logic

4.3 Order Management / Idempotency (archive/core/)
   Observed: Well-designed OrderManager, IdempotentExecutor, Reconciler, EventLogger
   Missing: All in archive/ and not imported by anything active

4.4 CI/CD
   Observed: pytest on PRs
   Missing: CI always passes with zero tests due to fallback echo

4.5 Signal Processing Pipeline
   Observed: src/bot/main.py reads signals.jsonl, calls process_signal()
   Missing: No signal validation, no schema enforcement, no deduplication, no dead-letter queue

## 5. What Is Completely Missing

Kill-switch — no way to halt all trading instantly (CRITICAL)
Position sizing — hardcoded 0.01 BTC, no % of equity (CRITICAL)
Max drawdown circuit breaker — no daily/weekly loss limits (CRITICAL)
Continuous SL/TP monitoring — only checked on incoming signals (HIGH)
Paper trading / dry-run mode (HIGH)
End-to-end integration — webhook to execution not connected (HIGH)
Schema validation on webhook payloads (HIGH)
Persistent state store — in-memory dicts reset on restart (HIGH)
Alerting on execution failures (MEDIUM)
Rate limiting on order placement (MEDIUM)
Walk-forward / out-of-sample validation (MEDIUM)
Short selling support (MEDIUM)
Slippage modeling (MEDIUM)
Unit tests for any active code (MEDIUM)
Structured logging with rotation (LOW)
Monitoring / Prometheus metrics (LOW)
Docker containerization (LOW)

## 6. Main Technical and Trading Risks

1. No position sizing — hardcoded 0.01 for every trade regardless of asset or balance
2. No continuous SL/TP monitoring — positions unmonitored between signals
3. Backtest-to-live gap — backtester uses computed indicators, live path receives pre-computed TradingView signals
4. Archive code is dead — most sophisticated modules unused
5. File-based signal queue — fragile, can lose signals on crash
6. Backtester VWAP is cumulative (not session-based) — creates unrealistic signals

## 7. Priority Next Steps

P0 — Before Any Real-Money Deployment
1. Implement kill-switch (/killswitch Telegram command)
2. Add position sizing (% of equity, max per asset, max total exposure)
3. Add continuous SL/TP monitoring (background loop, 10-15s interval)
4. Add daily/weekly max loss circuit breaker

P1 — For Reliable MVP
5. Wire archive modules into active path (OrderManager, IdempotentExecutor, EventLogger, Reconciler)
6. Add signal validation with Pydantic schemas on webhook
7. Add paper trading mode
8. Write unit tests for manager.py, binance_client.py, webhook
9. Replace file-based queue with SQLite or Redis
10. Add structured JSON logging

P2 — After MVP
11. Walk-forward validation in backtester
12. Short selling support
13. Slippage and market impact modeling
14. Docker containerization
15. Prometheus metrics + Grafana dashboards
16. Alembic DB migrations (from archive)

## 8. Two-Week Practical Roadmap

Week 1: Safety and Integration
   Mon: Rotate all secrets. Verify .env not tracked. Remove PEM from repo.
   Tue: Build kill-switch. Add max daily loss circuit breaker.
   Wed: Implement position sizing: % equity with max per asset. Add paper trading toggle.
   Thu: Add continuous SL/TP monitoring loop (background thread, 10s, checks Binance ticker).
   Fri: Move OrderManager + IdempotentExecutor + EventLogger from archive to src/. Wire into manager.py.

Week 2: Reliability and Testing
   Mon: Add Pydantic validation to webhook. Replace JSONL queue with SQLite.
   Tue: Write unit tests for manager.py, kill-switch, position sizing. Fix CI.
   Wed: Add structured logging (JSON, levels, rotation). Error alerting to Telegram.
   Thu: Paper-trade end-to-end: TradingView alert -> webhook -> queue -> execution -> reconciliation -> Telegram.
   Fri: Document live deployment runbook. Run 24hr paper trading soak test.

## 9. Final Blunt Recommendation

CONTINUE BUILDING, but do not deploy with real money until P0 is complete.

The backtesting infrastructure is genuinely useful — 230+ strategies, 6 years of data, optimization pipeline, Telegram UX, and AI analysis represent real work. However, the live trading path is dangerously thin. The sophisticated modules in archive/ (order manager, executor, reconciler, event logger) were built correctly but abandoned before integration.

The gap between backtesting maturity (solid) and execution maturity (toy-grade) is the primary risk. Closing that gap is a focused 2-week effort, not a rewrite.

## Compact Assessment Table

Area                      | Status     | Evidence                          | Risk     | Next Action
Repo structure            | OK         | Clean src/strategies/archive      | LOW      | None
TradingView webhook       | FRAGMENTED | 3 copies, none integrated         | HIGH     | Pick one, validate, wire to execution
Signal parsing            | MISSING    | No validation on active path      | HIGH     | Add schema validation
Security                  | NEEDS WORK | Secrets need rotation             | HIGH     | Rotate keys, verify gitignore
Exchange execution        | MINIMAL    | manager.py 126 lines, hardcoded   | HIGH     | Add position sizing, retries
Position sizing / risk    | MISSING    | Hardcoded 0.01 BTC always         | CRITICAL | Implement % equity with limits
SL / TP / kill-switch     | PARTIAL    | Calculated but not monitored      | CRITICAL | Add monitoring loop + kill-switch
Idempotency / dedup       | ARCHIVED   | archive/core/executor.py          | HIGH     | Integrate from archive
Logging / observability   | MINIMAL    | src/logger.py 28 lines            | MEDIUM   | Add structured JSON logging
Error handling / retries  | POOR       | Bare except everywhere            | MEDIUM   | Add retry logic
Secrets/config            | NEEDS WORK | .env pattern established          | HIGH     | Verify not tracked
Paper trading             | MISSING    | Testnet flag exists, no toggle    | HIGH     | Add dry-run mode
Tests / CI                | FAILING    | CI passes with zero tests         | MEDIUM   | Write tests, fix CI
Deployment readiness      | PARTIAL    | Systemd service exists            | MEDIUM   | Add Docker, monitoring
Backtesting engine        | STRONG     | 230+ strats, 6yr data, AI        | LOW      | Add walk-forward validation
Telegram bot UX           | STRONG     | 25+ commands, rate limiting       | LOW      | None urgent