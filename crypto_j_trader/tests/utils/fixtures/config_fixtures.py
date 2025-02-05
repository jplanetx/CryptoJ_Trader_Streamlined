"""
Test configuration fixtures for CryptoJ Trader tests.
"""
import pytest
from typing import Dict, Any
from crypto_j_trader.tests.utils.mocks.coinbase_mocks import MockExchangeService # Import MockExchangeService

@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Provide base test configuration for TradingBot."""
    return {
        'trading': {
            'symbols': ['BTC-USD', 'ETH-USD'],
            'base_currency': 'USD',
            'update_interval': 60,
            'max_trades_per_day': 10
        },
        'risk_management': {
            'max_position_size': 10.0,
            'max_daily_loss': 5000.0,
            'stop_loss_pct': 0.05,
            'take_profit_pct': 0.1,
            'max_leverage': 3.0,
            'risk_threshold': 0.1  # Default risk threshold for tests
        },
        'paper_trading': True,
        'api': {
            'rate_limit_per_second': 5,
            'max_retries': 3,
            'retry_delay': 1.0
        },
        'api_key': 'test_api_key',  # Dummy API key for tests
        'api_secret': 'test_api_secret'  # Dummy API secret for tests
    }

@pytest.fixture
def mock_market_data() -> Dict[str, Any]:
    """Provide mock market data for testing."""
    return {
        'BTC-USD': {
            'price': 45000.0,
            'volume': 1000.0,
            'bid': 44990.0,
            'ask': 45010.0,
            'timestamp': '2025-02-01T12:00:00Z'
        },
        'ETH-USD': {
            'price': 2800.0,
            'volume': 5000.0,
            'bid': 2799.0,
            'ask': 2801.0,
            'timestamp': '2025-02-01T12:00:00Z'
        }
    }

@pytest.fixture
def mock_account_balance() -> Dict[str, float]:
    """Provide mock account balance data for testing."""
    return {
        'USD': 100000.0,
        'BTC': 1.0,
        'ETH': 10.0
    }

@pytest.fixture
def test_env_config() -> Dict[str, Any]:
    """Provide environment-specific test configuration."""
    return {
        'test': {
            'api_base_url': 'https://api-test.coinbase.com',
            'ws_feed_url': 'wss://ws-feed-test.coinbase.com',
            'use_sandbox': True
        },
        'sandbox': {
            'api_base_url': 'https://api-public.sandbox.coinbase.com',
            'ws_feed_url': 'wss://ws-feed-public.sandbox.coinbase.com',
            'use_sandbox': True
        }
    }

@pytest.fixture
def mock_exchange_service():
    """Basic mock for exchange service."""
    return MockExchangeService() # Return MockExchangeService instance
