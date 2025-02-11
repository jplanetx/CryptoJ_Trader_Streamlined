"""Integration tests for order execution functionality."""

import pytest
from decimal import Decimal
from crypto_j_trader.src.trading.order_executor import OrderExecutor
from crypto_j_trader.src.trading.trading_core import TradingBot

@pytest.fixture
def test_config():
    """Test configuration."""
    return {
        'api_key': 'test_api_key',
        'base_url': 'https://api.testexchange.com',
        'timeout': 30,
        'trading_pairs': ['ETH-USD', 'BTC-USD'],
        'risk_management': {
            'stop_loss_pct': 0.05,
            'max_position_size': 1.0
        }
    }

@pytest.fixture
def order_executor(test_config):
    """Create OrderExecutor instance."""
    return OrderExecutor(
        api_key=test_config['api_key'],
        base_url=test_config['base_url'],
        timeout=test_config['timeout']
    )

@pytest.fixture
def trading_bot(test_config):
    """Create TradingBot instance."""
    return TradingBot(test_config)

def test_end_to_end_trading_flow(order_executor):
    """Test complete trading flow including position tracking."""
    # Initial buy order
    buy_result = order_executor.create_order(
        symbol="ETH-USD",
        side="buy",
        quantity=0.5,
        price=2000.0
    )
    assert buy_result["status"] == "filled"
    assert buy_result["order_id"] == "mock-order-id"
    
    # Verify position was created
    position = order_executor.get_position("ETH-USD")
    assert position is not None
    assert position["size"] == 0.5
    assert position["entry_price"] == 2000.0
    assert position["stop_loss"] == 1900.0  # 5% stop loss
    
    # Add to position
    buy_result2 = order_executor.create_order(
        symbol="ETH-USD",
        side="buy",
        quantity=0.3,
        price=2100.0
    )
    assert buy_result2["status"] == "filled"
    assert buy_result2["order_id"] == "mock-order-id"
    
    # Verify position was updated correctly
    position = order_executor.get_position("ETH-USD")
    assert position["size"] == 0.8
    expected_avg_price = (0.5 * 2000.0 + 0.3 * 2100.0) / 0.8
    assert abs(position["entry_price"] - expected_avg_price) < 0.01
    assert position["stop_loss"] == expected_avg_price * 0.95
    
    # Partial position reduction
    sell_result = order_executor.create_order(
        symbol="ETH-USD",
        side="sell",
        quantity=0.3,
        price=2200.0
    )
    assert sell_result["status"] == "filled"
    assert sell_result["order_id"] == "mock-order-id"
    
    # Verify position was reduced
    position = order_executor.get_position("ETH-USD")
    assert position["size"] == 0.5
    assert abs(position["entry_price"] - expected_avg_price) < 0.01
    assert position["stop_loss"] == expected_avg_price * 0.95

def test_multi_pair_trading(order_executor):
    """Test trading multiple pairs simultaneously."""
    # Create ETH position
    order_executor.create_order("ETH-USD", "buy", 1.0, 2000.0)
    
    # Create BTC position
    order_executor.create_order("BTC-USD", "buy", 0.1, 50000.0)
    
    # Verify both positions exist
    eth_pos = order_executor.get_position("ETH-USD")
    btc_pos = order_executor.get_position("BTC-USD")
    
    assert eth_pos["size"] == 1.0
    assert eth_pos["entry_price"] == 2000.0
    assert eth_pos["stop_loss"] == 1900.0
    
    assert btc_pos["size"] == 0.1
    assert btc_pos["entry_price"] == 50000.0
    assert btc_pos["stop_loss"] == 47500.0
    
    # Reduce ETH position
    order_executor.create_order("ETH-USD", "sell", 0.5, 2100.0)
    
    # Close BTC position
    order_executor.create_order("BTC-USD", "sell", 0.1, 52000.0)
    
    # Verify position updates
    eth_pos = order_executor.get_position("ETH-USD")
    btc_pos = order_executor.get_position("BTC-USD")
    
    assert eth_pos["size"] == 0.5
    assert eth_pos["entry_price"] == 2000.0
    assert eth_pos["stop_loss"] == 1900.0

    # BTC position should be fully closed
    assert btc_pos["size"] == 0.0
    assert btc_pos["entry_price"] == 0.0
    assert btc_pos["stop_loss"] == 0.0

def test_order_tracking(order_executor):
    """Test order status tracking through lifecycle."""
    # Create order
    buy_result = order_executor.create_order(
        symbol="ETH-USD",
        side="buy",
        quantity=1.0,
        price=2000.0
    )
    order_id = buy_result["order_id"]
    assert order_id == "mock-order-id"
    
    # Check status
    status = order_executor.get_order_status(order_id)
    assert status["status"] == "filled"
    
    # Cancel order (should fail since already filled)
    cancel_result = order_executor.cancel_order(order_id)
    assert cancel_result["status"] == "error"
    assert "Order not found" in cancel_result["message"]

def test_error_handling(order_executor):
    """Test error handling in trading flow."""
    # Try to sell without position
    result = order_executor.create_order(
        symbol="ETH-USD",
        side="sell",
        quantity=1.0,
        price=2000.0
    )
    assert result["status"] == "error"
    assert "Insufficient position size" in result["message"]
    
    # Create small position
    order_executor.create_order(
        symbol="ETH-USD",
        side="buy",
        quantity=0.5,
        price=2000.0
    )
    
    # Try to sell more than position size
    result = order_executor.create_order(
        symbol="ETH-USD",
        side="sell",
        quantity=1.0,
        price=2100.0
    )
    assert result["status"] == "error"
    assert "Insufficient position size" in result["message"]