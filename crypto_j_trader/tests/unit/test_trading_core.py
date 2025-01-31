"""
Comprehensive tests for TradingBot functionality
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from crypto_j_trader.src.trading.trading_core import TradingBot

@pytest.fixture
def trading_bot(test_config):
    """Create TradingBot instance with test configuration."""
    return TradingBot(test_config)

class TestInitialization:
    def test_init_basic(self, test_config):
        """Test basic initialization."""
        bot = TradingBot(test_config)
        assert bot.config == test_config
        assert bot.is_healthy is True
        assert not bot.shutdown_requested
        assert isinstance(bot.positions, dict)

    def test_init_missing_config(self):
        """Test initialization with missing config."""
        with pytest.raises(TypeError):
            TradingBot()

class TestOrderExecution:
    @pytest.mark.asyncio
    async def test_buy_order(self, trading_bot):
        """Test buy order execution."""
        result = await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        assert result['status'] == 'success'
        assert 'order_id' in result
        
        position = await trading_bot.get_position('BTC-USD')
        assert position['size'] == 1.0
        assert position['entry_price'] == 50000.0
        assert position['stop_loss'] == 47500.0  # 5% below entry

    @pytest.mark.asyncio
    async def test_sell_order(self, trading_bot):
        """Test sell order execution."""
        result = await trading_bot.execute_order('sell', 0.5, 51000.0, 'BTC-USD')
        assert result['status'] == 'success'
        assert 'order_id' in result
        
        position = await trading_bot.get_position('BTC-USD')
        assert position['size'] == -0.5
        assert position['entry_price'] == 51000.0
        assert position['stop_loss'] == 53550.0  # 5% above entry

    @pytest.mark.asyncio
    async def test_invalid_order(self, trading_bot):
        """Test order with invalid parameters."""
        with pytest.raises(ValueError):
            await trading_bot.execute_order('invalid', 1.0, 50000.0)

class TestPositionManagement:
    @pytest.mark.asyncio
    async def test_multiple_positions(self, trading_bot):
        """Test managing multiple positions."""
        # Open BTC position
        await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        # Open ETH position
        await trading_bot.execute_order('buy', 10.0, 2500.0, 'ETH-USD')
        
        btc_pos = await trading_bot.get_position('BTC-USD')
        eth_pos = await trading_bot.get_position('ETH-USD')
        
        assert btc_pos['size'] == 1.0
        assert eth_pos['size'] == 10.0

    @pytest.mark.asyncio
    async def test_position_modification(self, trading_bot):
        """Test modifying existing position."""
        # Initial position
        await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        # Add to position
        await trading_bot.execute_order('buy', 0.5, 51000.0, 'BTC-USD')
        
        position = await trading_bot.get_position('BTC-USD')
        assert position['size'] == 1.5
        # Average entry price would be updated in real implementation

class TestRiskManagement:
    @pytest.mark.asyncio
    async def test_stop_loss_calculation(self, trading_bot):
        """Test stop loss calculations."""
        await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        position = await trading_bot.get_position('BTC-USD')
        
        # 5% stop loss from config
        expected_stop = 50000.0 * 0.95
        assert position['stop_loss'] == expected_stop

    @pytest.mark.asyncio
    async def test_emergency_shutdown(self, trading_bot):
        """Test emergency shutdown procedure."""
        # Setup positions
        await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        await trading_bot.execute_order('buy', 10.0, 2500.0, 'ETH-USD')
        
        # Trigger shutdown
        await trading_bot.emergency_shutdown()
        
        assert trading_bot.shutdown_requested
        assert not trading_bot.is_healthy
        assert len(trading_bot.positions) == 0

class TestSystemHealth:
    @pytest.mark.asyncio
    async def test_health_check_success(self, trading_bot):
        """Test successful health check."""
        trading_bot.api_client = AsyncMock()
        trading_bot.api_client.get_server_time = AsyncMock(return_value={"serverTime": 1234567890000})
        
        health_status = await trading_bot.check_health()
        assert health_status is True
        assert trading_bot.last_health_check is not None

    @pytest.mark.asyncio
    async def test_health_check_failure(self, trading_bot):
        """Test health check failure."""
        trading_bot.api_client = AsyncMock()
        trading_bot.api_client.get_server_time = AsyncMock(side_effect=Exception("API Error"))
        
        health_status = await trading_bot.check_health()
        assert health_status is False
        assert not trading_bot.is_healthy