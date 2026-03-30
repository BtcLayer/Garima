# Strategy Runner Scripts - Usage Guide

## Overview
These 5 scripts run ALL strategies on different assets across all timeframes (15m, 1h, 4h).

## Files Created

| Script | Asset | Output CSV |
|--------|-------|------------|
| `run_btc_strategies.py` | BTCUSDT | `btc_all_results.csv` |
| `run_eth_strategies.py` | ETHUSDT | `eth_all_results.csv` |
| `run_bnb_strategies.py` | BNBUSDT | `bnb_all_results.csv` |
| `run_sol_strategies.py` | SOLUSDT | `sol_all_results.csv` |
| `run_xrp_strategies.py` | XRPUSDT | `xrp_all_results.csv` |
| `combine_all_results.py` | ALL | `all_assets_strategies_combined.csv` |

## How to Run

### Option 1: Run individual scripts
```bash
# Terminal 1 - Run BTC strategies
python run_btc_strategies.py

# Terminal 2 - Run ETH strategies  
python run_eth_strategies.py

# Terminal 3 - Run BNB strategies
python run_bnb_strategies.py

# Terminal 4 - Run SOL strategies
python run_sol_strategies.py

# Terminal 5 - Run XRP strategies
python run_xrp_strategies.py
```

### Option 2: Run all in sequence
```bash
python run_btc_strategies.py
python run_eth_strategies.py
python run_bnb_strategies.py
python run_sol_strategies.py
python run_xrp_strategies.py
```

### Combine Results
```bash
python combine_all_results.py
```

## What Each Script Does

1. **Loads ALL strategies** from the `strategies/` folder (230 strategies total)
2. **Tests each strategy** on 3 timeframes (15m, 1h, 4h)
3. **Records results**: ROI, Win Rate, Trade Count, SL, TP
4. **Saves to CSV** with asset-specific filename

## Output CSV Format

| Column | Description |
|--------|-------------|
| Asset | Trading pair (e.g., BTCUSDT) |
| Timeframe | 15m, 1h, or 4h |
| Strategy_ID | Unique strategy ID |
| Strategy_Name | Strategy name |
| Strategies | Comma-separated list of indicators |
| Trades | Number of trades executed |
| Win_Rate | Percentage of winning trades |
| ROI | Return on Investment (%) |
| SL | Stop Loss |
| TP | Take Profit |

## Common CSV Output

After running `combine_all_results.py`, you'll get:
- `all_assets_strategies_combined.csv` - Contains ALL results from all assets
- Top profitable strategies sorted by ROI
- Summary statistics by asset

## Notes

- BTC, ETH, BNB use local parquet data (fast)
- SOL, XRP fetch from Binance API (requires internet)
- Each script tests 230 strategies × 3 timeframes = 690 tests per asset
- With 5 assets = 3,450 total strategy tests!
