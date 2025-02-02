import pytest
from decimal import Decimal
from unittest.mock import Mock, AsyncMock
from ...src.trading.risk_management import RiskManager
from ...src.trading.exceptions import InsufficientLiquidityError, ValidationError

@pytest.fixture
def market_data_service():
    """Create a mock market data service."""
    service = AsyncMock()
    service.get_recent_prices.return_value = [100.0, 101.0, 99.0, 100.5]
    service.get_orderbook.return_value = {
        'asks': [[100.0, 1.0], [101.0, 2.0]],
        'bids': [[99.0, 1.0], [98.0, 2.0]]
    }
    return service

@pytest.fixture
def risk_manager(market_data_service):
    """Create a RiskManager instance with mock market data service."""
    return RiskManager(risk_threshold=0.5, market_data_service=market_data_service)

@pytest.mark.asyncio
async def test_assess_risk_normal_conditions(risk_manager):
    """Test risk assessment under normal conditions."""
    result = await risk_manager.assess_risk(100.0, 'BTC-USD')
    assert result is True

@pytest.mark.asyncio
async def test_assess_risk_high_exposure(risk_manager):
    """Test risk assessment with high exposure."""
    # Calculate a price that would exceed the risk threshold
    max_position = float(risk_manager.max_position_value)
    high_price = max_position / 100  # Using standard lot size
    
    result = await risk_manager.assess_risk(high_price * 2, 'BTC-USD')
    assert result is False

@pytest.mark.asyncio
async def test_assess_risk_high_volatility(risk_manager, market_data_service):
    """Test risk assessment with high volatility."""
    # Set up prices with high volatility
    market_data_service.get_recent_prices.return_value = [100.0, 150.0, 90.0, 120.0]
    
    result = await risk_manager.assess_risk(100.0, 'BTC-USD')
    assert result is False

@pytest.mark.asyncio
async def test_validate_order_success(risk_manager):
    """Test successful order validation."""
    order = {
        'price': 100.0,
        'size': 1.0,
        'trading_pair': 'BTC-USD',
        'side': 'buy'
    }
    
    is_valid, error_msg = await risk_manager.validate_order(order)
    assert is_valid is True
    assert error_msg is None

@pytest.mark.asyncio
async def test_validate_order_invalid_params(risk_manager):
    """Test order validation with invalid parameters."""
    order = {
        'price': -100.0,
        'size': 1.0,
        'trading_pair': 'BTC-USD'
    }
    
    is_valid, error_msg = await risk_manager.validate_order(order)
    assert is_valid is False
    assert "Price and size must be positive" in error_msg

@pytest.mark.asyncio
async def test_validate_order_insufficient_liquidity(risk_manager, market_data_service):
    """Test order validation with insufficient liquidity."""
    # Setup order size larger than available liquidity
    order = {
        'price': 100.0,
        'size': 10.0,  # Much larger than available liquidity
        'trading_pair': 'BTC-USD',
        'side': 'buy'
    }
    
    is_valid, error_msg = await risk_manager.validate_order(order)
    assert is_valid is False
    assert "Insufficient liquidity" in error_msg

@pytest.mark.asyncio
async def test_validate_order_below_minimum(risk_manager):
    """Test order validation with value below minimum."""
    min_value = float(risk_manager.min_position_value)
    small_order = {
        'price': min_value / 200,  # Will result in value below minimum
        'size': 1.0,
        'trading_pair': 'BTC-USD',
        'side': 'buy'
    }
    
    is_valid, error_msg = await risk_manager.validate_order(small_order)
    assert is_valid is False
    assert "below minimum" in error_msg

@pytest.mark.asyncio
async def test_validate_order_above_maximum(risk_manager):
    """Test order validation with value above maximum."""
    max_value = float(risk_manager.max_position_value)
    large_order = {
        'price': max_value,
        'size': 2.0,  # Will exceed maximum
        'trading_pair': 'BTC-USD',
        'side': 'buy'
    }
    
    is_valid, error_msg = await risk_manager.validate_order(large_order)
    assert is_valid is False
    assert "exceeds maximum" in error_msg

def test_calculate_position_value(risk_manager):
    """Test position value calculation."""
    # Test normal case
    value = risk_manager.calculate_position_value(Decimal('100.0'))
    assert value == Decimal('100.0') * Decimal('100')  # Standard lot size
    
    # Test minimum value enforcement
    small_value = risk_manager.calculate_position_value(Decimal('0.01'))
    assert small_value == risk_manager.min_position_value
    
    # Test maximum value enforcement
    large_value = risk_manager.calculate_position_value(Decimal('1000000.0'))
    assert large_value == risk_manager.max_position_value

def test_update_risk_threshold(risk_manager):
    """Test risk threshold updates."""
    new_threshold = 0.75
    risk_manager.update_risk_threshold(new_threshold)
    
    assert risk_manager.risk_threshold == Decimal(str(new_threshold))
    assert risk_manager.max_position_value == Decimal(str(new_threshold)) * Decimal('2')
    assert risk_manager.min_position_value == Decimal(str(new_threshold)) * Decimal('0.1')

@pytest.mark.asyncio
async def test_market_data_service_failure(risk_manager, market_data_service):
    """Test behavior when market data service fails."""
    market_data_service.get_recent_prices.side_effect = Exception("Service unavailable")
    
    result = await risk_manager.assess_risk(100.0, 'BTC-USD')
    assert result is False  # Should fail safely

def test_liquidity_ratio_calculation(risk_manager):
    """Test liquidity ratio calculation."""
    orderbook = {
        'asks': [[100.0, 1.0], [101.0, 2.0]],
        'bids': [[99.0, 1.0], [98.0, 2.0]]
    }
    
    order = {
        'side': 'buy',
        'size': 1.5,
        'price': 100.0,
        'trading_pair': 'BTC-USD'
    }
    
    ratio = risk_manager._calculate_liquidity_ratio(order, orderbook)
    expected_ratio = Decimal('1.5') / Decimal('3.0')  # size / total available liquidity
    assert ratio == expected_ratio

@pytest.mark.asyncio
async def test_validate_order_missing_fields(risk_manager):
    """Test order validation with missing required fields."""
    order = {
        'price': 100.0  # Missing size and trading_pair
    }
    
    is_valid, error_msg = await risk_manager.validate_order(order)
    assert is_valid is False
    assert "Invalid order parameters" in error_msg