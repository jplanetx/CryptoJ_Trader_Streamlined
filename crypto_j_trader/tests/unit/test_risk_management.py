"""Unit tests for risk management system."""
import pytest
from decimal import Decimal
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

from crypto_j_trader.src.trading.risk_management import RiskManager
from crypto_j_trader.src.trading.market_data import MarketDataService
from crypto_j_trader.src.trading.exceptions import InsufficientLiquidityError
from crypto_j_trader.src.trading.trading_core import TradingBot

@pytest.fixture
def risk_manager():
    """Create a RiskManager instance with test configuration"""
    config = {
        'risk_management': {
            'risk_threshold': Decimal('0.75'),
            'max_position_value': Decimal('100000.0'),
            'min_position_value': Decimal('100.0'),
            'max_daily_loss': Decimal('10000.0'),
            'loss_tolerance': Decimal('0.1'),  # 10% tolerance for loss limits
            'position_tolerance': Decimal('0.05'),  # 5% tolerance for position limits
            'volatility_threshold': Decimal('0.15'),  # 15% volatility threshold
            'liquidity_requirement': Decimal('0.5')  # 50% liquidity requirement
        }
    }
    rm = RiskManager(config)
    rm.market_data_service = MockMarketDataService()  # Add mock market data service
    rm.current_daily_loss = Decimal('0')  # Ensure clean state
    return rm

class MockMarketDataService:
    """Mock market data service for testing"""
    def __init__(self):
        self.price_feed = {
            "BTC-USD": Decimal("50000"),
            "ETH-USD": Decimal("2000"),
            "LOW_LIQUIDITY": Decimal("100"),
            "ZERO_LIQUIDITY": Decimal("100"),
            "HIGH_VOLATILITY": Decimal("1000")
        }
        self.order_books = {
            "BTC-USD": {
                "bids": [[49900, 1.0], [49800, 2.0]],
                "asks": [[50100, 1.0], [50200, 2.0]]
            },
            "LOW_LIQUIDITY": {
                "bids": [[99, 0.1]], 
                "asks": [[101, 0.1]]
            },
            "ZERO_LIQUIDITY": {
                "bids": [], 
                "asks": []
            }
        }

    async def get_price(self, symbol: str) -> Optional[Decimal]:
        return self.price_feed.get(symbol)

    async def get_order_book(self, symbol: str) -> Optional[Dict]:
        return self.order_books.get(symbol)

    async def get_recent_trades(self, symbol: str) -> List[Dict]:
        if (symbol == "HIGH_VOLATILITY"):
            return [
                {"price": "900"}, {"price": "1100"},
                {"price": "800"}, {"price": "1200"}
            ]
        return [
            {"price": "50000"}, {"price": "50100"},
            {"price": "49900"}, {"price": "50200"}
        ]

@pytest.fixture
def mock_market_data_service():
    mock_service = AsyncMock(spec=MarketDataService)

    async def mock_get_recent_prices(trading_pair):
        if (trading_pair == "HIGH_VOLATILITY"):
            return [100, 120, 90, 110]
        elif (trading_pair == "LOW_VOLATILITY"):
            return [100, 101, 99, 100]
        elif (trading_pair == "EMPTY"):
            return []
        return [100.0, 101.0, 99.0, 100.5]

    mock_service.get_recent_prices = mock_get_recent_prices

    async def mock_get_orderbook(trading_pair):
        if (trading_pair == "ZERO_LIQUIDITY"):
            return {'asks': [], 'bids': []}
        elif (trading_pair == "LOW_LIQUIDITY"):
            return {'asks': [[100, 0.1]], 'bids': [[99, 0.1]]}
        elif (trading_pair == "EMPTY_ORDERBOOK"):
            return None
        return {
            'asks': [[100.0, 1.0], [101.0, 2.0]],
            'bids': [[99.0, 1.0], [98.0, 2.0]]
        }

    mock_service.get_orderbook = mock_get_orderbook

    return mock_service

@pytest.fixture
def config_risk():
    return {
        'trading_pairs': ['BTC-USD'],
        'risk_management': {
            'max_position_size': 2.0,
            'max_daily_loss': 200.0,
            'stop_loss_pct': 0.05
        }
    }

@pytest.fixture
def trading_bot_risk(config_risk):
    return TradingBot(config=config_risk)

