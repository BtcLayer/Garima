"""
Binance API Client Module
Handles connection and basic operations with Binance API
"""
import os
from binance.client import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class BinanceClient:
    def __init__(self, testnet=True):
        """Initialize Binance client with API credentials"""
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')
        
        if not api_key or not api_secret:
            raise ValueError("BINANCE_API_KEY and BINANCE_API_SECRET must be set in .env file")
        
        # Initialize Binance client (testnet=True for testnet)
        if testnet:
            self.client = Client(api_key, api_secret, testnet=True)
        else:
            self.client = Client(api_key, api_secret)
    
    def get_account_info(self):
        """Fetch account information"""
        try:
            account = self.client.get_account()
            return account
        except Exception as e:
            print(f"Error fetching account info: {e}")
            return None
    
    def get_balance(self, symbol='USDT'):
        """Get balance for a specific asset"""
        try:
            account = self.client.get_account()
            balances = account.get('balances', [])
            for balance in balances:
                if balance['asset'] == symbol:
                    return {
                        'asset': balance['asset'],
                        'free': float(balance['free']),
                        'locked': float(balance['locked']),
                        'total': float(balance['free']) + float(balance['locked'])
                    }
            return None
        except Exception as e:
            print(f"Error fetching balance: {e}")
            return None
    
    def get_ticker_price(self, symbol='BTCUSDT'):
        """Get current price of a symbol"""
        try:
            ticker = self.client.get_symbol_info(symbol)
            price = self.client.get_recent_trades(symbol=symbol, limit=1)
            return price[-1]['price'] if price else None
        except Exception as e:
            print(f"Error fetching price: {e}")
            return None
    
    def get_klines(self, symbol='BTCUSDT', interval='1h', limit=100):
        """Get candlestick data (klines) for a symbol"""
        try:
            klines = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
            return klines
        except Exception as e:
            print(f"Error fetching klines: {e}")
            return None
    
    def place_order(self, symbol, side, order_type, quantity, price=None):
        """
        Place an order on Binance
        side: 'BUY' or 'SELL'
        order_type: 'LIMIT' or 'MARKET'
        """
        try:
            if order_type == 'LIMIT' and price is None:
                raise ValueError("Price required for LIMIT orders")
            
            if order_type == 'LIMIT':
                order = self.client.order_limit(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=price
                )
            else:
                order = self.client.order_market(
                    symbol=symbol,
                    side=side,
                    quantity=quantity
                )
            return order
        except Exception as e:
            print(f"Error placing order: {e}")
            return None


if __name__ == '__main__':
    # Test connection
    try:
        client = BinanceClient()
        print("Successfully connected to Binance")
        
        # Fetch account info
        account = client.get_account_info()
        if account:
            print(f"Account connected: {len(account['balances'])} assets")
        
        # Get USDT balance
        usdt_balance = client.get_balance('USDT')
        if usdt_balance:
            print(f"USDT Balance: {usdt_balance['free']}")
        
    except Exception as e:
        print(f"Connection failed: {e}")
