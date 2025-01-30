"""
Test configuration and shared fixtures for the crypto_j_trader test suite.
"""

import os
import sys
import pytest
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture
def config_path():
    """Path to test configuration file."""
    return os.path.join(project_root, 'config', 'example.json')

@pytest.fixture
def mock_market_data():
    """Mock market data for testing."""
    return {
        'BTC-USD': {
            'price': 50000.0,
            'volume': 100.0,
            'timestamp': '2024-01-28T00:00:00Z'
        },
        'ETH-USD': {
            'price': 2500.0,
            'volume': 200.0,
            'timestamp': '2024-01-28T00:00:00Z'
        }
    }

@pytest.fixture
def mock_portfolio():
    """Mock portfolio for testing."""
    return {
        'BTC-USD': {
            'quantity': 1.0,
            'entry_price': 48000.0,
            'entry_time': '2024-01-27T00:00:00Z'
        },
        'ETH-USD': {
            'quantity': 10.0,
            'entry_price': 2400.0,
            'entry_time': '2024-01-27T00:00:00Z'
        }
    }

@pytest.fixture
def test_config():
    """Test configuration."""
    return {
        'paper_trading': True,
        'initial_capital': 100000.0,
        'target_capital': 200000.0,
        'days_target': 90,
        'trading_pairs': [
            {
                'pair': 'BTC-USD',
                'weight': 0.6,
                'precision': 8
            },
            {
                'pair': 'ETH-USD',
                'weight': 0.4,
                'precision': 8
            }
        ],
        'risk_management': {
            'max_position_size': 0.1,
            'max_daily_loss': 0.02,
            'stop_loss_pct': 0.05
        },
        'strategy': {
            'indicators': {
                'rsi': {'period': 14},
                'macd': {
                    'fast_period': 12,
                    'slow_period': 26,
                    'signal_period': 9
                }
            },
            'entry_rules': {
                'min_volume_percentile': 50
            },
            'time_filters': {
                'min_candles': 30
            }
        }
    }
