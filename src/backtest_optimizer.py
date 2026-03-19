"""
Backtesting and Strategy Optimization Module

This module provides automated backtesting and optimization capabilities:
1. Analyze historical trades from trades.jsonl
2. Identify patterns in profitable vs losing trades
3. Optimize strategy parameters based on trade performance
4. Run backtest simulations to validate improvements
5. Output optimized parameters for the trading bot
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
import statistics
import random

# File paths
TRADES_FILE = "storage/trades.jsonl"
OPTIMIZATION_CONFIG = "storage/optimization_config.json"
OPTIMIZED_PARAMS_FILE = "storage/optimized_params.json"
BACKTEST_RESULTS_FILE = "storage/backtest_results.jsonl"


@dataclass
class TradeRecord:
    """Represents a single trade record."""
    logged_at: str
    symbol: str
    exit_reason: str
    entry_price: float
    exit_price: float
    pnl: float
    # Calculated fields
    pnl_pct: float = 0.0
    duration_minutes: float = 0.0
    
    def __post_init__(self):
        """Calculate derived fields."""
        if self.entry_price > 0:
            self.pnl_pct = ((self.exit_price - self.entry_price) / self.entry_price) * 100
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TradeRecord':
        """Create TradeRecord from dictionary."""
        return cls(**data)


@dataclass
class StrategyPerformance:
    """Performance metrics for a strategy configuration."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'total_pnl': round(self.total_pnl, 4),
            'total_pnl_pct': round(self.total_pnl_pct, 4),
            'avg_win': round(self.avg_win, 4),
            'avg_loss': round(self.avg_loss, 4),
            'win_rate': round(self.win_rate * 100, 2),
            'profit_factor': round(self.profit_factor, 4),
            'max_drawdown': round(self.max_drawdown, 4),
            'sharpe_ratio': round(self.sharpe_ratio, 4),
        }


@dataclass
class OptimizationConfig:
    """Configuration for strategy optimization."""
    # RSI Strategy parameters
    rsi_length_range: Tuple[int, int] = (7, 21)
    rsi_oversold_range: Tuple[int, int] = (20, 40)
    rsi_overbought_range: Tuple[int, int] = (60, 80)
    
    # SMC Lux Strategy parameters
    smc_lookback_range: Tuple[int, int] = (5, 20)
    
    # Squeeze Momentum parameters
    squeeze_length_range: Tuple[int, int] = (10, 30)
    
    # Backtest parameters
    initial_capital: float = 10000.0
    position_size_pct: float = 0.10  # 10% of capital per trade
    commission_pct: float = 0.001  # 0.1% commission
    
    # Optimization settings
    population_size: int = 20
    generations: int = 10
    mutation_rate: float = 0.1
    crossover_rate: float = 0.7
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'rsi_length_range': self.rsi_length_range,
            'rsi_oversold_range': self.rsi_oversold_range,
            'rsi_overbought_range': self.rsi_overbought_range,
            'smc_lookback_range': self.smc_lookback_range,
            'squeeze_length_range': self.squeeze_length_range,
            'initial_capital': self.initial_capital,
            'position_size_pct': self.position_size_pct,
            'commission_pct': self.commission_pct,
            'population_size': self.population_size,
            'generations': self.generations,
            'mutation_rate': self.mutation_rate,
            'crossover_rate': self.crossover_rate,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'OptimizationConfig':
        """Create from dictionary."""
        return cls(**{k: tuple(v) if isinstance(v, list) else v for k, v in data.items()})


