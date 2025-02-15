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
async def order_executor(test_config):
    """Create OrderExecutor instance."""
    executor = OrderExecutor(
        trading_pair="BTC-USD",
        api_key=test_config['api_key'],
        base_url=test_config['base_url'],
        timeout=test_config['timeout']
    )
    return executor

@pytest.fixture
async def trading_bot(test_config):
    """Create TradingBot instance."""
    return TradingBot(test_config)

@pytest.mark.asyncio
async def test_end_to_end_trading_flow(order_executor):
    """Test complete trading flow including position tracking."""
    # Initial buy order
    buy_result = await order_executor.create_order(
        symbol="ETH-USD",
        side="buy",
        quantity=0.5,
        price=2000.0
    )
    assert buy_result["status"] == "success"
    assert buy_result["order_id"] == "order_1001"
    
    # Verify position was created
    position = await order_executor.get_position("ETH-USD")
    assert position["size"] == Decimal('0.5')
    
    # Add to position
    buy_result2 = await order_executor.create_order(
        symbol="ETH-USD",
        side="buy",
        quantity=0.3,
        price=2100.0
    )
    assert buy_result2["status"] == "success"
    assert buy_result2["order_id"] == "order_1002"
    
    # Verify position was updated correctly
    position = await order_executor.get_position("ETH-USD")
    assert position["size"] == Decimal('0.8')
    expected_avg_price = (Decimal('0.5') * Decimal('2000.0') + Decimal('0.3') * Decimal('2100.0')) / Decimal('0.8')
    assert abs(position["entry_price"] - expected_avg_price) < Decimal('0.01')
    assert position["stop_loss"] == expected_avg_price * Decimal('0.95')
    
    # Partial position reduction
    sell_result = await order_executor.create_order(
        symbol="ETH-USD",
        side="sell",
        quantity=0.3,
        price=2200.0
    )
    assert sell_result["status"] == "success"
    assert sell_result["order_id"] == "order_1003"
    
    # Verify position was reduced
    position = await order_executor.get_position("ETH-USD")
    assert position["size"] == Decimal('0.5')
    assert abs(position["entry_price"] - expected_avg_price) < Decimal('0.01')
    assert position["stop_loss"] == expected_avg_price * Decimal('0.95')

@pytest.mark.asyncio
async def test_multi_pair_trading(order_executor):
    """Test trading multiple pairs simultaneously."""
    # Create ETH position
    await order_executor.create_order("ETH-USD", "buy", 1.0, 2000.0)
    
    # Create BTC position
    await order_executor.create_order("BTC-USD", "buy", 0.1, 50000.0)
    
    # Verify both positions exist
    eth_pos = await order_executor.get_position("ETH-USD")
    btc_pos = await order_executor.get_position("BTC-USD")
    
    assert eth_pos["size"] == Decimal('1.0')
    assert btc_pos["size"] == Decimal('0.1')
    
    # Reduce ETH position
    await order_executor.create_order("ETH-USD", "sell", 0.5, 2100.0)
    
    # Close BTC position
    await order_executor.create_order("BTC-USD", "sell", 0.1, 52000.0)
    
    # Verify position updates
    eth_pos = await order_executor.get_position("ETH-USD")
    btc_pos = await order_executor.get_position("BTC-USD")
    
    assert eth_pos["size"] == Decimal('0.5')
    assert btc_pos["size"] == Decimal('0.0')

@pytest.mark.asyncio
async def test_order_tracking(order_executor):
    """Test order status tracking through lifecycle."""
    # Create order
    buy_result = await order_executor.create_order(
        symbol="ETH-USD",
        side="buy",
        quantity=1.0,
        price=2000.0
    )
    order_id = buy_result["order_id"]
    assert order_id == "order_1001"
    
    # Check status
    status = await order_executor.get_order_status(order_id)
    assert status["status"] == "filled"
    
    # Cancel order (should fail since already filled)
    cancel_result = await order_executor.cancel_order(order_id)
    assert cancel_result["status"] == "error"
    assert "Order already filled" in cancel_result["message"]

@pytest.mark.asyncio
async def test_error_handling(order_executor):
    """Test error handling in trading flow."""
    # Create order with insufficient position size
    result = await order_executor.create_order(
        symbol="ETH-USD",
        side="sell",
        quantity=1.0,
        price=2000.0
    )
    assert result["status"] == "error"
    assert "Insufficient position" in result["message"]

@pytest.mark.asyncio
async def test_full_trading_cycle(order_executor):
    """Test full trading cycle including position tracking and error handling."""
    # Create initial position
    await order_executor.create_order(
        symbol="BTC-USD",
        side="buy",
        quantity=1.0,
        price=50000.0
    )
    
    # Verify position
    position = await order_executor.get_position("BTC-USD")
    assert position["size"] == Decimal('1.0')
    
    # Reduce position
    await order_executor.create_order(
        symbol="BTC-USD",
        side="sell",
        quantity=0.5,
        price=51000.0
    )
    
    # Verify reduced position
    position = await order_executor.get_position("BTC-USD")
    assert position["size"] == Decimal('0.5')
    
    # Close position
    await order_executor.create_order(
        symbol="BTC-USD",
        side="sell",
        quantity=0.5,
        price=52000.0
    )
    
    # Verify position is closed
    position = await order_executor.get_position("BTC-USD")
    assert position["size"] == Decimal('0.0')