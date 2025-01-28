import pytest
import pandas as pd
import numpy as np
from crypto_j_trader.src.trading.trading_core import PortfolioManager
from datetime import datetime

@pytest.fixture
def sample_config():
    return {
        'initial_capital': 10000,
        'target_capital': 20000,
        'days_target': 365,
        'dynamic_weights': {
            'max_pairs': 5,
            'rebalance_interval': 86400,
            'min_weight': 0.1,
            'max_weight': 0.5
        },
        'pair_filters': {
            'min_24h_volume': 100000,
            'min_price': 1.0,
            'max_spread': 0.05,
            'exclude': []
        },
        'trading_pairs': [
            {'pair': 'BTC-USD', 'weight': 0.3},
            {'pair': 'ETH-USD', 'weight': 0.2}
        ]
    }

@pytest.fixture
def sample_market_data():
    now = datetime.now()
    timestamps = pd.date_range(end=now, periods=100, freq='1T')
    return {
        'BTC-USD': pd.DataFrame({
            'close': np.random.normal(50000, 1000, 100),
            'volume': np.random.normal(1000, 100, 100),
            'high': np.random.normal(50100, 1000, 100),
            'low': np.random.normal(49900, 1000, 100)
        }, index=timestamps),
        'ETH-USD': pd.DataFrame({
            'close': np.random.normal(3000, 100, 100),
            'volume': np.random.normal(5000, 500, 100),
            'high': np.random.normal(3050, 100, 100),
            'low': np.random.normal(2950, 100, 100)
        }, index=timestamps)
    }

def test_dynamic_weight_calculation(sample_config, sample_market_data):
    pm = PortfolioManager(sample_config)
    weights = pm.calculate_dynamic_weights(sample_market_data)
    
    # Basic validation
    assert isinstance(weights, dict)
    assert len(weights) <= sample_config['dynamic_weights']['max_pairs']
    
    # Weight range validation
    for pair, weight in weights.items():
        assert sample_config['dynamic_weights']['min_weight'] <= weight <= sample_config['dynamic_weights']['max_weight']
        
    # Sum of weights should be ~1.0
    assert abs(sum(weights.values()) - 1.0) < 0.0001

def test_empty_market_data(sample_config):
    pm = PortfolioManager(sample_config)
    weights = pm.calculate_dynamic_weights({})
    assert weights == {}

def test_insufficient_data(sample_config):
    pm = PortfolioManager(sample_config)
    market_data = {
        'BTC-USD': pd.DataFrame({
            'close': [50000],
            'volume': [1000],
            'high': [50100],
            'low': [49900]
        })
    }
    weights = pm.calculate_dynamic_weights(market_data)
    assert weights == {}

def test_filtered_pairs(sample_config, sample_market_data):
    # Add a pair that should be filtered out
    sample_market_data['LOWVOL-USD'] = pd.DataFrame({
        'close': [0.5],
        'volume': [100],
        'high': [0.6],
        'low': [0.4]
    })
    
    pm = PortfolioManager(sample_config)
    weights = pm.calculate_dynamic_weights(sample_market_data)
    
    assert 'LOWVOL-USD' not in weights

def test_weight_normalization(sample_config, sample_market_data):
    pm = PortfolioManager(sample_config)
    weights = pm.calculate_dynamic_weights(sample_market_data)
    
    # Test that weights are properly normalized
    total_weight = sum(weights.values())
    assert abs(total_weight - 1.0) < 0.0001

def test_max_pairs_limit(sample_config, sample_market_data):
    # Add more pairs than the max limit
    for i in range(10):
        pair = f'TEST-{i}'
        sample_market_data[pair] = pd.DataFrame({
            'close': np.random.normal(100, 10, 100),
            'volume': np.random.normal(1000, 100, 100),
            'high': np.random.normal(105, 10, 100),
            'low': np.random.normal(95, 10, 100)
        })
    
    pm = PortfolioManager(sample_config)
    weights = pm.calculate_dynamic_weights(sample_market_data)
    
    assert len(weights) == sample_config['dynamic_weights']['max_pairs']

def test_weight_bounds(sample_config, sample_market_data):
    pm = PortfolioManager(sample_config)
    weights = pm.calculate_dynamic_weights(sample_market_data)
    
    for weight in weights.values():
        assert weight >= sample_config['dynamic_weights']['min_weight']
        assert weight <= sample_config['dynamic_weights']['max_weight']
