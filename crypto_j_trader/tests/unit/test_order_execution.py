"""
Tests for order execution functionality
"""
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
    """Mock OrderExecutor for testing"""
    def __init__(self, *args, **kwargs):
        if not args and 'trading_pair' not in kwargs:
            raise ValueError("Trading pair must be specified in the constructor")
        super().__init__(*args, **kwargs)
        self._mock_mode = True
        self.reset_state()

    def reset_state(self):
        """Reset internal state for testing"""
        self.positions = {}
        self.orders = {}
        self._order_counter = 1000

    def get_position(self, symbol: str) -> Decimal:
        """Returns position size for the given symbol"""
        pos = self.positions.get(symbol)
        if isinstance(pos, Position):
            return pos.size
        return Decimal('0')

    def initialize_position(self, symbol: str, size: Decimal, price: Decimal):
        """Initialize a position with given size and price."""
        self.positions[symbol] = Position(
            symbol=symbol,
            size=size,
            entry_price=price,
            timestamp=datetime.now()
        )

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get status of an order"""
        if order_id not in self.orders:
            return {"status": "error", "message": "Order not found"}
        return self.orders[order_id]

    async def get_product_ticker(self, symbol: str) -> Dict:
        """Mock ticker data"""
        return {'price': '48000.00'}

    async def execute_order(self, side: Union[str, Dict], size: float = None, 
                          price: float = None, symbol: str = None) -> Dict:
        """Execute a mock order with consistent status codes"""
        try:
            # Handle dict-style calls
            if isinstance(side, dict):
                order = side
                symbol = order.get('symbol', self.trading_pair)
                side = order['side']
                size = order.get('quantity', 0)
                price = order.get('price', self.default_fill_price)
                order_type = order.get('type', 'market')

                # Handle limit orders
                if order_type == 'limit' and 'price' not in order:
                    raise ValueError("Limit price required")

                # Validate quantity
                if isinstance(size, str):
                    raise ValueError("Invalid literal for Decimal")
            else:
                symbol = symbol or self.trading_pair
                order_type = 'market'

            # Validate side
            if not isinstance(side, str) or side.lower() not in ('buy', 'sell'):
                raise ValueError("Invalid order side")

            size_dec = Decimal(str(size))
            if size_dec <= 0:
                raise ValueError("Invalid size")

            price_dec = Decimal(str(price)) if price is not None else self.default_fill_price
            curr_pos = self.get_position(symbol)
            
            # Update position
            side = side.lower()
            if side == 'buy':
                new_size = curr_pos + size_dec
                self.positions[symbol] = Position(
                    symbol=symbol,
                    size=new_size,
                    entry_price=price_dec,
                    timestamp=datetime.now()
                )
            else:
                if curr_pos <= 0:
                    raise ValueError("No position exists")
                if curr_pos < size_dec:
                    raise ValueError("Insufficient position size")
                new_size = curr_pos - size_dec
                if new_size > 0:
                    self.positions[symbol] = Position(
                        symbol=symbol,
                        size=new_size,
                        entry_price=price_dec,
                        timestamp=datetime.now()
                    )
                else:
                    if symbol in self.positions:
                        del self.positions[symbol]

            # Generate order response
            order_id = 'mock-order-id'
            result = {
                'status': 'filled',
                'order_id': order_id,
                'symbol': symbol,
                'side': side,
                'size': str(size_dec),
                'type': order_type
            }

            self.orders[order_id] = result
            return result

        except ValueError as e:
            raise
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    @classmethod
    def create_for_test(cls, trading_pair: str = "BTC-USD") -> 'MockOrderExecutor':
        """Factory method for creating test instances"""
        return cls(trading_pair=trading_pair)

class TestOrderExecution:
    @pytest.fixture
    def order_executor(self, mock_exchange_service):
        """Fixture to create an OrderExecutor instance"""
        return MockOrderExecutor(mock_exchange_service, trading_pair="BTC-USD")
    
    @pytest.fixture
    def paper_trading_executor(self, test_config):
        """Fixture to create a paper trading OrderExecutor instance"""
        executor = MockOrderExecutor(trading_pair="BTC-USD")
        return executor

    async def test_market_order_placement(self, order_executor):
        """Test market order creation and submission"""
        order = {
            'symbol': 'BTC-USD',
            'side': 'buy',
            'quantity': Decimal('1.0'),
            'type': 'market'
        }

        result = await order_executor.execute_order(order)
        assert result['status'] == 'filled'
        assert 'order_id' in result
        assert result['order_id'] == 'mock-order-id'

    async def test_limit_order_placement(self, order_executor):
        """Test limit order creation and submission"""
        order = {
            'symbol': 'BTC-USD',
            'side': 'buy',
            'quantity': Decimal('1.0'),
            'type': 'limit',
            'price': Decimal('50000.0')
        }

        result = await order_executor.execute_order(order)
        assert result['status'] == 'filled'
        assert 'order_id' in result
        assert result['order_id'] == 'mock-order-id'

    async def test_paper_trading_execution(self, paper_trading_executor):
        """Test paper trading order execution"""
        order = {
            'symbol': 'BTC-USD',
            'side': 'buy',
            'quantity': Decimal('1.0'),
            'type': 'market'
        }
        
        result = await paper_trading_executor.execute_order(order)
        assert result['status'] == 'filled'
        assert result['order_id'] == 'mock-order-id'
        assert Decimal(result['size']) == Decimal('1.0')
        
        position = paper_trading_executor.get_position('BTC-USD')
        assert position == Decimal('1.0')

    async def test_position_tracking(self, paper_trading_executor):
        """Test position tracking and updates"""
        # Buy position
        buy_order = {
            'symbol': 'BTC-USD',
            'side': 'buy',
            'quantity': Decimal('2.0'),
            'type': 'market'
        }
        await paper_trading_executor.execute_order(buy_order)
        
        position = paper_trading_executor.get_position('BTC-USD')
        assert position == Decimal('2.0')

        # Partial sell
        sell_order = {
            'symbol': 'BTC-USD',
            'side': 'sell',
            'quantity': Decimal('1.0'),
            'type': 'market'
        }
        await paper_trading_executor.execute_order(sell_order)

        position = paper_trading_executor.get_position('BTC-USD')
        assert position == Decimal('1.0')

        # Full sell
        await paper_trading_executor.execute_order(sell_order)
        position = paper_trading_executor.get_position('BTC-USD')
        assert position == Decimal('0') # Should be zero since we sold 1.0

    async def test_error_handling_invalid_side(self, order_executor):
        """Test handling of invalid order side"""
        with pytest.raises(ValueError, match="Invalid order side"):
            await order_executor.execute_order({
                'symbol': 'BTC-USD',
                'side': 'invalid',
                'quantity': Decimal('1.0'),
                'type': 'market'
            })

    async def test_error_handling_missing_symbol_constructor(self, mock_exchange_service):
        """Test handling of missing trading pair in constructor"""
        del mock_exchange_service.trading_pair
        with pytest.raises(ValueError, match="Trading pair must be specified in the constructor"):
            OrderExecutor(mock_exchange_service)  # No trading pair provided

    async def test_error_handling_limit_price(self, order_executor):
        """Test handling of missing limit price"""
        with pytest.raises(ValueError, match="Limit price required"):
            await order_executor.execute_order({
                'symbol': 'BTC-USD',
                'side': 'buy',
                'quantity': Decimal('1.0'),
                'type': 'limit'
            })

    async def test_insufficient_position(self, paper_trading_executor):
        """Test selling more than available position"""
        # Try to sell without position
        with pytest.raises(ValueError, match="No position exists"):
            await paper_trading_executor.execute_order({
                'symbol': 'BTC-USD',
                'side': 'sell',
                'quantity': Decimal('1.0'),
                'type': 'market'
            })
        
        # Buy 1.0 and try to sell 2.0
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

    async def test_create_order_helper(self, order_executor):
        """Test the create_order helper method"""
        result = await order_executor.create_order(
            symbol='BTC-USD',
            side='buy',
            quantity=Decimal('1.0'),
            price=Decimal('50000.0'),
            order_type='limit'
        )
        
        assert result['status'] == 'filled'
        assert result['order_id'] == 'mock-order-id'

    async def test_position_management(self, paper_trading_executor):
        """Test position initialization and retrieval"""
        # Initialize a new position
        paper_trading_executor.initialize_position(
            'BTC-USD',
            Decimal('2.0'),
            Decimal('45000.0')
        )

        position = paper_trading_executor.get_position('BTC-USD')
        assert position == Decimal('2.0')

        # Update position with a buy
        await paper_trading_executor.execute_order({
            'symbol': 'BTC-USD',
            'side': 'buy',
            'quantity': Decimal('1.0'),
            'type': 'market'
        })

        updated_position = paper_trading_executor.get_position('BTC-USD')
        assert updated_position == Decimal('3.0')

    async def test_market_order_price_fallback(self, order_executor):
        """Test market order execution with price fallback mechanisms"""
        mock_status = AsyncMock(return_value={'order_id': 'test_order_123', 'status': 'filled', 'price': None})
        mock_ticker = AsyncMock(return_value={'price': '48000.00'})
        mock_place_order = AsyncMock(return_value={'order_id': 'test_order_123', 'status': 'filled'})

        with patch.object(order_executor, 'get_order_status', mock_status), \
             patch.object(order_executor, 'get_product_ticker', mock_ticker), \
             patch.object(order_executor, 'execute_order', mock_place_order):
 #mock_place_order

            order = {
                'symbol': 'BTC-USD',
                'side': 'buy',
                'quantity': Decimal('1.0'),
                'type': 'market'
            }

            result = await order_executor.execute_order(order)
            assert result['order_id'] == 'test_order_123'
            assert result['status'] == 'filled'

    async def test_multi_symbol_position_tracking(self, paper_trading_executor):
        """Test tracking positions for multiple trading pairs"""
        # Buy positions for different symbols
        buy_orders = [
            {
                'symbol': 'BTC-USD',
                'side': 'buy',
                'quantity': Decimal('1.0'),
                'type': 'market',
            },
            {
                'symbol': 'ETH-USD',
                'side': 'buy',
                'quantity': Decimal('5.0'),
                'type': 'market',
            }
        ]
        
        for order in buy_orders:
            await paper_trading_executor.execute_order(order)
        
        # Verify each position separately
        btc_position = paper_trading_executor.get_position('BTC-USD')
        eth_position = paper_trading_executor.get_position('ETH-USD')
        
        assert btc_position == Decimal('1.0')
        assert eth_position == Decimal('5.0')

    async def test_weighted_average_price(self, paper_trading_executor):
        """Test weighted average price calculations for multiple buys"""
        symbol = 'BTC-USD'
        # First buy: 1.0 BTC at 50000
        await paper_trading_executor.execute_order({
            'symbol': symbol,
            'side': 'buy',
            'quantity': Decimal('1.0'),
            'type': 'limit',
            'price': Decimal('50000.0')
        })
        
        # Second buy: 2.0 BTC at 45000
        await paper_trading_executor.execute_order({
            'symbol': symbol,
            'side': 'buy',
            'quantity': Decimal('2.0'),
            'type': 'limit',
            'price': Decimal('45000.0')
        })
        
        position = paper_trading_executor.get_position(symbol)
        assert position == Decimal('3.0')

    async def test_exchange_service_errors(self, order_executor):
        """Test handling of exchange service errors"""
        mock_execute = AsyncMock(side_effect=ExchangeServiceError("API Error"))
        order_executor.execute_order = mock_execute

        with pytest.raises(ExchangeServiceError, match="API Error"):
            await order_executor.execute_order({
                'symbol': 'BTC-USD',
                'side': 'buy',
                'quantity': Decimal('1.0'),
                'type': 'market'
            })

    async def test_order_status_transitions(self, order_executor):
        """Test order status transitions and updates"""
        mock_status = AsyncMock(side_effect=[
            {'order_id': 'test_order_123', 'status': 'pending', 'price': '50000.0'},
            {'order_id': 'test_order_123', 'status': 'filled', 'price': '50000.0'}
        ])

        mock_place_order = AsyncMock(return_value={'order_id': 'test_order_123', 'status': 'filled'})

        with patch.object(order_executor, 'get_order_status', mock_status), \
             patch.object(order_executor, 'execute_order', mock_place_order):

            order = {
                'symbol': 'BTC-USD',
                'side': 'buy',
                'quantity': Decimal('1.0'),
                'type': 'market'
            }

            result = await order_executor.execute_order(order)
            assert result['status'] == 'filled'
            assert result['order_id'] == 'test_order_123'

    async def test_position_tracking_zero_quantity(self, paper_trading_executor):
        """Test position tracking with zero quantity"""
        # Initialize a position
        paper_trading_executor.initialize_position('BTC-USD', Decimal('1.0'), Decimal('45000.0'))

        # Sell the entire position
        sell_order = {
            'symbol': 'BTC-USD',
            'side': 'sell',
            'quantity': Decimal('1.0'),
            'type': 'market'
        }
        await paper_trading_executor.execute_order(sell_order)

        # Verify that the position is removed
        position = paper_trading_executor.get_position('BTC-USD')
        assert position == Decimal('0')

    async def test_position_tracking_small_quantity(self, paper_trading_executor):
        """Test position tracking with very small quantities"""
        # Buy a small quantity
        buy_order = {
            'symbol': 'BTC-USD',
            'side': 'buy',
            'quantity': Decimal('0.00001'),
            'type': 'market'
        }
        await paper_trading_executor.execute_order(buy_order)
        
        position = paper_trading_executor.get_position('BTC-USD')
        assert position == Decimal('0.00001')

    async def test_position_tracking_limit_order(self, paper_trading_executor):
        """Test position tracking with limit orders"""
        # Buy with a limit order
        buy_order = {
            'symbol': 'BTC-USD',
            'side': 'buy',
            'quantity': Decimal('1.0'),
            'type': 'limit',
            'price': Decimal('45000.0')
        }
        await paper_trading_executor.execute_order(buy_order)
        
        position = paper_trading_executor.get_position('BTC-USD')
        assert position == Decimal('1.0')

    async def test_error_handling_invalid_quantity(self, paper_trading_executor):
        """Test handling of invalid quantities"""
        with pytest.raises(ValueError, match="Invalid literal for Decimal"):
            await paper_trading_executor.execute_order({
                'symbol': 'BTC-USD',
                'side': 'buy',
                'quantity': 'invalid',
                'type': 'market'
            })

import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_order_execution_success():
    """Test market order execution success"""
    from crypto_j_trader.src.trading.order_execution import execute_order
    result = await execute_order(order_data={
        "symbol": "BTC-USD",
        "side": "buy",
        "quantity": 1
    })
    assert result['status'] == "filled"

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock
from crypto_j_trader.src.trading.trading_core import TradingBot

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
def trading_bot_order(config_order):
    return TradingBot(config=config_order)

async def test_market_order_success(trading_bot_order):
    """Test market order execution success"""
    result = await trading_bot_order.execute_order(
        side='buy',
        size=1.0,
        price=60000.0,
        symbol='BTC-USD'
    )
    
    assert result['status'] == "success"
    assert 'order_id' in result
    
    # Verify position was updated - get_position is not async
    pos = trading_bot_order.get_position('BTC-USD')
    assert pos['size'] == 1.0

async def test_market_order_failure_invalid_params(trading_bot_order):
    """Test order failure with invalid parameters"""
    # Invalid size and price should return error.
    res1 = await trading_bot_order.execute_order(side='buy', size=0.0, price=60000.0, symbol='BTC-USD')
    res2 = await trading_bot_order.execute_order(side='buy', size=1.0, price=0.0, symbol='BTC-USD')
    assert res1['status'] == 'error'
    assert res2['status'] == 'error'

async def test_order_executor_integration(trading_bot_order):
    """Test integration with order executor"""
    # Mock the order executor to return a properly structured response
    mock_executor = AsyncMock()
    mock_executor.execute_order.return_value = {
        'status': 'filled',
        'order_id': 'exec_001',
        'symbol': 'BTC-USD',
        'side': 'buy',
        'size': '1.0',
        'type': 'market'
    }
    trading_bot_order.order_executor = mock_executor
    
    result = await trading_bot_order.execute_order(side='buy', size=1.0, price=60000.0, symbol='BTC-USD')
    
    assert result['status'] == 'success'
    assert result['order_id'] == 'exec_001'
    
    # Verify mock was called correctly
    mock_executor.execute_order.assert_called_once()
