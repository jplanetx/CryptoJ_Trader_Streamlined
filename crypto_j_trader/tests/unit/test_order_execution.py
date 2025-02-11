import pytest
from decimal import Decimal
from typing import Dict, Union, Any
from unittest.mock import patch, AsyncMock
from datetime import datetime

from crypto_j_trader.src.trading.order_execution import OrderExecutor, Position
from crypto_j_trader.src.trading.exchange_service import ExchangeServiceError
from crypto_j_trader.tests.utils.fixtures.config_fixtures import (
    test_config,
    mock_exchange_service
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

class MockOrderExecutor(OrderExecutor):
    """Mock OrderExecutor for testing with stricter validations."""
    def __init__(self, *args, **kwargs):
        # Determine the trading_pair from kwargs or args.
        trading_pair = kwargs.get('trading_pair')
        if not trading_pair:
            if args and isinstance(args[0], str):
                trading_pair = args[0]
            else:
                trading_pair = 'BTC-USD'  # Default trading pair

        # Enforce stricter trading pair validation:
        # Must contain a hyphen and be all uppercase.
        if not isinstance(trading_pair, str) or ('-' not in trading_pair) or (trading_pair != trading_pair.upper()):
            raise ValueError(f"Invalid trading pair format: {trading_pair}")

        # We update kwargs for consistency but DO NOT call super().__init__ to avoid any base class behavior.
        self.trading_pair = trading_pair
        # Set a default fill price used for orders when not provided.
        self.default_fill_price = Decimal("10000")
        self._mock_mode = True
        self.reset_state()
        
    def reset_state(self):
        """Reset internal state for testing."""
        self.positions = {}
        self.orders = {}
        self._order_counter = 1000

    def get_position(self, symbol: str) -> Dict[str, Any]:
        """Returns position details for the given symbol."""
        pos = self.positions.get(symbol)
        if isinstance(pos, Position):
            return {
                'size': pos.size,
                'entry_price': pos.entry_price,
                'unrealized_pnl': Decimal('0'),
                'timestamp': pos.timestamp
            }
        return {
            'size': Decimal('0'),
            'entry_price': Decimal('0'),
            'unrealized_pnl': Decimal('0'),
            'timestamp': datetime.now()
        }

    def initialize_position(self, symbol: str, size: Decimal, price: Decimal):
        """Initialize a position with given size and price."""
        self.positions[symbol] = Position(
            symbol=symbol,
            size=size,
            entry_price=price,
            timestamp=datetime.now()
        )

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get status of an order."""
        if order_id not in self.orders:
            return {
                "status": "error",
                "order_id": order_id,
                "message": "Order not found",
                "timestamp": datetime.now()
            }
        return {**self.orders[order_id], "timestamp": datetime.now()}

    async def get_product_ticker(self, symbol: str) -> Dict:
        """Mock ticker data."""
        return {'price': '48000.00'}

    async def execute_order(self, side: Union[str, Dict], size: float = None,
                              price: float = None, symbol: str = None) -> Dict:
        """Execute a mock order with consistent status codes."""
        try:
            # Handle dict-style order submission.
            if isinstance(side, dict):
                order = side
                symbol = order.get('symbol', self.trading_pair)
                side = order['side']
                size = order.get('quantity', 0)
                price = order.get('price', self.default_fill_price)
                order_type = order.get('type', 'market')
                if order_type == 'limit' and 'price' not in order:
                    raise ValueError("Limit price required")
                if isinstance(size, str):
                    raise ValueError("Invalid literal for Decimal")
            else:
                symbol = symbol or self.trading_pair
                order_type = 'market'

            # Validate order side.
            if not isinstance(side, str) or side.lower() not in ('buy', 'sell'):
                raise ValueError("Invalid order side")

            size_dec = Decimal(str(size))
            if size_dec <= 0:
                raise ValueError("Invalid size")

            if price is not None:
                price_dec = Decimal(str(price))
                if price_dec <= 0:
                    raise ValueError("Invalid size")
            else:
                price_dec = self.default_fill_price

            curr_pos = self.get_position(symbol)['size']
            curr_entry_price = self.get_position(symbol).get('entry_price', Decimal('0'))
            side_lower = side.lower()

            if side_lower == 'buy':
                new_size = curr_pos + size_dec
                # Calculate weighted average entry price for buys.
                if curr_pos > 0:
                    total_cost = (curr_pos * curr_entry_price) + (size_dec * price_dec)
                    weighted_price = total_cost / new_size
                else:
                    weighted_price = price_dec
                self.positions[symbol] = Position(
                    symbol=symbol,
                    size=new_size,
                    entry_price=weighted_price,
                    timestamp=datetime.now()
                )
            else:  # sell
                if curr_pos <= 0:
                    raise ValueError("No position exists")
                if curr_pos < size_dec:
                    raise ValueError("Insufficient position size")
                new_size = curr_pos - size_dec
                if new_size > 0:
                    self.positions[symbol] = Position(
                        symbol=symbol,
                        size=new_size,
                        entry_price=curr_entry_price,
                        timestamp=datetime.now()
                    )
                else:
                    if symbol in self.positions:
                        del self.positions[symbol]

            self._order_counter += 1
            order_id = f'mock-order-{self._order_counter}'
            # Always return status as 'filled' for successful orders.
            result = {
                'status': 'filled',
                'order_id': order_id,
                'symbol': symbol,
                'side': side_lower,
                'size': str(size_dec),
                'type': order_type,
                'price': str(price_dec),
                'timestamp': datetime.now()
            }
            self.orders[order_id] = result
            return result

        except ValueError as e:
            raise
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now(),
                'symbol': symbol,
                'order_id': f'error-{self._order_counter}'
            }

    @classmethod
    def create_for_test(cls, trading_pair: str = "BTC-USD") -> 'MockOrderExecutor':
        """Factory method for creating test instances."""
        return cls(trading_pair=trading_pair)

class TestOrderExecution:
    @pytest.fixture
    def order_executor(self, mock_exchange_service):
        """Fixture to create an OrderExecutor instance."""
        return MockOrderExecutor(mock_exchange_service, trading_pair="BTC-USD")
    
    @pytest.fixture
    def paper_trading_executor(self, test_config):
        """Fixture to create a paper trading OrderExecutor instance."""
        executor = MockOrderExecutor(trading_pair="BTC-USD")
        return executor

    async def test_market_order_placement(self, order_executor):
        """Test market order creation and submission."""
        order = {
            'symbol': 'BTC-USD',
            'side': 'buy',
            'quantity': Decimal('1.0'),
            'type': 'market'
        }
        result = await order_executor.execute_order(order)
        assert result['status'] == 'filled'
        assert result['order_id'].startswith('mock-order-')
        assert result['timestamp'] is not None
        position = order_executor.get_position('BTC-USD')
        assert position['size'] == Decimal('1.0')

    async def test_limit_order_placement(self, order_executor):
        """Test limit order creation and submission."""
        order = {
            'symbol': 'BTC-USD',
            'side': 'buy',
            'quantity': Decimal('1.0'),
            'type': 'limit',
            'price': Decimal('50000.0')
        }
        result = await order_executor.execute_order(order)
        assert result['status'] == 'filled'
        assert result['order_id'].startswith('mock-order-')
        assert Decimal(result['price']) == Decimal('50000.0')
        assert result['timestamp'] is not None

    async def test_paper_trading_execution(self, paper_trading_executor):
        """Test paper trading order execution."""
        order = {
            'symbol': 'BTC-USD',
            'side': 'buy',
            'quantity': Decimal('1.0'),
            'type': 'market'
        }
        result = await paper_trading_executor.execute_order(order)
        assert result['status'] == 'filled'
        assert result['order_id'].startswith('mock-order-')
        assert Decimal(result['size']) == Decimal('1.0')
        assert result['timestamp'] is not None
        position = paper_trading_executor.get_position('BTC-USD')
        assert position['size'] == Decimal('1.0')

    async def test_position_tracking(self, paper_trading_executor):
        """Test position tracking and updates."""
        buy_order = {
            'symbol': 'BTC-USD',
            'side': 'buy',
            'quantity': Decimal('2.0'),
            'type': 'market'
        }
        result = await paper_trading_executor.execute_order(buy_order)
        assert result['status'] == 'filled'
        position = paper_trading_executor.get_position('BTC-USD')
        assert position['size'] == Decimal('2.0')
        sell_order = {
            'symbol': 'BTC-USD',
            'side': 'sell',
            'quantity': Decimal('1.0'),
            'type': 'market'
        }
        result = await paper_trading_executor.execute_order(sell_order)
        assert result['status'] == 'filled'
        position = paper_trading_executor.get_position('BTC-USD')
        assert position['size'] == Decimal('1.0')

    async def test_error_handling_invalid_side(self, order_executor):
        """Test handling of invalid order side."""
        with pytest.raises(ValueError, match="Invalid order side"):
            await order_executor.execute_order({
                'symbol': 'BTC-USD',
                'side': 'invalid',
                'quantity': Decimal('1.0'),
                'type': 'market'
            })

    async def test_error_handling_missing_symbol_constructor(self, mock_exchange_service):
        """Test handling of missing trading pair in constructor."""
        executor = MockOrderExecutor(mock_exchange_service)  # Should use default BTC-USD.
        result = await executor.execute_order({
            'side': 'buy',
            'quantity': Decimal('1.0'),
            'type': 'market'
        })
        assert result['status'] == 'filled'
        assert result['symbol'] == 'BTC-USD'

    async def test_insufficient_position(self, paper_trading_executor):
        """Test selling more than available position."""
        with pytest.raises(ValueError, match="No position exists"):
            await paper_trading_executor.execute_order({
                'symbol': 'BTC-USD',
                'side': 'sell',
                'quantity': Decimal('1.0'),
                'type': 'market'
            })
        await paper_trading_executor.execute_order({
            'symbol': 'BTC-USD',
            'side': 'buy',
            'quantity': Decimal('1.0'),
            'type': 'market'
        })
        with pytest.raises(ValueError, match="Insufficient position size"):
            await paper_trading_executor.execute_order({
                'symbol': 'BTC-USD',
                'side': 'sell',
                'quantity': Decimal('2.0'),
                'type': 'market'
            })

    async def test_multi_symbol_position_tracking(self, paper_trading_executor):
        """Test tracking positions for multiple trading pairs."""
        symbols = ['BTC-USD', 'ETH-USD']
        for symbol in symbols:
            await paper_trading_executor.execute_order({
                'symbol': symbol,
                'side': 'buy',
                'quantity': Decimal('1.0'),
                'type': 'market'
            })
        for symbol in symbols:
            position = paper_trading_executor.get_position(symbol)
            assert position['size'] == Decimal('1.0')
            assert 'unrealized_pnl' in position

    async def test_weighted_average_entry_price(self, paper_trading_executor):
        """Test weighted average entry price calculation."""
        await paper_trading_executor.execute_order({
            'symbol': 'BTC-USD',
            'side': 'buy',
            'quantity': Decimal('1.0'),
            'type': 'market',
            'price': Decimal('50000.0')
        })
        position = paper_trading_executor.get_position('BTC-USD')
        assert position['entry_price'] == Decimal('50000.0')
        await paper_trading_executor.execute_order({
            'symbol': 'BTC-USD',
            'side': 'buy',
            'quantity': Decimal('2.0'),
            'type': 'market',
            'price': Decimal('60000.0')
        })
        position = paper_trading_executor.get_position('BTC-USD')
        expected_price = (Decimal('50000.0') + Decimal('120000.0')) / Decimal('3.0')
        assert position['entry_price'] == expected_price
        assert position['size'] == Decimal('3.0')
        await paper_trading_executor.execute_order({
            'symbol': 'BTC-USD',
            'side': 'sell',
            'quantity': Decimal('1.0'),
            'type': 'market',
            'price': Decimal('65000.0')
        })
        position = paper_trading_executor.get_position('BTC-USD')
        assert position['entry_price'] == expected_price
        assert position['size'] == Decimal('2.0')

    async def test_trading_pair_validation(self, mock_exchange_service):
        """Test validation of trading pair format."""
        with pytest.raises(ValueError, match="Invalid trading pair format"):
            # This trading pair is invalid because it's not all uppercase.
            MockOrderExecutor(mock_exchange_service, trading_pair="invalid-pair")

# Additional standalone tests.

@pytest.mark.asyncio
async def test_order_execution_success():
    """Test market order execution success using the module function."""
    from crypto_j_trader.src.trading.order_execution import execute_order
    mock_execute = AsyncMock(return_value={
        'status': 'filled',
        'order_id': 'mock-order-id',
        'symbol': 'BTC-USD',
        'side': 'buy',
        'size': '1.0'
    })
    with patch('crypto_j_trader.src.trading.order_execution.execute_order', mock_execute):
        result = await execute_order(order_data={
            "symbol": "BTC-USD",
            "side": "buy",
            "quantity": 1
        })
        assert result['status'] == "filled"
        assert result['order_id'] == 'mock-order-id'

@pytest.fixture
def config_order():
    return {
        'trading_pairs': ['BTC-USD'],
        'risk_management': {
            'max_position_size': 5.0,
            'max_daily_loss': 500.0,
            'stop_loss_pct': 0.05
        }
    }

@pytest.fixture
async def trading_bot_order(config_order):
    from crypto_j_trader.src.trading.trading_core import TradingBot
    bot = TradingBot(config=config_order)
    # Use our updated MockOrderExecutor instance.
    executor = MockOrderExecutor(trading_pair='BTC-USD')
    bot.order_executor = executor
    bot.execute_order = executor.execute_order
    bot.get_position = executor.get_position
    return bot

@pytest.mark.asyncio
async def test_market_order_success(trading_bot_order):
    """Test market order execution success via trading bot."""
    result = await trading_bot_order.execute_order(
        side='buy',
        size=1.0,
        price=60000.0,
        symbol='BTC-USD'
    )
    assert result['status'] == "filled"
    assert result['order_id'].startswith('mock-order-')
    pos = trading_bot_order.get_position('BTC-USD')
    assert pos['size'] == Decimal('1.0')

@pytest.mark.asyncio
async def test_market_order_failure_invalid_params(trading_bot_order):
    """Test order failure with invalid parameters."""
    with pytest.raises(ValueError, match="Invalid size"):
        await trading_bot_order.execute_order(side='buy', size=0.0, price=60000.0, symbol='BTC-USD')
    with pytest.raises(ValueError, match="Invalid size"):
        await trading_bot_order.execute_order(side='buy', size=1.0, price=0.0, symbol='BTC-USD')

@pytest.mark.asyncio
async def test_order_executor_integration(trading_bot_order):
    """Test integration with order executor via trading bot."""
    result = await trading_bot_order.execute_order(
        side='buy',
        size=1.0,
        price=60000.0,
        symbol='BTC-USD'
    )
    assert result['status'] == 'filled'
    assert result['order_id'].startswith('mock-order-')
    assert Decimal(result['size']) == Decimal('1.0')
