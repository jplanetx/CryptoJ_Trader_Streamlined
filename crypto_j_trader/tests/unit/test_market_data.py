"""Unit tests for market data handling."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from crypto_j_trader.src.trading.market_data import MarketDataManager

@pytest.fixture
def market_config():
    """Test configuration for market data."""
    return {
        'trading_pairs': ['BTC-USD', 'ETH-USD'],
        'granularity': 60,  # 1-minute candles
        'data_window': '1h'  # 1 hour of data
    }

@pytest.fixture
def mock_data_manager(market_config):
    """Create MarketDataManager with mocked API."""
    manager = MarketDataManager(market_config)
    manager.api_client = AsyncMock()
    return manager

@pytest.mark.asyncio
async def test_get_market_data_success(mock_data_manager):
    """Test successful market data retrieval."""
    mock_data = [
        [1625097600, 35000, 35100, 34900, 35050, 100],  # timestamp, open, high, low, close, volume
        [1625097660, 35050, 35200, 35000, 35150, 120]
    ]
    mock_data_manager.api_client.get_historic_rates = AsyncMock(return_value=mock_data)
    
    data = await mock_data_manager.get_market_data('BTC-USD')
    assert len(data) == 2
    assert all(key in data[0] for key in ['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    assert data[0]['close'] == 35050

@pytest.mark.asyncio
async def test_get_ticker_success(mock_data_manager):
    """Test successful ticker data retrieval."""
    mock_ticker = {
        'price': '35000.00',
        'volume': '1000.00',
        'time': datetime.now(timezone.utc).isoformat()
    }
    mock_data_manager.api_client.get_ticker = AsyncMock(return_value=mock_ticker)
    
    ticker = await mock_data_manager.get_ticker('BTC-USD')
    assert 'price' in ticker
    assert 'volume' in ticker
    assert isinstance(ticker['price'], float)
    assert ticker['price'] == 35000.00

@pytest.mark.asyncio
async def test_get_ticker_api_error(mock_data_manager):
    """Test ticker retrieval with API error."""
    mock_data_manager.api_client.get_ticker = AsyncMock(side_effect=Exception("API Error"))
    
    with pytest.raises(Exception, match="API Error"):
        await mock_data_manager.get_ticker('BTC-USD')

@pytest.mark.asyncio
async def test_aggregate_market_data_success(mock_data_manager):
    """Test successful market data aggregation."""
    mock_data = [
        {
            'timestamp': 1625097600,
            'open': 35000,
            'high': 35100,
            'low': 34900,
            'close': 35050,
            'volume': 100
        },
        {
            'timestamp': 1625097660,
            'open': 35050,
            'high': 35200,
            'low': 35000,
            'close': 35150,
            'volume': 120
        }
    ]
    
    agg_data = await mock_data_manager.aggregate_market_data(mock_data)
    assert all(key in agg_data for key in ['vwap', 'volume', 'high', 'low', 'close'])
    assert agg_data['vwap'] > 0
    assert agg_data['volume'] == 220
    assert agg_data['high'] == 35200
    assert agg_data['low'] == 34900

@pytest.mark.asyncio
async def test_aggregate_market_data_partial_failure(mock_data_manager):
    """Test market data aggregation with some invalid data."""
    mock_data = [
        {
            'timestamp': 1625097600,
            'open': 35000,
            'high': 35100,
            'low': 34900,
            'close': 35050,
            'volume': 100
        },
        {
            'timestamp': 1625097660,
            'open': None,  # Invalid open
            'high': None,  # Invalid high
            'low': None,  # Invalid low
            'close': None,  # Invalid close
            'volume': 120
        },
        {
            'timestamp': 1625097720,
            'open': 35150,
            'high': 35300,
            'low': 35100,
            'close': 35200,
            'volume': 90
        }
    ]
    
    agg_data = await mock_data_manager.aggregate_market_data(mock_data)
    assert all(key in agg_data for key in ['vwap', 'volume', 'high', 'low', 'close'])
    assert agg_data['volume'] == 310  # Should include all volumes
    assert agg_data['high'] == 35300  # Should use valid data points
    assert agg_data['low'] == 34900

@pytest.mark.asyncio
async def test_invalid_granularity(mock_data_manager):
    """Test handling of invalid granularity value."""
    mock_data_manager.config['granularity'] = 45  # Invalid value
    
    with pytest.raises(ValueError, match="Invalid granularity value"):
        await mock_data_manager.get_market_data('BTC-USD')

@pytest.mark.asyncio
async def test_empty_response_handling(mock_data_manager):
    """Test handling of empty API response."""
    mock_data_manager.api_client.get_historic_rates = AsyncMock(return_value=[])
    
    data = await mock_data_manager.get_market_data('BTC-USD')
    assert len(data) == 0

@pytest.mark.asyncio
async def test_technical_indicators(mock_data_manager):
    """Test calculation of technical indicators."""
    mock_data = [
        {
            'timestamp': ts,
            'open': 35000 + i * 100,
            'high': 35100 + i * 100,
            'low': 34900 + i * 100,
            'close': 35050 + i * 100,
            'volume': 100 + i * 10
        }
        for i, ts in enumerate(range(1625097600, 1625097600 + 3600, 60))
    ]
    
    indicators = await mock_data_manager.calculate_indicators(mock_data)
    assert all(key in indicators for key in ['rsi', 'macd', 'bb_upper', 'bb_lower'])
    assert isinstance(indicators['rsi'], float)
    assert len(indicators['macd']) == 3  # macd, signal, histogram

@pytest.mark.asyncio
async def test_market_status_check(mock_data_manager):
    """Test market status verification."""
    mock_data_manager.api_client.get_market_status = AsyncMock(return_value={'status': 'online'})
    
    status = await mock_data_manager.check_market_status('BTC-USD')
    assert status['status'] == 'online'

@pytest.mark.asyncio
async def test_data_freshness(mock_data_manager):
    """Test verification of data freshness."""
    # Set up current time in UTC
    current_time = datetime.now(timezone.utc)
    
    # Mock ticker data in UTC
    mock_ticker = {
        'price': '35000.00',
        'volume': '1000.00',
        'time': current_time.isoformat()
    }
    mock_data_manager.api_client.get_ticker = AsyncMock(return_value=mock_ticker)
    
    # Initialize last update time with current UTC time
    mock_data_manager.last_update['BTC-USD'] = current_time
    
    # Mock market data to simulate recent data
    mock_data = [
        [int(current_time.timestamp()), 35000, 35100, 34900, 35050, 100]
    ]
    mock_data_manager.cached_data['BTC-USD'] = [{
        'timestamp': int(current_time.timestamp()),
        'open': 35000,
        'high': 35100,
        'low': 34900,
        'close': 35050,
        'volume': 100
    }]
    mock_data_manager.api_client.get_historic_rates = AsyncMock(return_value=mock_data)
    
    # Test freshness verification
    is_fresh = await mock_data_manager.verify_data_freshness('BTC-USD')
    assert is_fresh is True

@pytest.mark.asyncio
async def test_stale_data_freshness(mock_data_manager):
    """Test verification of stale data."""
    # Set up stale time (10 minutes ago) in UTC
    current_time = datetime.now(timezone.utc)
    stale_time = current_time.replace(minute=current_time.minute - 10)
    
    mock_ticker = {
        'price': '35000.00',
        'volume': '1000.00',
        'time': stale_time.isoformat()
    }
    mock_data_manager.api_client.get_ticker = AsyncMock(return_value=mock_ticker)
    
    # Test freshness verification with stale data
    is_fresh = await mock_data_manager.verify_data_freshness('BTC-USD')
    assert is_fresh is False