"""Unit tests for market data handling."""
import pytest

@pytest.fixture
def market_config():
    """Mock market configuration fixture."""
    return {"granularity": 60}

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from crypto_j_trader.src.trading.market_data import MarketDataManager

@pytest.mark.asyncio
async def test_stale_data_freshness(market_config):
    """Test verification of stale data."""
    # Create manager with mock config
    manager = MarketDataManager(market_config)
    manager.api_client = AsyncMock()

    # Set up stale time (10 minutes ago) in UTC
    current_time = datetime.now(timezone.utc)
    stale_time = current_time - timedelta(minutes=10)
    
    # Create mock ticker with stale timestamp
    mock_ticker = {
        'price': '35000.00',
        'volume': '1000.00',
        'time': stale_time.isoformat()
    }
    manager.api_client.get_ticker = AsyncMock(return_value=mock_ticker)
    
    # Explicitly set last update to a stale time
    manager.last_update['BTC-USD'] = stale_time
    
    # Verify data freshness explicitly considers the stale time
    is_fresh = await manager.verify_data_freshness('BTC-USD')
    assert is_fresh is False, "Data should be considered stale after 10 minutes"