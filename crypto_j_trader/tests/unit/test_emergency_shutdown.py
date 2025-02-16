import pytest
import json
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch, Mock
from typing import Dict, Any, Optional
from ...src.trading.emergency_manager import EmergencyManager

@pytest.fixture
def config_file(tmp_path) -> Dict[str, Any]:
    """Create a temporary config file."""
    return {
        'emergency_thresholds': {
            'position_limit': Decimal('50000'),
            'risk_factor': Decimal('0.02'),
            'max_latency': 1000,
            'market_data_max_age': 60,
            'min_available_funds': Decimal('1000.0')
        },
        'trading': {
            'max_position_size': Decimal('100000'),
            'min_order_size': Decimal('10.0')
        },
        'monitoring': {
            'health_check_interval': 60,
            'state_save_interval': 300
        }
    }

@pytest.fixture
def state_file(tmp_path) -> str:
    """Create a temporary state file path."""
    return str(tmp_path / "test_emergency_state.json")

@pytest.fixture
def emergency_manager(config_file: Dict[str, Any], state_file: str) -> EmergencyManager:
    return EmergencyManager(config=config_file, state_file=state_file)

@pytest.mark.asyncio
async def test_validate_new_position_normal(emergency_manager: EmergencyManager) -> None:
    """Test position validation under normal conditions."""
    result = await emergency_manager.validate_new_position(
        trading_pair='BTC-USD',
        size=Decimal('1.0'),
        price=Decimal('40000.0')
    )
    assert result is True

@pytest.mark.asyncio
async def test_validate_new_position_emergency_mode(emergency_manager: EmergencyManager) -> None:
    """Test position validation during emergency mode."""
    emergency_manager.emergency_mode = True
    result = await emergency_manager.validate_new_position(
        trading_pair='BTC-USD',
        size=Decimal('1.0'),
        price=Decimal('40000.0')
    )
    assert result is False

@pytest.mark.asyncio
async def test_validate_new_position_exceeds_limit(emergency_manager: EmergencyManager) -> None:
    """Test position validation when exceeding position limits."""
    result = await emergency_manager.validate_new_position(
        trading_pair='BTC-USD',
        size=Decimal('60.0'),  # Exceeds configured limit
        price=Decimal('40000.0')
    )
    assert result is False

@pytest.mark.asyncio
async def test_validate_new_position_exceeds_risk(emergency_manager: EmergencyManager) -> None:
    """Test position validation when exceeding risk limits."""
    result = await emergency_manager.validate_new_position(
        trading_pair='BTC-USD',
        size=Decimal('25.0'),  # High value position
        price=Decimal('40000.0')
    )
    assert result is False

@pytest.mark.asyncio
async def test_emergency_shutdown(emergency_manager: EmergencyManager) -> None:
    """Test emergency shutdown procedure."""
    await emergency_manager.emergency_shutdown()
    assert emergency_manager.emergency_mode is True
    assert emergency_manager.position_limits == {}
    
    # Verify state persistence
    with open(emergency_manager.state_file) as f:
        state = json.load(f)
        assert state['emergency_mode'] is True

@pytest.mark.asyncio
async def test_restore_normal_operation(emergency_manager: EmergencyManager) -> None:
    """Test restoration of normal operation."""
    emergency_manager.emergency_mode = True
    result = await emergency_manager.restore_normal_operation()
    
    assert result is True
    assert emergency_manager.emergency_mode is False

def test_update_position_limits(emergency_manager: EmergencyManager) -> None:
    """Test position limit updates."""
    new_limits = {
        'BTC-USD': Decimal('5.0'),
        'ETH-USD': Decimal('50.0')
    }
    emergency_manager.update_position_limits(new_limits)
    
    assert emergency_manager.position_limits['BTC-USD'] == Decimal('5.0')
    assert emergency_manager.position_limits['ETH-USD'] == Decimal('50.0')

def test_get_system_health(emergency_manager: EmergencyManager) -> None:
    """Test system health status retrieval."""
    emergency_manager.position_limits = {
        'BTC-USD': Decimal('5.0'),
        'ETH-USD': Decimal('50.0')
    }
    
    health_status = emergency_manager.get_system_health()
    
    assert 'emergency_mode' in health_status
    assert 'position_limits' in health_status
    assert isinstance(health_status['position_limits']['BTC-USD'], float)

