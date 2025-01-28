import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from crypto_j_trader.src.trading.trading_core import TradingBot

@pytest.fixture
def config():
    return {
        'trading_pairs': [
            {'pair': 'BTC-USD', 'weight': 0.6, 'precision': 8},
            {'pair': 'ETH-USD', 'weight': 0.4, 'precision': 6}
        ],
        'websocket': {
            'enabled': True,
            'reconnect_max_attempts': 3,
            'reconnect_delay_seconds': 1,
            'heartbeat_interval_seconds': 30
        },
        'emergency_price_change_threshold': 0.1,
        'paper_trading': True,
        'initial_capital': 10000,
        'target_capital': 20000,
        'days_target': 30,
        'execution': {
            'interval_seconds': 60
        }
    }

@pytest.fixture
def mock_websocket():
    return AsyncMock()

@pytest.fixture
async def trading_bot(config):
    with patch('crypto_j_trader.j_trading.TradingBot.load_config', return_value=config):
        with patch('crypto_j_trader.j_trading.TradingBot.setup_api_client'):
            bot = TradingBot()
            yield bot
            # Cleanup
            if bot.websocket_handler:
                await bot.websocket_handler.stop()

@pytest.mark.asyncio
async def test_emergency_shutdown_price_movement(trading_bot):
    """Test emergency shutdown triggers on extreme price movement"""
    
    # Setup mock market data with extreme price change
    trading_bot.market_data = {
        'BTC-USD': Mock(
            empty=False,
            **{
                'price.iloc': [-2, -1],
                'size.iloc': [-1]
            }
        )
    }
    
    # Simulate extreme price movement
    result = trading_bot._check_emergency_conditions('BTC-USD', 60000)  # 100% price increase
    assert result is True
    
@pytest.mark.asyncio
async def test_emergency_shutdown_volume_spike(trading_bot):
    """Test emergency shutdown triggers on unusual volume"""
    
    # Setup mock market data with volume spike
    trading_bot.market_data = {
        'BTC-USD': Mock(
            empty=False,
            **{
                'size.rolling.return_value.mean.iloc': [-1],
                'size.iloc': [-1]
            }
        )
    }
    trading_bot.market_data['BTC-USD'].size.rolling.return_value.mean.iloc[-1] = 1.0
    trading_bot.market_data['BTC-USD'].size.iloc[-1] = 10.0  # 10x average volume
    
    result = trading_bot._check_emergency_conditions('BTC-USD', 50000)
    assert result is True

@pytest.mark.asyncio
async def test_emergency_shutdown_procedure(trading_bot):
    """Test complete emergency shutdown procedure"""
    
    # Setup mock positions
    trading_bot.portfolio.positions = {
        'BTC-USD': {'quantity': 1.0},
        'ETH-USD': {'quantity': 5.0}
    }
    
    # Setup mock market data
    trading_bot.market_data = {
        'BTC-USD': Mock(empty=False, **{'price.iloc': [-1]}),
        'ETH-USD': Mock(empty=False, **{'price.iloc': [-1]})
    }
    trading_bot.market_data['BTC-USD'].price.iloc[-1] = 50000
    trading_bot.market_data['ETH-USD'].price.iloc[-1] = 3000
    
    # Mock execute_trade to track calls
    trading_bot.execute_trade = AsyncMock()
    
    # Trigger emergency shutdown
    await trading_bot._initiate_emergency_shutdown()
    
    # Verify shutdown state
    assert trading_bot.emergency_shutdown is True
    assert trading_bot.shutdown_requested is True
    
    # Verify position closing attempts
    assert trading_bot.execute_trade.call_count == 2  # Should try to close both positions
    
@pytest.mark.asyncio
async def test_websocket_integration_shutdown(trading_bot, mock_websocket):
    """Test WebSocket integration during shutdown"""
    
    # Setup mock WebSocket handler
    trading_bot.websocket_handler.ws = mock_websocket
    
    # Trigger shutdown
    await trading_bot._initiate_emergency_shutdown()
    
    # Verify WebSocket cleanup
    assert mock_websocket.close.called
    
@pytest.mark.asyncio
async def test_trading_loop_emergency_handling(trading_bot):
    """Test trading loop handles emergency conditions"""
    
    # Setup conditions that should trigger emergency shutdown
    async def mock_check_system_health():
        return False
    
    trading_bot._check_system_health = mock_check_system_health
    trading_bot._initiate_emergency_shutdown = AsyncMock()
    
    # Start trading loop in background task
    loop_task = asyncio.create_task(trading_bot.run_trading_loop())
    
    # Wait briefly for loop to process
    await asyncio.sleep(0.1)
    
    # Stop the loop
    trading_bot.shutdown_requested = True
    await loop_task
    
    # Verify emergency shutdown was initiated
    assert trading_bot._initiate_emergency_shutdown.called

@pytest.mark.asyncio
async def test_system_health_monitoring(trading_bot):
    """Test system health monitoring"""
    
    # Test stale WebSocket connection
    trading_bot.websocket_handler.last_message_time = datetime.now()
    assert trading_bot._check_system_health() is True
    
    # Test stale market data
    trading_bot.market_data = {
        'BTC-USD': Mock(
            empty=False,
            **{
                'index': [-1],
                'iloc': lambda x: datetime.now()
            }
        )
    }
    assert trading_bot._check_system_health() is True