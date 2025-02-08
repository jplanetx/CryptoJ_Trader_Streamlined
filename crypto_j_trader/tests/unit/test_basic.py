"""
Basic functionality tests to verify testing infrastructure
"""
import pytest
from unittest.mock import patch
from decimal import Decimal
from crypto_j_trader.src.trading.trading_core import TradingBot
from crypto_j_trader.src.trading.market_data_handler import MarketDataHandler
from typing import Optional

class MockMarketDataHandler(MarketDataHandler):
    """Mock MarketDataHandler for testing."""
    async def get_last_price(self, trading_pair: str) -> Optional[float]:
        return 50000.0  # Return a fixed price for testing

    async def start(self) -> None:
        pass  # Do nothing for mock start

    async def stop(self) -> None:
        pass  # Do nothing for mock stop

@pytest.fixture
async def market_data_handler():
    handler = MarketDataHandler(config={"api_key": "dummy", "api_secret": "dummy"})
    if hasattr(handler, "initialize") and callable(handler.initialize):
        await handler.initialize()
    return handler

def test_trading_bot_init(test_config):
    """Test basic TradingBot initialization."""
    with patch('crypto_j_trader.src.trading.trading_core.MarketDataHandler', MockMarketDataHandler):
        bot = TradingBot(test_config)
        assert bot is not None
        assert bot.config == test_config

def test_get_empty_position(test_config):
    """Test getting position when none exists."""
    with patch('crypto_j_trader.src.trading.trading_core.MarketDataHandler', MockMarketDataHandler):
        bot = TradingBot(test_config)
        trading_pair = 'BTC-USD'
        position = bot.get_position(trading_pair)
        assert position['size'] == 0.0
        assert position['entry_price'] == 0.0
        assert position['unrealized_pnl'] == 0.0
        assert position['stop_loss'] == 0.0

@pytest.mark.asyncio
async def test_execute_simple_order(test_config, mock_exchange_service):
    """Test basic order execution."""
    print("\nStarting test_execute_simple_order")
    try:
        with patch('crypto_j_trader.src.trading.trading_core.RiskManager') as mock_risk_manager:

            # Configure risk manager mock
            mock_risk_manager.return_value.validate_order.return_value = True

            print("Creating TradingBot instance")
            bot = TradingBot(test_config, exchange_service=mock_exchange_service)

            print("Executing order")
            result = await bot.execute_order(
                symbol='BTC-USD',
                side='buy',
                quantity=Decimal('1.0'),
                price=Decimal('50000.0')
            )
            print(f"Order result: {result}")

            # Add explicit assertions with messages
            assert result is not None, "Order result should not be None"
            assert result.get('status') == 'success', f"Expected status 'success', got {result.get('status')}"
            assert 'order_id' in result, "Result should contain order_id"

            # Verify position was updated
            position = bot.get_position('BTC-USD')
            print(f"Position after order: {position}")

            assert position['size'] == 1.0, f"Expected position size 1.0, got {position['size']}"
            assert position['entry_price'] == 50000.0, f"Expected entry price 50000.0, got {position['entry_price']}"
            assert position['stop_loss'] == 47500.0, f"Expected stop loss 47500.0, got {position['stop_loss']}"

    except Exception as e:
        print(f"Test failed with exception: {str(e)}")
        raise
        assert result['status'] == 'success'
        assert 'order_id' in result

        # Verify position was updated
        position = bot.get_position('BTC-USD')
        assert position['size'] == 1.0
        assert position['entry_price'] == 50000.0
        assert position['stop_loss'] == 47500.0  # 5% stop loss

@pytest.mark.asyncio
async def test_health_check(test_config):
    """Test basic health check."""
    with patch('crypto_j_trader.src.trading.trading_core.MarketDataHandler', MockMarketDataHandler):
        bot = TradingBot(test_config)
        health_status = await bot.check_health()
        assert health_status['status'] == 'healthy'
        assert bot.last_health_check is not None
