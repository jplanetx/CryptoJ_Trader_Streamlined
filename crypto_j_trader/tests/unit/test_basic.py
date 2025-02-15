"""Basic unit tests for core functionality"""
import pytest
from unittest.mock import patch, AsyncMock
from decimal import Decimal, InvalidOperation
from typing import Optional
from crypto_j_trader.src.trading.trading_core import TradingBot
from crypto_j_trader.src.trading.market_data_handler import MarketDataHandler

class MockMarketDataHandler(MarketDataHandler):
    """Mock MarketDataHandler for testing."""
    
    async def get_last_price(self, trading_pair: str) -> Optional[float]:
        return 50000.0  # Return a fixed price for testing
    
    async def start(self) -> None:
        pass
    
    async def stop(self) -> None:
        pass

@pytest.fixture
async def market_data_handler():
    handler = MarketDataHandler(config={"api_key": "dummy", "api_secret": "dummy"})
    return handler

@pytest.fixture
def test_config():
    return {
        'trading_pairs': ['BTC-USD'],
        'risk_management': {
            'max_position_size': 5.0,
            'max_daily_loss': 500.0,
            'stop_loss_pct': 0.05
        },
        'paper_trading': True
    }

def test_trading_bot_init(test_config):
    """Test basic TradingBot initialization."""
    with patch('crypto_j_trader.src.trading.trading_core.MarketDataHandler', MockMarketDataHandler):
        bot = TradingBot(test_config)
        assert bot is not None
        assert bot.config == test_config
        assert isinstance(bot.positions, dict)

@pytest.mark.asyncio
async def test_get_empty_position(test_config):
    """Test getting position when none exists."""
    with patch('crypto_j_trader.src.trading.trading_core.MarketDataHandler', MockMarketDataHandler):
        bot = TradingBot(test_config)
        position = await bot.get_position('BTC-USD')
        assert isinstance(position, dict)
        assert position['size'] == Decimal('0')
        assert position['entry_price'] == Decimal('0')

@pytest.mark.asyncio
async def test_execute_simple_order(test_config):
    """Test basic order execution."""
    print("\nStarting test_execute_simple_order")
    with patch('crypto_j_trader.src.trading.trading_core.MarketDataHandler', MockMarketDataHandler):
        bot = TradingBot(test_config)
        result = await bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
        
        assert result['status'] == 'filled'
        assert 'order_id' in result
        
        position = await bot.get_position('BTC-USD')
        assert position['size'] == Decimal('1.0')
        assert position['entry_price'] == Decimal('50000.0')
        assert position['stop_loss'] == Decimal('47500.0')  # 5% stop loss

@pytest.mark.asyncio
async def test_health_check(test_config):
    """Test basic health check."""
    with patch('crypto_j_trader.src.trading.trading_core.MarketDataHandler', MockMarketDataHandler):
        bot = TradingBot(test_config)
        health_status = await bot.check_health()
        assert health_status is True  # Basic health check returns boolean
        
        # Test detailed health check
        bot.config['detailed_health_check'] = True
        detailed_status = await bot.check_health()
        assert isinstance(detailed_status, dict)
        assert detailed_status['status'] == 'healthy'
