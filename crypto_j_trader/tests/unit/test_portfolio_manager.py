import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from crypto_j_trader.src.trading.trading_core import PortfolioManager

@pytest.fixture
def test_config():
    return {
        'initial_capital': 10000,
        'target_capital': 20000,
        'days_target': 90,
        'portfolio': {
            'rebalance_interval': 3600,
            'max_correlation': 0.7
        },
        'dynamic_weights': {
            'max_pairs': 5,
            'min_weight': 0.1,
            'max_weight': 0.5,
            'rebalance_interval': 3600
        },
        'pair_filters': {
            'min_24h_volume': 100000,
            'min_price': 1.0,
            'max_spread': 0.01,
            'exclude': []
        }
    }

@pytest.fixture
def test_market_data():
    now = datetime.now()
    dates = pd.date_range(end=now, periods=100, freq='1T')
    return {
        'BTC-USD': pd.DataFrame({
            'close': np.linspace(30000, 35000, 100),
            'volume': np.linspace(1000, 2000, 100)
        }, index=dates),
        'ETH-USD': pd.DataFrame({
            'close': np.linspace(2000, 2500, 100),
            'volume': np.linspace(5000, 10000, 100)
        }, index=dates),
        'LTC-USD': pd.DataFrame({
            'close': np.linspace(100, 150, 100),
            'volume': np.linspace(10000, 20000, 100)
        }, index=dates)
    }

def test_correlation_calculation(test_config, test_market_data):
    pm = PortfolioManager(test_config)
    correlations = pm.calculate_correlation(
        {pair: data['close'] for pair, data in test_market_data.items()}
    )
    
    assert isinstance(correlations, pd.DataFrame)
    assert not correlations.empty
    assert all(-1 <= val <= 1 for val in correlations.values.flatten())

def test_dynamic_weights(test_config, test_market_data):
    pm = PortfolioManager(test_config)
    weights = pm.calculate_dynamic_weights(test_market_data)
    
    assert isinstance(weights, dict)
    assert len(weights) <= test_config['dynamic_weights']['max_pairs']
    assert all(
        test_config['dynamic_weights']['min_weight'] <= w <= test_config['dynamic_weights']['max_weight']
        for w in weights.values()
    )

def test_rebalance_logic(test_config, test_market_data):
    pm = PortfolioManager(test_config)
    
    # Initial state shouldn't need rebalance
    assert not pm.needs_rebalance()
    
    # Force time-based rebalance
    pm.last_rebalance = datetime.now() - timedelta(seconds=test_config['portfolio']['rebalance_interval'] + 1)
    assert pm.needs_rebalance()
    
    # Test correlation-based rebalance
    pm.positions = {'BTC-USD': {'quantity': 0.1}, 'ETH-USD': {'quantity': 0.1}}
    prices = {pair: data['close'].iloc[-1] for pair, data in test_market_data.items()}
    orders = pm.calculate_rebalance_orders(prices)
    
    assert isinstance(orders, list)
    if orders:
        assert all(isinstance(order, dict) for order in orders)

def test_volatility_regime_weights(test_config, test_market_data):
    pm = PortfolioManager(test_config)
    
    # Test high volatility regime
    high_vol_data = test_market_data.copy()
    high_vol_data['BTC-USD']['close'] = np.random.normal(30000, 1000, 100)
    weights = pm.calculate_dynamic_weights(high_vol_data)
    assert any(w > 0 for w in weights.values())
    
    # Test low volatility regime
    low_vol_data = test_market_data.copy()
    low_vol_data['BTC-USD']['close'] = np.linspace(30000, 30100, 100)
    weights = pm.calculate_dynamic_weights(low_vol_data)
    assert any(w > 0 for w in weights.values())