class TestRiskManager:
    def test_calculate_position_value(self, risk_manager):
        price = Decimal('1.0')
        small_value = risk_manager.calculate_position_value(price)
        assert small_value == min(price, risk_manager.max_position_value)

        negative_price = Decimal('-1.0')
        negative_value = risk_manager.calculate_position_value(negative_price)
        assert negative_value == risk_manager.min_position_value

    def test_calculate_position_value_negative_price(self, risk_manager):
        negative_price = Decimal('-1.0')
        negative_value = risk_manager.calculate_position_value(negative_price)
        assert negative_value == risk_manager.min_position_value

    def test_update_risk_threshold(self, risk_manager):
        new_threshold = 0.5
        risk_manager.update_risk_threshold(new_threshold)
        assert risk_manager.risk_threshold == Decimal(str(new_threshold))
        assert risk_manager.max_position_value == (Decimal(str(new_threshold)) * 2)

    def test_liquidity_ratio_calculation(self, risk_manager, mock_market_data_service):
        orderbook = {'asks': [[100.0, 10.0], [101.0, 20.0]], 'bids': [[99.0, 30.0]]}
        order = {'trading_pair': 'BTC-USD', 'side': 'buy', 'price': Decimal('100.0'), 'size': Decimal('5.0')}

        liquidity_ratio = risk_manager._calculate_liquidity_ratio(order, orderbook)
        assert liquidity_ratio == Decimal('5.0') / Decimal('10.0')

        order = {'trading_pair': 'BTC-USD', 'side': 'sell', 'price': Decimal('100.0'), 'size': Decimal('5.0')}

        liquidity_ratio = risk_manager._calculate_liquidity_ratio(order, orderbook)
        assert liquidity_ratio == Decimal('5.0') / Decimal('30.0')

