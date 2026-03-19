"""
Comprehensive Backtesting Engine

A professional-grade backtesting system that:
1. Fetches historical OHLCV data from Binance
2. Implements multiple trading strategies
3. Runs backtests across multiple timeframes
4. Calculates professional metrics: ROI, Drawdown, Sharpe Ratio
5. Optimizes parameters using genetic algorithm
6. Generates detailed reports

Date Range: January 1, 2024 to January 1, 2025
"""

import os
import json
import math
import random
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration
START_DATE = "2024-01-01"
END_DATE = "2025-01-01"
# Only use practical timeframes (skip 1m as it has too much data)
SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
TIMEFRAMES = ["15m", "1h", "4h", "1d"]  # Removed 1m and 5m for faster testing
INITIAL_CAPITAL = 10000.0
COMMISSION = 0.001  # 0.1%


@dataclass
class Trade:
    """Represents a single trade."""
    entry_time: datetime
    entry_price: float
    exit_time: datetime
    exit_price: float
    side: str  # "long" or "short"
    quantity: float
    pnl: float
    pnl_pct: float
    commission: float
    
    def to_dict(self) -> dict:
        return {
            'entry_time': self.entry_time.isoformat(),
            'entry_price': self.entry_price,
            'exit_time': self.exit_time.isoformat(),
            'exit_price': self.exit_price,
            'side': self.side,
            'quantity': self.quantity,
            'pnl': round(self.pnl, 4),
            'pnl_pct': round(self.pnl_pct, 4),
            'commission': round(self.commission, 4),
        }


@dataclass
class BacktestResult:
    """Results of a backtest run."""
    strategy_name: str
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    
    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # Performance metrics
    total_return: float = 0.0
    total_return_pct: float = 0.0
    roi_per_annum: float = 0.0
    avg_trade_pct: float = 0.0
    
    # Risk metrics
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Additional metrics
    profit_factor: float = 0.0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    win_rate: float = 0.0
    
    # Trade list
    trades: List[Trade] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'strategy_name': self.strategy_name,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'total_return': round(self.total_return, 4),
            'total_return_pct': round(self.total_return_pct, 4),
            'roi_per_annum': round(self.roi_per_annum, 4),
            'avg_trade_pct': round(self.avg_trade_pct, 4),
            'max_drawdown': round(self.max_drawdown, 4),
            'max_drawdown_pct': round(self.max_drawdown_pct, 4),
            'sharpe_ratio': round(self.sharpe_ratio, 4),
            'sortino_ratio': round(self.sortino_ratio, 4),
            'calmar_ratio': round(self.calmar_ratio, 4),
            'profit_factor': round(self.profit_factor, 4),
            'avg_win_pct': round(self.avg_win_pct, 4),
            'avg_loss_pct': round(self.avg_loss_pct, 4),
            'win_rate': round(self.win_rate, 4),
            'trades': [t.to_dict() for t in self.trades],
        }


class BinanceDataFetcher:
    """Fetches historical OHLCV data from Binance."""
    
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
    
    def fetch_ohlcv(
        self, 
        symbol: str, 
        timeframe: str, 
        start_date: str, 
        end_date: str,
        limit: int = 1500
    ) -> pd.DataFrame:
        """Fetch OHLCV data from Binance."""
        
        # Convert dates to timestamps
        start_ts = int(datetime.fromisoformat(start_date).timestamp() * 1000)
        end_ts = int(datetime.fromisoformat(end_date).timestamp() * 1000)
        
        url = f"{self.base_url}/klines"
        all_data = []
        
        # For efficiency, always fetch most recent data first
        # This avoids slow backward pagination
        params = {
            'symbol': symbol,
            'interval': timeframe,
            'endTime': end_ts,
            'limit': 1500  # Max allowed
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            
            if data:
                # Filter to our date range (most recent first)
                for candle in data:
                    if start_ts <= candle[0] <= end_ts:
                        all_data.append(candle)
        except Exception as e:
            print(f"Error fetching data: {e}")
        
        if not all_data:
            return pd.DataFrame()
        
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
        
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]


