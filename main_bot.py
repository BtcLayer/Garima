import time
import pandas as pd
from src.strategies import StrategyManager
from binance_client import BinanceClient as bnc    # This tells the bot HOW to talk to Binance
from src.manager import process_signal       # This tells the bot WHAT to do with a signal

# Configuration mapping your coins to PDF strategies
TRADING_CONFIG = {
    "BTCUSDT": {"method": StrategyManager.apply_smc_lux, "interval": "1h"},
    "ETHUSDT": {"method": StrategyManager.apply_rsi_strategy, "interval": "15m"},
    "SOLUSDT": {"method": StrategyManager.apply_squeeze_momentum, "interval": "1h"}
}

def run_trading_cycle():
    for symbol, config in TRADING_CONFIG.items():
        print(f"🔍 Analyzing {symbol} using {config['method'].__name__}...")
        
        # 1. Fetch data
        raw_klines = bnc.get_klines(symbol, interval=config['interval'])
        df = pd.DataFrame(raw_klines) # Convert to DataFrame
        
        # 2. Get Signal from the specific PDF strategy
        signal = config['method'](df)
        
        # 3. Execute
        if signal != "HOLD":
            process_signal({"symbol": symbol, "side": signal, "price": df['close'].iloc[-1]})

if __name__ == "__main__":
    while True:
        run_trading_cycle()
        time.sleep(60) # Scan every minute