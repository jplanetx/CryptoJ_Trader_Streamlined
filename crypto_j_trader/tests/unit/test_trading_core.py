"""
Unit tests for trading core functionality
"""
import asyncio
import pytest
import pytest_asyncio
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from crypto_j_trader.src.trading.trading_core import TradingBot

@patch("crypto_j_trader.src.trading.market_data.MarketDataHandler")
@pytest.fixture
def mock_config(mock_market_data_handler):
    """Test configuration"""
    return {
        'trading_pairs': ['BTC-USD'],
        'trading': {
            'symbols': ['ETH-USD']
        },
        'risk_management': {
            'max_position_size': 10.0,
            'max_daily_loss': 1000.0,
            'stop_loss_pct': 0.05
        }
    }

@pytest.fixture
def trading_bot(mock_config):
    """Create a trading bot instance with mock config"""
    return TradingBot(config=mock_config)

class TestTradingBot:
    @pytest.mark.asyncio
    async def test_init_from_config(self, trading_bot):
        """Test initialization from config"""
        assert 'BTC-USD' in trading_bot.trading_pairs

    @pytest.mark.asyncio
    async def test_get_position_new_symbol(self, trading_bot):
        """Test getting position for new symbol"""
        position = await trading_bot.get_position('BTC-USD')
        assert position['size'] == 0.0
        assert position['entry_price'] == 0.0
        assert position['unrealized_pnl'] == 0.0
        assert position['stop_loss'] == 0.0

    @pytest.mark.asyncio
    async def test_execute_order_invalid_params(self, trading_bot):
        """Test order execution with invalid parameters"""
        # Test invalid size
        result = await trading_bot.execute_order('buy', -1.0, 50000.0, 'BTC-USD')
        assert result['status'] == 'error'
        assert result['message'] == 'Invalid size'

        # Test invalid price
        result = await trading_bot.execute_order('buy', 1.0, -50000.0, 'BTC-USD')
        assert result['status'] == 'error'
        assert result['message'] == 'Invalid price'

    @pytest.mark.asyncio
    async def test_execute_order_position_limit(self, trading_bot):
        """Test order execution with position limit"""
        # Try to exceed max position size
        result = await trading_bot.execute_order('buy', 11.0, 50000.0, 'BTC-USD')
        assert result['status'] == 'error'
        assert result['message'] == 'position size limit exceeded'

    @pytest.mark.asyncio
    async def test_execute_order_daily_loss_limit(self, trading_bot):
        """Test order execution with daily loss limit"""
        trading_bot.daily_loss = -2000.0  # Exceed max daily loss
        result = await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        assert result['status'] == 'error'
        assert result['message'] == 'daily loss limit exceeded'

    @pytest.mark.asyncio
    async def test_paper_trading_buy_order(self, trading_bot):
        """Test paper trading buy order execution"""
        result = await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        assert result['status'] == 'success'
        assert 'order_id' in result
        
        position = await trading_bot.get_position('BTC-USD')
        assert position['size'] == 1.0
        assert position['entry_price'] == 50000.0
        assert position['stop_loss'] == 50000.0 * 0.95  # 5% stop loss

    @pytest.mark.asyncio
    async def test_paper_trading_sell_order(self, trading_bot):
        """Test paper trading sell order execution"""
        # First buy position
        await trading_bot.execute_order('buy', 2.0, 50000.0, 'BTC-USD')
        
        # Then sell partial position
        result = await trading_bot.execute_order('sell', 1.0, 51000.0, 'BTC-USD')
        assert result['status'] == 'success'
        
        position = await trading_bot.get_position('BTC-USD')
        assert position['size'] == 1.0

    @pytest.mark.asyncio
    async def test_insufficient_position_size(self, trading_bot):
        """Test selling more than available position"""
        await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        result = await trading_bot.execute_order('sell', 2.0, 51000.0, 'BTC-USD')
        assert result['status'] == 'error'
        assert result['message'] == 'Insufficient position size'

    @pytest.mark.asyncio
    async def test_short_selling(self, trading_bot):
        """Test short selling execution"""
        result = await trading_bot.execute_order('sell', 1.0, 50000.0, 'BTC-USD')
        assert result['status'] == 'success'
        
        position = await trading_bot.get_position('BTC-USD')
        assert position['size'] == -1.0
        assert position['stop_loss'] == 0.0  # No stop loss until position is closed

    @pytest.mark.asyncio
    async def test_update_market_price(self, trading_bot):
        """Test market price updates and PnL calculation"""
        # Create long position
        await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        
        # Update market price
        await trading_bot.update_market_price('BTC-USD', 51000.0)
        
        position = await trading_bot.get_position('BTC-USD')
        assert position['unrealized_pnl'] == 1000.0  # (51000 - 50000) * 1.0

    @pytest.mark.asyncio
    async def test_check_positions_stop_loss(self, trading_bot):
        """Test stop loss trigger"""
        # Create long position
        await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        
        # Update price below stop loss
        await trading_bot.update_market_price('BTC-USD', 47000.0)  # Below 5% stop loss
        
        # Position should be closed
        position = await trading_bot.get_position('BTC-USD')
        assert position['size'] == 0.0

    @pytest.mark.asyncio
    async def test_emergency_shutdown(self, trading_bot):
        """Test emergency shutdown procedure"""
        # Create positions
        await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        await trading_bot.execute_order('sell', 0.5, 49000.0, 'ETH-USD')

        # Execute shutdown
        result = await trading_bot.emergency_shutdown()
        assert result['status'] == 'success'
        assert trading_bot.shutdown_requested
        assert not trading_bot.is_healthy

        # Check positions closed
        btc_position = await trading_bot.get_position('BTC-USD')
        assert btc_position['size'] == 0.0
        eth_position = await trading_bot.get_position('ETH-USD')
        assert eth_position['size'] == 0.0

    @pytest.mark.asyncio
    async def test_daily_stats(self, trading_bot):
        """Test daily statistics tracking"""
        # Execute some trades
        await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        await trading_bot.execute_order('sell', 0.5, 51000.0, 'BTC-USD')
        
        stats = trading_bot.get_daily_stats()
        assert stats['trades'] == 2
        assert stats['volume'] == 75500.0  # 50000 + 25500
        
        # Test reset
        await trading_bot.reset_daily_stats()
        stats = trading_bot.get_daily_stats()
        assert stats['trades'] == 0
        assert stats['volume'] == 0.0
        assert stats['pnl'] == 0.0
        assert trading_bot.daily_loss == 0.0

    @pytest.mark.asyncio
    async def test_buy_and_sell_different_amounts(self, trading_bot):
        """Test buying and selling different amounts of the same symbol"""
        # Buy 1.0 BTC-USD
        await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        
        # Sell 0.5 BTC-USD
        await trading_bot.execute_order('sell', 0.5, 51000.0, 'BTC-USD')
        
        position = await trading_bot.get_position('BTC-USD')
        assert position['size'] == 0.5

    @pytest.mark.asyncio
    async def test_buy_and_sell_different_symbols(self, trading_bot):
        """Test buying and selling the same amount of different symbols"""
        # Buy 1.0 BTC-USD
        await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        
        # Sell 1.0 ETH-USD
        await trading_bot.execute_order('sell', 1.0, 3000.0, 'ETH-USD')
        
        btc_position = await trading_bot.get_position('BTC-USD')
        assert btc_position['size'] == 1.0
        
        eth_position = await trading_bot.get_position('ETH-USD')
        assert eth_position['size'] == -1.0

    @pytest.mark.asyncio
    async def test_execute_order_validation(self, trading_bot):
        """Test order validation logic"""
        # Test invalid size (zero)
        result = await trading_bot.execute_order('buy', 0.0, 50000.0, 'BTC-USD')
        assert result['status'] == 'error'
        assert result['message'] == 'Invalid size'
        
        # Test invalid price (zero)
        result = await trading_bot.execute_order('buy', 1.0, 0.0, 'BTC-USD')
        assert result['status'] == 'error'
        assert result['message'] == 'Invalid price'

    @pytest.mark.asyncio
    async def test_system_status(self, trading_bot):
        """Test system status reporting"""
        status = trading_bot.get_system_status()
        assert 'health' in status
        assert 'last_check' in status
        assert 'positions' in status
        assert 'daily_stats' in status
        assert 'shutdown_requested' in status

    @pytest.mark.asyncio
    async def test_reset_system(self, trading_bot):
        """Test complete system reset"""
        # Create some state
        await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        trading_bot.market_prices['BTC-USD'] = 51000.0
        
        # Reset system
        await trading_bot.reset_system()
        
        # Verify clean state
        assert not trading_bot.positions
        assert not trading_bot.market_prices
        assert trading_bot.is_healthy
        assert not trading_bot.shutdown_requested
        
        stats = trading_bot.get_daily_stats()
        assert stats['trades'] == 0
        assert stats['volume'] == 0.0
        assert stats['pnl'] == 0.0

    @pytest.mark.asyncio
    async def test_market_data_integration(self, trading_bot):
        """Test market data integration and PnL calculation"""
        # Mock market data handler
        mock_market_data_handler = AsyncMock()
        trading_bot.market_data_handler = mock_market_data_handler
        
        # Create long position
        await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        
        # Update market price
        await trading_bot.update_market_price('BTC-USD', 51000.0)
        
        # Verify that market data handler was called
        mock_market_data_handler.update_price.assert_called_once_with('BTC-USD')
        
        position = await trading_bot.get_position('BTC-USD')
        assert position['unrealized_pnl'] == 1000.0  # (51000 - 50000) * 1.0

    @pytest.mark.asyncio
    async def test_error_handling(self, trading_bot):
        """Test error handling mechanisms"""
        # Mock order executor to raise an exception
        mock_order_executor = AsyncMock()
        mock_order_executor.create_order.side_effect = Exception("Order failed")
        trading_bot.order_executor = mock_order_executor
        
        # Execute order and verify error status
        result = await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        assert result['status'] == 'error'
        assert result['message'] == "Order failed"

    @pytest.mark.asyncio
    async def test_concurrency(self, trading_bot):
        """Test concurrent execution of multiple orders and market data updates"""
        # Create multiple tasks
        tasks = [
            trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD'),
            trading_bot.update_market_price('BTC-USD', 51000.0),
            trading_bot.execute_order('sell', 0.5, 51000.0, 'BTC-USD')
        ]
        
        # Execute tasks concurrently
        await asyncio.gather(*tasks)
        
        # Verify that all tasks completed successfully (no exceptions raised)
        # Add more specific assertions as needed

    @pytest.mark.asyncio
    async def test_get_position_existing_symbol(self, trading_bot):
        """Test getting position for an existing symbol"""
        await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        position = await trading_bot.get_position('BTC-USD')
        assert position['size'] == 1.0
        assert position['entry_price'] == 50000.0

    @pytest.mark.asyncio
    async def test_update_market_price_no_position(self, trading_bot):
        """Test updating market price with no existing position"""
        await trading_bot.update_market_price('BTC-USD', 51000.0)
        position = await trading_bot.get_position('BTC-USD')
        assert position['unrealized_pnl'] == 0.0

    @pytest.mark.asyncio
    async def test_check_positions_no_stop_loss(self, trading_bot):
        """Test checking positions with no stop loss set"""
        await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        await trading_bot.update_market_price('BTC-USD', 51000.0)
        await trading_bot.check_positions()
        position = await trading_bot.get_position('BTC-USD')
        assert position['size'] == 1.0

    @pytest.mark.asyncio
    async def test_check_positions_with_stop_loss(self, trading_bot):
        """Test checking positions with stop loss triggered"""
        await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        await trading_bot.update_market_price('BTC-USD', 47000.0)
        await trading_bot.check_positions()
        position = await trading_bot.get_position('BTC-USD')
        assert position['size'] == 0.0

    @pytest.mark.asyncio
    async def test_reset_system_with_positions(self, trading_bot):
        """Test resetting system with existing positions"""
        await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        await trading_bot.reset_system()
        position = await trading_bot.get_position('BTC-USD')
        assert position['size'] == 0.0
        assert not trading_bot.positions
        assert not trading_bot.market_prices
        assert trading_bot.is_healthy
        assert not trading_bot.shutdown_requested

    @pytest.mark.asyncio
    async def test_market_data_handler_integration(self, trading_bot):
        """Test integration with market data handler"""
        mock_market_data_handler = AsyncMock()
        trading_bot.market_data_handler = mock_market_data_handler
        await trading_bot.update_market_price('BTC-USD', 51000.0)
        mock_market_data_handler.update_price.assert_called_once_with('BTC-USD')

    @pytest.mark.asyncio
    async def test_order_executor_integration(self, trading_bot):
        """Test integration with order executor"""
        mock_order_executor = AsyncMock()
        trading_bot.order_executor = mock_order_executor
        mock_order_executor.create_order.return_value = {'id': 'order123'}
        result = await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        assert result['status'] == 'success'
        assert result['order_id'] == 'order123'
        mock_order_executor.create_order.assert_called_once_with('BTC-USD', 'buy', Decimal('1.0'), Decimal('50000.0'))

    @pytest.mark.asyncio
    async def test_check_health(self, trading_bot):
        """Test system health check"""
        health_status = await trading_bot.check_health()
        assert health_status['status'] == 'healthy'
        assert 'last_check' in health_status
        assert 'api_status' in health_status
        assert 'metrics' in health_status

    @pytest.mark.asyncio
    async def test_emergency_shutdown_no_positions(self, trading_bot):
        """Test emergency shutdown with no positions"""
        result = await trading_bot.emergency_shutdown()
        assert result['status'] == 'success'
        assert trading_bot.shutdown_requested
        assert not trading_bot.is_healthy

    @pytest.mark.asyncio
    async def test_reset_daily_stats(self, trading_bot):
        """Test resetting daily statistics"""
        await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        await trading_bot.reset_daily_stats()
        stats = trading_bot.get_daily_stats()
        assert stats['trades'] == 0
        assert stats['volume'] == 0.0
        assert stats['pnl'] == 0.0
        assert trading_bot.daily_loss == 0.0