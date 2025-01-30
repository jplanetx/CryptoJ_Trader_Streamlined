import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from crypto_j_trader.j_trading import PortfolioManager

@pytest.fixture
def large_market_data():
    """Generate large market data for benchmarking"""
    now = datetime.now()
    timestamps = pd.date_range(end=now, periods=1000, freq='1T')
    data = {}
    
    # Generate data for 100 pairs
    for i in range(100):
        pair = f'PAIR-{i}'
        data[pair] = pd.DataFrame({
            'close': np.random.normal(100, 10, 1000),
            'volume': np.random.normal(1000, 100, 1000),
            'high': np.random.normal(105, 10, 1000),
            'low': np.random.normal(95, 10, 1000)
        }, index=timestamps)
    
    return data

@pytest.fixture
def benchmark_config():
    return {
        'initial_capital': 1000000,
        'target_capital': 2000000,
        'days_target': 365,
        'dynamic_weights': {
            'max_pairs': 50,
            'rebalance_interval': 86400,
            'min_weight': 0.01,
            'max_weight': 0.5
        },
        'pair_filters': {
            'min_24h_volume': 100000,
            'min_price': 1.0,
            'max_spread': 0.05,
            'exclude': []
        }
    }

def test_weight_calculation_benchmark(benchmark, benchmark_config, large_market_data):
    """Benchmark the weight calculation performance"""
    pm = PortfolioManager(benchmark_config)
    
    def calculate_weights():
        return pm.calculate_dynamic_weights(large_market_data)
    
    # Run benchmark
    result = benchmark(calculate_weights)
    
    # Assert performance requirements
    assert result.stats['mean'] < 0.5  # Mean time should be less than 500ms
    assert result.stats['max'] < 1.0   # Max time should be less than 1 second

def test_rebalance_benchmark(benchmark, benchmark_config, large_market_data):
    """Benchmark the full rebalance process"""
    pm = PortfolioManager(benchmark_config)
    current_prices = {pair: data['close'].iloc[-1] for pair, data in large_market_data.items()}
    
    def rebalance():
        return pm.calculate_rebalance_orders(current_prices)
    
    # Run benchmark
    result = benchmark(rebalance)
    
    # Assert performance requirements
    assert result.stats['mean'] < 0.75  # Mean time should be less than 750ms
    assert result.stats['max'] < 1.5    # Max time should be less than 1.5 seconds

def test_large_dataset_handling(benchmark, benchmark_config, large_market_data):
    """Test handling of large datasets"""
    pm = PortfolioManager(benchmark_config)
    
    # Test weight calculation with large dataset
    weights = pm.calculate_dynamic_weights(large_market_data)
    assert len(weights) == benchmark_config['dynamic_weights']['max_pairs']
    
    # Test rebalance with large dataset
    current_prices = {pair: data['close'].iloc[-1] for pair, data in large_market_data.items()}
    orders = pm.calculate_rebalance_orders(current_prices)
    assert len(orders) == benchmark_config['dynamic_weights']['max_pairs']

def test_memory_usage(benchmark, benchmark_config, large_market_data):
    """Test memory usage during weight calculation"""
    import tracemalloc
    
    pm = PortfolioManager(benchmark_config)
    
    def calculate_weights():
        tracemalloc.start()
        weights = pm.calculate_dynamic_weights(large_market_data)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return peak / 1024 / 1024  # Convert to MB
    
    # Run benchmark
    peak_memory = benchmark(calculate_weights)
    
    # Assert memory requirements
    assert peak_memory.stats['mean'] < 100  # Mean memory usage should be less than 100MB
    assert peak_memory.stats['max'] < 150   # Max memory usage should be less than 150MB
