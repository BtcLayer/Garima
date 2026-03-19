"""
Example usage of Binance client
Run this file to test your Binance API connection
"""
from binance_client import BinanceClient

def main():
    # Initialize client
    print("Initializing Binance client...")
    client = BinanceClient()
    
    # Test 1: Get account info
    print("\n--- Account Information ---")
    account = client.get_account_info()
    if account:
        print(f"Trading enabled: {account['canTrade']}")
        print(f"Total assets: {len(account['balances'])}")
    
    # Test 2: Get balances for major assets
    print("\n--- Your Balances ---")
    for symbol in ['USDT', 'BTC', 'ETH']:
        balance = client.get_balance(symbol)
        if balance and float(balance['free']) > 0:
            print(f"{symbol}: {balance['free']}")
    
    # Test 3: Get current prices
    print("\n--- Market Prices ---")
    for symbol in ['BTCUSDT', 'ETHUSDT']:
        try:
            ticker = client.client.get_symbol_ticker(symbol=symbol)
            print(f"{symbol}: ${ticker['price']}")
        except Exception as e:
            print(f"Error: {e}")
    
    # Test 4: Get candlestick data (last 5 1-hour candles)
    print("\n--- BTC/USDT Last 5 Hours ---")
    klines = client.get_klines('BTCUSDT', interval='1h', limit=5)
    if klines:
        for kline in klines:
            close_time = kline[6]
            close_price = kline[4]
            volume = kline[7]
            print(f"Close: ${close_price} | Volume: {volume}")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
