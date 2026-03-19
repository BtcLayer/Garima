"""
Automated Strategy Optimization Integration

This module integrates the backtesting optimizer with the trading bot:
1. Periodically runs optimization based on new trade data
2. Applies optimized parameters to the live trading strategies
3. Monitors performance and adjusts accordingly
4. Provides CLI interface for manual optimization
"""

import json
import os
import sys
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest_optimizer import (
    BacktestRunner,
    StrategyOptimizer,
    OptimizationConfig,
    TRADES_FILE,
    OPTIMIZED_PARAMS_FILE,
)


# Configuration file for auto-optimization
AUTO_OPTIMIZE_CONFIG = "storage/auto_optimize_config.json"


@dataclass
class AutoOptimizeConfig:
    """Configuration for automated optimization."""
    enabled: bool = True
    interval_hours: int = 24  # Run optimization every 24 hours
    min_trades_before_optimize: int = 5  # Minimum trades needed
    auto_apply_params: bool = True  # Auto-apply optimized params
    notify_on_improvement: bool = True
    min_improvement_pct: float = 5.0  # Minimum improvement to auto-apply
    
    def to_dict(self) -> dict:
        return {
            'enabled': self.enabled,
            'interval_hours': self.interval_hours,
            'min_trades_before_optimize': self.min_trades_before_optimize,
            'auto_apply_params': self.auto_apply_params,
            'notify_on_improvement': self.notify_on_improvement,
            'min_improvement_pct': self.min_improvement_pct,
        }
    
    @classmethod
    def load(cls, filepath: str = AUTO_OPTIMIZE_CONFIG) -> 'AutoOptimizeConfig':
        """Load config from file."""
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = json.load(f)
                return cls(**data)
        return cls()
    
    def save(self, filepath: str = AUTO_OPTIMIZE_CONFIG) -> None:
        """Save config to file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


class OptimizedStrategyManager:
    """Manages optimized strategy parameters and applies them to trading."""
    
    def __init__(self):
        self.optimized_params: Optional[Dict[str, Any]] = None
        self.current_params: Dict[str, Any] = {
            'rsi_length': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'smc_lookback': 10,
            'squeeze_length': 20,
            'stop_loss_pct': 1.0,
            'take_profit_pct': 2.0,
        }
        self.last_optimization: Optional[str] = None
        self.load_optimized_params()
    
    def load_optimized_params(self) -> None:
        """Load optimized parameters from file."""
        if os.path.exists(OPTIMIZED_PARAMS_FILE):
            with open(OPTIMIZED_PARAMS_FILE, 'r') as f:
                self.optimized_params = json.load(f)
                print(f"📂 Loaded optimized params: {self.optimized_params}")
        else:
            print("📂 No optimized params file found, using defaults")
    
    def get_active_params(self) -> Dict[str, Any]:
        """Get currently active parameters (optimized if available, else defaults)."""
        if self.optimized_params:
            return {**self.current_params, **self.optimized_params}
        return self.current_params.copy()
    
    def apply_params(self, params: Dict[str, Any]) -> bool:
        """Apply new parameters to the trading system."""
        try:
            # Update current params
            self.current_params.update(params)
            
            # Also save as optimized
            self.optimized_params = params
            with open(OPTIMIZED_PARAMS_FILE, 'w') as f:
                json.dump(params, f, indent=2)
            
            self.last_optimization = datetime.utcnow().isoformat()
            
            print(f"✅ Applied new strategy parameters: {params}")
            return True
        except Exception as e:
            print(f"❌ Failed to apply params: {e}")
            return False
    
    def get_params_for_strategy(self, strategy_name: str) -> Dict[str, Any]:
        """Get parameters for a specific strategy."""
        active = self.get_active_params()
        
        if strategy_name == 'rsi':
            return {
                'length': active.get('rsi_length', 14),
                'oversold': active.get('rsi_oversold', 30),
                'overbought': active.get('rsi_overbought', 70),
            }
        elif strategy_name == 'smc':
            return {
                'lookback': active.get('smc_lookback', 10),
            }
        elif strategy_name == 'squeeze':
            return {
                'length': active.get('squeeze_length', 20),
            }
        
        return {}


class AutoOptimizer:
    """Automated optimization scheduler and runner."""
    
    def __init__(self, config: AutoOptimizeConfig = None):
        self.config = config or AutoOptimizeConfig.load()
        self.strategy_manager = OptimizedStrategyManager()
        self.runner = BacktestRunner()
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def check_trades_available(self) -> bool:
        """Check if enough trades are available for optimization."""
        if not os.path.exists(TRADES_FILE):
            return False
        
        with open(TRADES_FILE, 'r') as f:
            trade_count = sum(1 for line in f if line.strip())
        
        return trade_count >= self.config.min_trades_before_optimize
    
    def run_optimization(self, auto_apply: bool = None) -> Dict[str, Any]:
        """Run optimization and optionally apply results."""
        if auto_apply is None:
            auto_apply = self.config.auto_apply_params
        
        print("\n" + "="*50)
        print("🔄 RUNNING AUTOMATED OPTIMIZATION")
        print("="*50)
        
        # Check if enough trades
        if not self.check_trades_available():
            print(f"⚠️ Not enough trades for optimization (need {self.config.min_trades_before_optimize})")
            return {'status': 'skipped', 'reason': 'insufficient_trades'}
        
        # Run backtest and optimization
        results = self.runner.run_full_analysis()
        
        # Get recommendations
        recommendations = results.get('recommendations', {})
        optimized_params = recommendations.get('optimized_params')
        improvement = recommendations.get('improvement', {})
        
        if not optimized_params:
            print("❌ No optimization results generated")
            return {'status': 'error', 'reason': 'no_results'}
        
        # Check if improvement is significant enough
        improvement_pct = improvement.get('improvement_pct', 0)
        
        should_apply = (
            auto_apply and 
            improvement_pct >= self.config.min_improvement_pct
        )
        
        if should_apply:
            # Apply optimized parameters
            success = self.strategy_manager.apply_params(optimized_params)
            
            if success:
                print(f"\n✅ Auto-applied optimized parameters!")
                print(f"   Improvement: {improvement_pct:.1f}%")
            else:
                print(f"\n⚠️ Failed to auto-apply parameters")
        
        # Save results
        self.runner.save_results(results)
        
        # Prepare output
        output = {
            'status': 'success',
            'timestamp': datetime.utcnow().isoformat(),
            'optimized_params': optimized_params,
            'current_params': self.strategy_manager.current_params,
            'improvement': improvement,
            'auto_applied': should_apply,
            'trade_analysis': {
                'total_trades': results.get('trade_statistics', {}).get('total_trades', 0),
                'win_rate': results.get('trade_statistics', {}).get('win_rate', 0),
            }
        }
        
        print("\n" + "="*50)
        
        return output
    
    def start_scheduler(self) -> None:
        """Start the automated optimization scheduler."""
        if not self.config.enabled:
            print("⚠️ Auto-optimization is disabled")
            return
        
        if self._running:
            print("⚠️ Scheduler is already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()
        print(f"🚀 Auto-optimization scheduler started (interval: {self.config.interval_hours}h)")
    
    def stop_scheduler(self) -> None:
        """Stop the automated optimization scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("🛑 Auto-optimization scheduler stopped")
    
    def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                # Run optimization
                result = self.run_optimization()
                
                if result.get('status') == 'success':
                    print(f"✅ Optimization completed: {result.get('improvement', {}).get('improvement_pct', 0):.1f}% improvement")
            except Exception as e:
                print(f"❌ Optimization error: {e}")
            
            # Wait for next interval
            interval_seconds = self.config.interval_hours * 3600
            for _ in range(interval_seconds):
                if not self._running:
                    break
                time.sleep(1)


