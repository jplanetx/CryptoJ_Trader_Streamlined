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

def pytest_configure(config):
    """Configure pytest with custom settings and markers."""
    # Set asyncio mode to strict
    config.option.asyncio_mode = "strict"
    
    # Register custom markers
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "performance: Performance benchmark tests")
    config.addinivalue_line("markers", "api: Tests that interact with the Coinbase API")
    config.addinivalue_line("markers", "websocket: Tests for websocket functionality")
    config.addinivalue_line("markers", "paper_trading: Tests for paper trading mode")

@pytest.fixture(scope="function")
def event_loop():
    """Create an instance of the default event loop for each test function."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

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
    'event_loop',
    'test_config_path',
    'emergency_config'
]