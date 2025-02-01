import pytest
from unittest.mock import AsyncMock, MagicMock
import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from crypto_j_trader.src.trading.trading_core import TradingBot

@pytest.fixture
def mock_config():
    return {
        'trading_pairs': ['BTC-USD', 'ETH-USD'],
        'risk_management': {
            'max_position_size': 10.0,
            'max_daily_loss': 100.0
        }
    }

@pytest.fixture
def mock_order_executor():
    mock = AsyncMock()
    mock.create_order.return_value = {'id': 'test_order_id'}
    return mock

@pytest.fixture
def mock_market_data_handler():
    mock = MagicMock()
    mock.is_data_fresh.return_value = True
    mock._ws_handler = MagicMock()
    mock._ws_handler.is_connected = True
    return mock


@pytest.fixture
def trading_bot(mock_config, mock_order_executor, mock_market_data_handler):
    return TradingBot(
        config=mock_config,
        order_executor=mock_order_executor,
        market_data_handler = mock_market_data_handler
    )


@pytest.mark.asyncio
async def test_execute_buy_order(trading_bot, mock_order_executor):
    """Test executing a buy order"""
    result = await trading_bot.execute_order("buy", 0.1, 50000.0, "BTC-USD")
    assert result['status'] == 'success'
    assert "order_id" in result
    mock_order_executor.create_order.assert_called_with("BTC-USD", "buy", Decimal("0.1"), Decimal("50000.0"))
    position = await trading_bot.get_position("BTC-USD")
    assert isinstance(position['size'], float)
    assert position['size'] == 0.1
    assert position['entry_price'] == 50000.0

@pytest.mark.asyncio
async def test_execute_sell_order(trading_bot, mock_order_executor):
    """Test executing a sell order"""
    # First create a buy order to get a position
    await trading_bot.execute_order("buy", 0.2, 50000.0, "BTC-USD")

    result = await trading_bot.execute_order("sell", 0.1, 51000.0, "BTC-USD")
    assert result['status'] == 'success'
    assert "order_id" in result
    mock_order_executor.create_order.assert_called_with("BTC-USD", "sell", Decimal("0.1"), Decimal("51000.0"))
    
    position = await trading_bot.get_position("BTC-USD")
    assert isinstance(position['size'], float)
    assert position['size'] == 0.1
    assert position['entry_price'] == 50000.0

@pytest.mark.asyncio
async def test_execute_order_invalid_parameters(trading_bot):
    """Test order execution with invalid parameters"""
    result = await trading_bot.execute_order("invalid", 0.1, 50000.0, "BTC-USD")
    assert result['status'] == 'error'
    assert "Invalid side" in result['message']
    
    result = await trading_bot.execute_order("buy", 0, 50000.0, "BTC-USD")
    assert result['status'] == 'error'
    assert "Invalid size" in result['message']

    result = await trading_bot.execute_order("buy", 0.1, -50000.0, "BTC-USD")
    assert result['status'] == 'error'
    assert "Invalid price" in result['message']

    result = await trading_bot.execute_order("buy", 0.1, 50000.0, "INVALID-USD")
    assert result['status'] == 'error'
    assert "Invalid symbol" in result['message']

@pytest.mark.asyncio
async def test_execute_order_position_limit(trading_bot):
    """Test order execution exceeding position limit"""
    result = await trading_bot.execute_order("buy", 11.0, 50000.0, "BTC-USD")
    assert result['status'] == 'error'
    assert "Position size limit exceeded" in result['message']


@pytest.mark.asyncio
async def test_check_health(trading_bot, mock_market_data_handler):
    """Test system health check"""
    assert (await trading_bot.check_health())['status'] == 'healthy'

    mock_market_data_handler.is_data_fresh.return_value = False
    assert (await trading_bot.check_health())['status'] == 'unhealthy'

    mock_market_data_handler._ws_handler.is_connected = False
    assert (await trading_bot.check_health())['status'] == 'unhealthy'

    trading_bot.positions = None
    assert (await trading_bot.check_health())['status'] == 'unhealthy'

    trading_bot.daily_stats = None
    assert (await trading_bot.check_health())['status'] == 'unhealthy'

    trading_bot.config = None
    assert (await trading_bot.check_health())['status'] == 'unhealthy'

@pytest.mark.asyncio
async def test_emergency_shutdown(trading_bot):
    """Test emergency shutdown"""
    result = await trading_bot.emergency_shutdown()
    assert result['status'] == 'success'
    assert trading_bot.shutdown_requested == True

@pytest.mark.asyncio
async def test_reset_daily_stats(trading_bot):
    """Test resetting daily statistics"""
    trading_bot.daily_loss = 100.0
    trading_bot.daily_trades_count = 10
    trading_bot.daily_volume = 5000.0
    trading_bot.daily_stats['peak_pnl'] = 50.0
    trading_bot.daily_stats['lowest_pnl'] = -10.0
    trading_bot.daily_stats['total_fees'] = 1.0
    trading_bot.daily_stats['win_count'] = 5
    trading_bot.daily_stats['loss_count'] = 5
    await trading_bot.reset_daily_stats()
    assert trading_bot.daily_loss == 0.0
    assert trading_bot.daily_trades_count == 0
    assert trading_bot.daily_volume == 0.0
    assert trading_bot.daily_stats['peak_pnl'] == 0.0
    assert trading_bot.daily_stats['lowest_pnl'] == 0.0
    assert trading_bot.daily_stats['total_fees'] == 0.0
    assert trading_bot.daily_stats['win_count'] == 0
    assert trading_bot.daily_stats['loss_count'] == 0

@pytest.mark.asyncio
async def test_get_daily_stats(trading_bot):
    """Test getting daily statistics"""
    trading_bot.daily_loss = 50.0
    trading_bot.daily_trades_count = 10
    trading_bot.daily_stats['win_count'] = 6
    stats = await trading_bot.get_daily_stats()
    assert stats['pnl']['current'] == -50.0
    assert stats['trades']['count'] == 10
    assert stats['trades']['win_rate'] == 60.0
    assert stats['fees'] == 0.0 # default value

@pytest.mark.asyncio
async def test_get_system_status(trading_bot, mock_market_data_handler):
    """Test getting system status"""
    status = await trading_bot.get_system_status()
    assert status['trading']['active'] == True
    assert status['trading']['health'] == {'status': 'healthy'}
    assert status['positions']['count'] == 0

    mock_market_data_handler.is_data_fresh.return_value = False
    status = await trading_bot.get_system_status()
    assert status['trading']['health'] == {'status': 'unhealthy'}

@pytest.mark.asyncio
async def test_reset_system(trading_bot):
    """Test resetting the system"""
    trading_bot.positions = {"BTC-USD": {"size": 0.1, "entry_price": 50000.0}}
    trading_bot.market_prices = {"BTC-USD": 51000.0}
    result = await trading_bot.reset_system()
    assert result['status'] == 'success'
    assert trading_bot.shutdown_requested == False
    assert len(trading_bot.positions) == 0
    assert len(trading_bot.market_prices) == 0