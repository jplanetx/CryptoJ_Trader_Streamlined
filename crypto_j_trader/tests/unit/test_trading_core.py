"""
Unit tests for trading core functionality
"""
import pytest
import pytest_asyncio
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from crypto_j_trader.src.trading.trading_core import TradingBot
from crypto_j_trader.src.trading.market_data_handler import MarketDataHandler
from crypto_j_trader.src.trading.exchange_service import ExchangeService, MarketOrder, LimitOrder

class MockCoinbaseClient:
    """Mock Coinbase client for testing"""
    async def create_order(self, order):
        return {
            "order_id": "test_order_id",
            "product_id": order.product_id,
            "side": order.side,
            "size": order.size,
            "status": "filled"
        }
    
    async def get_order(self, order_id):
        return {"order_id": order_id, "status": "filled"}
    
    async def cancel_order(self, order_id):
        return {"order_id": order_id, "status": "cancelled"}
    
    async def get_account(self):
        return {
            "balances": {
                "USD": {"amount": "100000.00", "hold": "0.00"},
                "BTC": {"amount": "10.00000000", "hold": "0.00000000"}
            }
        }

@pytest.fixture
def mock_config():
    """Test configuration"""
    return {
        'paper_trading': True,
        'api_key': 'test_key',
        'api_secret': 'test_secret',
        'risk_management': {
            'position_limits': {'BTC-USD': Decimal('10')},
            'order_size_limits': {'BTC-USD': Decimal('5')}
        },
        'max_positions': {'BTC-USD': Decimal('10')},
        'risk_limits': {'max_exposure': Decimal('100')},
        'emergency_thresholds': {'max_drawdown': Decimal('0.1')}
    }

class AsyncExchangeService(ExchangeService):
    """Mock exchange service with async methods"""
    async def place_market_order(self, order: MarketOrder) -> Dict[str, Any]:
        return {
            "order_id": "test_market_order",
            "product_id": order.product_id,
            "side": order.side,
            "size": str(order.size),
            "status": "filled"
        }
    
    async def place_limit_order(self, order: LimitOrder) -> Dict[str, Any]:
        return {
            "order_id": "test_limit_order",
            "product_id": order.product_id,
            "side": order.side,
            "size": str(order.size),
            "price": str(order.price),
            "status": "open"
        }

@pytest_asyncio.fixture
async def mock_trading_bot(mock_config):
    """Trading bot instance with mocked dependencies"""
    with patch('crypto_j_trader.src.trading.trading_core.MarketDataHandler') as mock_market_data, \
         patch('crypto_j_trader.src.trading.trading_core.RiskManager') as mock_risk_manager, \
         patch('crypto_j_trader.src.trading.trading_core.EmergencyManager') as mock_emergency_manager, \
         patch('crypto_j_trader.src.trading.trading_core.HealthMonitor') as mock_health_monitor, \
         patch('crypto_j_trader.src.trading.exchange_service.CoinbaseAdvancedClient', return_value=MockCoinbaseClient()):
        
        # Configure mocks
        mock_market_data.return_value.get_last_price = AsyncMock(return_value=50000.0)
        mock_market_data.return_value.start = AsyncMock()
        mock_market_data.return_value.stop = AsyncMock()
        mock_risk_manager.return_value.validate_order = MagicMock(return_value=True)
        mock_health_monitor.return_value.check_health = AsyncMock(return_value={"status": "healthy"})
        mock_emergency_manager.return_value.emergency_shutdown = AsyncMock()
        
        # Initialize bot with test config and async exchange service
        trading_bot = TradingBot(config=mock_config)
        trading_bot.exchange = AsyncExchangeService(credentials=mock_config, paper_trading=True)
        await trading_bot.start()
        yield trading_bot
        await trading_bot.stop()

