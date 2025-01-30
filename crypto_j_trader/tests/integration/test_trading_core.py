import pytest
from crypto_j_trader.src.trading.trading_core import TradingBot

@pytest.fixture
def config():
    return {
        'stop_loss_pct': 0.05
    }

def test_trading_bot_initialization(config):
    bot = TradingBot(config)
    assert bot.config == config
    assert bot.positions == {}
    assert bot.is_healthy is True

def test_execute_order_buy(config):
    bot = TradingBot(config)
    result = bot.execute_order('buy', 10, 100)
    assert result['status'] == 'success'
    assert result['order_id'] == 'test_order_id'
    assert bot.positions['size'] == 10
    assert bot.positions['entry_price'] == 100
    assert bot.positions['stop_loss'] == 95.0

def test_execute_order_sell(config):
    bot = TradingBot(config)
    result = bot.execute_order('sell', 5, 200)
    assert result['status'] == 'success'
    assert result['order_id'] == 'test_order_id'
    assert bot.positions['size'] == -5
    assert bot.positions['entry_price'] == 200
    assert bot.positions['stop_loss'] == 210.0

def test_get_position_empty(config):
    bot = TradingBot(config)
    position = bot.get_position()
    assert position['size'] == 0.0
    assert position['entry_price'] == 0.0
    assert position['unrealized_pnl'] == 0.0
    assert position['stop_loss'] == 0.0

def test_get_position_after_order(config):
    bot = TradingBot(config)
    bot.execute_order('buy', 10, 100)
    position = bot.get_position()
    assert position['size'] == 10
    assert position['entry_price'] == 100
    assert position['stop_loss'] == 95.0
    assert position['unrealized_pnl'] == 0.0

def test_check_health(config):
    bot = TradingBot(config)
    assert bot.check_health() is True
    assert bot.last_health_check is not None

def test_emergency_shutdown(config, monkeypatch):
    bot = TradingBot(config)
    monkeypatch.setattr(bot, '_emergency_shutdown', bot._emergency_shutdown)
    bot._emergency_shutdown()
    assert bot.is_healthy is False
    assert bot.positions == {}