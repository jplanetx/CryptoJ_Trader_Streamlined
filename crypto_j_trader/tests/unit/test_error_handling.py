import pytest
from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime
from crypto_j_trader.src.trading.order_executor import OrderExecutor, OrderResponse, PositionInfo

@pytest.fixture
def test_config() -> Dict[str, Any]:
    return {
        'api_key': 'test_api_key',
        'base_url': 'https://api.testexchange.com',
        'timeout': 30,
        'trading_pair': 'BTC-USD'
    }

@pytest.fixture
def order_executor(test_config: Dict[str, Any]) -> OrderExecutor:
    return OrderExecutor(
        trading_pair=test_config['trading_pair'],
        api_key=test_config.get('api_key'),
        base_url=test_config.get('base_url'),
        timeout=test_config.get('timeout', 30)
    )

def verify_order_response_format(response: Dict) -> None:
    """Verify that order response contains all required fields with correct types"""
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
        
    # Verify status is one of the allowed values
    assert response['status'] in ('filled', 'error', 'success'), f"Invalid status: {response['status']}"

def verify_position_info_format(position: Dict) -> None:
    """Verify that position info contains all required fields with correct types"""
    required_fields = {
        'size': (Decimal, str),  # Can be Decimal or string
        'entry_price': (Decimal, str),
        'unrealized_pnl': (Decimal, str),
        'timestamp': (datetime, str)
    }
    
    for field, expected_types in required_fields.items():
        assert field in position, f"Missing required field: {field}"
        assert isinstance(position[field], expected_types), f"Field {field} has wrong type"

@pytest.mark.asyncio
async def test_null_checks(order_executor: OrderExecutor) -> None:
    """Test null parameter handling"""
    try:
        result = await order_executor.create_order(symbol=None, side="buy", quantity=Decimal('0.1'), price=Decimal('50000.0'))
    except ValueError as e:
        assert "Invalid symbol" in str(e)
    else:
        verify_order_response_format(result)
        assert result["status"] == "error"
        assert "Invalid symbol" in result["message"]

@pytest.mark.asyncio
async def test_negative_quantity(order_executor: OrderExecutor) -> None:
    """Test negative quantity handling"""
    try:
        result = await order_executor.create_order(
            symbol="BTC-USD", 
            side="buy", 
            quantity=Decimal('-0.1'), 
            price=Decimal('50000.0')
        )
    except ValueError as e:
        assert "Invalid quantity" in str(e)
    else:
        assert result["status"] == "error"
        assert "Invalid quantity" in result["message"]

@pytest.mark.asyncio
async def test_invalid_order_type(order_executor: OrderExecutor) -> None:
    """Test invalid order type handling"""
    try:
        result = await order_executor.create_order(
            symbol="BTC-USD",
            side="invalid",
            quantity=Decimal('0.1'),
            price=Decimal('50000.0')
        )
    except ValueError as e:
        assert "Invalid side" in str(e)
    else:
        assert result["status"] == "error"
        assert "Invalid side" in result["message"]  # Updated to match actual error

@pytest.mark.asyncio
async def test_error_recovery(order_executor: OrderExecutor) -> None:
    """Test error recovery flow"""
    # First create an invalid order
    try:
        error_result = await order_executor.create_order(
            symbol=None,
            side="buy",
            quantity=Decimal('0.1'),
            price=Decimal('50000.0')
        )
    except ValueError:
        pass  # Expected error
    
    # Then create a valid order
    success_result = await order_executor.create_order(
        symbol="BTC-USD",
        side="buy",
        quantity=Decimal('0.1'),
        price=Decimal('50000.0')
    )
    # Check that either 'filled' or 'success' status is returned
    assert success_result["status"] in ("filled", "success")

@pytest.mark.asyncio
async def test_response_format_success(order_executor: OrderExecutor) -> None:
    """Test successful order response format"""
    result = await order_executor.create_order(
        symbol="BTC-USD",
        side="buy",
        quantity=Decimal('0.1'),
        price=Decimal('50000.0')
    )
    verify_order_response_format(result)
    assert result["status"] in ("filled", "success")
    assert Decimal(result["size"]) == Decimal('0.1')
    assert Decimal(result["price"]) == Decimal('50000.0')

@pytest.mark.asyncio
async def test_position_format(order_executor: OrderExecutor) -> None:
    """Test position info format"""
    # First create a position
    await order_executor.create_order(
        symbol="BTC-USD",
        side="buy",
        quantity=Decimal('0.1'),
        price=Decimal('50000.0')
    )
    
    # Get and verify position
    position = order_executor.get_position("BTC-USD")
    verify_position_info_format(position)
    assert Decimal(str(position["size"])) == Decimal('0.1')
    
    # Verify empty position format
    empty_position = order_executor.get_position("ETH-USD")
    verify_position_info_format(empty_position)
    assert Decimal(str(empty_position["size"])) == Decimal('0')