class TestTradingBot:
    @pytest.mark.asyncio
    async def test_order_execution(self, mock_trading_bot):
        """Test market order execution and position tracking"""
        symbol = "BTC-USD"
        quantity = Decimal('0.5')
        
        # Test buy order
        result = await mock_trading_bot.execute_order(
            symbol=symbol,
            side="buy",
            quantity=quantity
        )
        assert isinstance(result, dict), "Order execution should return a dict"
        assert mock_trading_bot.get_position(symbol) == quantity

        # Test sell order
        result = await mock_trading_bot.execute_order(
            symbol=symbol,
            side="sell",
            quantity=quantity
        )
        assert isinstance(result, dict), "Order execution should return a dict"
        assert mock_trading_bot.get_position(symbol) == Decimal('0')

    @pytest.mark.asyncio
    async def test_limit_order_execution(self, mock_trading_bot):
        """Test limit order execution"""
        symbol = "BTC-USD"
        quantity = Decimal('0.5')
        price = Decimal('50000')
        
        result = await mock_trading_bot.execute_order(
            symbol=symbol,
            side="buy",
            quantity=quantity,
            order_type="limit",
            price=price
        )
        assert isinstance(result, dict), "Order execution should return a dict"
        assert mock_trading_bot.get_position(symbol) == quantity

    @pytest.mark.asyncio
    async def test_position_tracking(self, mock_trading_bot):
        """Test position tracking functionality"""
        symbol = "BTC-USD"
        
        # Test initial position
        assert mock_trading_bot.get_position(symbol) == Decimal('0')
        
        # Test position after buy
        await mock_trading_bot.execute_order(symbol=symbol, side="buy", quantity=Decimal('1'))
        assert mock_trading_bot.get_position(symbol) == Decimal('1')
        
        # Test position after partial sell
        await mock_trading_bot.execute_order(symbol=symbol, side="sell", quantity=Decimal('0.5'))
        assert mock_trading_bot.get_position(symbol) == Decimal('0.5')

    @pytest.mark.asyncio
    async def test_health_check(self, mock_trading_bot):
        """Test health monitoring functionality"""
        health_status = await mock_trading_bot.check_health()
        assert isinstance(health_status, dict), "Health check should return a dict"
        assert health_status["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_failed_health_check(self, mock_trading_bot):
        """Test order rejection when system health is critical"""
        with patch.object(mock_trading_bot.health_monitor, 'check_health', 
                         new_callable=AsyncMock, return_value={"status": "critical"}):
            with pytest.raises(RuntimeError, match="System health critical"):
                await mock_trading_bot.execute_order(
                    symbol="BTC-USD",
                    side="buy",
                    quantity=Decimal('1')
                )

    @pytest.mark.asyncio
    async def test_failed_risk_validation(self, mock_trading_bot):
        """Test order rejection when risk validation fails"""
        with patch.object(mock_trading_bot.risk_manager, 'validate_order', return_value=False):
            with pytest.raises(ValueError, match="Order failed risk validation"):
                await mock_trading_bot.execute_order(
                    symbol="BTC-USD",
                    side="buy",
                    quantity=Decimal('1')
                )

    @pytest.mark.asyncio
    async def test_limit_order_without_price(self, mock_trading_bot):
        """Test limit order rejection when price is not provided"""
        with pytest.raises(ValueError, match="Price required for limit orders"):
            await mock_trading_bot.execute_order(
                symbol="BTC-USD",
                side="buy",
                quantity=Decimal('1'),
                order_type="limit"
            )

    @pytest.mark.asyncio
    async def test_emergency_shutdown(self, mock_trading_bot):
        """Test emergency shutdown functionality"""
        # Setup: Create a position
        symbol = "BTC-USD"
        await mock_trading_bot.execute_order(symbol=symbol, side="buy", quantity=Decimal('1'))
        assert mock_trading_bot.get_position(symbol) == Decimal('1')
        
        # Test shutdown
        await mock_trading_bot.emergency_shutdown()
        
        # Verify bot is stopped
        assert not mock_trading_bot.is_running
        
        # In paper trading mode, positions should be closed
        assert mock_trading_bot.get_position(symbol) == Decimal('0')

    @pytest.mark.asyncio
    async def test_emergency_shutdown_with_failed_position_close(self, mock_trading_bot):
        """Test emergency shutdown when position closing fails"""
        # Setup: Create a position
        symbol = "BTC-USD"
        await mock_trading_bot.execute_order(symbol=symbol, side="buy", quantity=Decimal('1'))
        
        # Make execute_order raise an exception during shutdown
        with patch.object(mock_trading_bot, 'execute_order', 
                         side_effect=Exception("Failed to close position")):
            # Shutdown should complete even if position closing fails
            await mock_trading_bot.emergency_shutdown()
            assert not mock_trading_bot.is_running

    def test_initialization_from_file_config(self):
        """Test bot initialization from config file"""
        with patch('crypto_j_trader.src.trading.trading_core.load_config') as mock_load_config, \
             patch('crypto_j_trader.src.trading.trading_core.ExchangeService', new_callable=MagicMock) as mock_exchange_service, \
             patch('crypto_j_trader.src.trading.trading_core.MarketDataHandler', new_callable=MagicMock) as mock_market_data_handler, \
             patch('crypto_j_trader.src.trading.trading_core.RiskManager', new_callable=MagicMock) as mock_risk_manager, \
             patch('crypto_j_trader.src.trading.trading_core.HealthMonitor', new_callable=MagicMock) as mock_health_monitor, \
             patch('crypto_j_trader.src.trading.trading_core.EmergencyManager', new_callable=MagicMock) as mock_emergency_manager:
            
            # Configure mock config
            mock_config_instance = MagicMock()
            mock_config_instance.config = {
                'paper_trading': True,
                'risk_management': {},
                'health': {}
            }
            mock_config_instance.is_paper_trading.return_value = True
            mock_load_config.return_value = mock_config_instance
            
            # Create bot instance
            trading_bot = TradingBot()
            
            assert trading_bot.paper_trading == True
            assert isinstance(trading_bot.config, dict)
            mock_load_config.assert_called_once()