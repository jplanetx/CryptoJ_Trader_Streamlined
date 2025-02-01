"""Tests for emergency shutdown functionality."""

import pytest
import asyncio
import os
import json
from datetime import datetime, timedelta
import pandas as pd
from unittest.mock import Mock, AsyncMock, patch, mock_open

from crypto_j_trader.src.trading.emergency_manager import EmergencyManager
from crypto_j_trader.src.trading.risk_management import RiskManager

@pytest.fixture
def config():
    return {
        'emergency_price_change_threshold': 0.1,
        'volume_spike_threshold': 5.0,
        'max_data_age_seconds': 300,
        'max_position_close_attempts': 3,
        'position_close_retry_delay': 1,
        'emergency_state_file': 'test_emergency_state.json',
        'trading_pairs': [
            {'pair': 'BTC-USD', 'weight': 0.6},
            {'pair': 'ETH-USD', 'weight': 0.4}
        ],
        'risk_management': {
            'daily_loss_limit': 0.02,
            'position_size_limit': 0.1,
            'stop_loss_pct': 0.05,
            'max_positions': 5,
            'max_exposure': 0.5
        }
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

@pytest.fixture
def risk_manager(config, mock_market_data_handler):
    risk_manager = RiskManager(config, mock_market_data_handler)
    risk_manager.validate_new_position = Mock(return_value = False)
    return risk_manager

@pytest.fixture
def mock_market_data_handler():
    market_data_handler = Mock()
    market_data_handler.is_running = True
    market_data_handler.is_data_fresh.return_value = True
    return market_data_handler

@pytest.mark.asyncio
async def test_emergency_price_movement(emergency_manager, mock_market_data_handler):
    """Test emergency shutdown triggers on extreme price movement"""
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
async def test_position_close_retry_mechanism(emergency_manager):
    """Test position closing retry mechanism"""
    # Mock trade execution that fails twice then succeeds
    call_count = 0
    async def mock_execute_trade(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Trade failed")
        return True

    position = {'quantity': 1.0}
    success = await emergency_manager.close_position_with_retry(
        'BTC-USD',
        position,
        mock_execute_trade
    )
    
    assert success is True
    assert call_count == 3  # Should succeed on third try

@pytest.mark.asyncio
async def test_emergency_shutdown_persistence(emergency_manager):
    """Test emergency state persistence"""
    mock_file = mock_open()
    with patch('builtins.open', mock_file):
        emergency_manager.emergency_shutdown = True
        emergency_manager.save_state()
        
    # Verify file write was called with correct data
    mock_file.assert_called_once()
    written_data = mock_file().write.call_args[0][0]
    state = json.loads(written_data)
    assert state['emergency_shutdown'] is True
    assert 'timestamp' in state

@pytest.mark.asyncio
async def test_system_health_monitoring(emergency_manager, mock_market_data, mock_websocket):
    """Test system health monitoring"""
    # Test initial health status
    health = emergency_manager.get_system_health()
    assert health['emergency_mode'] is False
    assert all(health['system_checks'].values())
    
    # Test health degradation
    mock_websocket.last_message_time = datetime.now() - timedelta(seconds=400)
    await emergency_manager.check_emergency_conditions(
        'BTC-USD',
        50000,
        mock_market_data,
        mock_websocket
    )
    
    health = emergency_manager.get_system_health()
    assert health['system_checks']['websocket_health'] is False

@pytest.mark.asyncio
async def test_emergency_shutdown_procedure(emergency_manager, risk_manager):
    """Test complete emergency shutdown procedure with risk management"""
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
    
    # Verify risk management blocks new positions
    risk_manager.set_emergency_mode(True)
    portfolio_value = 10000
    assert risk_manager.validate_new_position("BTC-USD", 1000, portfolio_value) is False
    assert risk_manager.calculate_position_size(portfolio_value, 0.2) == 0.0

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

@pytest.mark.asyncio
async def test_emergency_state_reset(emergency_manager):
    """Test emergency state reset functionality"""
    # Set emergency state
    emergency_manager.emergency_shutdown = True
    emergency_manager.shutdown_requested = True
    emergency_manager.system_health_checks['websocket_health'] = False
    
    # Reset emergency state
    emergency_manager.reset_emergency_state()
    
    # Verify reset
    assert emergency_manager.emergency_shutdown is False
    assert emergency_manager.shutdown_requested is False
    assert all(emergency_manager.system_health_checks.values())

@pytest.mark.asyncio
async def test_full_shutdown_sequence(emergency_manager):
    """Test complete shutdown sequence with all components"""
    positions = {
        'BTC-USD': {'quantity': 1.0},
        'ETH-USD': {'quantity': 2.0}
    }
    
    successful_trades = set()
    
    async def mock_execute_trade(pair, **kwargs):
        successful_trades.add(pair)
        return True
    
    mock_websocket = AsyncMock()
    
    # Execute shutdown
    await emergency_manager.initiate_emergency_shutdown(
        positions,
        mock_execute_trade,
        mock_websocket
    )
    
    # Verify all positions were handled
    assert successful_trades == {'BTC-USD', 'ETH-USD'}
    assert mock_websocket.stop.called
    assert emergency_manager.emergency_shutdown is True
    
    # Verify system health status
    health = emergency_manager.get_system_health()
    assert health['emergency_mode'] is True
    assert not health['system_checks']['websocket_health']  # WebSocket should be marked as unhealthy after stop
