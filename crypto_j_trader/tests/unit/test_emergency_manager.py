import pytest
import json
import os
import tempfile
from decimal import Decimal
from typing import Any, Dict
from pathlib import Path

from crypto_j_trader.src.trading import EmergencyManager

@pytest.fixture
def mock_config(emergency_config) -> Dict[str, Any]:
    """Fixture providing test configuration."""
    return {
        "max_positions": {
            "BTC-USD": 50000,
            "ETH-USD": 25000
        },
        "risk_limits": {
            "BTC-USD": 50000,  # Increased from 10000 to allow test position
            "ETH-USD": 25000
        },
        "emergency_thresholds": {
            "max_latency": 1000,
            "market_data_max_age": 60,
            "min_available_funds": 1000.0
        },
        "position_limit": 50000,
        "state_file": "test_emergency_state.json",
        "risk_factor": 0.02
    }

@pytest.fixture
def temp_dir():
    """Fixture providing a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture
def emergency_manager(mock_config, temp_dir) -> EmergencyManager:
    """Fixture providing EmergencyManager instance."""
    state_file = os.path.join(temp_dir, mock_config["state_file"])
    manager = EmergencyManager(config=mock_config, state_file=state_file)
    return manager

@pytest.mark.asyncio
async def test_validate_new_position(emergency_manager):
    """Test position validation functionality."""
    # Test valid position with realistic values
    valid = await emergency_manager.validate_new_position(
        trading_pair="BTC-USD",
        size=0.5,  # Reduced size
        price=40000.0
    )
    assert valid is True, "Valid position should be accepted"
    
    # Test invalid position (exceeds limit)
    invalid = await emergency_manager.validate_new_position(
        trading_pair="BTC-USD",
        size=2.0,
        price=30000.0
    )
    assert invalid is False, "Position exceeding limits should be rejected"

@pytest.mark.asyncio
async def test_emergency_shutdown(emergency_manager):
    """Test emergency shutdown functionality."""
    # Initial state
    assert emergency_manager.emergency_mode is False
    
    # Perform shutdown
    await emergency_manager.emergency_shutdown()
    
    # Verify system entered emergency mode
    assert emergency_manager.emergency_mode is True
    
    # Verify state was saved
    assert Path(emergency_manager.state_file).exists()
    
    with open(emergency_manager.state_file) as f:
        state = json.load(f)
    assert state["emergency_mode"] is True

@pytest.mark.asyncio
async def test_restore_normal_operation(emergency_manager):
    """Test restoration of normal operation."""
    # First put system in emergency mode
    await emergency_manager.emergency_shutdown()
    assert emergency_manager.emergency_mode is True
    
    # Attempt restoration
    success = await emergency_manager.restore_normal_operation()
    assert success is True
    assert emergency_manager.emergency_mode is False

def test_get_system_health(emergency_manager):
    """Test system health status retrieval."""
    health_status = emergency_manager.get_system_health()
    
    assert isinstance(health_status, dict)
    assert "emergency_mode" in health_status
    assert "position_limits" in health_status
    assert "exposure_percentages" in health_status
    assert "timestamp" in health_status

def test_update_position_limits(emergency_manager):
    """Test position limit updates."""
    new_limits = {
        "BTC-USD": 60000,
        "ETH-USD": 30000
    }
    
    emergency_manager.update_position_limits(new_limits)
    
    # Verify limits were updated
    health_status = emergency_manager.get_system_health()
    assert "BTC-USD" in health_status["position_limits"]
    assert float(health_status["position_limits"]["BTC-USD"]) == 60000.0

@pytest.mark.asyncio
async def test_emergency_state_persistence(emergency_manager, temp_dir):
    """Test emergency state persistence."""
    # Update some state
    emergency_manager.update_position_limits({"BTC-USD": 70000})
    
    # Save state explicitly
    emergency_manager._save_state()
    
    # Create new manager instance with same state file
    new_manager = EmergencyManager(
        config=emergency_manager.config,  # Use the stored configuration
        state_file=emergency_manager.state_file
    )
    
    # Verify state was loaded
    health = new_manager.get_system_health()
    assert float(health["position_limits"]["BTC-USD"]) == 70000.0

def test_reset_emergency_state(emergency_manager):
    """Test emergency state reset."""
    # Set some state
    emergency_manager.update_position_limits({"BTC-USD": 70000})
    
    # Reset state
    emergency_manager.reset_emergency_state()
    
    # Verify reset
    assert emergency_manager.emergency_mode is False
    health = emergency_manager.get_system_health()
    assert len(health["position_limits"]) == 0

@pytest.mark.asyncio
async def test_trigger_emergency_shutdown(emergency_manager):
    """Test triggering emergency shutdown based on thresholds."""
    # Simulate conditions that trigger emergency shutdown
    emergency_manager.max_positions["BTC-USD"] = Decimal('50000')  # Use Decimal for consistency

    # Key Change: Set the current position *exactly* at the limit
    emergency_manager.position_limits["BTC-USD"] = Decimal('50000') 

    # Validate a new position, even a tiny one, should trigger shutdown.
    # Important: Must use price > 0.  If price is zero, validation will pass due to 0 value.
    await emergency_manager.validate_new_position("BTC-USD", 0.001, 1.0)  # tiny size, price=1
    
    # Verify emergency mode is triggered
    assert emergency_manager.emergency_mode is True

@pytest.mark.asyncio
async def test_close_positions(emergency_manager):
    """Test closing positions during emergency."""
    # Simulate open positions
    emergency_manager.position_limits["BTC-USD"] = Decimal('60000')
    
    # Close positions
    await emergency_manager.close_positions()
    
    # Verify positions are closed
    assert emergency_manager.position_limits["BTC-USD"] == Decimal('0')

@pytest.mark.asyncio
async def test_system_state_management(emergency_manager):
    """Test system state management during emergency and recovery."""
    # Simulate emergency state
    await emergency_manager.emergency_shutdown()
    assert emergency_manager.emergency_mode is True
    
    # Restore normal operation
    success = await emergency_manager.restore_normal_operation()
    assert success is True
    assert emergency_manager.emergency_mode is False