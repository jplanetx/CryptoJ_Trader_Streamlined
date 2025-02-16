import sys
import os

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

"""
Global pytest configuration and fixtures for CryptoJ Trader tests.
"""
import pytest
import pytest_asyncio
from typing import Dict, Any
from .utils import (
    async_timeout,
    test_config,
    mock_market_data,
    mock_account_balance,
    test_env_config
)

"""Base test fixtures and utilities"""
from decimal import Decimal
from datetime import datetime

from crypto_j_trader.src.trading.config_manager import ConfigManager
from crypto_j_trader.src.trading.order_executor import OrderExecutor
from crypto_j_trader.src.trading.trading_core import TradingBot

def pytest_configure(config):
    """Configure pytest with custom settings and markers."""
    # Register custom markers
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "performance: Performance benchmark tests")
    config.addinivalue_line("markers", "api: Tests that interact with the Coinbase API")
    config.addinivalue_line("markers", "websocket: Tests for websocket functionality")
    config.addinivalue_line("markers", "paper_trading: Tests for paper trading mode")

@pytest.fixture(autouse=True)
def test_timeout():
    """Global test timeout to prevent hanging tests."""
    # Default 5 second timeout for all tests
    pytest.timeout = 5

@pytest.fixture
def mock_response_factory():
    """Factory for creating mock API responses with custom data."""
    def _create_mock_response(success: bool = True, data: Dict[str, Any] = None, 
                            error: str = None) -> Dict[str, Any]:
        if success and data is not None:
            return {
                "success": True,
                "data": data,
                "error": None
            }
        return {
            "success": False,
            "data": None,
            "error": error or "Mock error response"
        }
    return _create_mock_response

@pytest.fixture
def performance_thresholds():
    """Define performance test thresholds."""
    return {
        'api_response_time': 0.5,  # seconds
        'order_execution_time': 0.1,  # seconds
        'websocket_message_processing': 0.05,  # seconds
        'max_memory_increase': 50 * 1024 * 1024,  # 50MB
    }

@pytest.fixture
def test_config_path():
    """Fixture providing the path to test configuration."""
    return os.path.abspath(os.path.join(project_root, '..', 'config', 'test_config.json'))

@pytest.fixture
def emergency_config():
    """Fixture providing emergency manager test configuration."""
    return {
        "position_limit": 50000,
        "state_file": "test_emergency_state.json",
        "risk_factor": 0.02,
        "emergency_thresholds": {
            "max_latency": 1000,
            "market_data_max_age": 60,
            "min_available_funds": 1000.0
        },
        "trading": {
            "max_position_size": 100000,
            "min_order_size": 10.0
        },
        "monitoring": {
            "health_check_interval": 60,
            "state_save_interval": 300
        }
    }

@pytest.fixture(scope="session")
def config_manager():
    """Provide ConfigManager instance for tests"""
    return ConfigManager()

@pytest.fixture(scope="function")
def test_config(config_manager) -> Dict[str, Any]:
    """Provide test configuration"""
    return config_manager.get_test_config()

@pytest.fixture(scope="function")
def order_executor(test_config) -> OrderExecutor:
    """Provide OrderExecutor instance configured for testing"""
    trading_pair = test_config['trading_pairs'][0]  # Use first pair by default
    return OrderExecutor(
        trading_pair=trading_pair,
        mock_mode=True
    )

@pytest.fixture(scope="function")
def trading_bot(test_config, order_executor) -> TradingBot:
    """Provide TradingBot instance configured for testing"""
    bot = TradingBot(config=test_config)
    bot.order_executor = order_executor
    return bot

@pytest.fixture(scope="function")
def initialize_test_position(order_executor):
    """Helper fixture to initialize a test position"""
    async def _initialize(symbol: str, size: Decimal, price: Decimal):
        await order_executor.execute_order(
            side="buy",
            size=float(size),
            price=float(price),
            symbol=symbol
        )
    return _initialize

