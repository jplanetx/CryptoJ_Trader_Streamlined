import pytest
from crypto_j_trader.src.trading.trading_core import TradingBot

@pytest.fixture
def config():
    return {
        'trading_pairs': ['BTC-USD'],
        'risk_management': {
            'stop_loss_pct': 0.05,
            'max_position_size': 20.0,  # Large enough for test orders
            'max_drawdown': 0.2,
            'max_daily_loss': 1000.0  # Large value to prevent daily loss limit during tests
        },
        'paper_trading': True
    }

def test_trading_bot_initialization(config):
    bot = TradingBot(config)
    assert bot.config == config
    assert bot.positions == {}
    assert bot.is_healthy is True

@pytest.mark.asyncio
async def test_execute_order_buy(config):
    bot = TradingBot(config)
    trading_pair = 'BTC-USD'
    result = await bot.execute_order('buy', 10, 100, trading_pair)
    assert result['status'] == 'success'
    assert 'order_id' in result
    
    position = await bot.get_position(trading_pair)
    assert position['size'] == 10
    assert position['entry_price'] == 100
    assert position['stop_loss'] == 95.0

@pytest.mark.asyncio
async def test_execute_order_sell(config):
    bot = TradingBot(config)
    trading_pair = 'BTC-USD'
    result = await bot.execute_order('sell', 5, 200, trading_pair)
    assert result['status'] == 'success'
    assert 'order_id' in result
    
    position = await bot.get_position(trading_pair)
    assert position['size'] == -5
    assert position['entry_price'] == 200
    assert position['stop_loss'] == 210.0

@pytest.mark.asyncio
async def test_get_position_empty(config):
    bot = TradingBot(config)
    trading_pair = 'BTC-USD'
    position = await bot.get_position(trading_pair)
    assert position['size'] == 0.0
    assert position['entry_price'] == 0.0
    assert position['unrealized_pnl'] == 0.0
    assert position['stop_loss'] == 0.0

@pytest.mark.asyncio
async def test_get_position_after_order(config):
    bot = TradingBot(config)
    trading_pair = 'BTC-USD'
    await bot.execute_order('buy', 10, 100, trading_pair)
    position = await bot.get_position(trading_pair)
    assert position['size'] == 10
    assert position['entry_price'] == 100
    assert position['stop_loss'] == 95.0
    assert position['unrealized_pnl'] == 0.0

@pytest.mark.asyncio
async def test_check_health(config):
    bot = TradingBot(config)
    assert await bot.check_health() is True
    assert bot.last_health_check is not None

@pytest.mark.asyncio
async def test_emergency_shutdown(config):
    bot = TradingBot(config)
    await bot.emergency_shutdown()
    assert bot.is_healthy is False
    assert bot.positions == {}
    assert bot.shutdown_requested is True
