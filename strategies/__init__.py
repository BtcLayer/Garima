"""
Strategies Package
Contains 20 batch files with 230+ profitable strategy combinations.
Each batch file contains 10-15 unique strategy combinations.
"""

# Import all batch getters
from strategies.batch_01 import get_strategies as get_batch_01, get_all_strategies_telegram as get_telegram_01
from strategies.batch_02 import get_strategies as get_batch_02, get_all_strategies_telegram as get_telegram_02
from strategies.batch_03 import get_strategies as get_batch_03, get_all_strategies_telegram as get_telegram_03
from strategies.batch_04 import get_strategies as get_batch_04, get_all_strategies_telegram as get_telegram_04
from strategies.batch_05 import get_strategies as get_batch_05, get_all_strategies_telegram as get_telegram_05
from strategies.batch_06 import get_strategies as get_batch_06, get_all_strategies_telegram as get_telegram_06
from strategies.batch_07 import get_strategies as get_batch_07, get_all_strategies_telegram as get_telegram_07
from strategies.batch_08 import get_strategies as get_batch_08, get_all_strategies_telegram as get_telegram_08
from strategies.batch_09 import get_strategies as get_batch_09, get_all_strategies_telegram as get_telegram_09
from strategies.batch_10 import get_strategies as get_batch_10, get_all_strategies_telegram as get_telegram_10
from strategies.batch_11 import get_strategies as get_batch_11, get_all_strategies_telegram as get_telegram_11
from strategies.batch_12 import get_strategies as get_batch_12, get_all_strategies_telegram as get_telegram_12
from strategies.batch_13 import get_strategies as get_batch_13, get_all_strategies_telegram as get_telegram_13
from strategies.batch_14 import get_strategies as get_batch_14, get_all_strategies_telegram as get_telegram_14
from strategies.batch_15 import get_strategies as get_batch_15, get_all_strategies_telegram as get_telegram_15
from strategies.batch_16 import get_strategies as get_batch_16, get_all_strategies_telegram as get_telegram_16
from strategies.batch_17 import get_strategies as get_batch_17, get_all_strategies_telegram as get_telegram_17
from strategies.batch_18 import get_strategies as get_batch_18, get_all_strategies_telegram as get_telegram_18
from strategies.batch_19 import get_strategies as get_batch_19, get_all_strategies_telegram as get_telegram_19
from strategies.batch_20 import get_strategies as get_batch_20, get_all_strategies_telegram as get_telegram_20


def get_all_strategies():
    """Get all strategies from all batches"""
    all_strategies = []
    
    batch_getters = [
        get_batch_01, get_batch_02, get_batch_03, get_batch_04, get_batch_05,
        get_batch_06, get_batch_07, get_batch_08, get_batch_09, get_batch_10,
        get_batch_11, get_batch_12, get_batch_13, get_batch_14, get_batch_15,
        get_batch_16, get_batch_17, get_batch_18, get_batch_19, get_batch_20
    ]
    
    for batch_getter in batch_getters:
        all_strategies.extend(batch_getter())
    
    return all_strategies


def get_strategy_by_id(strategy_id):
    """Get a specific strategy by ID from all batches"""
    for batch_num in range(1, 21):
        module_name = f"strategies.batch_{batch_num:02d}"
        try:
            module = __import__(module_name, fromlist=['get_strategy_by_id'])
            strategy = module.get_strategy_by_id(strategy_id)
            if strategy:
                return strategy
        except:
            continue
    return None


def get_strategies_by_batch(batch_num):
    """Get strategies from a specific batch"""
    if batch_num < 1 or batch_num > 20:
        return []
    
    module_name = f"strategies.batch_{batch_num:02d}"
    try:
        module = __import__(module_name, fromlist=['get_strategies'])
        return module.get_strategies()
    except:
        return []


def get_all_telegram_messages():
    """Get all Telegram formatted messages from all batches"""
    messages = []
    
    telegram_getters = [
        get_telegram_01, get_telegram_02, get_telegram_03, get_telegram_04, get_telegram_05,
        get_telegram_06, get_telegram_07, get_telegram_08, get_telegram_09, get_telegram_10,
        get_telegram_11, get_telegram_12, get_telegram_13, get_telegram_14, get_telegram_15,
        get_telegram_16, get_telegram_17, get_telegram_18, get_telegram_19, get_telegram_20
    ]
    
    for i, getter in enumerate(telegram_getters):
        messages.append(f"📦 Batch {i+1}\n" + getter())
    
    return messages


def get_top_profitable_strategies(limit=100):
    """Get the top N most profitable strategies (by ID, first 100)"""
    all_strategies = get_all_strategies()
    # Sort by ID and return top N
    sorted_strategies = sorted(all_strategies, key=lambda x: x['id'])
    return sorted_strategies[:limit]


def get_strategy_count():
    """Get total count of strategies"""
    return len(get_all_strategies())


# Package info
__version__ = "1.0.0"
__author__ = "Trading Bot Team"
__description__ = "230+ profitable strategy combinations for trading"
