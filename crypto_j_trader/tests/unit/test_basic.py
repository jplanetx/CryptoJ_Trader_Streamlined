"""
Basic functionality tests to verify testing infrastructure
"""
import pytest
from unittest.mock import patch
from crypto_j_trader.src.trading.trading_core import TradingBot

def test_trading_bot_init(test_config):
    """Test basic TradingBot initialization."""
    bot = TradingBot(test_config)
    assert bot is not None
    assert bot.config == test_config
    assert bot.is_healthy is True

@pytest.mark.asyncio
async def test_get_empty_position(test_config):
    """Test getting position when none exists."""
    bot = TradingBot(test_config)
    trading_pair = 'BTC-USD'
    position = await bot.get_position(trading_pair)
    assert position['size'] == 0.0
    assert position['entry_price'] == 0.0
    assert position['unrealized_pnl'] == 0.0
    assert position['stop_loss'] == 0.0

@pytest.mark.asyncio
async def test_execute_simple_order(test_config):
    """Test basic order execution."""
    bot = TradingBot(test_config)
    result = await bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
    assert result['status'] == 'success'
    assert 'order_id' in result
    
    # Verify position was updated
    position = await bot.get_position('BTC-USD')
    assert position['size'] == 1.0
    assert position['entry_price'] == 50000.0
    assert position['stop_loss'] == 47500.0  # 5% stop loss

@pytest.mark.asyncio
async def test_health_check(test_config):
    """Test basic health check."""
    bot = TradingBot(test_config)
    health_status = await bot.check_health()
    assert health_status['status'] == 'healthy'
    assert bot.last_health_check is not None
