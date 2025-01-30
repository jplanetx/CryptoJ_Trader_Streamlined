import pytest
import pandas as pd
import numpy as np
from crypto_j_trader.src.trading.trading_core import PortfolioManager
from datetime import datetime, timedelta

@pytest.fixture
def sample_config():
    return {
        'initial_capital': 10000,
        'target_capital': 20000,
        'days_target': 365,
        'dynamic_weights': {
            'max_pairs': 5,
            'rebalance_interval': 86400,  # 1 day in seconds
            'min_weight': 0.1,
            'max_weight': 0.5
        },
        'pair_filters': {
            'min_24h_volume': 100000,
            'min_price': 1.0,
            'max_spread': 0.05,
            'exclude': []
        },
        'portfolio': {
            'rebalance_interval': 86400
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

def test_rebalance_needed(sample_config):
    pm = PortfolioManager(sample_config)
    assert not pm.needs_rebalance()  # Just initialized
    
    # Force last rebalance time to be older than interval
    pm.last_rebalance = datetime.now() - timedelta(seconds=sample_config['portfolio']['rebalance_interval'] + 1)
    assert pm.needs_rebalance()

def test_rebalance_orders(sample_config, sample_market_data):
    pm = PortfolioManager(sample_config)
    current_prices = {pair: data['close'].iloc[-1] for pair, data in sample_market_data.items()}
    
    # Initial rebalance should create buy orders
    orders = pm.calculate_rebalance_orders(current_prices)
    assert len(orders) == len(sample_config['trading_pairs'])
    assert all(order['side'] == 'buy' for order in orders)
    
    # Simulate positions being filled
    for pair in sample_config['trading_pairs']:
        pm.positions[pair['pair']] = {
            'quantity': 0.1,
            'entry_price': current_prices[pair['pair']]
        }
    
    # Test rebalance with existing positions
    orders = pm.calculate_rebalance_orders(current_prices)
    assert len(orders) > 0

def test_rebalance_with_price_changes(sample_config, sample_market_data):
    pm = PortfolioManager(sample_config)
    current_prices = {pair: data['close'].iloc[-1] for pair, data in sample_market_data.items()}
    
    # Initial positions
    for pair in sample_config['trading_pairs']:
        pm.positions[pair['pair']] = {
            'quantity': 0.1,
            'entry_price': current_prices[pair['pair']]
        }
    
    # Simulate price changes
    new_prices = {
        'BTC-USD': current_prices['BTC-USD'] * 1.2,  # 20% increase
        'ETH-USD': current_prices['ETH-USD'] * 0.8   # 20% decrease
    }
    
    orders = pm.calculate_rebalance_orders(new_prices)
    assert len(orders) > 0
    
    # Verify BTC sell and ETH buy orders
    btc_order = next((o for o in orders if o['pair'] == 'BTC-USD'), None)
    eth_order = next((o for o in orders if o['pair'] == 'ETH-USD'), None)
    
    assert btc_order['side'] == 'sell'
    assert eth_order['side'] == 'buy'

def test_rebalance_with_new_pairs(sample_config, sample_market_data):
    pm = PortfolioManager(sample_config)
    current_prices = {pair: data['close'].iloc[-1] for pair, data in sample_market_data.items()}
    
    # Add a new pair to config
    sample_config['trading_pairs'].append({'pair': 'LTC-USD', 'weight': 0.1})
    sample_market_data['LTC-USD'] = pd.DataFrame({
        'close': np.random.normal(100, 10, 100),
        'volume': np.random.normal(1000, 100, 100),
        'high': np.random.normal(105, 10, 100),
        'low': np.random.normal(95, 10, 100)
    })
    
    orders = pm.calculate_rebalance_orders(current_prices)
    ltc_order = next((o for o in orders if o['pair'] == 'LTC-USD'), None)
    assert ltc_order is not None
    assert ltc_order['side'] == 'buy'

def test_rebalance_with_removed_pairs(sample_config, sample_market_data):
    pm = PortfolioManager(sample_config)
    current_prices = {pair: data['close'].iloc[-1] for pair, data in sample_market_data.items()}
    
    # Add initial positions
    for pair in sample_config['trading_pairs']:
        pm.positions[pair['pair']] = {
            'quantity': 0.1,
            'entry_price': current_prices[pair['pair']]
        }
    
    # Remove a pair from config
    removed_pair = sample_config['trading_pairs'].pop()
    
    orders = pm.calculate_rebalance_orders(current_prices)
    remove_order = next((o for o in orders if o['pair'] == removed_pair['pair']), None)
    assert remove_order is not None
    assert remove_order['side'] == 'sell'
    assert remove_order['reason'] == 'remove_pair'
