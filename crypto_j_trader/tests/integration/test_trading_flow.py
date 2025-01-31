import pytest
from unittest.mock import patch
from crypto_j_trader.src.trading.trading_core import TradingBot

@pytest.fixture
def trading_bot():
    config = {
        'trading_pairs': ['BTC-USD', 'ETH-USD'],
        'risk_management': {
            'stop_loss_pct': 0.05,
            'max_position_size': 20.0,  # Large enough for test orders
            'max_drawdown': 0.2,
            'max_daily_loss': 1000.0  # Large value to prevent daily loss limit during tests
        },
        'paper_trading': True
    }
    return TradingBot(config)

@patch('crypto_j_trader.src.trading.trading_core.logger')
@pytest.mark.asyncio
async def test_full_trading_cycle(mock_logger, trading_bot):
    trading_pair = 'BTC-USD'
    # Execute buy order
    buy_result = await trading_bot.execute_order('buy', 2.0, 50000.0, trading_pair)
    assert buy_result['status'] == 'success'
    assert 'order_id' in buy_result

    # Verify position
    position = await trading_bot.get_position(trading_pair)
    assert position['size'] == 2.0
    assert position['entry_price'] == 50000.0
    assert position['stop_loss'] == 47500.0

    # Execute sell order
    sell_result = await trading_bot.execute_order('sell', 2.0, 55000.0, trading_pair)
    assert sell_result['status'] == 'success'
    assert 'order_id' in sell_result

    # Verify position after sell
    position = await trading_bot.get_position(trading_pair)
    assert position['size'] == 0.0
    assert position['entry_price'] == 0.0
    assert position['stop_loss'] == 0.0

@patch('crypto_j_trader.src.trading.trading_core.logger')
@pytest.mark.asyncio
async def test_emergency_shutdown_during_trade(mock_logger, trading_bot):
    trading_pair = 'BTC-USD'
    # Execute buy order
    buy_result = await trading_bot.execute_order('buy', 1.0, 50000.0, trading_pair)
    assert buy_result['status'] == 'success'

    # Initiate emergency shutdown
    await trading_bot.emergency_shutdown()

    # Verify bot state after shutdown
    position = await trading_bot.get_position(trading_pair)
    assert position['size'] == 0.0
    assert position['entry_price'] == 0.0
    assert position['stop_loss'] == 0.0
    assert trading_bot.is_healthy is False
    assert trading_bot.shutdown_requested is True

@pytest.mark.asyncio
async def test_trading_flow_without_orders(trading_bot):
    trading_pair = 'BTC-USD'
    # Verify initial state
    position = await trading_bot.get_position(trading_pair)
    assert position['size'] == 0.0
    assert position['entry_price'] == 0.0
    assert position['stop_loss'] == 0.0

@pytest.mark.asyncio
async def test_trading_flow_with_invalid_orders(trading_bot):
    trading_pair = 'BTC-USD'
    # Execute invalid buy order
    buy_result = await trading_bot.execute_order('buy', -1.0, 50000.0, trading_pair)
    assert buy_result['status'] == 'error'
    assert 'Invalid order parameters' in buy_result.get('error', '')

    # Execute invalid sell order
    sell_result = await trading_bot.execute_order('sell', 0.0, 55000.0, trading_pair)
    assert sell_result['status'] == 'error'
    assert 'Invalid order parameters' in sell_result.get('error', '')
