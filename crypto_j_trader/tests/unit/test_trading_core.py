"""
Unit tests for trading core functionality
"""
import pytest
import pytest_asyncio
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from crypto_j_trader.src.trading.trading_core import TradingBot

@pytest.fixture
def mock_config():
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
        assert 'ETH-USD' in trading_bot.trading_pairs

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
        assert position['stop_loss'] == 50000.0 * 1.05  # 5% stop loss for short

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
        eth_position = await trading_bot.get_position('ETH-USD')
        assert btc_position['size'] == 0.0
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