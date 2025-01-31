"""Integration tests for order execution functionality."""

import pytest
from decimal import Decimal
from crypto_j_trader.src.trading.order_execution import OrderExecutor
from crypto_j_trader.src.trading.trading_core import TradingBot

@pytest.fixture
def trading_config():
    """Test configuration."""
    return {
        'trading_pairs': ['ETH-USD'],
        'paper_trading': True,
        'risk_management': {
            'stop_loss_pct': 0.05,
            'max_position_size': 0.1
        }
    }

@pytest.fixture
def order_executor():
    """Create OrderExecutor instance in paper trading mode."""
    return OrderExecutor(
        exchange_client=None,
        trading_pair='ETH-USD',
        paper_trading=True
    )

@pytest.fixture
def trading_bot(trading_config):
    """Create TradingBot instance."""
    return TradingBot(trading_config)

def test_order_execution_success(order_executor):
    """Test that a paper trading order is executed successfully."""
    result = order_executor.execute_order(
        side='buy',
        size=Decimal('0.1'),
        order_type='market'
    )
    
    assert result['status'] == 'filled'
    assert result['product_id'] == 'ETH-USD'
    assert result['side'] == 'buy'
    assert result['size'] == '0.1'

def test_order_execution_limit_order(order_executor):
    """Test executing a limit order in paper trading mode."""
    result = order_executor.execute_order(
        side='buy',
        size=Decimal('0.1'),
        order_type='limit',
        limit_price=Decimal('2000.00')
    )
    
    assert result['status'] == 'filled'
    assert result['type'] == 'limit'
    assert result['price'] == '2000.00'

def test_order_execution_validation(order_executor):
    """Test order validation."""
    with pytest.raises(ValueError, match="Invalid order side"):
        order_executor.execute_order(
            side='invalid',
            size=Decimal('0.1')
        )
    
    with pytest.raises(ValueError, match="Limit price required"):
        order_executor.execute_order(
            side='buy',
            size=Decimal('0.1'),
            order_type='limit'
        )