import pytest
from unittest.mock import MagicMock
from crypto_j_trader.src.trading.trading_core import TradingBot

def test_execute_order_buy():
    config = {'stop_loss_pct': 0.05}
    bot = TradingBot(config)
    result = bot.execute_order('buy', 10, 100)
    assert result['status'] == 'success'
    assert result['order_id'] == 'test_order_id'
    assert bot.positions['size'] == 10
    assert bot.positions['entry_price'] == 100
    assert bot.positions['stop_loss'] == 95.0

def test_execute_order_sell():
    config = {'stop_loss_pct': 0.05}
    bot = TradingBot(config)
    result = bot.execute_order('sell', 5, 200)
    assert result['status'] == 'success'
    assert result['order_id'] == 'test_order_id'
    assert bot.positions['size'] == -5
    assert bot.positions['entry_price'] == 200
    assert bot.positions['stop_loss'] == 210.0

def test_execute_order_exception(monkeypatch):
    config = {'stop_loss_pct': 0.05}
    bot = TradingBot(config)
    monkeypatch.setattr(bot, 'positions', None)
    result = bot.execute_order('buy', 10, 100)
    assert result['status'] == 'error'
    assert 'AttributeError' in result['error']

def test_get_position_empty():
    config = {'stop_loss_pct': 0.05}
    bot = TradingBot(config)
    position = bot.get_position()
    assert position['size'] == 0.0
    assert position['entry_price'] == 0.0
    assert position['unrealized_pnl'] == 0.0
    assert position['stop_loss'] == 0.0

def test_get_position():
    config = {'stop_loss_pct': 0.05}
    bot = TradingBot(config)
    bot.execute_order('buy', 10, 100)
    position = bot.get_position()
    assert position['size'] == 10
    assert position['entry_price'] == 100
    assert position['stop_loss'] == 95.0
    assert position['unrealized_pnl'] == 0.0

def test_check_health():
    config = {'stop_loss_pct': 0.05}
    bot = TradingBot(config)
    assert bot.check_health() == True
    assert bot.last_health_check is not None
