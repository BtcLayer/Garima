# Garima Approval Pack

## Summary
- Frozen shortlist size: 5 paper-trade candidates from `combo_strategy_results_good.csv`.
- `combo_strategy_results_cagr.csv` and `combo_strategy_results_cagr2.csv` are treated as screening inputs, not direct promotion inputs.
- No strategy is promotion-ready for live deployment until walk-forward / OOS validation passes.

## Realism Assumptions
- Fixed notional per trade: `$1000`
- Max position cap: `10%` of current equity
- Slippage assumption: `0.05%` per execution
- Preferred timeframe: `4h`

## Frozen Paper Candidates
| Strategy | Asset | TF | ROI/day | PF | GDD% | Trades | Gate |
|----------|-------|----|---------|----|------|--------|------|
| Donchian Trend | ETH | 4h | 1.1938 | 12.05 | 9.05 | 1263 | BLOCKED_PENDING_OOS |
| Donchian Trend | SUI | 4h | 2.1522 | 9.86 | 11.27 | 378 | BLOCKED_PENDING_OOS |
| CCI Trend | LDO | 4h | 1.4230 | 10.67 | 10.33 | 529 | BLOCKED_PENDING_OOS |
| CCI Trend | ETH | 4h | 0.8062 | 9.07 | 12.39 | 1082 | BLOCKED_PENDING_OOS |
| Donchian Trend | AVAX | 4h | 1.3242 | 8.37 | 13.55 | 807 | BLOCKED_PENDING_OOS |

## Selection Notes
- **Donchian Trend / ETH / 4h**: 4h candidate with ROI/day 1.1938, PF 12.05, GDD 9.05%, and 1263 trades from the validated base sheet. Paper-trade only until walk-forward/OOS passes.
- **Donchian Trend / SUI / 4h**: 4h candidate with ROI/day 2.1522, PF 9.86, GDD 11.27%, and 378 trades from the validated base sheet. Paper-trade only until walk-forward/OOS passes.
- **CCI Trend / LDO / 4h**: 4h candidate with ROI/day 1.4230, PF 10.67, GDD 10.33%, and 529 trades from the validated base sheet. Paper-trade only until walk-forward/OOS passes.
- **CCI Trend / ETH / 4h**: 4h candidate with ROI/day 0.8062, PF 9.07, GDD 12.39%, and 1082 trades from the validated base sheet. Good candidate but drawdown needs extra watch in paper validation.
- **Donchian Trend / AVAX / 4h**: 4h candidate with ROI/day 1.3242, PF 8.37, GDD 13.55%, and 807 trades from the validated base sheet. Good candidate but drawdown needs extra watch in paper validation.

## Promotion Rule
- Current state: `paper-trade candidate only`.
- Required next gate: `walk-forward / OOS PASS` before any approval for live use.
- Until that gate is recorded, these candidates should not be moved into the live approved manifest.
