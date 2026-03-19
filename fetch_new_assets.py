"""
Fetch historical data for 5 new assets:
  ADAUSDT, AVAXUSDT, DOTUSDT, LINKUSDT, LTCUSDT
Each: 15m, 1h, 4h — 1 year of data (2025-03-17 to 2026-03-17)
Run this FIRST before running the new asset strategy scripts.
"""

from src.data_fetcher import DataFetcher

START_DATE = "2025-03-17"
END_DATE   = "2026-03-17"

NEW_ASSETS = ["ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT"]
TIMEFRAMES = ["15m", "1h", "4h"]

def main():
    fetcher = DataFetcher(cache_enabled=True)
    total = len(NEW_ASSETS) * len(TIMEFRAMES)
    done  = 0

    for symbol in NEW_ASSETS:
        for tf in TIMEFRAMES:
            done += 1
            print(f"[{done}/{total}] Fetching {symbol} {tf} ...")
            try:
                df = fetcher.fetch_with_pagination(
                    symbol=symbol,
                    timeframe=tf,
                    start_date=START_DATE,
                    end_date=END_DATE,
                )
                if df is not None and not df.empty:
                    print(f"  ✅ {len(df)} candles saved to cache")
                else:
                    print(f"  ⚠️  No data returned")
            except Exception as e:
                print(f"  ❌ Error: {e}")

    print("\nAll fetches complete.")
    print("Now run: python run_ada_strategies.py  (and the other 4)")

if __name__ == "__main__":
    main()
