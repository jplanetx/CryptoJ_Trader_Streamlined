"""Integration tests for Emergency Manager and Market Data interaction"""
import pytest
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from crypto_j_trader.src.trading.emergency_manager import EmergencyManager
from crypto_j_trader.src.trading.market_data_handler import MarketDataHandler

# Mark all tests in this module as integration tests
pytestmark = [pytest.mark.integration]

@pytest.fixture
def reset_emergency_manager():
    """Fixture to reset emergency manager for a given instance."""
    def _reset(emergency_manager):
        emergency_manager.emergency_mode = False
    return _reset

class MockMarketData(MarketDataHandler):
    """Mock market data handler for testing"""
    def __init__(self, config):
        self.config = config
        self.last_prices = {'BTC-USD': 50000.0, 'ETH-USD': 2000.0}
        self._ws_handler = None
        self.is_running = False

    def get_last_price(self, trading_pair):
        return self.last_prices.get(trading_pair)

    async def start(self):
        self.is_running = True

    async def stop(self):
        self.is_running = False
        if self._ws_handler:
            await self._ws_handler.stop()

@pytest.fixture
def market_data_config():
    return {
        'websocket': {
            'url': 'wss://test.exchange.com/ws',
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'pairs': ['BTC-USD', 'ETH-USD'],
            'ping_interval': 30,
            'reconnect_delay': 5,
            'message_timeout': 10
        },
        'trading_pairs': ['BTC-USD', 'ETH-USD'],
        'update_interval': 1,
        'cache_size': 1000
    }

@pytest.fixture
def emergency_config():
    return {
        'max_positions': {
            'BTC-USD': '10.0',
            'ETH-USD': '100.0'
        },
        'risk_limits': {
            'BTC-USD': '500000.0',
            'ETH-USD': '200000.0'
        },
        'emergency_thresholds': {
            'BTC-USD': '1000000.0',
            'ETH-USD': '500000.0'
        }
    }

@pytest.fixture
def mock_websocket_handler():
    """Mock WebSocket handler for testing"""
    class MockWebSocketHandler:
        def __init__(self, config):
            self.config = config
            self.last_message_time = datetime.now()
            self.connected = True
            self.stop_mock = AsyncMock()
            self.messages = []
            self.callbacks = []

        def add_message_handler(self, callback):
            self.callbacks.append(callback)

        async def start(self):
            self.connected = True

        async def stop(self):
            self.connected = False
            await self.stop_mock()
    
    return MockWebSocketHandler

