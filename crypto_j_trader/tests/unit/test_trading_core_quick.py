"""Quick but comprehensive tests for TradingBot core functionality."""
import pytest
from pytest_asyncio import fixture
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
from crypto_j_trader.src.trading.trading_core import TradingBot

@fixture
def trading_config():
    """Basic trading configuration for testing."""
    return {
        'trading_pairs': ['BTC-USD'],
        'risk_management': {
            'stop_loss_pct': 0.05,
            'max_position_size': 20.0,  # Large enough for test orders
            'max_drawdown': 0.2,
            'max_daily_loss': 1000.0  # Large value to prevent daily loss limit during tests
        },
        'paper_trading': True,
        'api_keys': {
            'key': 'test_key',
            'secret': 'test_secret'
        }
    }

@fixture
def trading_bot(trading_config):
    """Create TradingBot instance with mocked API."""
    bot = TradingBot(trading_config)
    bot.api_client = AsyncMock()
    return bot

class TestOrderExecution:
    @pytest.mark.asyncio
    async def test_market_buy(self, trading_bot):
        """Test market buy order execution."""
        result = await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        assert result['status'] == 'success'
        assert 'order_id' in result
        
        position = await trading_bot.get_position('BTC-USD')
        assert position['size'] == 1.0
        assert position['entry_price'] == 50000.0
        assert position['stop_loss'] == pytest.approx(47500.0)  # 5% stop loss

    @pytest.mark.asyncio
    async def test_position_sizing(self, trading_bot):
        """Test position size limits."""
        # Try to open too large a position
        large_size = trading_bot.config['risk_management']['max_position_size'] * 2
        result = await trading_bot.execute_order('buy', large_size, 50000.0, 'BTC-USD')
        assert result['status'] == 'error'
        assert 'position size limit' in result.get('error', '').lower()

    @pytest.mark.asyncio
    async def test_stop_loss_trigger(self, trading_bot):
        """Test stop loss trigger."""
        # Open position
        await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        
        # Simulate price drop below stop loss
        await trading_bot.update_market_price('BTC-USD', 47000.0)  # Below 5% stop loss
        await trading_bot.check_positions()
        
        position = await trading_bot.get_position('BTC-USD')
        assert position['size'] == 0.0  # Position should be closed

class TestPositionManagement:
    @pytest.mark.asyncio
    async def test_profit_taking(self, trading_bot):
        """Test automated profit taking logic."""
        # Open position
        await trading_bot.execute_order('buy', 2.0, 50000.0, 'BTC-USD')
        
        # Simulate price increase to trigger profit taking
        await trading_bot.update_market_price('BTC-USD', 52500.0)  # 5% profit
        await trading_bot.check_positions()
        
        position = await trading_bot.get_position('BTC-USD')
        # Should have taken 30% of position at 5% profit
        assert position['size'] == pytest.approx(2.0 * 0.7, rel=0.1)

    @pytest.mark.asyncio
    async def test_position_rebalancing(self, trading_bot):
        """Test volatility-based position rebalancing."""
        # Open position
        await trading_bot.execute_order('buy', 2.0, 50000.0, 'BTC-USD')
        
        # Simulate high volatility (price drop to 45000 - 10% change)
        await trading_bot.update_market_price('BTC-USD', 45000.0)
        await trading_bot.check_positions()
        
        position = await trading_bot.get_position('BTC-USD')
        # Should have reduced position by 20%
        assert position['size'] == pytest.approx(2.0 * 0.8, rel=0.1)
    @pytest.mark.asyncio
    async def test_position_tracking(self, trading_bot):
        """Test position tracking through multiple trades."""
        trading_pair = 'BTC-USD'
        # Open initial position
        result = await trading_bot.execute_order('buy', 1.0, 50000.0, trading_pair)
        assert result['status'] == 'success'
        
        position = await trading_bot.get_position(trading_pair)
        assert position['size'] == 1.0
        
        # Add to position
        result = await trading_bot.execute_order('buy', 0.5, 51000.0, trading_pair)
        assert result['status'] == 'success'
        
        position = await trading_bot.get_position(trading_pair)
        assert position['size'] == 1.5
        assert position['entry_price'] == pytest.approx(50333.33, rel=1e-2)  # Weighted average

    @pytest.mark.asyncio
    async def test_pnl_calculation(self, trading_bot):
        """Test P&L calculation."""
        # Open position
        await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        
        # Update market price
        await trading_bot.update_market_price('BTC-USD', 52000.0)
        
        position = await trading_bot.get_position('BTC-USD')
        assert position['unrealized_pnl'] == pytest.approx(2000.0)

class TestRiskManagement:
    @pytest.mark.asyncio
    async def test_daily_loss_limit(self, trading_bot):
        """Test daily loss limit enforcement."""
        trading_pair = 'BTC-USD'
        
        # Open initial position
        result = await trading_bot.execute_order('buy', 1.0, 50000.0, trading_pair)
        assert result['status'] == 'success'
        
        # Simulate massive loss to trigger daily loss limit
        # Note: Having daily_loss_limit high in config allows initial order, then we simulate loss
        trading_bot.daily_loss = -50000.0  # Set a large loss
        
        # Try to open new position
        result = await trading_bot.execute_order('buy', 0.1, 50000.0, trading_pair)
        assert result['status'] == 'error'
        assert 'Daily loss limit reached' in result['error']

    @pytest.mark.asyncio
    async def test_emergency_shutdown(self, trading_bot):
        """Test emergency shutdown procedure."""
        # Open positions
        await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        
        # Trigger emergency shutdown
        await trading_bot.emergency_shutdown()
        
        assert trading_bot.shutdown_requested is True
        assert not trading_bot.is_healthy
        
        # Verify positions are closed
        position = await trading_bot.get_position('BTC-USD')
        assert position['size'] == 0.0

class TestSystemHealth:
    @pytest.mark.asyncio
    async def test_health_monitoring(self, trading_bot):
        """Test comprehensive health monitoring system."""
        # Initial health check
        health = await trading_bot.check_health()
        assert trading_bot.is_healthy is True
        assert health is True  # Basic check mode

        # Test detailed health metrics
        trading_bot.config['detailed_health_check'] = True
        detailed_health = await trading_bot.check_health()
        assert isinstance(detailed_health, dict)
        assert detailed_health['status'] == 'healthy'
        assert detailed_health['api_status'] == 'unknown'  # No API checks yet
        
        # Simulate API connectivity failure
        trading_bot.api_client.get_server_time = AsyncMock(side_effect=Exception("API Error"))
        detailed_health = await trading_bot.check_health()
        assert detailed_health['api_status'] == 'disconnected'
        assert detailed_health['status'] == 'degraded'

        # Test position health warnings
        await trading_bot.execute_order('buy', 5.0, 50000.0, 'BTC-USD')
        await trading_bot.update_market_price('BTC-USD', 45000.0)  # Create large loss
        detailed_health = await trading_bot.check_health()
        assert detailed_health['position_status'] == 'warning'
        assert detailed_health['risk_status'] == 'critical'
        assert detailed_health['status'] == 'unhealthy'

        # Test metrics collection
        metrics = detailed_health['metrics']
        assert metrics['position_count'] == 1
        assert metrics['daily_pnl'] > 0  # Should reflect loss from position
        assert metrics['max_drawdown'] > 0.0