def test_load_invalid_config(tmp_path) -> None:
    """Test handling of invalid configuration file."""
    invalid_config = tmp_path / "invalid_config.json"
    with open(invalid_config, 'w') as f:
        f.write("invalid json")
    
    with pytest.raises(Exception):
        EmergencyManager(str(invalid_config))

@pytest.mark.asyncio
async def test_emergency_shutdown_persistence(emergency_manager: EmergencyManager) -> None:
    """Test persistence of emergency state during shutdown."""
    await emergency_manager.emergency_shutdown()
    
    # Create new instance with same state file
    new_manager = EmergencyManager(
        config_file,
        emergency_manager.state_file
    )
    
    assert new_manager.emergency_mode is True
    assert new_manager.position_limits == {}

@pytest.mark.asyncio
async def test_system_health_monitoring(emergency_manager: EmergencyManager) -> None:
    """Test system health monitoring during operations."""
    # Test normal operation
    health_before = emergency_manager.get_system_health()
    assert health_before['emergency_mode'] is False
    
    # Test after emergency
    await emergency_manager.emergency_shutdown()
    health_after = emergency_manager.get_system_health()
    assert health_after['emergency_mode'] is True
    
    # Test after restoration
    await emergency_manager.restore_normal_operation()
    health_restored = emergency_manager.get_system_health()
    assert health_restored['emergency_mode'] is False

def test_invalid_position_limits(emergency_manager: EmergencyManager) -> None:
    """Test handling of invalid position limits."""
    with pytest.raises(ValueError):
        emergency_manager.update_position_limits({
            'BTC-USD': Decimal('-1.0')  # Negative value should raise error
        })

@pytest.mark.asyncio
async def test_verify_system_health(emergency_manager: EmergencyManager) -> None:
    """Test system health verification."""
    # Test with all necessary data
    assert await emergency_manager._verify_system_health() is True
    
    # Test with missing risk limits
    emergency_manager.risk_limits = {}
    assert await emergency_manager._verify_system_health() is False

"""Unit tests for emergency shutdown functionality"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from ...src.trading.emergency_manager import EmergencyManager

@pytest.fixture
def emergency_config() -> Dict[str, Any]:
    """Test configuration for emergency shutdown"""
    return {
        'max_positions': {
            'BTC-USD': Decimal('50000'),
            'ETH-USD': Decimal('25000')
        },
        'risk_limits': {
            'BTC-USD': Decimal('100000'),
            'ETH-USD': Decimal('50000')
        },
        'emergency_thresholds': {
            'max_latency': 1000,
            'market_data_max_age': 60,
            'min_available_funds': Decimal('1000.0')
        }
    }

@pytest.mark.asyncio
async def test_get_system_health(emergency_config: Dict[str, Any]) -> None:
    """Test system health check during normal operation"""
    manager = EmergencyManager(emergency_config)
    health = await manager.get_system_health()
    assert health['status'] == 'healthy'
    assert 'last_check' in health
    assert 'metrics' in health

@pytest.mark.asyncio
async def test_emergency_shutdown_persistence(emergency_config: Dict[str, Any]) -> None:
    """Test emergency state persistence"""
    manager = EmergencyManager(emergency_config)
    
    # Trigger shutdown
    manager.emergency_shutdown = True
    await manager.save_state()
    
    # Create new instance to test loading
    new_manager = EmergencyManager(emergency_config)
    assert new_manager.emergency_shutdown is True

@pytest.mark.asyncio
async def test_system_health_monitoring(emergency_config: Dict[str, Any]) -> None:
    """Test health monitoring triggers"""
    manager = EmergencyManager(emergency_config)
    
    # Simulate high latency
    manager.last_latency = 2000  # Above threshold
    health = await manager.get_system_health()
    assert health['status'] == 'warning'

@pytest.mark.asyncio
async def test_invalid_position_limits(emergency_config: Dict[str, Any]) -> None:
    """Test position limit validation"""
    manager = EmergencyManager(emergency_config)
    
    with pytest.raises(ValueError):
        await manager.validate_new_position(
            trading_pair="BTC-USD",
            size=Decimal('-1.0'),
            price=Decimal('50000.0')
        )

@pytest.mark.asyncio
async def test_verify_system_health(emergency_config: Dict[str, Any]) -> None:
    """Test system health verification"""
    manager = EmergencyManager(emergency_config)
    status = await manager.verify_system_health()
    assert status is True  # System should be healthy by default