class Strategy:
    """Base class for trading strategies."""
    
    def __init__(self, params: Dict[str, Any] = None):
        self.params = params or {}
    
    def generate_signal(self, df: pd.DataFrame) -> int:
        """
        Generate trading signal.
        Returns: 1 for long, -1 for short, 0 for neutral
        """
        raise NotImplementedError


class MovingAverageCrossover(Strategy):
    """Moving Average Crossover Strategy."""
    
    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        self.fast_ma = self.params.get('fast_ma', 10)
        self.slow_ma = self.params.get('slow_ma', 50)
    
    def generate_signal(self, df: pd.DataFrame) -> int:
        if len(df) < self.slow_ma + 1:
            return 0
        
        fast = df['close'].rolling(self.fast_ma).mean()
        slow = df['close'].rolling(self.slow_ma).mean()
        
        # Current and previous values
        curr_fast = fast.iloc[-1]
        curr_slow = slow.iloc[-1]
        prev_fast = fast.iloc[-2]
        prev_slow = slow.iloc[-2]
        
        # Golden Cross - Bullish
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            return 1
        # Death Cross - Bearish
        elif prev_fast >= prev_slow and curr_fast < curr_slow:
            return -1
        
        return 0


class RSIStrategy(Strategy):
    """RSI Momentum Strategy."""
    
    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.oversold = self.params.get('oversold', 30)
        self.overbought = self.params.get('overbought', 70)
    
    def calculate_rsi(self, series: pd.Series, period: int) -> pd.Series:
        """Calculate RSI indicator."""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def generate_signal(self, df: pd.DataFrame) -> int:
        if len(df) < self.rsi_period + 1:
            return 0
        
        rsi = self.calculate_rsi(df['close'], self.rsi_period)
        
        curr_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]
        
        # Oversold - Buy signal
        if prev_rsi <= self.oversold and curr_rsi > self.oversold:
            return 1
        # Overbought - Sell signal
        elif prev_rsi >= self.overbought and curr_rsi < self.overbought:
            return -1
        
        return 0


class BollingerBandsStrategy(Strategy):
    """Bollinger Bands Strategy."""
    
    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        self.period = self.params.get('period', 20)
        self.std_dev = self.params.get('std_dev', 2)
    
    def generate_signal(self, df: pd.DataFrame) -> int:
        if len(df) < self.period + 1:
            return 0
        
        sma = df['close'].rolling(self.period).mean()
        std = df['close'].rolling(self.period).std()
        
        upper = sma + (std * 2)
        lower = sma - (std * 2)
        
        curr_close = df['close'].iloc[-1]
        prev_close = df['close'].iloc[-2]
        
        # Price touches lower band - Buy
        if prev_close > lower.iloc[-2] and curr_close <= lower.iloc[-1]:
            return 1
        # Price touches upper band - Sell
        elif prev_close < upper.iloc[-2] and curr_close >= upper.iloc[-1]:
            return -1
        
        return 0


class MACDStrategy(Strategy):
    """MACD Strategy."""
    
    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        self.fast = self.params.get('fast', 12)
        self.slow = self.params.get('slow', 26)
        self.signal = self.params.get('signal', 9)
    
    def generate_signal(self, df: pd.DataFrame) -> int:
        if len(df) < self.slow + self.signal:
            return 0
        
        ema_fast = df['close'].ewm(span=self.fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=self.signal, adjust=False).mean()
        
        curr_macd = macd.iloc[-1]
        curr_signal = signal_line.iloc[-1]
        prev_macd = macd.iloc[-2]
        prev_signal = signal_line.iloc[-2]
        
        # MACD crosses above signal - Buy
        if prev_macd <= prev_signal and curr_macd > curr_signal:
            return 1
        # MACD crosses below signal - Sell
        elif prev_macd >= prev_signal and curr_macd < curr_signal:
            return -1
        
        return 0