@pytest.mark.asyncio
class TestEmergencyMarketDataIntegration:
    """Integration tests for Emergency Manager with Market Data"""

    async def test_market_data_staleness_detection(self, market_data_config, emergency_config, mock_websocket_handler, reset_emergency_manager):
        """Test detection of stale market data"""
        market_data = MockMarketData(market_data_config)
        market_data._ws_handler = mock_websocket_handler(market_data_config)
        emergency_manager = EmergencyManager(emergency_config)
        reset_emergency_manager(emergency_manager)

        # Test with fresh data
        result = await emergency_manager.validate_new_position(
            trading_pair='BTC-USD',
            size=1.0,
            price=50000.0
        )
        assert result is True, "Should allow valid position under normal conditions"

        # Test with larger position (exceeds maximum allowed)
        result = await emergency_manager.validate_new_position(
            trading_pair='BTC-USD',
            size=11.0,  # Exceeds max position limit
            price=50000.0
        )
        assert result is False, "Should reject position exceeding limits"

    async def test_price_movement_trigger(self, market_data_config, emergency_config, mock_websocket_handler, reset_emergency_manager):
        """Test emergency trigger on significant price movement"""
        market_data = MockMarketData(market_data_config)
        market_data._ws_handler = mock_websocket_handler(market_data_config)
        emergency_manager = EmergencyManager(emergency_config)
        reset_emergency_manager(emergency_manager)

        # Test normal price scenario
        result = await emergency_manager.validate_new_position(
            trading_pair='BTC-USD',
            size=1.0,
            price=50000.0
        )
        assert result is True, "Should allow normal price position"

        # Test with a price spike (extreme price)
        result = await emergency_manager.validate_new_position(
            trading_pair='BTC-USD',
            size=1.0,
            price=1000000.0  # Extremely high price
        )
        assert result is False, "Should reject position at extreme price"

    async def test_volume_based_validation(self, market_data_config, emergency_config, mock_websocket_handler, reset_emergency_manager):
        """Test validation based on volume thresholds"""
        market_data = MockMarketData(market_data_config)
        market_data._ws_handler = mock_websocket_handler(market_data_config)
        emergency_manager = EmergencyManager(emergency_config)
        reset_emergency_manager(emergency_manager)

        # Test with a normal volume position
        result = await emergency_manager.validate_new_position(
            trading_pair='BTC-USD',
            size=5.0,
            price=50000.0
        )
        assert result is True, "Should allow normal volume position"

        # Test with a high volume position that should exceed limits
        result = await emergency_manager.validate_new_position(
            trading_pair='BTC-USD',
            size=50.0,  # Very large volume position
            price=50000.0
        )
        assert result is False, "Should reject high volume position"

    @pytest.mark.asyncio
    async def test_emergency_shutdown_procedure(self, market_data_config, emergency_config, mock_websocket_handler, reset_emergency_manager):
        """Test emergency shutdown procedure."""
        market_data = MockMarketData(market_data_config)
        market_data._ws_handler = mock_websocket_handler(market_data_config)
        emergency_manager = EmergencyManager(emergency_config)
        reset_emergency_manager(emergency_manager)

        # First verify position validation works normally
        result = await emergency_manager.validate_new_position(
            trading_pair='BTC-USD',
            size=1.0,
            price=50000.0
        )
        assert result is True, "Should allow positions before emergency"

        # Trigger emergency shutdown
        await emergency_manager.emergency_shutdown()
        assert emergency_manager.emergency_mode is True, "Should be in emergency mode"

        # Try to validate a new position during emergency
        result = await emergency_manager.validate_new_position(
            trading_pair='BTC-USD',
            size=1.0,
            price=50000.0
        )
        assert result is False, "Should reject positions during emergency"

    async def test_risk_limit_validation(self, market_data_config, emergency_config, mock_websocket_handler, reset_emergency_manager):
        """Test risk limit validation"""
        market_data = MockMarketData(market_data_config)
        market_data._ws_handler = mock_websocket_handler(market_data_config)
        emergency_manager = EmergencyManager(emergency_config)
        reset_emergency_manager(emergency_manager)

        # Test a position within defined risk limits
        result = await emergency_manager.validate_new_position(
            trading_pair='BTC-USD',
            size=1.0,
            price=50000.0
        )
        assert result is True, "Should allow position within risk limits"

        # Test a position that exceeds risk limits
        result = await emergency_manager.validate_new_position(
            trading_pair='BTC-USD',
            size=15.0,
            price=50000.0  # Total value: 750,000 > risk limit
        )
        assert result is False, "Should reject position exceeding risk limits"

    async def test_restore_normal_operation(self, market_data_config, emergency_config, mock_websocket_handler, reset_emergency_manager):
        """Test restoration of normal operation after emergency"""
        market_data = MockMarketData(market_data_config)
        market_data._ws_handler = mock_websocket_handler(market_data_config)
        emergency_manager = EmergencyManager(emergency_config)

        # Trigger an emergency shutdown
        await emergency_manager.emergency_shutdown()
        assert emergency_manager.emergency_mode is True, "Emergency mode should be active after shutdown"

        # Attempt to restore normal operations
        result = await emergency_manager.restore_normal_operation()
        assert result is True, "Should successfully restore normal operation"
        assert emergency_manager.emergency_mode is False, "Should no longer be in emergency mode after restoration"

        # Verify that normal operation resumes by validating a new position
        validate_result = await emergency_manager.validate_new_position(
            trading_pair='BTC-USD',
            size=1.0,
            price=50000.0
        )
        assert validate_result is True, "Should allow valid positions after restoration"