"""Integration tests for emergency management functionality"""
import pytest
import asyncio
from decimal import Decimal
from typing import Dict, Any
from datetime import datetime
from ...src.trading.emergency_manager import EmergencyManager

@pytest.fixture
def config_emergency() -> Dict[str, Any]:
    """Test configuration for emergency manager"""
    return {
        'trading_pairs': ['BTC-USD', 'ETH-USD'],
        'risk_management': {
            'max_position_size': Decimal('5.0'),
            'max_daily_loss': Decimal('500.0'),
            'stop_loss_pct': Decimal('0.05'),
            'position_size_limit': Decimal('50000.0')
        },
        'emergency_thresholds': {
            'max_latency': 1000,
            'market_data_max_age': 60,
            'min_available_funds': 1000.0
        },
        'state_file': "test_emergency_state.json"
    }

@pytest.fixture
def emergency_manager(config_emergency: Dict[str, Any]) -> EmergencyManager:
    """Create EmergencyManager instance for testing"""
    return EmergencyManager(config=config_emergency)

@pytest.mark.asyncio
async def test_validate_new_position(emergency_manager: EmergencyManager) -> None:
    """Test position validation functionality"""
    # Test valid position
    result = await emergency_manager.validate_new_position(
        trading_pair="BTC-USD",
        size=1.0,
        price=40000.0
    )
    assert result is True, "Valid position should be accepted"

    # Test exceeding position limit
    result = await emergency_manager.validate_new_position(
        trading_pair="BTC-USD",
        size=60.0,
        price=40000.0
    )
    assert result is False, "Position exceeding limits should be rejected"

@pytest.mark.asyncio
async def test_emergency_shutdown(emergency_manager: EmergencyManager) -> None:
    """Test emergency shutdown functionality"""
    # Trigger shutdown
    emergency_manager.emergency_shutdown = True
    await emergency_manager.save_state()
    
    # Validate positions are rejected during shutdown
    result = await emergency_manager.validate_new_position(
        trading_pair="BTC-USD",
        size=1.0,
        price=40000.0
    )
    assert result is False, "Positions should be rejected during shutdown"

    # Verify state persistence
    loaded_state = await emergency_manager.load_state()
    assert loaded_state.get('emergency_shutdown') is True

@pytest.mark.asyncio
async def test_system_health(emergency_manager: EmergencyManager) -> None:
    """Test system health monitoring"""
    health_status = await emergency_manager.get_system_health()
    assert isinstance(health_status, dict)
    assert 'status' in health_status
    assert 'last_check' in health_status
    assert 'metrics' in health_status

@pytest.mark.asyncio
async def test_risk_controls(emergency_manager: EmergencyManager) -> None:
    """Test risk control functionality"""
    # Test within limits
    result = await emergency_manager.validate_new_position(
        trading_pair="BTC-USD",
        size=1.0,
        price=40000.0
    )
    assert result is True

    # Test position value limit
    result = await emergency_manager.validate_new_position(
        trading_pair="BTC-USD",
        size=100.0,
        price=40000.0
    )
    assert result is False