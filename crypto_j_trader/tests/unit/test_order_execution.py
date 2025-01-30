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

def test_create_order(order_executor):
    """Test basic order creation"""
    result = order_executor.create_order("BTC-USD", "buy", 0.1, 50000.0)
    assert result["status"] == "success"
    assert "order_id" in result
    assert result["symbol"] == "BTC-USD"

def test_create_order_invalid_parameters(order_executor):
    """Test order creation with invalid parameters"""
    result = order_executor.create_order("", "buy", 0.1, 50000.0)
    assert result["status"] == "error"
    assert "Invalid symbol" in result["message"]

def test_order_status_tracking(order_executor):
    """Test order status tracking"""
    create_result = order_executor.create_order("BTC-USD", "buy", 0.1, 50000.0)
    status_result = order_executor.get_order_status(create_result["order_id"])
    assert status_result["status"] == "filled"
    assert "filled_quantity" in status_result
    assert "remaining_quantity" in status_result

def test_cancel_order(order_executor):
    """Test order cancellation"""
    create_result = order_executor.create_order("BTC-USD", "buy", 0.1, 50000.0)
    cancel_result = order_executor.cancel_order(create_result["order_id"])
    assert cancel_result["status"] == "success"
    assert cancel_result["order_id"] == create_result["order_id"]

def test_create_order_missing_symbol(order_executor):
    """Test order creation with missing symbol"""
    result = order_executor.create_order(None, "buy", 0.1, 50000.0)
    assert result["status"] == "error"
    assert "Invalid symbol" in result["message"]

def test_create_order_missing_quantity(order_executor):
    """Test order creation with missing quantity"""
    result = order_executor.create_order("BTC-USD", "buy", 0, 50000.0)
    assert result["status"] == "error"
    assert "Invalid quantity" in result["message"]

def test_create_order_invalid_price(order_executor):
    """Test order creation with invalid price"""
    result = order_executor.create_order("BTC-USD", "buy", 0.1, -50000.0)
    assert result["status"] == "error"
    assert "Invalid price" in result["message"]