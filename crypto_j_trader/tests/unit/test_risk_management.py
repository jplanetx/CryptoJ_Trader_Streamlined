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
    return RiskManager(risk_threshold=0.75, market_data_service=market_data_service)

@pytest.mark.asyncio
async def test_assess_risk_normal_conditions(risk_manager):
    """Test risk assessment under normal conditions."""
    result = await risk_manager.assess_risk(100.0, 'BTC-USD', 1.0)
    assert result is True

@pytest.mark.asyncio
async def test_assess_risk_high_exposure(risk_manager):
    """Test risk assessment with high exposure."""
    # Calculate a price that would exceed the risk threshold
    max_position = float(risk_manager.max_position_value)
    high_price = max_position / 100  # Using standard lot size
    
    result = await risk_manager.assess_risk(high_price * 2, 'BTC-USD', 1.0)
    assert result is False

@pytest.mark.asyncio
async def test_assess_risk_high_volatility(risk_manager, market_data_service):
    """Test risk assessment with high volatility."""
    # Set up prices with high volatility
    market_data_service.get_recent_prices.return_value = [100.0, 150.0, 90.0, 120.0]
    
    result = await risk_manager.assess_risk(100.0, 'BTC-USD', 1.0)
    assert result is False

@pytest.mark.asyncio
async def test_validate_order_success(risk_manager):
    """Test successful order validation."""
    order = {
        'price': 0.01,
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
    assert "Insufficient liquidity" in error_msg or "exceeds maximum" in error_msg

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

@pytest.mark.asyncio
async def test_validate_order_exactly_at_minimum(risk_manager):
    """Test order validation with value exactly at minimum."""
    min_value = float(risk_manager.min_position_value)
    order = {
        'price': float(risk_manager.min_position_value),  # Standard lot size is 100
        'size': 1.0,
        'trading_pair': 'BTC-USD',
        'side': 'buy'
    }

    is_valid, error_msg = await risk_manager.validate_order(order)
    assert is_valid is True
    assert error_msg is None

@pytest.mark.asyncio
async def test_validate_order_exactly_at_maximum(risk_manager):
    """Test order validation with value exactly at maximum."""
    max_value = float(risk_manager.max_position_value)
    order = {
        'price': float(risk_manager.max_position_value),
        'size': 1.0,
        'trading_pair': 'BTC-USD',
        'side': 'buy'
    }

    is_valid, error_msg = await risk_manager.validate_order(order)
    assert is_valid is True
    assert error_msg is None

@pytest.mark.asyncio
async def test_validate_order_exceeds_maximum_by_small_amount(risk_manager):
    """Test order validation when exceeding the maximum position value by a small amount."""
    max_value = float(risk_manager.max_position_value)
    order = {
        'price': (max_value + 1) / 100,  # Exceeds maximum by 10
        'size': 1.0,
        'trading_pair': 'BTC-USD',
        'side': 'buy'
    }

    is_valid, error_msg = await risk_manager.validate_order(order)
    assert is_valid is False
    assert "exceeds maximum" in error_msg

@pytest.mark.asyncio
async def test_validate_order_below_minimum_by_small_amount(risk_manager):
    """Test order validation when below the minimum position value by a small amount."""
    min_value = float(risk_manager.min_position_value)
    order = {
        'price': (min_value - 0.01) / 100,  # Below minimum by 0.01
        'size': 1.0,
        'trading_pair': 'BTC-USD',
        'side': 'buy'
    }

    is_valid, error_msg = await risk_manager.validate_order(order)
    assert is_valid is False
    assert "below minimum" in error_msg

def test_calculate_position_value(risk_manager):
    """Test position value calculation."""
    # Test normal case
    value = risk_manager.calculate_position_value(Decimal('0.015'))
    assert value == risk_manager.max_position_value  # Capped at max_position_value

    # Test minimum value enforcement
    small_value = risk_manager.calculate_position_value(Decimal('0.01'))
    assert small_value == risk_manager.min_position_value
    
    # Test maximum value enforcement
    large_value = risk_manager.calculate_position_value(Decimal('1000000.0'))
    assert large_value == risk_manager.max_position_value

def test_calculate_position_value_negative_price(risk_manager):
    """Test position value calculation with a negative price."""
    value = risk_manager.calculate_position_value(Decimal('-1.0'))
    assert value == risk_manager.min_position_value

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

    result = await risk_manager.assess_risk(100.0, 'BTC-USD', 1.0)
    assert result is True  # Should pass safely when market data service fails

@pytest.mark.asyncio
async def test_assess_risk_no_market_data(risk_manager):
    """Test risk assessment when market data service returns None."""
    risk_manager.market_data_service = None
    result = await risk_manager.assess_risk(100.0, 'BTC-USD', 1.0)
    assert result is True  # Should pass safely if no market data

@pytest.mark.asyncio
async def test_assess_risk_empty_market_data(risk_manager, market_data_service):
    """Test risk assessment when market data service returns an empty list."""
    market_data_service.get_recent_prices.return_value = []
    result = await risk_manager.assess_risk(100.0, 'BTC-USD', 1.0)
    assert result is True  # Should pass safely if no market data

@pytest.mark.asyncio
async def test_assess_risk_high_price_low_volatility(risk_manager, market_data_service):
    """Test risk assessment with a high price but low volatility."""
    market_data_service.get_recent_prices.return_value = [100000.0, 100001.0, 99999.0, 100000.5]
    result = await risk_manager.assess_risk(100000.0, 'BTC-USD', 1.0)
    assert result is False

@pytest.mark.asyncio
async def test_assess_risk_moderate_volatility(risk_manager, market_data_service):
    """Test risk assessment with moderate volatility."""
    market_data_service.get_recent_prices.return_value = [100.0, 102.0, 98.0, 101.0]
    result = await risk_manager.assess_risk(100.0, 'BTC-USD', 1.0)
    assert result is True

@pytest.mark.asyncio
async def test_assess_risk_extreme_volatility(risk_manager, market_data_service):
    """Test risk assessment with extreme volatility."""
    market_data_service.get_recent_prices.return_value = [50.0, 150.0, 25.0, 175.0]
    result = await risk_manager.assess_risk(100.0, 'BTC-USD', 1.0)
    assert result is False

@pytest.mark.asyncio
async def test_assess_risk_normal_conditions_with_low_price(risk_manager):
    """Test risk assessment under normal conditions with a low price."""
    result = await risk_manager.assess_risk(1.0, 'BTC-USD', 1.0)
    assert result is True

@pytest.mark.asyncio
async def test_assess_risk_normal_conditions_with_high_price(risk_manager):
    """Test risk assessment under normal conditions with a high price."""
    result = await risk_manager.assess_risk(100000.0, 'BTC-USD', 1.0)
    assert result is False

@pytest.mark.asyncio
async def test_validate_order_empty_orderbook(risk_manager, market_data_service):
    """Test order validation with an empty orderbook."""
    market_data_service.get_orderbook.return_value = None
    order = {
        'price': 0.01,
        'size': 1.0,
        'trading_pair': 'BTC-USD',
        'side': 'buy'
    }

    is_valid, error_msg = await risk_manager.validate_order(order)
    assert is_valid is True
    assert error_msg is None

@pytest.mark.asyncio
async def test_validate_order_zero_liquidity(risk_manager, market_data_service):
    """Test order validation when the orderbook has zero liquidity."""
    market_data_service.get_orderbook.return_value = {
        'asks': [],
        'bids': []
    }
    order = {
        'price': 100.0,
        'size': 1.0,
        'trading_pair': 'BTC-USD',
        'side': 'buy'
    }

    is_valid, error_msg = await risk_manager.validate_order(order)
    assert is_valid is False
    assert "Insufficient liquidity" in error_msg

@pytest.mark.asyncio
async def test_validate_order_invalid_side(risk_manager):
    """Test order validation with an invalid order side."""
    order = {
        'price': 100.0,
        'size': 1.0,
        'trading_pair': 'BTC-USD',
        'side': 'invalid'
    }

    is_valid, error_msg = await risk_manager.validate_order(order)
    assert is_valid is False
    assert "Invalid order parameters" in error_msg

@pytest.mark.asyncio
async def test_liquidity_ratio_calculation(risk_manager):
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

@pytest.mark.asyncio
async def test_validate_order_exceeds_loss_limit(risk_manager):
    """Test order validation when exceeding the maximum daily loss limit."""
    risk_manager.current_daily_loss = risk_manager.max_daily_loss
    order = {
        'price': 100.0,
        'size': 1.0,
        'trading_pair': 'BTC-USD',
        'side': 'buy'
    }

    is_valid, error_msg = await risk_manager.validate_order(order)
    assert is_valid is False
    assert "Maximum daily loss exceeded" in error_msg or "exceeds maximum" in error_msg

@pytest.mark.asyncio
async def test_validate_order_within_loss_limit(risk_manager):
    """Test order validation when within the maximum daily loss limit."""
    risk_manager.current_daily_loss = 0
    order = {
        'price': 0.01,
        'size': 1.0,
        'trading_pair': 'BTC-USD',
        'side': 'buy'
    }

    is_valid, error_msg = await risk_manager.validate_order(order)
    assert is_valid is True
    assert error_msg is None

@pytest.mark.asyncio
async def test_validate_order_close_to_loss_limit(risk_manager):
    """Test order validation when close to exceeding the maximum daily loss limit."""
    risk_manager.current_daily_loss = risk_manager.max_daily_loss - 10
    order = {
        'price': 0.01,
        'size': 1.0,
        'trading_pair': 'BTC-USD',
        'side': 'buy'
    }

    is_valid, error_msg = await risk_manager.validate_order(order)
    assert is_valid is True
    assert error_msg is None

@pytest.mark.asyncio
async def test_validate_order_exceeds_loss_limit_by_small_amount(risk_manager):
    """Test order validation when exceeding the maximum daily loss limit by a small amount."""
    risk_manager.current_daily_loss = risk_manager.max_daily_loss - 5
    order = {
        'price': 10.0,
        'size': 1.0,
        'trading_pair': 'BTC-USD',
        'side': 'buy'
    }

    is_valid, error_msg = await risk_manager.validate_order(order)
    assert is_valid is False
    assert "Maximum daily loss exceeded" in error_msg or "exceeds maximum" in error_msg

@pytest.mark.asyncio
async def test_validate_order_position_limit_with_low_liquidity(risk_manager, market_data_service):
    """Test order validation with position limit and low liquidity."""
    # Set up low liquidity
    market_data_service.get_orderbook.return_value = {
        'asks': [[100.0, 0.1], [101.0, 0.2]],  # Very low liquidity
        'bids': [[99.0, 0.1], [98.0, 0.2]]
    }

    # Set up order that exceeds position limit
    max_value = float(risk_manager.max_position_value)
    order = {
        'price': max_value / 100,
        'size': 1.0,
        'trading_pair': 'BTC-USD',
        'side': 'buy'
    }

    is_valid, error_msg = await risk_manager.validate_order(order)
    assert is_valid is False
    assert "Insufficient liquidity" in error_msg or "exceeds maximum" in error_msg