def verify_position_info(position: Dict[str, Any]) -> None:
    """Verify position info structure"""
    required_fields = {
        'size': Decimal,
        'entry_price': Decimal,
        'unrealized_pnl': Decimal,
        'timestamp': datetime,
        'stop_loss': Decimal
    }
    
    for field, expected_type in required_fields.items():
        assert field in position, f"Missing required field: {field}"
        assert isinstance(position[field], expected_type), f"Field {field} has wrong type"

def verify_order_response(response: Dict[str, Any]) -> None:
    """Verify order response structure"""
    required_fields = {
        'status': str,
        'order_id': str,
        'symbol': str,
        'side': str,
        'size': str,
        'price': str,
        'type': str,
        'timestamp': str
    }
    
    for field, expected_type in required_fields.items():
        assert field in response, f"Missing required field: {field}"
        assert isinstance(response[field], expected_type), f"Field {field} has wrong type"
    
    assert response['status'] in ('filled', 'error', 'success'), f"Invalid status: {response['status']}"

# Re-export fixtures from utils
__all__ = [
    'async_timeout',
    'test_config',
    'mock_market_data',
    'mock_account_balance',
    'test_env_config',
    'test_timeout',
    'mock_response_factory',
    'performance_thresholds',
    'test_config_path',
    'emergency_config'
]

"""Configure test fixtures"""
import os
import pytest
from decimal import Decimal
from typing import Dict, Any
from crypto_j_trader.src.trading.order_execution import OrderExecutor
from crypto_j_trader.src.trading.paper_trading import PaperTrader
from crypto_j_trader.src.trading.market_data_handler import MarketDataHandler

class MockMarketData(MarketDataHandler):
    """Mock market data handler for testing"""
    def __init__(self):
        self.price_feed = {
            "BTC-USD": Decimal("50000"),
            "ETH-USD": Decimal("2000")
        }
        self.price_history = {
            "BTC-USD": [
                Decimal("49800"),
                Decimal("49900"),
                Decimal("50000"),
                Decimal("50100"),
                Decimal("50200")
            ],
            "ETH-USD": [
                Decimal("1980"),
                Decimal("1990"),
                Decimal("2000"),
                Decimal("2010"),
                Decimal("2020")
            ]
        }
        
    def get_current_price(self, trading_pair: str) -> Decimal:
        """Get current price from mock data"""
        return self.price_feed.get(trading_pair)
    
    def get_price_history(self, symbol: str, period: str = '5m') -> list:
        """Get historical prices for volatility calculation"""
        return self.price_history.get(symbol, [])

@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Create test configuration for trading system"""
    return {
        'api_key': 'test_api_key',
        'api_secret': 'test_api_secret',
        'timeout': 30,
        'paper_trading': {
            'enabled': True,
            'initial_balance': 100000.0,
            'simulate_slippage': True,
            'slippage_pct': 0.001
        },
        'trading_pairs': ['BTC-USD', 'ETH-USD'],
        'risk_management': {
            'max_position_size': 5.0,
            'stop_loss_pct': 0.05,
            'max_drawdown': 0.2,
            'daily_loss_limit': 1000.0
        },
        'market_data': {
            'update_interval': '1s',
            'history_length': '1h'
        }
    }

@pytest.fixture
def trading_system(test_config):
    """Create trading system with mock components"""
    market_data = MockMarketData()
    trader = PaperTrader(market_data, trading_pair="BTC-USD")
    return {
        "trader": trader,
        "market_data": market_data,
        "config": test_config
    }

@pytest.fixture
def multi_asset_trading_system(test_config):
    """Set up trading system for multi-asset trading"""
    market_data = MockMarketData()
    trader = PaperTrader(market_data, trading_pair="BTC-USD")
    return {
        "market_data": market_data,
        "trader": trader,
        "config": test_config
    }