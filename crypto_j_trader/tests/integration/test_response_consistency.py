"""Integration tests for response format consistency across the trading system."""
import pytest
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any

from crypto_j_trader.src.trading.order_executor import OrderExecutor
from crypto_j_trader.src.trading.trading_core import TradingBot

@pytest.fixture
def test_config() -> Dict[str, Any]:
    return {
        'trading_pairs': ['BTC-USD'],
        'risk_management': {
            'max_position_size': 5.0,
            'stop_loss_pct': 0.05
        }
    }

@pytest.mark.asyncio
async def test_order_lifecycle_key_consistency(test_config):
    """Test that all response dictionaries maintain consistent key structure throughout order lifecycle."""
    executor = OrderExecutor(trading_pair="BTC-USD")
    
    # 1. Create order
    create_response = await executor.create_order(
        symbol="BTC-USD",
        side="buy",
        quantity=Decimal('1.0'),
        price=Decimal('50000.0')
    )
    
    # 2. Get order status
    status_response = executor.get_order_status(create_response['order_id'])
    
    # 3. Get position info
    position_info = executor.get_position("BTC-USD")
    
    # Verify key consistency across all responses
    assert 'size' in create_response and 'size' in status_response
    assert 'size' in position_info
    assert 'quantity' not in create_response  # Ensure old key is not present
    assert 'quantity' not in status_response
    assert 'quantity' not in position_info
    
    # Verify value consistency
    assert Decimal(create_response['size']) == Decimal('1.0')
    assert Decimal(status_response['size']) == Decimal('1.0')
    assert position_info['size'] == Decimal('1.0')

@pytest.mark.asyncio
async def test_error_response_consistency(test_config):
    """Test that error responses maintain consistent structure."""
    executor = OrderExecutor(trading_pair="BTC-USD")
    
    # Test various error scenarios
    error_cases = [
        (None, "buy", Decimal('1.0'), Decimal('50000.0')),  # Invalid symbol
        ("BTC-USD", "invalid", Decimal('1.0'), Decimal('50000.0')),  # Invalid side
        ("BTC-USD", "buy", Decimal('-1.0'), Decimal('50000.0')),  # Invalid quantity
        ("BTC-USD", "buy", Decimal('1.0'), Decimal('-50000.0'))  # Invalid price
    ]
    
    for symbol, side, quantity, price in error_cases:
        try:
            response = await executor.create_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price
            )
        except ValueError as e:
            # Even exceptions should have consistent message format
            assert "Invalid" in str(e)
            continue
            
        # If no exception, verify error response format
        assert response['status'] == 'error'
        assert 'message' in response
        assert 'size' in response  # Should still have standard fields
        assert response['size'] == '0'  # Error responses should have safe default values