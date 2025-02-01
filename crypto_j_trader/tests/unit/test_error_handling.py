import pytest
from crypto_j_trader.src.trading.order_executor import OrderExecutor

@pytest.fixture
def test_config():
    return {
        'api_key': 'test_api_key',
        'base_url': 'https://api.testexchange.com',
        'timeout': 30
    }

@pytest.fixture
def order_executor(test_config):
    return OrderExecutor(
        api_key=test_config['api_key'],
        base_url=test_config['base_url'],
        timeout=test_config['timeout']
    )

def test_null_checks(order_executor):
    """Test null parameter handling"""
    result = order_executor.create_order(None, "buy", 0.1, 50000.0)
    assert result["status"] == "error"
    assert "Invalid symbol" in result["message"]

def test_negative_quantity(order_executor):
    """Test negative quantity handling"""
    result = order_executor.create_order("BTC-USD", "buy", -0.1, 50000.0)
    assert result["status"] == "error"
    assert "Invalid quantity" in result["message"]

def test_invalid_order_type(order_executor):
    """Test invalid order type handling"""
    result = order_executor.create_order("BTC-USD", "invalid", 0.1, 50000.0)
    assert result["status"] == "error"

def test_error_recovery(order_executor):
    """Test error recovery flow"""
    # First create an invalid order
    error_result = order_executor.create_order(None, "buy", 0.1, 50000.0)
    assert error_result["status"] == "error"
    
    # Then create a valid order
    success_result = order_executor.create_order("BTC-USD", "buy", 0.1, 50000.0)
    assert success_result["status"] == "success"