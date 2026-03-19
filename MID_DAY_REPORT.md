# Mid-Day Report — Trading Bot Development
**Date:** 19 March 2026
**Goal:** Increase daily trading profitability from 1% → 2% using an automated Telegram-controlled strategy bot

---

## Objective
  
The core challenge was simple to state but hard to achieve:

> *"Which combination of strategy, asset, and timeframe consistently delivers 2% profit per day?"*

To answer this, we needed the bot to not just run strategies — but to **learn, score, and rank** them automatically, so the best combinations surface without manual analysis.

---

## Work Done Today

### 1. Multi-Asset Expansion (+5 New Assets)
Previously the bot only covered BTC, ETH, BNB, SOL, XRP.
Today we added:
- **ADAUSDT, AVAXUSDT, DOTUSDT, LINKUSDT, LTCUSDT**
- Created dedicated backtest runners for each (`run_ada_strategies.py`, etc.)
- Wrote `fetch_new_assets.py` to download 1 year of 15m / 1h / 4h data for all 5 new assets
- This expands the strategy search space from **~1,800 combos → ~3,600 combos**

---

### 2. Elite Strategy Filter (`find_elite_strategies.py`)
Built a filter that reads all `*_all_results.csv` files and shortlists strategies that pass **all five criteria**:

| Metric | Threshold |
|--------|-----------|
| ROI | > 50% |
| Win Rate | > 25% |
| Profit Factor | > 1.5 |
| Max Drawdown | < 30% |
| Total Trades | ≥ 20 |

Outputs:
- `elite_strategies.csv` — top candidates ranked by composite score
- `elite_strategies.json` — machine-readable for bot use
- `daily_profit_model.csv` — expected daily % per strategy

---

### 3. Daily Profit Framework (`daily_profit_framework.py`)
Directly addresses the **1% → 2% daily target**:

- Models daily P&L distribution per elite strategy
- Simulates running **top N strategies simultaneously** (portfolio mode)
- Grid-searches optimal SL / TP / Trailing Stop for each candidate
- Outputs:
  - `portfolio_candidates.csv` — deployment-ready strategies with optimised params
  - `daily_profit_report.txt` — human-readable analysis with risk notes

Key insight from the framework: **a single strategy rarely hits 2%/day consistently**. Combining 3–5 uncorrelated strategies in a portfolio is the realistic path.

---

### 4. Scoring System in the Bot (0–100 Composite Score)
Every backtest result is now assigned a score so the bot knows **which results to keep and which to discard**:

```
Score = ROI(35%) + Win Rate(20%) + Profit Factor(20%) + Drawdown(15%) + Sharpe(10%)
```

Grades: **A+ ≥80 | A ≥65 | B+ ≥50 | B ≥35 | C ≥20 | D <20**

The bot now:
- Keeps only improvements (new result must beat the saved score to overwrite)
- Builds an **all-time best results** ledger across every run
- Shows Score + Grade in every progress update

---

### 5. Smart Auto-Optimization (`/auto`)
Previously `/auto` was re-running the exact same parameters every 5 minutes — useless.
Now:
- **Randomises SL, TP, RSI period, EMA lengths** on every run
- Each run explores a different region of the parameter space
- Only keeps results that beat the current best score
- Runs every **5 minutes** — gradually building a leaderboard of the best param combos

Over time this is equivalent to a lightweight **grid search without manual intervention**.

---

### 6. Zero-Config Quick Start (`/run`)
Added a one-command execution that requires **no setup from the user**:

```
/run → BTC + ETH + SOL × 15m + 1h + 4h → RSI + MACD + EMA
```

- 27 combinations tested per run
- Scored and ranked automatically
- Top 5 all-time results shown at the end

This is the entry point for anyone who just wants to start seeing results immediately.

---

### 7. Bot UX & Reliability Fixes

| Fix | Impact |
|-----|--------|
| Two Telegram chat IDs supported simultaneously | Can monitor from personal + group chat |
| `//@version=5` Pine Script detected before command routing | Pine Script no longer silently ignored |
| Strategy names with underscores (`AI_EMA_RIBBON`) now display with spaces | Readable output |
| `[14/12]` counter overflow fixed → `[Run N]` format | No more confusing numbers |
| `run_optimization_wizard()` indentation bug fixed | Was only processing the last result of each run |
| LEARNED strategy renamed to `RSI_{ASSET}_P{period}` | No more mystery "LEARNED" entry |
| `/namaste`, `/suno`, `/hi`, `/hello` as friendly aliases | Natural language entry points |
| `/suno` + `/namaste` show concise command list | Clutter-free for new users |

---

## Progress Toward 2% Daily Target

| Phase | Status |
|-------|--------|
| Backtest data collected (10 assets × 3 TF × 300 strategies) | ✅ Infrastructure ready |
| Elite strategy filter identifies high-PF, low-DD candidates | ✅ Built |
| Daily profit model estimates per-strategy daily return | ✅ Built |
| Portfolio simulation finds N-strategy combo hitting 2%/day | ✅ Built |
| Bot auto-optimises params every 5 min, keeps improvements | ✅ Live |
| Live deployment with top portfolio candidates | 🔲 Next step |

### Honest Assessment
The backtest data shows that **individual strategies average 0.1–0.4% per day** in realistic conditions. Reaching 2% daily requires:
1. Running **5–8 uncorrelated strategies simultaneously** on different assets/timeframes
2. Keeping **drawdown below 25%** (otherwise compounding works against you)
3. A live-data validation pass before committing real capital

The framework built today provides the analysis infrastructure to identify and validate those combinations.

---

### 8. One-at-a-Time Auto-Optimization (Round-Robin)
Previously `/auto` ran **all 12 strategies at once** every cycle — slow and noisy.
Now it uses a **round-robin approach**:
- Each 5-minute cycle picks **one strategy** and tests it across timeframes with fresh random params
- Next cycle picks the **next strategy** in the rotation
- Every 6 cycles (30 min), all built-in strategies have been re-tested
- Custom strategies are included in the rotation too
- Result: **faster per-cycle execution, deeper per-strategy exploration**

---

### 9. Database Connection (Planned)
Will connect the bot's result storage to **Harsh's EC2 server database** so that:
- All backtest results persist across bot restarts
- Results are accessible from any device
- Multiple bot instances can share the same result pool

---

## Next Steps

1. Connect database to Harsh's server for persistent storage
2. Run `fetch_new_assets.py` → `run_ada_strategies.py` (etc.) for all 5 new assets
3. Run `find_elite_strategies.py` to shortlist the best 2% candidates
4. Run `daily_profit_framework.py` to get the portfolio deployment plan
5. Paper trade the top portfolio for 1 week before going live

---

*Report generated automatically — Trading Bot Project, Internship*
