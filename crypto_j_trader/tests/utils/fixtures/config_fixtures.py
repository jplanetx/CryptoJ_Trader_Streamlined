"""
Test configuration fixtures for CryptoJ Trader tests.
"""
import pytest
from typing import Dict, Any
from decimal import Decimal
from crypto_j_trader.tests.utils.mocks.coinbase_mocks import MockExchangeService # Import MockExchangeService

@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Base test configuration"""
    return {
        'trading_pairs': ['BTC-USD', 'ETH-USD'],
        'risk_management': {
            'stop_loss_pct': 0.05,
            'max_position_size': 5.0,
            'max_daily_loss': 500.0,
            'position_size_limit': 50000.0,
            'max_drawdown': 0.2
        },
        'paper_trading': True,
        'timeout': 30,
        'api_key': 'test_api_key',
        'api_secret': 'test_secret',
        'base_url': 'https://api.test.com',
        'detailed_health_check': True,
        'initial_capital': 100000.0
    }

@pytest.fixture
def test_env_config(test_config: Dict[str, Any]) -> Dict[str, Any]:
    """Test environment specific configuration"""
    config = test_config.copy()
    config.update({
        'environment': 'test',
        'log_level': 'DEBUG',
        'paper_trading': True  # Force paper trading in test environment
    })
    return config

@pytest.fixture
def mock_market_data() -> Dict[str, Any]:
    """Mock market data for testing"""
    return {
        'BTC-USD': {
            'price': 50000.0,
            'volume': 100.0,
            'bid': 49950.0,
            'ask': 50050.0,
            'timestamp': '2025-02-13T00:00:00Z'
        },
        'ETH-USD': {
            'price': 2000.0,
            'volume': 1000.0,
            'bid': 1995.0,
            'ask': 2005.0,
            'timestamp': '2025-02-13T00:00:00Z'
        }
    }

@pytest.fixture
def mock_account_balance() -> Dict[str, Decimal]:
    """Mock account balance data"""
    return {
        'USD': Decimal('100000.00'),
        'BTC': Decimal('1.0'),
        'ETH': Decimal('10.0')
    }

@pytest.fixture
def mock_exchange_service():
    """Basic mock for exchange service."""
    return MockExchangeService() # Return MockExchangeService instance
