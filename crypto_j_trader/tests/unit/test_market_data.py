"""Unit tests for market data handling."""
import pytest
import numpy as np
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch
from crypto_j_trader.src.trading.market_data import MarketDataManager

@pytest.fixture
def market_config():
    """Mock market configuration fixture."""
    return {
        "granularity": 60,
        "websocket": {
            "url": "wss://test.example.com/ws",
            "ping_interval": 30,
            "reconnect_delay": 0.1,
            "subscriptions": ["BTC-USD"]
        }
    }

@pytest.fixture
def mock_ws_handler():
    """Mock WebSocket handler fixture."""
    with patch('crypto_j_trader.src.trading.market_data.WebSocketHandler') as mock:
        handler = Mock()
        handler.is_connected = True
        handler.is_healthy = True
        handler.subscribe = AsyncMock(return_value=True)
        handler.start = AsyncMock()
        handler.stop = AsyncMock()
        mock.return_value = handler
        yield handler

@pytest.fixture
def sample_market_data():
    """Sample market data for testing."""
    return [
        {
            'timestamp': 1643673600,
            'open': 35000.0,
            'high': 35100.0,
            'low': 34900.0,
            'close': 35050.0,
            'volume': 100.0
        },
        {
            'timestamp': 1643673660,
            'open': 35050.0,
            'high': 35200.0,
            'low': 35000.0,
            'close': 35150.0,
            'volume': 150.0
        }
    ]

@pytest.mark.asyncio
async def test_market_data_initialization(market_config, mock_ws_handler):
    """Test MarketDataManager initialization."""
    manager = MarketDataManager(market_config)
    assert manager.config == market_config
    assert manager.ws_handler is not None
    assert len(manager.trading_pairs) == 0

@pytest.mark.asyncio
async def test_start_stop(market_config, mock_ws_handler):
    """Test starting and stopping the market data manager."""
    manager = MarketDataManager(market_config)
    await manager.start()
    mock_ws_handler.start.assert_called_once()
    
    await manager.stop()
    mock_ws_handler.stop.assert_called_once()

@pytest.mark.asyncio
async def test_subscribe_to_trading_pair(market_config, mock_ws_handler):
    """Test subscribing to trading pairs."""
    manager = MarketDataManager(market_config)
    success = await manager.subscribe_to_trading_pair("BTC-USD")
    assert success
    assert "BTC-USD" in manager.trading_pairs
    mock_ws_handler.subscribe.assert_called_once_with("BTC-USD")

@pytest.mark.asyncio
async def test_handle_ws_message(market_config, mock_ws_handler):
    """Test WebSocket message handling."""
    manager = MarketDataManager(market_config)
    test_message = {
        'type': 'ticker',
        'product_id': 'BTC-USD',
        'price': '35000.00',
        'volume_24h': '1000.00',
        'time': datetime.now(timezone.utc).isoformat()
    }
    
    await manager._handle_ws_message(test_message)
    assert 'BTC-USD' in manager.latest_tickers
    assert float(test_message['price']) == manager.latest_tickers['BTC-USD']['price']

@pytest.mark.asyncio
async def test_stale_data_freshness(market_config):
    """Test verification of stale data."""
    manager = MarketDataManager(market_config)
    manager.api_client = AsyncMock()

    current_time = datetime.now(timezone.utc)
    stale_time = current_time - timedelta(minutes=10)
    
    mock_ticker = {
        'price': '35000.00',
        'volume': '1000.00',
        'time': stale_time.isoformat()
    }
    manager.api_client.get_ticker = AsyncMock(return_value=mock_ticker)
    manager.last_update['BTC-USD'] = stale_time
    
    is_fresh = await manager.verify_data_freshness('BTC-USD')
    assert is_fresh is False, "Data should be considered stale after 10 minutes"

@pytest.mark.asyncio
async def test_fresh_data_verification(market_config):
    """Test verification of fresh data."""
    manager = MarketDataManager(market_config)
    manager.api_client = AsyncMock()
    
    current_time = datetime.now(timezone.utc)
    fresh_time = current_time - timedelta(seconds=30)
    
    mock_ticker = {
        'price': '35000.00',
        'volume': '1000.00',
        'time': fresh_time.isoformat()
    }
    manager.api_client.get_ticker = AsyncMock(return_value=mock_ticker)
    manager.last_update['BTC-USD'] = fresh_time
    manager.latest_tickers['BTC-USD'] = {
        'price': 35000.0,
        'volume': 1000.0,
        'time': fresh_time.isoformat()
    }
    
    is_fresh = await manager.verify_data_freshness('BTC-USD')
    assert is_fresh is True, "Recent data should be considered fresh"

@pytest.mark.asyncio
async def test_market_data_aggregation(market_config, sample_market_data):
    """Test market data aggregation."""
    manager = MarketDataManager(market_config)
    
    aggregated = await manager.aggregate_market_data(sample_market_data)
    assert isinstance(aggregated, dict)
    assert all(k in aggregated for k in ['vwap', 'volume', 'high', 'low', 'close'])
    assert aggregated['high'] == 35200.0
    assert aggregated['low'] == 34900.0
    assert aggregated['close'] == 35150.0

@pytest.mark.asyncio
async def test_indicator_calculation(market_config, sample_market_data):
    """Test technical indicator calculations."""
    manager = MarketDataManager(market_config)
    
    indicators = await manager.calculate_indicators(sample_market_data)
    assert isinstance(indicators, dict)
    assert all(k in indicators for k in ['rsi', 'macd', 'bb'])
    
    # Test empty data handling
    empty_indicators = await manager.calculate_indicators([])
    assert empty_indicators['rsi'] == 0.0
    assert empty_indicators['macd'] == (0.0, 0.0, 0.0)
    assert empty_indicators['bb'] == (0.0, 0.0)

@pytest.mark.asyncio
async def test_market_status(market_config, mock_ws_handler):
    """Test market status checking."""
    manager = MarketDataManager(market_config)
    manager.api_client = AsyncMock()
    manager.api_client.get_market_status = AsyncMock(return_value={'status': 'online'})
    
    # Test with healthy WebSocket
    status = await manager.check_market_status('BTC-USD')
    assert status['status'] == 'online'
    
    # Test with unhealthy WebSocket
    mock_ws_handler.is_healthy = False
    status = await manager.check_market_status('BTC-USD')
    assert status['status'] == 'error'
    assert 'WebSocket connection unhealthy' in status['message']

@pytest.mark.asyncio
async def test_cached_data_handling(market_config):
    """Test cached data retrieval."""
    manager = MarketDataManager(market_config)
    
    # Test with no cached data
    assert manager.get_cached_data('BTC-USD') is None
    
    # Test with fresh cached data
    current_time = datetime.now(timezone.utc)
    manager.last_update['BTC-USD'] = current_time
    manager.cached_data['BTC-USD'] = [{'price': 35000.0}]
    
    cached = manager.get_cached_data('BTC-USD')
    assert cached is not None
    assert len(cached) == 1
    assert cached[0]['price'] == 35000.0
    
    # Test with stale cached data
    manager.last_update['BTC-USD'] = current_time - timedelta(minutes=5)
    assert manager.get_cached_data('BTC-USD') is None