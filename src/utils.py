import os
from dotenv import load_dotenv
from binance.client import Client

def get_binance_client():
    load_dotenv()
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        raise ValueError("API Keys missing in .env file!")
        
    return Client(api_key, api_secret)
