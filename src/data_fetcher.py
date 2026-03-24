"""
Historical Data Fetcher Module

A separate module for fetching and caching historical OHLCV data from Binance.
Supports:
- Pagination for large date ranges (1+ year)
- Local caching to avoid repeated API calls
- Multiple symbols and timeframes

Usage:
    from src.data_fetcher import DataFetcher
    
    fetcher = DataFetcher()
    df = fetcher.fetch_with_pagination(
        symbol="BTCUSDT",
        timeframe="15m",
        start_date="2024-01-01",
        end_date="2025-01-01"
    )
"""

import os
import json
import time

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration
CACHE_DIR = Path("storage/historical_data")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Binance API
BASE_URL = "https://api.binance.com/api/v3"

# Maximum candles per request (Binance limit is 1000)
MAX_CANDLES_PER_REQUEST = 1000

# Rate limiting
REQUEST_DELAY = 0.2  # seconds between requests


class DataFetcher:
    """
    Fetches historical OHLCV data from Binance with pagination support.
    """
    
    def __init__(self, cache_enabled: bool = True):
        self.cache_enabled = cache_enabled
        self.session = requests.Session()
        
    def _get_cache_path(self, symbol: str, timeframe: str, start_date: str, end_date: str) -> Path:
        """
        Generate cache file path using human-readable naming convention:
        {SYMBOL}_{timeframe}_{start_date}_{end_date}.parquet
        This matches files produced by fetch_data_chunks.py so they are reused.
        """
        filename = f"{symbol}_{timeframe}_{start_date}_{end_date}.parquet"
        return CACHE_DIR / filename

    def _save_to_cache(self, df: pd.DataFrame, symbol: str, timeframe: str,
                       start_date: str, end_date: str) -> None:
        """Save DataFrame to cache."""
        if not self.cache_enabled:
            return
        cache_path = self._get_cache_path(symbol, timeframe, start_date, end_date)
        df.to_parquet(cache_path, index=False)
        print(f"  [CACHE] Saved to {cache_path.name}")

    def _load_from_cache(self, symbol: str, timeframe: str,
                         start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        Load from cache. Checks two ways:
        1. Exact filename match (same date range requested before).
        2. Any existing file for the same symbol/timeframe whose stored data
           covers the requested range — so older downloads are reused.
        """
        if not self.cache_enabled:
            return None

        # 1. Exact match
        exact = self._get_cache_path(symbol, timeframe, start_date, end_date)
        candidates = [exact] if exact.exists() else []

        # 2. Scan for any file that might cover a superset of the requested range
        if not candidates:
            prefix = f"{symbol}_{timeframe}_"
            candidates = [
                p for p in CACHE_DIR.glob(f"{prefix}*.parquet")
                if p.name != exact.name
            ]

        start_dt = pd.Timestamp(start_date)
        end_dt   = pd.Timestamp(end_date)

        for path in candidates:
            try:
                df = pd.read_parquet(path)
                if "timestamp" not in df.columns:
                    continue
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                # Check the file actually covers the requested window
                if df["timestamp"].min() <= start_dt and df["timestamp"].max() >= end_dt:
                    df = df[(df["timestamp"] >= start_dt) & (df["timestamp"] <= end_dt)]
                    df = df.reset_index(drop=True)
                    print(f"  [CACHE] Loaded {len(df)} candles from {path.name}")
                    return df
            except Exception as e:
                print(f"  [ERR] Cache read error ({path.name}): {e}")
                continue

        return None
    
    def _fetch_single_batch(self, symbol: str, timeframe: str,
                           end_ts: int = None, start_ts: int = None,
                           limit: int = None) -> List:
        """Fetch a single batch of klines from Binance."""
        url = f"{BASE_URL}/klines"

        params = {
            'symbol': symbol,
            'interval': timeframe,
            'limit': limit or MAX_CANDLES_PER_REQUEST
        }
        if start_ts is not None:
            params['startTime'] = start_ts
        if end_ts is not None:
            params['endTime'] = end_ts

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"  [X] API Error: {e}")
            return []
    
    def fetch_with_pagination(
        self, 
        symbol: str, 
        timeframe: str, 
        start_date: str, 
        end_date: str,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Fetch historical data with automatic pagination.
        
        Binance API allows fetching up to 1000 candles per request.
        This method handles fetching data in batches from newest to oldest.
        """
        # Check cache first
        if use_cache:
            cached = self._load_from_cache(symbol, timeframe, start_date, end_date)
            if cached is not None and len(cached) > 0:
                return cached
        
        print(f"Fetching {symbol} {timeframe} data: {start_date} to {end_date}")
        
        # Convert dates to timestamps
        start_ts = int(datetime.fromisoformat(start_date).timestamp() * 1000)
        end_ts = int(datetime.fromisoformat(end_date).timestamp() * 1000)
        
        all_candles = []
        current_start_ts = start_ts
        batch_count = 0

        while True:
            # Fetch batch going forward from current_start_ts
            batch = self._fetch_single_batch(
                symbol, timeframe,
                start_ts=current_start_ts, end_ts=end_ts,
            )

            if not batch:
                break

            batch_count += 1
            print(f"  Batch {batch_count}: {len(batch)} candles")

            # Add all candles
            all_candles.extend(batch)

            # batch[-1][0] = newest timestamp in this batch
            newest_ts = batch[-1][0]

            # If we've reached the end date, stop
            if newest_ts >= end_ts:
                break

            # If we got fewer than max candles, no more data available
            if len(batch) < MAX_CANDLES_PER_REQUEST:
                break

            # Move start forward past the last candle we got
            current_start_ts = newest_ts + 1

            # Safety check: prevent infinite loops
            if batch_count > 2000:
                print(f"  [WARN] Max iterations reached")
                break

            # Rate limiting
            time.sleep(REQUEST_DELAY)
        
        if not all_candles:
            print(f"  [WARN] No data returned for {symbol} {timeframe}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(all_candles, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        # Convert types
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        # Deduplicate, filter to exact date range, sort
        df = df.drop_duplicates(subset=['timestamp'])
        df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
        df = df.sort_values('timestamp').reset_index(drop=True)

        # Keep only needed columns
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

        print(f"  [OK] Total: {len(df)} candles fetched in {batch_count} batches")
        
        # Save to cache
        self._save_to_cache(df, symbol, timeframe, start_date, end_date)
        
        return df
    
    def get_date_range_for_timeframe(self, timeframe: str, days: int = 365) -> Tuple[str, str]:
        """
        Calculate date range for a given timeframe and number of days.
        
        This ensures we fetch enough data for indicators to warm up.
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Add extra buffer for indicator warm-up
        # RSI needs ~14 candles, Moving averages need more
        buffer_days = 60  # Extra 60 days for warm-up
        start_date = start_date - timedelta(days=buffer_days)
        
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')


class BatchDataFetcher:
    """
    Fetches data for multiple symbol/timeframe combinations efficiently.
    """
    
    def __init__(self, cache_enabled: bool = True):
        self.fetcher = DataFetcher(cache_enabled=cache_enabled)
        
    def fetch_multiple(
        self,
        symbols: List[str],
        timeframes: List[str],
        start_date: str,
        end_date: str,
        skip_existing: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple symbol/timeframe combinations.
        
        Returns:
            Dict with keys like 'BTCUSDT_15m' -> DataFrame
        """
        results = {}
        total = len(symbols) * len(timeframes)
        current = 0
        
        print(f"\n=== Starting batch fetch: {total} combinations")
        print("=" * 50)
        
        for symbol in symbols:
            for timeframe in timeframes:
                current += 1
                key = f"{symbol}_{timeframe}"
                print(f"[{current}/{total}] {key}")
                
                try:
                    df = self.fetcher.fetch_with_pagination(
                        symbol=symbol,
                        timeframe=timeframe,
                        start_date=start_date,
                        end_date=end_date,
                        use_cache=not skip_existing
                    )
                    results[key] = df
                except Exception as e:
                    print(f"\n  [ERR] Error: {e}")
                    results[key] = pd.DataFrame()
        
        print("\n" + "=" * 50)
        print(f"Batch fetch complete: {len(results)} datasets")
        
        return results


def fetch_one_year_data(
    symbols: List[str] = None,
    timeframes: List[str] = None,
    days: int = 365
) -> Dict[str, pd.DataFrame]:
    """
    Convenience function to fetch 1 year of data for multiple symbols/timeframes.
    
    Args:
        symbols: List of trading pairs
        timeframes: List of timeframes
        days: Number of days of historical data
        
    Returns:
        Dictionary of DataFrames
    """
    if symbols is None:
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
    
    if timeframes is None:
        timeframes = ["15m", "1h", "4h", "1d"]
    
    # Calculate date range
    fetcher = DataFetcher()
    start_date, end_date = fetcher.get_date_range_for_timeframe("15m", days)
    
    print(f"Date range: {start_date} to {end_date} ({days} days + buffer)")
    
    # Fetch all combinations
    batch_fetcher = BatchDataFetcher(cache_enabled=True)
    results = batch_fetcher.fetch_multiple(
        symbols=symbols,
        timeframes=timeframes,
        start_date=start_date,
        end_date=end_date
    )
    
    return results


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    print("Testing Data Fetcher Module")
    print("=" * 50)
    
    # Test single fetch with pagination
    fetcher = DataFetcher(cache_enabled=True)
    
    # Test 15m timeframe (needs many batches)
    print("\n[TEST] Testing 15m timeframe (3 months):")
    df = fetcher.fetch_with_pagination(
        symbol="BTCUSDT",
        timeframe="15m",
        start_date="2024-10-01",
        end_date="2025-01-01"
    )
    
    if not df.empty:
        print(f"  Data range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"  Total candles: {len(df)}")
    
    # Test 1h timeframe
    print("\n[TEST] Testing 1h timeframe (6 months):")
    df = fetcher.fetch_with_pagination(
        symbol="ETHUSDT",
        timeframe="1h",
        start_date="2024-07-01",
        end_date="2025-01-01"
    )
    
    if not df.empty:
        print(f"  Data range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"  Total candles: {len(df)}")
    
    print("\n=== Tests complete!")