@pytest.mark.asyncio
class TestRiskManagerAsync:
    async def test_assess_risk_normal_conditions(self, risk_manager, mock_market_data_service):
        """Test risk assessment under normal conditions."""
        risk_manager.market_data_service = mock_market_data_service
        result = await risk_manager.assess_risk(
            Decimal('1000'), 
            "BTC-USD",
            Decimal('0.15')
        )
        assert result is True

    async def test_assess_risk_high_exposure(self, risk_manager, mock_market_data_service):
        risk_manager.market_data_service = mock_market_data_service
        result = await risk_manager.assess_risk(risk_manager.max_position_value + 1, "BTC-USD", Decimal('1.0'))
        assert result is False

    async def test_assess_risk_high_volatility(self, risk_manager, mock_market_data_service):
        """Test risk assessment with high volatility."""
        risk_manager.market_data_service = mock_market_data_service
        result = await risk_manager.assess_risk(
            Decimal('1000'),
            "HIGH_VOLATILITY",
            Decimal('0.15')
        )
        assert result is False

    async def test_validate_order_success(self, risk_manager, mock_market_data_service):
        """Test successful order validation."""
        risk_manager.market_data_service = mock_market_data_service
        order = {
            'trading_pair': 'BTC-USD',
            'side': 'buy',
            'price': Decimal('50000'),
            'size': Decimal('0.1')
        }
        is_valid, msg = await risk_manager.validate_order(order)
        assert is_valid is True
        assert "successful" in msg

    async def test_validate_order_invalid_params(self, risk_manager, mock_market_data_service):
        risk_manager.market_data_service = mock_market_data_service
        order = {'trading_pair': 'BTC-USD', 'side': 'buy', 'price': Decimal('-1.0'), 'size': Decimal('1.0')}
        is_valid, error_msg = await risk_manager.validate_order(order)
        assert "Price and size must be positive" in error_msg

    async def test_validate_order_insufficient_liquidity(self, risk_manager, mock_market_data_service):
        """Test order validation with insufficient liquidity."""
        risk_manager.market_data_service = mock_market_data_service
        order = {
            'trading_pair': 'LOW_LIQUIDITY',
            'side': 'buy',
            'price': Decimal('100'),
            'size': Decimal('1.0')
        }
        is_valid, msg = await risk_manager.validate_order(order)
        assert is_valid is False
        assert "liquidity" in msg.lower()

    async def test_validate_order_below_minimum(self, risk_manager, mock_market_data_service):
        risk_manager.market_data_service = mock_market_data_service
        order = {'trading_pair': 'BTC-USD', 'side': 'buy', 'price': Decimal('0.01'), 'size': Decimal('1.0')}
        is_valid, error_msg = await risk_manager.validate_order(order)
        assert "Order value below minimum position limit" in error_msg

    async def test_validate_order_above_maximum(self, risk_manager, mock_market_data_service):
        risk_manager.market_data_service = mock_market_data_service
        order = {'trading_pair': 'BTC-USD', 'side': 'buy', 'price': risk_manager.max_position_value * Decimal('10.0'), 'size': Decimal('1.0')}
        is_valid, error_msg = await risk_manager.validate_order(order)
        assert "Order value exceeds maximum position limit" in error_msg

    async def test_validate_order_exactly_at_minimum(self, risk_manager, mock_market_data_service):
        """Test order validation with value exactly at minimum."""
        risk_manager.market_data_service = mock_market_data_service
        min_size = Decimal('0.002')  # For $100 min value at $50000 price
        order = {
            'trading_pair': 'BTC-USD',
            'side': 'buy',
            'price': Decimal('50000'),
            'size': min_size
        }
        is_valid, msg = await risk_manager.validate_order(order)
        assert is_valid is True

    async def test_validate_order_exactly_at_maximum(self, risk_manager, mock_market_data_service):
        risk_manager.market_data_service = mock_market_data_service
        order = {'trading_pair': 'BTC-USD', 'side': 'buy', 'price': Decimal('1.0'), 'size': risk_manager.max_position_value}
        is_valid, error_msg = await risk_manager.validate_order(order)
        assert is_valid is True

    async def test_validate_order_exceeds_maximum_by_small_amount(self, risk_manager, mock_market_data_service):
        risk_manager.market_data_service = mock_market_data_service
        order = {'trading_pair': 'BTC-USD', 'side': 'buy', 'price': risk_manager.min_position_value / Decimal('2.0') , 'size': Decimal('1.0')}
        is_valid, error_msg = await risk_manager.validate_order(order)
        assert "Order value below minimum position limit" in error_msg

    async def test_validate_order_below_minimum_by_small_amount(self, risk_manager, mock_market_data_service):
        risk_manager.market_data_service = mock_market_data_service
        order = {'trading_pair': 'BTC-USD', 'side': 'buy', 'price': Decimal('1.0'), 'size': risk_manager.min_position_value}
        is_valid, error_msg = await risk_manager.validate_order(order)
        assert is_valid is True

    async def test_validate_order_zero_liquidity(self, risk_manager, mock_market_data_service):
        risk_manager.market_data_service = mock_market_data_service
        risk_manager.current_daily_loss = 0
        order = {'trading_pair': 'ZERO_LIQUIDITY', 'side': 'buy', 'price': Decimal('1.0'), 'size': risk_manager.min_position_value}
        is_valid, error_msg = await risk_manager.validate_order(order)
        assert "Insufficient liquidity" in error_msg

    async def test_validate_order_within_loss_limit(self, risk_manager, mock_market_data_service):
        """Test order validation within loss limit."""
        risk_manager.market_data_service = mock_market_data_service
        risk_manager.current_daily_loss = risk_manager.max_daily_loss / Decimal('2')
        order = {
            'trading_pair': 'BTC-USD',
            'side': 'buy',
            'price': Decimal('50000'),
            'size': Decimal('0.1')
        }
        is_valid, msg = await risk_manager.validate_order(order)
        assert is_valid is True

    async def test_validate_order_close_to_loss_limit(self, risk_manager, mock_market_data_service):
        risk_manager.market_data_service = mock_market_data_service
        risk_manager.current_daily_loss = risk_manager.max_daily_loss * Decimal('0.9')
        order = {'trading_pair': 'BTC-USD', 'side': 'sell', 'price': Decimal('1.0'), 'size': risk_manager.min_position_value}
        is_valid, error_msg = await risk_manager.validate_order(order)
        assert is_valid is True

    async def test_validate_order_exceeds_loss_limit_by_small_amount(self, risk_manager, mock_market_data_service):
        risk_manager.market_data_service = mock_market_data_service
        risk_manager.current_daily_loss = risk_manager.max_daily_loss * Decimal('0.96')
        order = {'trading_pair': 'BTC-USD', 'side': 'buy', 'price': Decimal('1.0'), 'size': risk_manager.min_position_value}
        is_valid, error_msg = await risk_manager.validate_order(order)
        assert is_valid is True

    async def test_validate_order_position_limit_with_low_liquidity(self, risk_manager, mock_market_data_service):
        risk_manager.market_data_service = mock_market_data_service
        order = {'trading_pair': 'LOW_LIQUIDITY', 'side': 'buy', 'price': Decimal('1.0'), 'size': risk_manager.max_position_value + 1}
        is_valid, error_msg = await risk_manager.validate_order(order)
        assert 'Order value exceeds maximum position limit' in error_msg or 'Insufficient liquidity' in error_msg

        order = {'trading_pair': 'LOW_LIQUIDITY', 'side': 'buy', 'price': Decimal('1.0'), 'size': risk_manager.min_position_value / Decimal('2.0')}
        is_valid, error_msg = await risk_manager.validate_order(order)
        assert 'Order value below minimum position limit' in error_msg or 'Insufficient liquidity' in error_msg

    async def test_validate_order_empty_orderbook(self, risk_manager, mock_market_data_service):
        risk_manager.market_data_service = mock_market_data_service
        order = {'trading_pair': 'EMPTY_ORDERBOOK', 'side': 'buy', 'price': Decimal('1.0'), 'size': Decimal('1.0')}
        is_valid, error_msg = await risk_manager.validate_order(order)
        assert "Insufficient liquidity" in error_msg or not is_valid

    async def test_validate_order_zero_liquidity(self, risk_manager, mock_market_data_service):
        risk_manager.market_data_service = mock_market_data_service
        risk_manager.current_daily_loss = 0
        order = {'trading_pair': 'ZERO_LIQUIDITY', 'side': 'buy', 'price': Decimal('1.0'), 'size': risk_manager.min_position_value}
        is_valid, error_msg = await risk_manager.validate_order(order)
        assert "Insufficient liquidity" in error_msg

    async def test_validate_order_invalid_side(self, risk_manager, mock_market_data_service):
        risk_manager.market_data_service = mock_market_data_service
        order = {'trading_pair': 'BTC-USD', 'side': 'invalid', 'price': Decimal('1.0'), 'size': Decimal('1.0')}
        is_valid, error_msg = await risk_manager.validate_order(order)
        assert "Invalid order side" in error_msg

    async def test_validate_order_missing_fields(self, risk_manager, mock_market_data_service):
        """Test order validation with missing fields."""
        risk_manager.market_data_service = mock_market_data_service
        order = {
            'trading_pair': 'BTC-USD',
            'side': 'buy'
        }
        is_valid, msg = await risk_manager.validate_order(order)
        assert is_valid is False
        assert "Missing required fields" in msg

    async def test_validate_order_exceeds_loss_limit(self, risk_manager, mock_market_data_service):
        """Test order validation exceeding loss limit."""
        risk_manager.market_data_service = mock_market_data_service
        risk_manager.current_daily_loss = risk_manager.max_daily_loss * Decimal('1.1')
        order = {
            'trading_pair': 'BTC-USD',
            'side': 'buy',
            'price': Decimal('50000'),
            'size': Decimal('0.1')
        }
        is_valid, msg = await risk_manager.validate_order(order)
        assert is_valid is False
        assert "loss" in msg.lower()

    async def test_assess_risk_high_price_low_volatility(self, risk_manager, mock_market_data_service):
        risk_manager.market_data_service = mock_market_data_service
        result = await risk_manager.assess_risk(risk_manager.max_position_value * Decimal('0.99'), "LOW_VOLATILITY", Decimal('1.0'))
        assert result is True

    async def test_assess_risk_moderate_volatility(self, risk_manager, mock_market_data_service):
        risk_manager.market_data_service = mock_market_data_service
        result = await risk_manager.assess_risk(Decimal('1.0'), "BTC-USD", Decimal('1.0'))
        assert result is True

    async def test_assess_risk_extreme_volatility(self, risk_manager, mock_market_data_service):
        risk_manager.market_data_service = mock_market_data_service
        result = await risk_manager.assess_risk(Decimal('1.0'), "HIGH_VOLATILITY", Decimal('1.0'))
        assert result is False

    async def test_assess_risk_normal_conditions_with_low_price(self, risk_manager, mock_market_data_service):
        risk_manager.market_data_service = mock_market_data_service
        result = await risk_manager.assess_risk(risk_manager.min_position_value / Decimal('2.0'), "BTC-USD", Decimal('1.0'))
        assert result is True

    async def test_assess_risk_normal_conditions_with_high_price(self, risk_manager, mock_market_data_service):
        risk_manager.market_data_service = mock_market_data_service
        result = await risk_manager.assess_risk(risk_manager.max_position_value, "LOW_VOLATILITY", Decimal('1.0'))
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_order_edge_case_tolerance_minimum(self, risk_manager, mock_market_data_service):
        """
        Test that an order slightly below the minimum position value (but within tolerance) is accepted.
        """
        risk_manager.market_data_service = mock_market_data_service
        # Calculate a size that results in a value ~3% below min_position_value.
        adjusted_size = risk_manager.min_position_value * Decimal('0.97')
        order = {
            'trading_pair': 'BTC-USD',
            'side': 'buy',
            'price': Decimal('1.0'),
            'size': adjusted_size
        }
        is_valid, error_msg = await risk_manager.validate_order(order)
        assert is_valid is True, f"Order should be valid within tolerance but failed: {error_msg}"

    @pytest.mark.asyncio
    async def test_validate_order_edge_case_tolerance_loss_limit(self, risk_manager, mock_market_data_service):
        """
        Test that an order causing total loss slightly over the limit but within loss tolerance passes.
        """
        risk_manager.market_data_service = mock_market_data_service
        # Set current daily loss to 90% of the max loss.
        risk_manager.current_daily_loss = risk_manager.max_daily_loss * Decimal('0.9')
        # Create an order with a potential loss that, when added, is within 10% over the max.
        order = {
            'trading_pair': 'BTC-USD',
            'side': 'buy',
            'price': Decimal('1.0'),
            'size': risk_manager.min_position_value  # Use a small order value.
        }
        is_valid, error_msg = await risk_manager.validate_order(order)
        assert is_valid is True, f"Order should be valid within loss tolerance but failed: {error_msg}"

    def test_calculate_volatility(self, risk_manager):
        """Test volatility calculation."""
        prices = [
            Decimal('100'),
            Decimal('110'),
            Decimal('90'),
            Decimal('105')
        ]
        volatility = risk_manager._calculate_volatility(prices)
        assert volatility > Decimal('0')
        assert isinstance(volatility, Decimal)

    def test_calculate_liquidity_ratio(self, risk_manager):
        """Test liquidity ratio calculation."""
        order = {
            'trading_pair': 'BTC-USD',
            'side': 'buy',
            'price': Decimal('50000'),
            'size': Decimal('1.0')
        }
        orderbook = {
            'asks': [[50000, 2.0], [50100, 3.0]],
            'bids': [[49900, 2.0], [49800, 3.0]]
        }
        ratio = risk_manager._calculate_liquidity_ratio(order, orderbook)
        assert ratio == Decimal('0.2')  # 1.0 / 5.0

    def test_position_value_calculation(self, risk_manager):
        """Test position value calculation."""
        value = risk_manager.calculate_position_value(Decimal('50000'))
        assert value == min(Decimal('50000'), risk_manager.max_position_value)

        # Test with negative price
        value = risk_manager.calculate_position_value(Decimal('-50000'))
        assert value == risk_manager.min_position_value

def test_position_limit_exceeded(trading_bot_risk, event_loop):
    # Exceeding max position size should fail.
    res = event_loop.run_until_complete(
        trading_bot_risk.execute_order('buy', 3.0, 60000.0, 'BTC-USD')
    )
    assert res['status'] == 'error'
    assert 'position size limit exceeded' in res['message']

def test_daily_loss_limit(trading_bot_risk, event_loop):
    # Exceeding daily loss limit should disallow new orders.
    trading_bot_risk.daily_loss = -250.0
    res = event_loop.run_until_complete(
        trading_bot_risk.execute_order('buy', 0.5, 60000.0, 'BTC-USD')
    )
    assert res['status'] == 'error'
    assert 'daily loss limit exceeded' in res['message']

def test_risk_calculation(trading_bot_risk, event_loop):
    # Validate risk calculations (e.g. stop loss) on a buy order.
    event_loop.run_until_complete(
        trading_bot_risk.execute_order('buy', 1.0, 60000.0, 'BTC-USD')
    )
    pos = event_loop.run_until_complete(trading_bot_risk.get_position('BTC-USD'))
    expected_sl = 60000.0 * (1 - 0.05)
    assert pos['stop_loss'] == expected_sl

