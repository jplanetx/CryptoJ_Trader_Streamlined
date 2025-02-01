"""Integration tests for Emergency Manager and Market Data interaction"""
import pytest
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from crypto_j_trader.src.trading.emergency_manager import EmergencyManager
from crypto_j_trader.src.trading.market_data import MarketDataHandler

# Mark all tests in this module as both emergency and integration tests
pytestmark = [pytest.mark.emergency, pytest.mark.integration]

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
def emergency_config(tmp_path):
    return {
        'emergency_state_file': str(tmp_path / "test_emergency_state.json"),
        'max_data_age_seconds': 300,
        'emergency_price_change_threshold': 0.1,
        'volume_spike_threshold': 5.0,
        'max_position_close_attempts': 3,
        'position_close_retry_delay': 1
    }

@pytest.fixture
def mock_websocket_handler():
    """Mock WebSocket handler for testing"""
    class MockWebSocketHandler:
        def __init__(self, config):
            self.config = config
            self.last_message_time = datetime.now()
            self.connected = True
            self.stop = AsyncMock()
            self.messages = []
            self.callbacks = []

        def add_message_handler(self, callback):
            self.callbacks.append(callback)

        async def start(self):
            self.connected = True

        async def stop(self):
            self.connected = False
            await self.stop()

    return MockWebSocketHandler

@pytest.mark.asyncio
class TestEmergencyMarketDataIntegration:
    """Integration tests for Emergency Manager with Market Data"""

    async def test_market_data_staleness_detection(self, market_data_config, emergency_config, mock_websocket_handler):
        """Test detection of stale market data"""
        with patch('crypto_j_trader.src.trading.market_data.WebSocketHandler', mock_websocket_handler):
            market_data = MarketDataHandler(market_data_config)
            emergency_manager = EmergencyManager(emergency_config)

            market_data._ws_handler.last_message_time = datetime.now()
            
            assert not await emergency_manager.check_emergency_conditions(
                'BTC-USD',
                50000.0,
                {'BTC-USD': pd.DataFrame({
                    'price': [50000.0],
                    'size': [1.0]
                }, index=[datetime.now()])},
                market_data._ws_handler
            )

            market_data._ws_handler.last_message_time = datetime.now() - timedelta(seconds=301)
            assert await emergency_manager.check_emergency_conditions(
                'BTC-USD',
                50000.0,
                {'BTC-USD': pd.DataFrame({
                    'price': [50000.0],
                    'size': [1.0]
                }, index=[datetime.now() - timedelta(seconds=301)])},
                market_data._ws_handler
            )

    @pytest.mark.asyncio
    async def test_price_movement_trigger(self, market_data_config, emergency_config, mock_websocket_handler):
        """Test emergency trigger on significant price movement"""
        with patch('crypto_j_trader.src.trading.market_data.WebSocketHandler', mock_websocket_handler):
            market_data = MarketDataHandler(market_data_config)
            emergency_manager = EmergencyManager(emergency_config)

            spike_data = pd.DataFrame({
                'price': [50000.0] * 9 + [60000.0],
                'size': [1.0] * 10
            }, index=pd.date_range(end=datetime.now(), periods=10, freq='1min'))

            market_data.last_prices['BTC-USD'] = 60000.0

            result = await emergency_manager.check_emergency_conditions(
                'BTC-USD',
                60000.0,
                {'BTC-USD': spike_data},
                market_data._ws_handler
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_volume_spike_trigger(self, market_data_config, emergency_config, mock_websocket_handler):
        """Test emergency trigger on volume spike"""
        with patch('crypto_j_trader.src.trading.market_data.WebSocketHandler', mock_websocket_handler):
            market_data = MarketDataHandler(market_data_config)
            emergency_manager = EmergencyManager(emergency_config)

            volume_spike_data = pd.DataFrame({
                'price': [50000.0] * 10,
                'size': [1.0] * 9 + [10.0]
            }, index=pd.date_range(end=datetime.now(), periods=10, freq='1min'))
            
            result = await emergency_manager.check_emergency_conditions(
                'BTC-USD',
                50000.0,
                {'BTC-USD': volume_spike_data},
                market_data._ws_handler
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_emergency_shutdown_procedure(self, market_data_config, emergency_config, mock_websocket_handler):
        """Test complete emergency shutdown process"""
        with patch('crypto_j_trader.src.trading.market_data.WebSocketHandler', mock_websocket_handler):
            market_data = MarketDataHandler(market_data_config)
            emergency_manager = EmergencyManager(emergency_config)
            
            async def mock_execute_trade(pair, side, quantity):
                return True

            test_positions = {'BTC-USD': {'quantity': 1.0}}

            await emergency_manager.initiate_emergency_shutdown(
                test_positions,
                mock_execute_trade,
                market_data._ws_handler
            )

            assert emergency_manager.emergency_shutdown is True
            assert emergency_manager.shutdown_requested is True