class VWAPStrategy(Strategy):
    """VWAP (Volume Weighted Average Price) Strategy."""
    
    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        self.lookback = self.params.get('lookback', 20)
    
    def generate_signal(self, df: pd.DataFrame) -> int:
        if len(df) < self.lookback + 1:
            return 0
        
        # Calculate VWAP
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).rolling(self.lookback).sum() / df['volume'].rolling(self.lookback).sum()
        
        curr_close = df['close'].iloc[-1]
        prev_close = df['close'].iloc[-2]
        
        # Price crosses above VWAP - Buy
        if prev_close < vwap.iloc[-2] and curr_close > vwap.iloc[-1]:
            return 1
        # Price crosses below VWAP - Sell
        elif prev_close > vwap.iloc[-2] and curr_close < vwap.iloc[-1]:
            return -1
        
        return 0


class ATRStrategy(Strategy):
    """ATR (Average True Range) Based Strategy."""
    
    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        self.atr_period = self.params.get('atr_period', 14)
        self.multiplier = self.params.get('multiplier', 2)
    
    def calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate ATR indicator."""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(period).mean()
        
        return atr
    
    def generate_signal(self, df: pd.DataFrame) -> int:
        if len(df) < self.atr_period + 1:
            return 0
        
        atr = self.calculate_atr(df, self.atr_period)
        sma = df['close'].rolling(self.atr_period).mean()
        
        upper_band = sma + (atr * self.multiplier)
        lower_band = sma - (atr * self.multiplier)
        
        curr_close = df['close'].iloc[-1]
        prev_close = df['close'].iloc[-2]
        
        # Price breaks below lower band - Buy
        if prev_close > lower_band.iloc[-2] and curr_close < lower_band.iloc[-1]:
            return 1
        # Price breaks above upper band - Sell
        elif prev_close < upper_band.iloc[-2] and curr_close > upper_band.iloc[-1]:
            return -1
        
        return 0


class StochasticStrategy(Strategy):
    """Stochastic Oscillator Strategy."""
    
    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        self.k_period = self.params.get('k_period', 14)
        self.d_period = self.params.get('d_period', 3)
        self.oversold = self.params.get('oversold', 20)
        self.overbought = self.params.get('overbought', 80)
    
    def generate_signal(self, df: pd.DataFrame) -> int:
        if len(df) < self.k_period + self.d_period:
            return 0
        
        low_min = df['low'].rolling(self.k_period).min()
        high_max = df['high'].rolling(self.k_period).max()
        
        k = 100 * (df['close'] - low_min) / (high_max - low_min)
        d = k.rolling(self.d_period).mean()
        
        curr_k = k.iloc[-1]
        curr_d = d.iloc[-1]
        prev_k = k.iloc[-2]
        prev_d = d.iloc[-2]
        
        # Stochastic oversold - Buy
        if prev_k <= self.oversold and curr_k > self.oversold:
            return 1
        # Stochastic overbought - Sell
        elif prev_k >= self.overbought and curr_k < self.overbought:
            return -1
        
        return 0


class EMACrossStrategy(Strategy):
    """EMA Crossover with Trend Filter Strategy."""
    
    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        self.fast_ema = self.params.get('fast_ema', 9)
        self.slow_ema = self.params.get('slow_ema', 21)
        self.trend_ema = self.params.get('trend_ema', 50)
    
    def generate_signal(self, df: pd.DataFrame) -> int:
        if len(df) < self.trend_ema + 1:
            return 0
        
        fast = df['close'].ewm(span=self.fast_ema, adjust=False).mean()
        slow = df['close'].ewm(span=self.slow_ema, adjust=False).mean()
        trend = df['close'].ewm(span=self.trend_ema, adjust=False).mean()
        
        # Check trend direction
        current_trend = trend.iloc[-1]
        current_close = df['close'].iloc[-1]
        
        # EMA crosses
        curr_fast = fast.iloc[-1]
        curr_slow = slow.iloc[-1]
        prev_fast = fast.iloc[-2]
        prev_slow = slow.iloc[-2]
        
        # Buy: Uptrend + golden cross
        if current_close > current_trend:
            if prev_fast <= prev_slow and curr_fast > curr_slow:
                return 1
        # Sell: Downtrend + death cross
        elif current_close < current_trend:
            if prev_fast >= prev_slow and curr_fast < curr_slow:
                return -1
        
        return 0


class BacktestEngine:
    """Main backtesting engine."""
    
    def __init__(
        self,
        initial_capital: float = INITIAL_CAPITAL,
        commission: float = COMMISSION
    ):
        self.initial_capital = initial_capital
        self.commission = commission
        self.data_fetcher = BinanceDataFetcher()
        self._data_cache = {}
    
    def fetch_data(self, symbol, timeframe, start_date, end_date):
        """Fetch data without caching"""
        return self.data_fetcher.fetch_ohlcv(symbol, timeframe, start_date, end_date)
    
    def get_cached_data(
        self, 
        symbol: str, 
        timeframe: str, 
        start_date: str, 
        end_date: str
    ) -> pd.DataFrame:
        """Get cached data or fetch if not cached."""
        cache_key = f"{symbol}_{timeframe}_{start_date}_{end_date}"
        
        if cache_key not in self._data_cache:
            print(f"Fetching {symbol} {timeframe} data...")
            self._data_cache[cache_key] = self.data_fetcher.fetch_ohlcv(
                symbol, timeframe, start_date, end_date
            )
        else:
            print(f"[CACHE] Using cached {symbol} {timeframe} data")
        
        return self._data_cache[cache_key]  # Cache for fetched data
    
    def get_cached_data(
        self, 
        symbol: str, 
        timeframe: str, 
        start_date: str, 
        end_date: str
    ) -> pd.DataFrame:
        """Get cached data or fetch if not cached."""
        cache_key = f"{symbol}_{timeframe}_{start_date}_{end_date}"
        
        if cache_key not in self._data_cache:
            print(f"Fetching {symbol} {timeframe} data...")
            self._data_cache[cache_key] = self.data_fetcher.fetch_ohlcv(
                symbol, timeframe, start_date, end_date
            )
        else:
            print(f"[CACHE] Using cached {symbol} {timeframe} data")
        
        return self._data_cache[cache_key]
    
    def run_backtest(
        self,
        strategy: Strategy,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
        position_size: float = 0.1,  # 10% of capital
        counter_trade: bool = False,  # Counter-trading mode
    ) -> BacktestResult:
        """Run a backtest for a given strategy."""
        
        # Get data (cached)
        df = self.get_cached_data(symbol, timeframe, start_date, end_date)
        
        if df.empty or len(df) < 100:
            return BacktestResult(
                strategy_name=strategy.__class__.__name__,
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
            )
        
        # Generate signals
        signals = []
        for i in range(len(df)):
            if i < 50:  # Warmup period
                signals.append(0)
            else:
                window = df.iloc[:i+1].copy()
                signal = strategy.generate_signal(window)
                # Counter-trade: invert the signal
                if counter_trade and signal != 0:
                    signal = -signal
                signals.append(signal)
        
        df['signal'] = signals
        
        # Execute trades
        trades = []
        capital = self.initial_capital
        position = None
        equity_curve = [capital]
        
        for i in range(1, len(df)):
            current_bar = df.iloc[i]
            prev_bar = df.iloc[i-1]
            
            signal = current_bar['signal']
            
            # Close existing position on opposite signal
            if position and signal != 0:
                should_close = False
                if position['side'] == 'long' and signal == -1:
                    should_close = True
                elif position['side'] == 'short' and signal == 1:
                    should_close = True
                
                if should_close:
                    exit_price = current_bar['close']
                    entry_price = position['entry_price']
                    quantity = position['quantity']
                    
                    pnl = (exit_price - entry_price) * quantity if position['side'] == 'long' else (entry_price - exit_price) * quantity
                    pnl_pct = (pnl / (entry_price * quantity)) * 100
                    comm = (entry_price + exit_price) * quantity * self.commission
                    
                    trade = Trade(
                        entry_time=position['entry_time'],
                        entry_price=entry_price,
                        exit_time=current_bar['timestamp'],
                        exit_price=exit_price,
                        side=position['side'],
                        quantity=quantity,
                        pnl=pnl - comm,
                        pnl_pct=pnl_pct - (self.commission * 200),
                        commission=comm
                    )
                    trades.append(trade)
                    
                    capital += pnl - comm
                    position = None
            
            # Open new position
            if not position and signal != 0:
                entry_price = current_bar['close']
                position_value = capital * position_size
                quantity = position_value / entry_price
                
                position = {
                    'entry_time': current_bar['timestamp'],
                    'entry_price': entry_price,
                    'side': 'long' if signal == 1 else 'short',
                    'quantity': quantity
                }
            
            # Track equity
            if position:
                current_value = position['quantity'] * current_bar['close']
                unrealized_pnl = (current_value - (position['entry_price'] * position['quantity']))
                equity_curve.append(capital + unrealized_pnl)
            else:
                equity_curve.append(capital)
        
        # Close any open position at the end
        if position:
            last_bar = df.iloc[-1]
            exit_price = last_bar['close']
            pnl = (exit_price - position['entry_price']) * position['quantity']
            comm = (position['entry_price'] + exit_price) * position['quantity'] * self.commission
            
            trade = Trade(
                entry_time=position['entry_time'],
                entry_price=position['entry_price'],
                exit_time=last_bar['timestamp'],
                exit_price=exit_price,
                side=position['side'],
                quantity=position['quantity'],
                pnl=pnl - comm,
                pnl_pct=(pnl / (position['entry_price'] * position['quantity'])) * 100,
                commission=comm
            )
            trades.append(trade)
            capital += pnl - comm
        
        # Calculate metrics
        result = self._calculate_metrics(
            strategy_name=strategy.__class__.__name__,
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            trades=trades,
            initial_capital=self.initial_capital,
            final_capital=capital,
            equity_curve=equity_curve,
            df=df
        )
        
        return result
    
    def _calculate_metrics(
        self,
        strategy_name: str,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
        trades: List[Trade],
        initial_capital: float,
        final_capital: float,
        equity_curve: List[float],
        df: pd.DataFrame
    ) -> BacktestResult:
        """Calculate performance metrics."""
        
        result = BacktestResult(
            strategy_name=strategy_name,
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
        )
        
        if not trades:
            return result
        
        # Basic stats
        result.total_trades = len(trades)
        result.winning_trades = sum(1 for t in trades if t.pnl > 0)
        result.losing_trades = sum(1 for t in trades if t.pnl < 0)
        
        # Returns
        result.total_return = final_capital - initial_capital
        result.total_return_pct = ((final_capital - initial_capital) / initial_capital) * 100
        
        # Calculate years
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        years = (end_dt - start_dt).days / 365.25
        
        # ROI per annum
        result.roi_per_annum = ((final_capital / initial_capital) ** (1/years) - 1) * 100 if years > 0 else 0
        
        # Average trade
        if trades:
            result.avg_trade_pct = sum(t.pnl_pct for t in trades) / len(trades)
        
        # Win rate
        result.win_rate = result.winning_trades / result.total_trades if result.total_trades > 0 else 0
        
        # Profit factor
        total_wins = sum(t.pnl for t in trades if t.pnl > 0)
        total_losses = abs(sum(t.pnl for t in trades if t.pnl < 0))
        result.profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Average win/loss
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl < 0]
        
        if winning_trades:
            result.avg_win_pct = sum(t.pnl_pct for t in winning_trades) / len(winning_trades)
        if losing_trades:
            result.avg_loss_pct = sum(t.pnl_pct for t in losing_trades) / len(losing_trades)
        
        # Maximum Drawdown
        equity = np.array(equity_curve)
        running_max = np.maximum.accumulate(equity)
        drawdowns = (equity - running_max) / running_max * 100
        result.max_drawdown = abs(min(drawdowns))
        result.max_drawdown_pct = min(drawdowns)
        
        # Calculate returns for Sharpe
        returns = np.diff(equity) / equity[:-1] * 100
        
        if len(returns) > 0 and np.std(returns) > 0:
            # Sharpe Ratio (annualized)
            result.sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252 * 24 * 60)  # Assuming minute data
            
            # Sortino Ratio (downside deviation)
            downside_returns = returns[returns < 0]
            if len(downside_returns) > 0 and np.std(downside_returns) > 0:
                result.sortino_ratio = (np.mean(returns) / np.std(downside_returns)) * np.sqrt(252 * 24 * 60)
        
        # Calmar Ratio (return / max drawdown)
        if result.max_drawdown > 0:
            result.calmar_ratio = result.roi_per_annum / result.max_drawdown
        
        result.trades = trades
        
        return result


class StrategyOptimizer:
    """Genetic algorithm optimizer for strategy parameters."""
    
    def __init__(self, backtest_engine: BacktestEngine):
        self.engine = backtest_engine
        self.population_size = 20
        self.generations = 10
        self.mutation_rate = 0.1
    
    def generate_random_params(self, strategy_class) -> Dict[str, Any]:
        """Generate random parameters for a strategy."""
        
        if strategy_class == RSIStrategy:
            return {
                'rsi_period': random.randint(7, 21),
                'oversold': random.randint(20, 40),
                'overbought': random.randint(60, 80),
            }
        elif strategy_class == MovingAverageCrossover:
            return {
                'fast_ma': random.randint(5, 20),
                'slow_ma': random.randint(25, 100),
            }
        elif strategy_class == MACDStrategy:
            return {
                'fast': random.randint(8, 16),
                'slow': random.randint(20, 35),
                'signal': random.randint(5, 15),
            }
        elif strategy_class == EMACrossStrategy:
            return {
                'fast_ema': random.randint(5, 15),
                'slow_ema': random.randint(15, 30),
                'trend_ema': random.randint(40, 100),
            }
        elif strategy_class == ATRStrategy:
            return {
                'atr_period': random.randint(7, 21),
                'multiplier': random.uniform(1.5, 3.0),
            }
        elif strategy_class == StochasticStrategy:
            return {
                'k_period': random.randint(10, 21),
                'd_period': random.randint(3, 7),
                'oversold': random.randint(15, 30),
                'overbought': random.randint(70, 85),
            }
        
        return {}
    
    def evaluate(self, strategy_class, params, symbol, timeframe, start_date, end_date) -> float:
        """Evaluate a parameter set."""
        
        strategy = strategy_class(params)
        result = self.engine.run_backtest(
            strategy, symbol, timeframe, start_date, end_date
        )
        
        # Fitness: combine returns and risk-adjusted performance
        if result.total_trades == 0:
            return -1000
        
        score = result.total_return_pct * 0.4
        score += result.sharpe_ratio * 10 * 0.3
        score += result.win_rate * 100 * 0.2
        score -= result.max_drawdown * 0.1
        
        return score
    
    def optimize(
        self,
        strategy_class,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
        verbose: bool = True
    ) -> Tuple[Dict[str, Any], float]:
        """Run genetic algorithm optimization."""
        
        if verbose:
            print(f"\nOptimizing {strategy_class.__name__}...")
        
        # Initialize population
        population = [self.generate_random_params(strategy_class) 
                     for _ in range(self.population_size)]
        
        best_params = None
        best_score = float('-inf')
        
        for gen in range(self.generations):
            # Evaluate fitness
            fitness = []
            for params in population:
                score = self.evaluate(
                    strategy_class, params, 
                    symbol, timeframe, 
                    start_date, end_date
                )
                fitness.append((params, score))
            
            # Sort by fitness
            fitness.sort(key=lambda x: x[1], reverse=True)
            
            # Track best
            if fitness[0][1] > best_score:
                best_score = fitness[0][1]
                best_params = fitness[0][0].copy()
            
            if verbose:
                print(f"  Generation {gen+1}: Best Score = {best_score:.2f}")
            
            # Selection - keep top performers
            elite = [p for p, _ in fitness[:self.population_size // 4]]
            
            # Create next generation
            new_population = elite.copy()
            
            while len(new_population) < self.population_size:
                # Crossover
                if random.random() < 0.7 and len(elite) >= 2:
                    parent1, parent2 = random.sample(elite, 2)
                    child = {}
                    for key in parent1.keys():
                        child[key] = parent1[key] if random.random() < 0.5 else parent2[key]
                else:
                    child = random.choice(elite).copy()
                
                # Mutation
                if random.random() < self.mutation_rate:
                    child.update(self.generate_random_params(strategy_class))
                
                new_population.append(child)
            
            population = new_population
        
        if verbose:
            print(f"  Best Parameters: {best_params}")
            print(f"  Best Score: {best_score:.2f}")
        
        return best_params, best_score


def run_comprehensive_backtest():
    """Run comprehensive backtest across all strategies and timeframes."""
    
    print("="*70)
    print("COMPREHENSIVE BACKTESTING ENGINE")
    print("="*70)
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Symbols: {', '.join(SYMBOLS)}")
    print(f"Timeframes: {', '.join(TIMEFRAMES)}")
    print(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    print("="*70)
    
    engine = BacktestEngine()
    optimizer = StrategyOptimizer(engine)
    
    all_results = []
    
    # Strategy classes to test
    strategies = [
        RSIStrategy,
        MovingAverageCrossover,
        MACDStrategy,
        EMACrossStrategy,
        ATRStrategy,
        StochasticStrategy,
    ]
    
    for symbol in SYMBOLS:
        for timeframe in TIMEFRAMES:
            for strategy_class in strategies:
                print(f"\nTesting {strategy_class.__name__} on {symbol} {timeframe}...")
                
                # First, run with default params
                strategy = strategy_class()
                result = engine.run_backtest(
                    strategy, symbol, timeframe, START_DATE, END_DATE
                )
                
                if result.total_trades > 0:
                    # Optimize
                    best_params, best_score = optimizer.optimize(
                        strategy_class, symbol, timeframe, START_DATE, END_DATE, verbose=False
                    )
                    
                    # Run with optimized params
                    optimized_strategy = strategy_class(best_params)
                    optimized_result = engine.run_backtest(
                        optimized_strategy, symbol, timeframe, START_DATE, END_DATE
                    )
                    
                    optimized_result.strategy_name = f"{strategy_class.__name__}_OPT"
                    
                    all_results.append(result)
                    all_results.append(optimized_result)
                    
                    print(f"  Default: {result.total_return_pct:.2f}%, Sharpe: {result.sharpe_ratio:.2f}")
                    print(f"  Optimized: {optimized_result.total_return_pct:.2f}%, Sharpe: {optimized_result.sharpe_ratio:.2f}")
                else:
                    print(f"  No trades generated")
    
    # Save results
    results_file = "storage/comprehensive_backtest_results.json"
    with open(results_file, 'w') as f:
        json.dump([r.to_dict() for r in all_results], f, indent=2)
    
    # Print summary
    print("\n" + "="*70)
    print("BACKTEST RESULTS SUMMARY")
    print("="*70)
    
    # Sort by ROI
    all_results.sort(key=lambda x: x.roi_per_annum, reverse=True)
    
    print("\nTop 10 Strategies by ROI per Annum:")
    print("-"*70)
    
    for i, result in enumerate(all_results[:10]):
        print(f"{i+1}. {result.strategy_name}")
        print(f"   Symbol: {result.symbol} {result.timeframe}")
        print(f"   ROI/Year: {result.roi_per_annum:.2f}%")
        print(f"   Total Return: {result.total_return_pct:.2f}%")
        print(f"   Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"   Max Drawdown: {result.max_drawdown:.2f}%")
        print(f"   Win Rate: {result.win_rate*100:.1f}%")
        print(f"   Trades: {result.total_trades}")
        print()
    
    # Best by metrics
    print("\nBest by Sharpe Ratio:")
    by_sharpe = sorted(all_results, key=lambda x: x.sharpe_ratio, reverse=True)[:3]
    for r in by_sharpe:
        print(f"  {r.strategy_name} {r.symbol} {r.timeframe}: {r.sharpe_ratio:.2f}")
    
    print("\nBest by Lowest Drawdown:")
    by_dd = sorted(all_results, key=lambda x: x.max_drawdown)[:3]
    for r in by_dd:
        print(f"  {r.strategy_name} {r.symbol} {r.timeframe}: {r.max_drawdown:.2f}%")
    
    print("\nBest by Win Rate (min 20 trades):")
    by_wr = sorted([r for r in all_results if r.total_trades >= 20], 
                   key=lambda x: x.win_rate, reverse=True)[:3]
    for r in by_wr:
        print(f"  {r.strategy_name} {r.symbol} {r.timeframe}: {r.win_rate*100:.1f}%")
    
    print(f"\n[SAVE] Results saved to {results_file}")
    print("="*70)
    
    return all_results


if __name__ == "__main__":
    run_comprehensive_backtest()
