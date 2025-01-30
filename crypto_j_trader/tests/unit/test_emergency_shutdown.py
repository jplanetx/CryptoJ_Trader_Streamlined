"""Tests for emergency shutdown functionality."""

import pytest
import asyncio
from datetime import datetime, timedelta
import pandas as pd
from unittest.mock import Mock, AsyncMock, patch
from crypto_j_trader.src.trading.emergency_manager import EmergencyManager

@pytest.fixture
def config():
    return {
        'emergency_price_change_threshold': 0.1,
        'volume_spike_threshold': 5.0,
        'max_data_age_seconds': 300,
        'trading_pairs': [
            {'pair': 'BTC-USD', 'weight': 0.6},
            {'pair': 'ETH-USD', 'weight': 0.4}
        ]
    }

@pytest.fixture
def mock_market_data():
    now = datetime.now()
    index = pd.date_range(end=now, periods=10, freq='1min')
    
    df = pd.DataFrame({
        'price': [50000] * 10,  # Stable price
        'size': [100] * 10,     # Stable volume
        'low': [49900] * 10,
        'high': [50100] * 10,
        'open': [49950] * 10,
        'close': [50050] * 10,
    }, index=index)
    
    return {'BTC-USD': df}

@pytest.fixture
def mock_websocket():
    mock = AsyncMock()
    mock.last_message_time = datetime.now()
    return mock

@pytest.fixture
def emergency_manager(config):
    return EmergencyManager(config)

@pytest.mark.asyncio
async def test_emergency_price_movement(emergency_manager, mock_market_data):
    """Test emergency shutdown triggers on extreme price movement"""
    # Set up mock data with price spike
    df = mock_market_data['BTC-USD'].copy()
    df.iloc[-1, df.columns.get_loc('price')] = 60000  # 20% increase
    mock_market_data['BTC-USD'] = df

    result = await emergency_manager.check_emergency_conditions(
        'BTC-USD',
        60000,  # Current price
        mock_market_data
    )
    assert result is True

@pytest.mark.asyncio
async def test_emergency_volume_spike(emergency_manager, mock_market_data):
    """Test emergency shutdown triggers on volume spike"""
    # Set up mock data with volume spike
    df = mock_market_data['BTC-USD'].copy()
    df.iloc[-1, df.columns.get_loc('size')] = 1000  # 10x volume spike
    mock_market_data['BTC-USD'] = df
    
    result = await emergency_manager.check_emergency_conditions(
        'BTC-USD',
        50000,
        mock_market_data
    )
    assert result is True

@pytest.mark.asyncio
async def test_emergency_shutdown_procedure(emergency_manager):
    """Test complete emergency shutdown procedure"""
    positions = {
        'BTC-USD': {'quantity': 1.0},
        'ETH-USD': {'quantity': 5.0}
    }
    
    mock_execute_trade = AsyncMock()
    mock_websocket = AsyncMock()
    
    await emergency_manager.initiate_emergency_shutdown(
        positions,
        mock_execute_trade,
        mock_websocket
    )
    
    # Verify shutdown state
    assert emergency_manager.emergency_shutdown is True
    assert emergency_manager.shutdown_requested is True
    
    # Verify position closing attempts
    assert mock_execute_trade.call_count == 2  # Should try to close both positions
    assert mock_websocket.stop.called

@pytest.mark.asyncio
async def test_websocket_connection_health(emergency_manager, mock_market_data, mock_websocket):
    """Test WebSocket connection health monitoring"""
    # Test with fresh connection
    result = await emergency_manager.check_emergency_conditions(
        'BTC-USD',
        50000,
        mock_market_data,
        mock_websocket
    )
    assert result is False
    
    # Test with stale connection
    mock_websocket.last_message_time = datetime.now() - timedelta(seconds=emergency_manager.max_data_age_seconds + 10)
    result = await emergency_manager.check_emergency_conditions(
        'BTC-USD',
        50000,
        mock_market_data,
        mock_websocket
    )
    assert result is True

@pytest.mark.asyncio
async def test_market_data_freshness(emergency_manager, mock_market_data):
    """Test market data freshness check"""
    # Test with fresh data
    result = await emergency_manager.check_emergency_conditions(
        'BTC-USD',
        50000,
        mock_market_data
    )
    assert result is False
    
    # Test with stale data
    df = mock_market_data['BTC-USD'].copy()
    df.index = [
        datetime.now() - timedelta(seconds=emergency_manager.max_data_age_seconds + i)
        for i in range(len(df), 0, -1)
    ]
    mock_market_data['BTC-USD'] = df
    
    result = await emergency_manager.check_emergency_conditions(
        'BTC-USD',
        50000,
        mock_market_data
    )
    assert result is True

@pytest.mark.asyncio
async def test_error_handling(emergency_manager):
    """Test error handling during emergency checks"""
    # Test with invalid market data
    result = await emergency_manager.check_emergency_conditions(
        'BTC-USD',
        50000,
        {'BTC-USD': None}
    )
    assert result is True  # Should trigger shutdown on error
    
    # Test with missing data
    result = await emergency_manager.check_emergency_conditions(
        'BTC-USD',
        50000,
        {}
    )
    assert result is False  # No data is not an emergency

@pytest.mark.asyncio
async def test_shutdown_cleanup(emergency_manager):
    """Test cleanup during emergency shutdown"""
    positions = {'BTC-USD': {'quantity': 1.0}}
    mock_execute_trade = AsyncMock(side_effect=Exception("Trade failed"))
    mock_websocket = AsyncMock()
    
    await emergency_manager.initiate_emergency_shutdown(
        positions,
        mock_execute_trade,
        mock_websocket
    )
    
    # Verify shutdown completed despite errors
    assert emergency_manager.emergency_shutdown is True
    assert mock_websocket.stop.called  # WebSocket cleanup should still occur