def run_optimization_cli():
    """CLI interface for running optimization."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Automated Strategy Optimizer')
    parser.add_argument('--auto-apply', action='store_true', 
                       help='Automatically apply optimized parameters')
    parser.add_argument('--schedule', action='store_true',
                       help='Run as background scheduler')
    parser.add_argument('--config', action='store_true',
                       help='Configure auto-optimization settings')
    
    args = parser.parse_args()
    
    if args.config:
        # Configure settings
        config = AutoOptimizeConfig.load()
        
        print("\n📝 Auto-Optimization Configuration")
        print("="*40)
        
        config.enabled = input("Enable auto-optimization? (y/n): ").lower() == 'y'
        config.interval_hours = int(input("Optimization interval (hours): ") or "24")
        config.min_trades_before_optimize = int(input("Min trades before optimize: ") or "5")
        config.auto_apply_params = input("Auto-apply params? (y/n): ").lower() == 'y'
        config.min_improvement_pct = float(input("Min improvement % to auto-apply: ") or "5")
        
        config.save()
        print("✅ Configuration saved!")
        return
    
    if args.schedule:
        # Run as scheduler
        optimizer = AutoOptimizer()
        try:
            optimizer.start_scheduler()
            # Keep main thread alive
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            optimizer.stop_scheduler()
        return
    
    # Single optimization run
    optimizer = AutoOptimizer()
    result = optimizer.run_optimization(auto_apply=args.auto_apply)
    
    if result.get('status') == 'success':
        print("\n✅ Optimization Complete!")
        print(f"   Auto-applied: {result.get('auto_applied', False)}")
        if result.get('improvement'):
            print(f"   Improvement: {result.get('improvement', {}).get('improvement_pct', 0):.1f}%")


def integrate_with_strategy(strategy_class):
    """
    Decorator to integrate optimization with a strategy class.
    
    Usage:
        @integrate_with_strategy
        class MyStrategy:
            ...
    """
    original_init = strategy_class.__init__
    
    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        
        # Load optimized parameters
        manager = OptimizedStrategyManager()
        optimized = manager.get_active_params()
        
        # Apply to strategy if it has these attributes
        if hasattr(self, 'rsi_length'):
            self.rsi_length = optimized.get('rsi_length', 14)
        if hasattr(self, 'rsi_oversold'):
            self.rsi_oversold = optimized.get('rsi_oversold', 30)
        if hasattr(self, 'rsi_overbought'):
            self.rsi_overbought = optimized.get('rsi_overbought', 70)
        if hasattr(self, 'lookback'):
            self.lookback = optimized.get('smc_lookback', 10)
    
    strategy_class.__init__ = __init__
    return strategy_class


def get_optimized_strategy_params() -> Dict[str, Any]:
    """Get current optimized strategy parameters."""
    manager = OptimizedStrategyManager()
    return manager.get_active_params()


if __name__ == "__main__":
    run_optimization_cli()
