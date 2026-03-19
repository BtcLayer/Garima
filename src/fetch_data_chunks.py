"""
Chunk-based Data Fetcher

Fetches historical data by splitting the date range into smaller chunks.
Each chunk is saved separately, then merged into a single dataset.

This approach avoids complex API pagination issues.

Usage:
    python src/fetch_data_chunks.py --symbol BTCUSDT --timeframe 15m --days 365
    python src/fetch_data_chunks.py --symbol BTCUSDT --timeframe 1h --days 180
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration
CHUNK_DAYS = 30  # Fetch 30 days at a time
MAX_CANDLES = 1000  # Binance limit per request
REQUEST_DELAY = 0.2
BASE_URL = "https://api.binance.com/api/v3"

# Output directory
OUTPUT_DIR = Path("storage/historical_data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def fetch_klines(symbol: str, interval: str, start_ts: int, end_ts: int, limit: int = 1000) -> List:
    """Fetch klines from Binance for a given time range."""
    url = f"{BASE_URL}/klines"
    
    params = {
        'symbol': symbol,
        'interval': interval,
        'startTime': start_ts,
        'endTime': end_ts,
        'limit': limit
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return []


def date_range_list(start_date: datetime, end_date: datetime, chunk_days: int) -> List[tuple]:
    """Split a date range into chunks."""
    ranges = []
    current = start_date
    
    while current < end_date:
        chunk_end = min(current + timedelta(days=chunk_days), end_date)
        ranges.append((current, chunk_end))
        current = chunk_end
    
    return ranges


def fetch_and_save_chunks(symbol: str, timeframe: str, start_date: str, end_date: str) -> str:
    """
    Fetch data in chunks and save to a single merged file.
    Returns the path to the saved file.
    """
    start_dt = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date)
    
    print(f"Fetching {symbol} {timeframe} from {start_date} to {end_date}")
    print(f"Total days: {(end_dt - start_dt).days}")
    
    # Split into chunks
    chunks = date_range_list(start_dt, end_dt, CHUNK_DAYS)
    print(f"Fetching in {len(chunks)} chunks of ~{CHUNK_DAYS} days each")
    
    all_data = []
    
    for i, (chunk_start, chunk_end) in enumerate(chunks):
        start_ts = int(chunk_start.timestamp() * 1000)
        end_ts = int(chunk_end.timestamp() * 1000)
        
        print(f"  Chunk {i+1}/{len(chunks)}: {chunk_start.date()} to {chunk_end.date()}...", end=" ")
        
        # Fetch data
        data = fetch_klines(symbol, timeframe, start_ts, end_ts)
        
        if data:
            all_data.extend(data)
            print(f"OK ({len(data)} candles)")
        else:
            print("No data")
        
        # Rate limiting
        time.sleep(REQUEST_DELAY)
    
    if not all_data:
        print("No data fetched!")
        return None
    
    # Convert to DataFrame
    df = pd.DataFrame(all_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    # Convert types
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    # Remove duplicates (in case chunks overlap)
    df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    
    # Keep only needed columns
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    print(f"\nTotal: {len(df)} unique candles")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # Save to file
    filename = f"{symbol}_{timeframe}_{start_date}_{end_date}.parquet"
    filepath = OUTPUT_DIR / filename
    df.to_parquet(filepath, index=False)
    print(f"Saved to: {filepath}")
    
    return str(filepath)


def fetch_multiple(symbols: List[str], timeframes: List[str], days: int = 365):
    """Fetch data for multiple symbols and timeframes."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    print(f"\n{'='*60}")
    print(f"Fetching {days} days of data: {start_str} to {end_str}")
    print(f"Symbols: {symbols}")
    print(f"Timeframes: {timeframes}")
    print(f"{'='*60}\n")
    
    results = {}
    
    for symbol in symbols:
        for timeframe in timeframes:
            key = f"{symbol}_{timeframe}"
            print(f"\n[{key}]")
            try:
                filepath = fetch_and_save_chunks(symbol, timeframe, start_str, end_str)
                results[key] = filepath
            except Exception as e:
                print(f"Error: {e}")
                results[key] = None
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for key, filepath in results.items():
        status = "OK" if filepath else "FAILED"
        print(f"  {key}: {status}")
    
    return results


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fetch historical data in chunks')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Trading symbol')
    parser.add_argument('--timeframe', type=str, default='1h', help='Timeframe (15m, 1h, 4h, 1d)')
    parser.add_argument('--days', type=int, default=365, help='Number of days of history')
    parser.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--symbols', type=str, help='Comma-separated symbols (e.g., BTCUSDT,ETHUSDT)')
    parser.add_argument('--timeframes', type=str, help='Comma-separated timeframes (e.g., 15m,1h,4h)')
    
    args = parser.parse_args()
    
    # Determine date range
    if args.start and args.end:
        start_date = args.start
        end_date = args.end
    else:
        end_date = datetime.now()
        start_date = (end_date - timedelta(days=args.days)).strftime('%Y-%m-%d')
        end_date = end_date.strftime('%Y-%m-%d')
    
    # Single symbol/timeframe
    if args.symbols is None:
        fetch_and_save_chunks(args.symbol, args.timeframe, start_date, end_date)
    else:
        # Multiple symbols/timeframes
        symbols = args.symbols.split(',') if args.symbols else [args.symbol]
        timeframes = args.timeframes.split(',') if args.timeframes else [args.timeframe]
        fetch_multiple(symbols, timeframes, args.days)
