"""
Tests for order execution functionality
"""
import pytest
from decimal import Decimal
from unittest.mock import patch, AsyncMock

from crypto_j_trader.src.trading.order_execution import OrderExecutor
from crypto_j_trader.src.trading.exchange_service import ExchangeServiceError
from crypto_j_trader.tests.utils.fixtures.config_fixtures import (
    test_config,
    mock_exchange_service
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

class TestOrderExecution:
    @pytest.fixture
    def order_executor(self, mock_exchange_service):
        """Fixture to create an OrderExecutor instance"""
        return OrderExecutor(mock_exchange_service, trading_pair="BTC-USD")
    
    @pytest.fixture
    def paper_trading_executor(self, test_config):
        """Fixture to create a paper trading OrderExecutor instance"""
        return OrderExecutor(None, trading_pair="BTC-USD", paper_trading=True)

    async def test_market_order_placement(self, order_executor):
        """Test market order creation and submission"""
        order = {
            'symbol': 'BTC-USD',
            'side': 'buy',
            'quantity': Decimal('1.0'),
            'type': 'market'
        }
        
        result = await order_executor.execute_order(order)
        assert result['status'] == 'success'
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
        assert result['status'] == 'success'
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
        assert result['order_id'] == 'paper_trade'
        assert Decimal(result['size']) == Decimal('1.0')
        
        position = paper_trading_executor.get_position('BTC-USD')
        assert position is not None
        assert position['quantity'] == Decimal('1.0')

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
        assert position['quantity'] == Decimal('2.0')
        
        # Partial sell
        sell_order = {
            'symbol': 'BTC-USD',
            'side': 'sell',
            'quantity': Decimal('1.0'),
            'type': 'market'
        }
        await paper_trading_executor.execute_order(sell_order)
        
        position = paper_trading_executor.get_position('BTC-USD')
        assert position['quantity'] == Decimal('1.0')
        
        # Full sell
        await paper_trading_executor.execute_order(sell_order)
        position = paper_trading_executor.get_position('BTC-USD')
        assert position is None

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
        
        assert result['status'] == 'success'
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
        assert position is not None
        assert position['quantity'] == Decimal('2.0')
        assert position['entry_price'] == Decimal('45000.0')
        
        # Update position with a buy
        await paper_trading_executor.execute_order({
            'symbol': 'BTC-USD',
            'side': 'buy',
            'quantity': Decimal('1.0'),
            'type': 'market'
        })
        
        updated_position = paper_trading_executor.get_position('BTC-USD')
        assert updated_position['quantity'] == Decimal('3.0')

    async def test_market_order_price_fallback(self, order_executor):
        """Test market order execution with price fallback mechanisms"""
        mock_status = AsyncMock(return_value={'order_id': 'test-order', 'status': 'filled', 'price': None})
        mock_ticker = AsyncMock(return_value={'price': '48000.00'})
        mock_place_order = AsyncMock(return_value={'order_id': 'test-order'})
        
        with patch.object(order_executor.exchange, 'get_order_status', mock_status), \
             patch.object(order_executor.exchange, 'get_product_ticker', mock_ticker), \
             patch.object(order_executor.exchange, 'place_market_order', mock_place_order):
            
            order = {
                'symbol': 'BTC-USD',
                'side': 'buy',
                'quantity': Decimal('1.0'),
                'type': 'market'
            }
            
            result = await order_executor.execute_order(order)
            assert result['order_id'] == 'test-order'
            assert result['status'] == 'filled'

    async def test_multi_symbol_position_tracking(self, paper_trading_executor):
        """Test tracking positions for multiple trading pairs"""
        # Initialize positions for different symbols
        symbols = ['BTC-USD', 'ETH-USD']
        quantities = [Decimal('1.0'), Decimal('5.0')]
        prices = [Decimal('50000.0'), Decimal('3000.0')]
        
        for symbol, qty, price in zip(symbols, quantities, prices):
            await paper_trading_executor.execute_order({
                'symbol': symbol,
                'side': 'buy',
                'quantity': qty,
                'type': 'market',
                'price': price
            })
        
        # Verify positions
        for symbol, qty in zip(symbols, quantities):
            position = paper_trading_executor.get_position(symbol)
            assert position is not None
            assert position['quantity'] == qty

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
        assert position['quantity'] == Decimal('3.0')
        # Weighted average: ((1.0 * 50000) + (2.0 * 45000)) / 3.0 = 46666.67
        expected_price = (Decimal('50000.0') + Decimal('90000.0')) / Decimal('3.0')
        assert position['entry_price'] == expected_price

    async def test_exchange_service_errors(self, order_executor):
        """Test handling of exchange service errors"""
        mock_place_order = AsyncMock(side_effect=ExchangeServiceError("API Error"))
        
        with patch.object(order_executor.exchange, 'place_market_order', mock_place_order):
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
            {'order_id': 'test-order', 'status': 'pending', 'price': '50000.0'},
            {'order_id': 'test-order', 'status': 'filled', 'price': '50000.0'}
        ])
        
        mock_place_order = AsyncMock(return_value={'order_id': 'test-order'})
        
        with patch.object(order_executor.exchange, 'get_order_status', mock_status), \
             patch.object(order_executor.exchange, 'place_market_order', mock_place_order):
            
            order = {
                'symbol': 'BTC-USD',
                'side': 'buy',
                'quantity': Decimal('1.0'),
                'type': 'market'
            }
            
            result = await order_executor.execute_order(order)
            assert result['status'] in ['pending', 'filled']
            assert result['order_id'] == 'test-order'

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
        assert position is None

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
        assert position['quantity'] == Decimal('0.00001')

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
        assert position['quantity'] == Decimal('1.0')

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

def test_market_order_success(trading_bot_order, event_loop):
    # Paper trading: valid order should update position and stats properly.
    result = event_loop.run_until_complete(
        trading_bot_order.execute_order('buy', 1.0, 60000.0, 'BTC-USD')
    )
    assert result['status'] == 'success'
    pos = event_loop.run_until_complete(trading_bot_order.get_position('BTC-USD'))
    assert pos['size'] == 1.0
    # ...existing assertions...

def test_market_order_failure_invalid_params(trading_bot_order, event_loop):
    # Invalid size and price should return error.
    res1 = event_loop.run_until_complete(
        trading_bot_order.execute_order('buy', 0.0, 60000.0, 'BTC-USD')
    )
    res2 = event_loop.run_until_complete(
        trading_bot_order.execute_order('buy', 1.0, 0.0, 'BTC-USD')
    )
    assert res1['status'] == 'error'
    assert res2['status'] == 'error'

def test_order_executor_integration(trading_bot_order, event_loop):
    # When order_executor is provided, result should be taken from it.
    mock_executor = AsyncMock()
    mock_executor.create_order.return_value = {'id': 'exec_001'}
    mock_executor.get_position.return_value = {'quantity': 1, 'entry_price': 60000.0}
    trading_bot_order.order_executor = mock_executor
    result = event_loop.run_until_complete(
        trading_bot_order.execute_order('buy', 1.0, 60000.0, 'BTC-USD')
    )
    assert result['status'] == 'success'
    assert result['order_id'] == 'exec_001'
