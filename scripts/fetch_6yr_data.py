"""
Download 6 years of historical data for all 10 assets × 3 timeframes.
Bypasses cache to get fresh, complete data.

Expected candle counts (approx):
  15m: ~210,000 candles per asset
  1h:  ~52,500 candles per asset
  4h:  ~13,100 candles per asset

Run: python fetch_6yr_data.py
"""

import os
import sys
import time
import pandas as pd
import requests
from datetime import datetime

# Config
CACHE_DIR = "storage/historical_data"
os.makedirs(CACHE_DIR, exist_ok=True)

BASE_URL = "https://api.binance.com/api/v3/klines"
MAX_CANDLES = 1000
DELAY = 0.25  # seconds between API calls

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT",
]
TIMEFRAMES = ["15m", "1h", "4h"]

START_DATE = "2020-01-01"
END_DATE = "2026-03-21"

# Some assets listed later — use their actual start dates
ASSET_START = {
    "SOLUSDT": "2020-08-11",
    "AVAXUSDT": "2020-09-22",
    "DOTUSDT": "2020-08-18",
}


def fetch_all_candles(symbol, timeframe, start_date, end_date):
    """Fetch all candles by paginating forward from start_date."""
    start_ts = int(datetime.fromisoformat(start_date).timestamp() * 1000)
    end_ts = int(datetime.fromisoformat(end_date).timestamp() * 1000)

    all_candles = []
    batch = 0

    while start_ts < end_ts:
        params = {
            "symbol": symbol,
            "interval": timeframe,
            "startTime": start_ts,
            "endTime": end_ts,
            "limit": MAX_CANDLES,
        }

        for attempt in range(3):
            try:
                r = requests.get(BASE_URL, params=params, timeout=30)
                if r.status_code == 429:
                    wait = int(r.headers.get("Retry-After", 30))
                    print(f"    Rate limited — waiting {wait}s...")
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                data = r.json()
                break
            except Exception as e:
                print(f"    Retry {attempt+1}/3: {e}")
                time.sleep(2)
                data = []

        if not data:
            break

        batch += 1
        all_candles.extend(data)

        # Move past last candle
        last_ts = data[-1][0]
        if last_ts <= start_ts:
            break
        start_ts = last_ts + 1

        if len(data) < MAX_CANDLES:
            break  # No more data

        if batch % 20 == 0:
            print(f"    ... batch {batch}, {len(all_candles)} candles so far")

        time.sleep(DELAY)

    return all_candles


def to_dataframe(candles):
    """Convert raw Binance klines to clean DataFrame."""
    if not candles:
        return pd.DataFrame()

    df = pd.DataFrame(candles, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore",
    ])

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    df = df[["timestamp", "open", "high", "low", "close", "volume"]]
    df = df.drop_duplicates(subset=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def main():
    total = len(SYMBOLS) * len(TIMEFRAMES)
    done = 0
    skipped = 0

    print(f"Downloading 6yr data: {len(SYMBOLS)} assets x {len(TIMEFRAMES)} TFs = {total} files")
    print(f"Period: {START_DATE} to {END_DATE}")
    print("=" * 60)

    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            done += 1
            key = f"{symbol}_{tf}"
            start = ASSET_START.get(symbol, START_DATE)
            filename = f"{symbol}_{tf}_{start}_{END_DATE}.parquet"
            filepath = os.path.join(CACHE_DIR, filename)

            # Skip if already downloaded with enough data
            if os.path.exists(filepath):
                existing = pd.read_parquet(filepath)
                if len(existing) > 500:  # has real data
                    print(f"[{done}/{total}] {key}: already have {len(existing)} candles — skip")
                    skipped += 1
                    continue

            print(f"[{done}/{total}] {key}: fetching {start} to {END_DATE}...")

            candles = fetch_all_candles(symbol, tf, start, END_DATE)
            df = to_dataframe(candles)

            if df.empty:
                print(f"  NO DATA returned!")
                continue

            df.to_parquet(filepath, index=False)
            actual_start = str(df["timestamp"].min())[:10]
            actual_end = str(df["timestamp"].max())[:10]
            print(f"  Saved: {len(df)} candles ({actual_start} to {actual_end})")

    print("\n" + "=" * 60)
    print(f"Done! {done - skipped} downloaded, {skipped} skipped (already had data)")


if __name__ == "__main__":
    main()
