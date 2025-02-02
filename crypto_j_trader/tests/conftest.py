"""
Global pytest configuration and fixtures for CryptoJ Trader tests.
"""
import pytest
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

# Re-export fixtures from utils
__all__ = [
    'async_timeout',
    'test_config',
    'mock_market_data',
    'mock_account_balance',
    'test_env_config',
    'test_timeout',
    'mock_response_factory',
    'performance_thresholds'
]