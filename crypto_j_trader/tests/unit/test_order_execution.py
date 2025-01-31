import pytest
from decimal import Decimal
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
    assert result["quantity"] == 0.1
    assert result["price"] == 50000.0

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
    assert status_result["filled_quantity"] == 0.1
    assert status_result["remaining_quantity"] == 0.0
    assert status_result["price"] == 50000.0

def test_cancel_order(order_executor):
    """Test order cancellation"""
    create_result = order_executor.create_order("BTC-USD", "buy", 0.1, 50000.0)
    cancel_result = order_executor.cancel_order(create_result["order_id"])
    assert cancel_result["status"] == "success"
    assert cancel_result["order_id"] == create_result["order_id"]
    
    # Verify cancelled order cannot be found
    status_result = order_executor.get_order_status(create_result["order_id"])
    assert status_result["status"] == "error"
    assert "Order not found" in status_result["message"]

def test_position_tracking_buy(order_executor):
    """Test position tracking for buy orders"""
    # Initial buy
    result1 = order_executor.create_order("BTC-USD", "buy", 0.1, 50000.0)
    assert result1["status"] == "success"
    
    position = order_executor.get_position("BTC-USD")
    assert position is not None
    assert position["symbol"] == "BTC-USD"
    assert position["quantity"] == 0.1
    assert position["entry_price"] == 50000.0
    
    # Additional buy - should update position
    result2 = order_executor.create_order("BTC-USD", "buy", 0.2, 51000.0)
    assert result2["status"] == "success"
    
    position = order_executor.get_position("BTC-USD")
    assert position["quantity"] == 0.3
    # Check weighted average entry price
    expected_price = (0.1 * 50000.0 + 0.2 * 51000.0) / 0.3
    assert abs(position["entry_price"] - expected_price) < 0.01

def test_position_tracking_sell(order_executor):
    """Test position tracking for sell orders"""
    # Initial buy
    order_executor.create_order("BTC-USD", "buy", 0.3, 50000.0)
    
    # Partial sell
    result = order_executor.create_order("BTC-USD", "sell", 0.1, 52000.0)
    assert result["status"] == "success"
    
    position = order_executor.get_position("BTC-USD")
    assert position["quantity"] == 0.2
    assert position["entry_price"] == 50000.0  # Entry price unchanged for sells
    
    # Sell remaining - position should be closed
    order_executor.create_order("BTC-USD", "sell", 0.2, 53000.0)
    position = order_executor.get_position("BTC-USD")
    assert position is None

def test_sell_without_position(order_executor):
    """Test selling without an existing position"""
    result = order_executor.create_order("BTC-USD", "sell", 0.1, 50000.0)
    assert result["status"] == "error"
    assert "No position exists" in result["message"]

def test_sell_exceeding_position(order_executor):
    """Test selling more than position size"""
    # Buy 0.1
    order_executor.create_order("BTC-USD", "buy", 0.1, 50000.0)
    
    # Try to sell 0.2
    result = order_executor.create_order("BTC-USD", "sell", 0.2, 51000.0)
    assert result["status"] == "error"
    assert "Insufficient position size" in result["message"]

def test_create_order_validation(order_executor):
    """Test comprehensive order validation"""
    # Test invalid side
    result = order_executor.create_order("BTC-USD", "invalid", 0.1, 50000.0)
    assert result["status"] == "error"
    assert "Invalid side" in result["message"]
    
    # Test zero quantity
    result = order_executor.create_order("BTC-USD", "buy", 0, 50000.0)
    assert result["status"] == "error"
    assert "Invalid quantity" in result["message"]
    
    # Test negative price
    result = order_executor.create_order("BTC-USD", "buy", 0.1, -50000.0)
    assert result["status"] == "error"
    assert "Invalid price" in result["message"]

def test_multiple_positions(order_executor):
    """Test tracking multiple positions"""
    # Create BTC position
    order_executor.create_order("BTC-USD", "buy", 0.1, 50000.0)
    
    # Create ETH position
    order_executor.create_order("ETH-USD", "buy", 1.0, 3000.0)
    
    # Verify both positions
    btc_pos = order_executor.get_position("BTC-USD")
    eth_pos = order_executor.get_position("ETH-USD")
    
    assert btc_pos["quantity"] == 0.1
    assert btc_pos["entry_price"] == 50000.0
    assert eth_pos["quantity"] == 1.0
    assert eth_pos["entry_price"] == 3000.0