class TradeAnalyzer:
    """Analyzes historical trades to extract insights."""
    
    def __init__(self, trades_file: str = TRADES_FILE):
        self.trades_file = trades_file
        self.trades: List[TradeRecord] = []
        self.load_trades()
    
    def load_trades(self) -> None:
        """Load trades from JSONL file."""
        if not os.path.exists(self.trades_file):
            print(f"[!] No trades file found at {self.trades_file}")
            return
        
        with open(self.trades_file, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        self.trades.append(TradeRecord.from_dict(data))
                    except json.JSONDecodeError:
                        continue
        
        print(f"📊 Loaded {len(self.trades)} trades from {self.trades_file}")
    
    def get_winning_trades(self) -> List[TradeRecord]:
        """Get all profitable trades."""
        return [t for t in self.trades if t.pnl > 0]
    
    def get_losing_trades(self) -> List[TradeRecord]:
        """Get all losing trades."""
        return [t for t in self.trades if t.pnl < 0]
    
    def analyze_by_exit_reason(self) -> Dict[str, StrategyPerformance]:
        """Analyze performance grouped by exit reason."""
        by_reason = defaultdict(list)
        for trade in self.trades:
            by_reason[trade.exit_reason].append(trade)
        
        results = {}
        for reason, trades in by_reason.items():
            results[reason] = self._calculate_performance(trades)
        
        return results
    
    def analyze_by_symbol(self) -> Dict[str, StrategyPerformance]:
        """Analyze performance grouped by symbol."""
        by_symbol = defaultdict(list)
        for trade in self.trades:
            by_symbol[trade.symbol].append(trade)
        
        results = {}
        for symbol, trades in by_symbol.items():
            results[symbol] = self._calculate_performance(trades)
        
        return results
    
    def get_trade_distribution(self) -> Dict[str, int]:
        """Get distribution of trades by exit reason."""
        distribution = defaultdict(int)
        for trade in self.trades:
            distribution[trade.exit_reason] += 1
        return dict(distribution)
    
    def get_pnl_statistics(self) -> Dict[str, float]:
        """Get overall PnL statistics."""
        if not self.trades:
            return {}
        
        pnls = [t.pnl for t in self.trades]
        winning_pnls = [t.pnl for t in self.trades if t.pnl > 0]
        losing_pnls = [t.pnl for t in self.trades if t.pnl < 0]
        
        return {
            'total_pnl': sum(pnls),
            'total_trades': len(self.trades),
            'winning_trades': len(winning_pnls),
            'losing_trades': len(losing_pnls),
            'win_rate': len(winning_pnls) / len(self.trades) if self.trades else 0,
            'avg_pnl': statistics.mean(pnls) if pnls else 0,
            'avg_win': statistics.mean(winning_pnls) if winning_pnls else 0,
            'avg_loss': statistics.mean(losing_pnls) if losing_pnls else 0,
            'max_win': max(winning_pnls) if winning_pnls else 0,
            'max_loss': min(losing_pnls) if losing_pnls else 0,
            'median_pnl': statistics.median(pnls) if pnls else 0,
        }
    
    def identify_profitable_patterns(self) -> Dict[str, Any]:
        """Identify patterns in profitable trades."""
        winning = self.get_winning_trades()
        losing = self.get_losing_trades()
        
        if not winning:
            return {'message': 'No winning trades to analyze'}
        
        patterns = {
            'winning_count': len(winning),
            'losing_count': len(losing),
            'win_rate': len(winning) / len(self.trades) if self.trades else 0,
        }
        
        # Analyze exit reasons for winners vs losers
        winning_reasons = defaultdict(int)
        losing_reasons = defaultdict(int)
        
        for t in winning:
            winning_reasons[t.exit_reason] += 1
        for t in losing:
            losing_reasons[t.exit_reason] += 1
        
        patterns['winning_exit_reasons'] = dict(winning_reasons)
        patterns['losing_exit_reasons'] = dict(losing_reasons)
        
        # Calculate avg pnl by exit reason
        reason_pnls = defaultdict(list)
        for t in self.trades:
            reason_pnls[t.exit_reason].append(t.pnl)
        
        patterns['avg_pnl_by_exit_reason'] = {
            reason: statistics.mean(pnls) 
            for reason, pnls in reason_pnls.items()
        }
        
        # Recommendations based on patterns
        recommendations = []
        
        # Check if STOP_LOSS is causing most losses
        sl_pnls = reason_pnls.get('STOP_LOSS', [])
        tp_pnls = reason_pnls.get('TAKE_PROFIT', [])
        
        if sl_pnls and statistics.mean(sl_pnls) < -0.1:
            recommendations.append({
                'type': 'STOP_LOSS_TUNING',
                'message': 'Stop-loss trades are causing significant losses',
                'suggestion': 'Consider tightening stop-loss percentage or use dynamic SL'
            })
        
        if tp_pnls:
            avg_tp = statistics.mean(tp_pnls)
            if avg_tp < 0.1:
                recommendations.append({
                    'type': 'TAKE_PROFIT_TUNING',
                    'message': 'Take-profit targets are too small',
                    'suggestion': f'Consider increasing TP percentage (current avg: {avg_tp:.4f})'
                })
        
        if patterns['win_rate'] < 0.4:
            recommendations.append({
                'type': 'STRATEGY_REVIEW',
                'message': f'Low win rate: {patterns["win_rate"]*100:.1f}%',
                'suggestion': 'Consider adjusting entry conditions or switching strategy'
            })
        
        patterns['recommendations'] = recommendations
        
        return patterns
    
    def _calculate_performance(self, trades: List[TradeRecord]) -> StrategyPerformance:
        """Calculate performance metrics for a list of trades."""
        if not trades:
            return StrategyPerformance()
        
        winning = [t for t in trades if t.pnl > 0]
        losing = [t for t in trades if t.pnl < 0]
        
        total_pnl = sum(t.pnl for t in trades)
        total_pnl_pct = sum(t.pnl_pct for t in trades)
        
        perf = StrategyPerformance(
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            avg_win=statistics.mean([t.pnl for t in winning]) if winning else 0,
            avg_loss=statistics.mean([t.pnl for t in losing]) if losing else 0,
            win_rate=len(winning) / len(trades) if trades else 0,
        )
        
        # Calculate profit factor
        total_wins = sum(t.pnl for t in winning) if winning else 0
        total_losses = abs(sum(t.pnl for t in losing)) if losing else 0
        perf.profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Calculate max drawdown
        cumulative = 0
        peak = 0
        max_dd = 0
        for t in trades:
            cumulative += t.pnl
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd
        perf.max_drawdown = max_dd
        
        # Calculate Sharpe-like ratio (simplified)
        if len(trades) > 1:
            returns = [t.pnl_pct for t in trades]
            mean_return = statistics.mean(returns)
            std_return = statistics.stdev(returns) if len(returns) > 1 else 0
            perf.sharpe_ratio = mean_return / std_return if std_return > 0 else 0
        
        return perf


class BacktestSimulator:
    """Simulates trading with different strategy parameters."""
    
    def __init__(self, config: OptimizationConfig = None):
        self.config = config or OptimizationConfig()
    
    def simulate_rsi_strategy(
        self, 
        trades: List[TradeRecord],
        rsi_length: int = 14,
        rsi_oversold: int = 30,
        rsi_overbought: int = 70,
    ) -> StrategyPerformance:
        """
        Simulate RSI strategy with given parameters.
        
        This simulates what would have happened if we used
        different RSI parameters for entry/exit decisions.
        """
        if not trades:
            return StrategyPerformance()
        
        # Simplified simulation: estimate trade outcomes based on
        # how RSI parameters would have affected entry/exit timing
        simulated_trades = []
        
        for trade in trades:
            # Estimate if RSI params would have changed the outcome
            # This is a simplified model - in reality you'd need OHLCV data
            entry_price = trade.entry_price
            exit_price = trade.exit_price
            
            # Simulate with position sizing and commission
            position_value = self.config.initial_capital * self.config.position_size_pct
            shares = position_value / entry_price
            
            # Simulate entry with RSI oversold (BUY signal)
            # If oversold, we enter earlier = better entry
            rsi_adjustment = (rsi_oversold - 30) / 100  # -0.1 to 0.1
            adjusted_entry = entry_price * (1 - rsi_adjustment * 0.01)
            
            # Simulate exit with RSI overbought (SELL signal)
            # If overbought, we exit earlier = safer exit
            rsi_exit_adjustment = (70 - rsi_overbought) / 100
            adjusted_exit = exit_price * (1 + rsi_exit_adjustment * 0.01)
            
            # Calculate PnL
            pnl = (adjusted_exit - adjusted_entry) * shares
            pnl -= position_value * self.config.commission_pct * 2  # Entry + Exit commission
            
            trade_copy = TradeRecord(
                logged_at=trade.logged_at,
                symbol=trade.symbol,
                exit_reason=trade.exit_reason,
                entry_price=adjusted_entry,
                exit_price=adjusted_exit,
                pnl=pnl,
            )
            simulated_trades.append(trade_copy)
        
        return self._calculate_performance(simulated_trades)
    
    def simulate_smc_strategy(
        self,
        trades: List[TradeRecord],
        lookback: int = 10,
    ) -> StrategyPerformance:
        """Simulate SMC Lux strategy with different lookback periods."""
        if not trades:
            return StrategyPerformance()
        
        simulated_trades = []
        
        for trade in trades:
            # SMC lookback affects entry quality
            # Higher lookback = stronger signals but potentially missed entries
            lookback_factor = (lookback - 10) / 20  # -0.25 to 0.25
            entry_adjustment = 1 + lookback_factor * 0.005
            exit_adjustment = 1 - lookback_factor * 0.003
            
            position_value = self.config.initial_capital * self.config.position_size_pct
            shares = position_value / trade.entry_price
            
            adjusted_entry = trade.entry_price * entry_adjustment
            adjusted_exit = trade.exit_price * exit_adjustment
            
            pnl = (adjusted_exit - adjusted_entry) * shares
            pnl -= position_value * self.config.commission_pct * 2
            
            trade_copy = TradeRecord(
                logged_at=trade.logged_at,
                symbol=trade.symbol,
                exit_reason=trade.exit_reason,
                entry_price=adjusted_entry,
                exit_price=adjusted_exit,
                pnl=pnl,
            )
            simulated_trades.append(trade_copy)
        
        return self._calculate_performance(simulated_trades)
    
    def simulate_squeeze_strategy(
        self,
        trades: List[TradeRecord],
        length: int = 20,
    ) -> StrategyPerformance:
        """Simulate Squeeze Momentum strategy with different lengths."""
        if not trades:
            return StrategyPerformance()
        
        simulated_trades = []
        
        for trade in trades:
            # Squeeze length affects momentum calculation
            length_factor = (length - 20) / 20
            entry_adjustment = 1 + length_factor * 0.003
            exit_adjustment = 1 - length_factor * 0.002
            
            position_value = self.config.initial_capital * self.config.position_size_pct
            shares = position_value / trade.entry_price
            
            adjusted_entry = trade.entry_price * entry_adjustment
            adjusted_exit = trade.exit_price * exit_adjustment
            
            pnl = (adjusted_exit - adjusted_entry) * shares
            pnl -= position_value * self.config.commission_pct * 2
            
            trade_copy = TradeRecord(
                logged_at=trade.logged_at,
                symbol=trade.symbol,
                exit_reason=trade.exit_reason,
                entry_price=adjusted_entry,
                exit_price=adjusted_exit,
                pnl=pnl,
            )
            simulated_trades.append(trade_copy)
        
        return self._calculate_performance(simulated_trades)
    
    def _calculate_performance(self, trades: List[TradeRecord]) -> StrategyPerformance:
        """Calculate performance metrics."""
        if not trades:
            return StrategyPerformance()
        
        winning = [t for t in trades if t.pnl > 0]
        losing = [t for t in trades if t.pnl < 0]
        
        total_pnl = sum(t.pnl for t in trades)
        total_pnl_pct = sum(t.pnl_pct for t in trades)
        
        perf = StrategyPerformance(
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            avg_win=statistics.mean([t.pnl for t in winning]) if winning else 0,
            avg_loss=statistics.mean([t.pnl for t in losing]) if losing else 0,
            win_rate=len(winning) / len(trades) if trades else 0,
        )
        
        total_wins = sum(t.pnl for t in winning) if winning else 0
        total_losses = abs(sum(t.pnl for t in losing)) if losing else 0
        perf.profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        cumulative = 0
        peak = 0
        max_dd = 0
        for t in trades:
            cumulative += t.pnl
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd
        perf.max_drawdown = max_dd
        
        if len(trades) > 1:
            returns = [t.pnl_pct for t in trades]
            mean_return = statistics.mean(returns)
            std_return = statistics.stdev(returns) if len(returns) > 1 else 0
            perf.sharpe_ratio = mean_return / std_return if std_return > 0 else 0
        
        return perf


class StrategyOptimizer:
    """Optimizes strategy parameters using genetic algorithm."""
    
    def __init__(self, config: OptimizationConfig = None):
        self.config = config or OptimizationConfig()
        self.analyzer = TradeAnalyzer()
        self.simulator = BacktestSimulator(self.config)
    
    def generate_random_params(self) -> Dict[str, Any]:
        """Generate random strategy parameters."""
        return {
            'rsi_length': random.randint(*self.config.rsi_length_range),
            'rsi_oversold': random.randint(*self.config.rsi_oversold_range),
            'rsi_overbought': random.randint(*self.config.rsi_overbought_range),
            'smc_lookback': random.randint(*self.config.smc_lookback_range),
            'squeeze_length': random.randint(*self.config.squeeze_length_range),
        }
    
    def evaluate_params(self, params: Dict[str, Any]) -> float:
        """Evaluate a set of parameters. Returns fitness score."""
        trades = self.analyzer.trades
        if not trades:
            return 0
        
        # Run simulations for each strategy with these params
        rsi_perf = self.simulator.simulate_rsi_strategy(
            trades, 
            params['rsi_length'],
            params['rsi_oversold'],
            params['rsi_overbought'],
        )
        
        smc_perf = self.simulator.simulate_smc_strategy(
            trades,
            params['smc_lookback'],
        )
        
        squeeze_perf = self.simulator.simulate_squeeze_strategy(
            trades,
            params['squeeze_length'],
        )
        
        # Combine scores (weighted by total PnL and win rate)
        scores = []
        for perf in [rsi_perf, smc_perf, squeeze_perf]:
            if perf.total_trades > 0:
                # Score = total_pnl * win_rate * profit_factor
                score = perf.total_pnl * (0.5 + perf.win_rate * 0.5) * (1 + perf.profit_factor * 0.1)
                scores.append(score)
        
        return sum(scores) / len(scores) if scores else 0
    
    def mutate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mutate parameters."""
        mutated = params.copy()
        
        if random.random() < self.config.mutation_rate:
            mutated['rsi_length'] = random.randint(*self.config.rsi_length_range)
        
        if random.random() < self.config.mutation_rate:
            mutated['rsi_oversold'] = random.randint(*self.config.rsi_oversold_range)
        
        if random.random() < self.config.mutation_rate:
            mutated['rsi_overbought'] = random.randint(*self.config.rsi_overbought_range)
        
        if random.random() < self.config.mutation_rate:
            mutated['smc_lookback'] = random.randint(*self.config.smc_lookback_range)
        
        if random.random() < self.config.mutation_rate:
            mutated['squeeze_length'] = random.randint(*self.config.squeeze_length_range)
        
        return mutated
    
    def crossover(self, parent1: Dict[str, Any], parent2: Dict[str, Any]) -> Dict[str, Any]:
        """Crossover two parameter sets."""
        if random.random() > self.config.crossover_rate:
            return parent1.copy()
        
        child = {}
        for key in parent1.keys():
            child[key] = parent1[key] if random.random() < 0.5 else parent2[key]
        
        return child
    
    def optimize(self, verbose: bool = True) -> Dict[str, Any]:
        """Run genetic algorithm optimization."""
        if verbose:
            print("[*] Starting strategy optimization...")
            print(f"    Population: {self.config.population_size}, Generations: {self.config.generations}")
        
        # Initialize population
        population = [self.generate_random_params() for _ in range(self.config.population_size)]
        
        best_params = None
        best_score = float('-inf')
        
        for gen in range(self.config.generations):
            # Evaluate fitness
            fitness_scores = [(params, self.evaluate_params(params)) for params in population]
            fitness_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Track best
            if fitness_scores[0][1] > best_score:
                best_score = fitness_scores[0][1]
                best_params = fitness_scores[0][0].copy()
            
            if verbose:
                print(f"   Generation {gen + 1}: Best Score = {best_score:.4f}")
            
            # Selection - keep top performers
            elite_count = self.config.population_size // 4
            elite = [params for params, _ in fitness_scores[:elite_count]]
            
            # Create next generation
            new_population = elite.copy()
            
            while len(new_population) < self.config.population_size:
                # Tournament selection
                tournament = random.sample(elite, min(3, len(elite)))
                tournament.sort(key=lambda x: self.evaluate_params(x), reverse=True)
                parent1 = tournament[0]
                
                tournament = random.sample(elite, min(3, len(elite)))
                tournament.sort(key=lambda x: self.evaluate_params(x), reverse=True)
                parent2 = tournament[0]
                
                child = self.crossover(parent1, parent2)
                child = self.mutate(child)
                new_population.append(child)
            
            population = new_population
        
        if verbose:
            print(f"\n[*] Optimization complete! Best score: {best_score:.4f}")
        
        return best_params
    
    def get_recommendations(self) -> Dict[str, Any]:
        """Get optimization recommendations based on trade analysis."""
        patterns = self.analyzer.identify_profitable_patterns()
        
        recommendations = {
            'analysis': patterns,
            'optimized_params': None,
            'current_params': {
                'rsi_length': 14,
                'rsi_oversold': 30,
                'rsi_overbought': 70,
                'smc_lookback': 10,
                'squeeze_length': 20,
            },
        }
        
        # Run optimization
        optimized = self.optimize(verbose=False)
        recommendations['optimized_params'] = optimized
        
        # Evaluate improvement
        current_score = self.evaluate_params(recommendations['current_params'])
        optimized_score = self.evaluate_params(optimized)
        
        recommendations['improvement'] = {
            'current_score': current_score,
            'optimized_score': optimized_score,
            'improvement_pct': ((optimized_score - current_score) / abs(current_score) * 100) 
                               if current_score != 0 else 0,
        }
        
        return recommendations


class BacktestRunner:
    """Runs backtests and generates reports."""
    
    def __init__(self, config: OptimizationConfig = None):
        self.config = config or OptimizationConfig()
        self.analyzer = TradeAnalyzer()
        self.optimizer = StrategyOptimizer(self.config)
    
    def run_full_analysis(self) -> Dict[str, Any]:
        """Run complete backtesting analysis."""
        results = {
            'generated_at': datetime.utcnow().isoformat(),
            'trade_statistics': self.analyzer.get_pnl_statistics(),
            'exit_reason_analysis': {},
            'pattern_analysis': self.analyzer.identify_profitable_patterns(),
            'recommendations': {},
        }
        
        # Analyze by exit reason
        exit_analysis = self.analyzer.analyze_by_exit_reason()
        for reason, perf in exit_analysis.items():
            results['exit_reason_analysis'][reason] = perf.to_dict()
        
        # Get recommendations
        results['recommendations'] = self.optimizer.get_recommendations()
        
        return results
    
    def save_results(self, results: Dict[str, Any], filepath: str = None) -> None:
        """Save backtest results to file."""
        filepath = filepath or BACKTEST_RESULTS_FILE
        
        with open(filepath, 'a') as f:
            f.write(json.dumps(results) + '\n')
        
        print(f"[+] Results saved to {filepath}")
    
    def print_summary(self, results: Dict[str, Any]) -> None:
        """Print a summary of backtest results."""
        print("\n" + "="*60)
        print("📊 BACKTEST ANALYSIS SUMMARY")
        print("="*60)
        
        # Trade Statistics
        stats = results.get('trade_statistics', {})
        print(f"\n📈 Trade Statistics:")
        print(f"   Total Trades: {stats.get('total_trades', 0)}")
        print(f"   Winning Trades: {stats.get('winning_trades', 0)}")
        print(f"   Losing Trades: {stats.get('losing_trades', 0)}")
        print(f"   Win Rate: {stats.get('win_rate', 0)*100:.1f}%")
        print(f"   Total PnL: {stats.get('total_pnl', 0):.4f}")
        print(f"   Avg Win: {stats.get('avg_win', 0):.4f}")
        print(f"   Avg Loss: {stats.get('avg_loss', 0):.4f}")
        
        # Pattern Analysis
        patterns = results.get('pattern_analysis', {})
        print(f"\n🔍 Pattern Analysis:")
        print(f"   Win Rate: {patterns.get('win_rate', 0)*100:.1f}%")
        
        if 'avg_pnl_by_exit_reason' in patterns:
            print(f"   Avg PnL by Exit Reason:")
            for reason, pnl in patterns['avg_pnl_by_exit_reason'].items():
                print(f"      {reason}: {pnl:.4f}")
        
        # Recommendations
        recs = results.get('recommendations', {})
        if 'optimized_params' in recs and recs['optimized_params']:
            print(f"\n🎯 Optimized Parameters:")
            for key, value in recs['optimized_params'].items():
                print(f"   {key}: {value}")
            
            if 'improvement' in recs:
                imp = recs['improvement']
                print(f"\n📈 Improvement:")
                print(f"   Current Score: {imp.get('current_score', 0):.4f}")
                print(f"   Optimized Score: {imp.get('optimized_score', 0):.4f}")
                print(f"   Improvement: {imp.get('improvement_pct', 0):.1f}%")
        
        print("\n" + "="*60)


def run_backtest():
    """Main function to run backtesting and optimization."""
    print("🚀 Starting Automated Backtesting & Optimization\n")
    
    # Create runner
    runner = BacktestRunner()
    
    # Run full analysis
    results = runner.run_full_analysis()
    
    # Print summary
    runner.print_summary(results)
    
    # Save results
    runner.save_results(results)
    
    # Save optimized params separately
    if results.get('recommendations', {}).get('optimized_params'):
        optimized = results['recommendations']['optimized_params']
        with open(OPTIMIZED_PARAMS_FILE, 'w') as f:
            json.dump(optimized, f, indent=2)
        print(f"\n💾 Optimized params saved to {OPTIMIZED_PARAMS_FILE}")
    
    return results


if __name__ == "__main__":
    run_backtest()
