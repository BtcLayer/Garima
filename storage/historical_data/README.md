# Historical Data — Download Instructions

## What This Contains
30 parquet files — 10 crypto assets × 3 timeframes (15m, 1h, 4h)
Period: 2020-01-01 to 2026-03-21 (~6 years)
Total size: ~86MB

## Assets
BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, LINK, LTC (all USDT pairs on Binance Spot)

## How to Download
```bash
cd storage/historical_data/
python ../../scripts/fetch_6yr_data.py
```
This fetches from Binance API in batches of 1000 candles. Takes ~10 minutes.

## File Format
`{SYMBOL}_{TIMEFRAME}_{START}_{END}.parquet`
Example: `ETHUSDT_4h_2020-01-01_2026-03-21.parquet`

Columns: timestamp, open, high, low, close, volume

## Notes
- SOL/AVAX/DOT start later (Aug-Sep 2020)
- Data is gitignored (~86MB) — must download locally
- Server has a copy at `/home/ubuntu/Garima/storage/historical_data/`
- Harsh's 15m data (20 assets, 3yr) is at server: `/home/ubuntu/tradingview_webhook_bot/storage/backtest_data/`
