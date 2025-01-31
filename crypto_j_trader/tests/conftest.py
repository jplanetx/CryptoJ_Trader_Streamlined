"""
Test configuration and fixtures
"""
import pytest
import asyncio
from pathlib import Path
import sys
from typing import AsyncGenerator
from asyncio import AbstractEventLoop

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
            'max_position_size': 0.1,
            'max_drawdown': 0.2
        },
        'api_keys': {
            'key': 'test_key',
            'secret': 'test_secret'
        },
        'paper_trading': True
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