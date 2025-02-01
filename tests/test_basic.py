import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
import sys
import os

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading_bot import TradingBot

@pytest.fixture
def mock_dependencies():
    return {
        'order_executor': AsyncMock(),
        'market_data_handler': AsyncMock(),
        'risk_manager': AsyncMock()
    }

@pytest.fixture
def test_config():
    return {
        'trading': {
            'symbols': ['BTC-USD'],
            'max_position_size': 1000,
            'risk_limit_percent': 2.0
        }
    }

def test_trading_bot_init(test_config, mock_dependencies):
    bot = TradingBot(
        config=test_config,
        order_executor=mock_dependencies['order_executor'],
        market_data_handler=mock_dependencies['market_data_handler'],
        risk_manager=mock_dependencies['risk_manager']
    )
    assert bot.config == test_config
    assert bot.is_healthy == True
    assert isinstance(bot.last_health_check, datetime)
    assert bot.positions == {}

@pytest.mark.asyncio
async def test_get_empty_position(test_config, mock_dependencies):
    bot = TradingBot(
        config=test_config,
        order_executor=mock_dependencies['order_executor'],
        market_data_handler=mock_dependencies['market_data_handler'],
        risk_manager=mock_dependencies['risk_manager']
    )
    position = await bot.get_position('BTC-USD')
    assert position == {'size': 0, 'entry_price': 0}