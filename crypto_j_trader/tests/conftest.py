"""
Test configuration and fixtures
"""
import pytest
import asyncio
from pathlib import Path
import sys
from typing import AsyncGenerator
from asyncio import AbstractEventLoop
from crypto_j_trader.src.trading.order_executor import OrderExecutor

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Instead of providing event_loop fixture, use the pytest-asyncio policy
@pytest.fixture
def event_loop_policy():
    """Customize the event loop policy if needed."""
    return asyncio.DefaultEventLoopPolicy()

@pytest.fixture
def test_config():
    """Trading bot test configuration."""
    return {
        'trading_pairs': ['BTC-USD', 'ETH-USD'],
        'risk_management': {
            'stop_loss_pct': 0.05,
            'max_position_size': 2.0,  # Increased to allow test orders of 1.0 BTC
            'max_drawdown': 0.2,
            'max_daily_loss': 1000.0  # Large value to prevent daily loss limit during tests
        },
        'api_keys': {
            'key': 'test_key',
            'secret': 'test_secret'
        },
        'paper_trading': True,
        'exchange': {
            'api_key': 'test_api_key',
            'base_url': 'https://api.testexchange.com',
            'timeout': 30
        }
    }

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
    """Mock portfolio data for testing."""
    return {
        'BTC-USD': {
            'size': 1.0,
            'entry_price': 48000.0,
            'stop_loss': 45600.0,
            'unrealized_pnl': 2000.0
        },
        'ETH-USD': {
            'size': 10.0,
            'entry_price': 2400.0,
            'stop_loss': 2280.0,
            'unrealized_pnl': 1000.0
        }
    }

@pytest.fixture
def mock_order_executor(test_config):
    """Create a standardized OrderExecutor instance for testing."""
    return OrderExecutor(
        api_key=test_config['exchange']['api_key'],
        base_url=test_config['exchange']['base_url'],
        timeout=test_config['exchange']['timeout']
    )

@pytest.fixture
def mock_filled_order():
    """Mock order data for a filled order."""
    return {
        'id': 'test_order_1',
        'product_id': 'BTC-USD',
        'side': 'buy',
        'type': 'market',
        'size': '1.0',
        'price': '50000.0',
        'status': 'filled',
        'filled_quantity': 1.0,
        'remaining_quantity': 0.0,
        'timestamp': '2024-01-28T00:00:00Z'
    }
