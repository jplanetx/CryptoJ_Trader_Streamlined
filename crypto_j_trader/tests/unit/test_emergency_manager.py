import pytest
import json
import os
from decimal import Decimal
from typing import Any, Dict

from crypto_j_trader.src.trading import EmergencyManager

@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Fixture providing test configuration."""
    return {
        "position_limit": 50000,
        "state_file": "test_emergency_state.json",
        "risk_factor": 0.02
    }

@pytest.fixture
def emergency_manager(mock_config) -> EmergencyManager:
    """Fixture providing EmergencyManager instance."""
    return EmergencyManager(config=mock_config)

@pytest.mark.asyncio
async def test_check_system_health(emergency_manager):
    """Test system health check functionality."""
    health_status = await emergency_manager.check_system_health()
    
    assert isinstance(health_status, dict)
    assert "healthy" in health_status
    assert "latency" in health_status
    assert "market_data_fresh" in health_status
    assert "position_limit" in health_status
    assert health_status["position_limit"] == 50000

@pytest.mark.asyncio
async def test_save_emergency_state(emergency_manager, mock_config):
    """Test emergency state persistence."""
    result = await emergency_manager.save_emergency_state()
    assert result is True
    
    # Verify file was created and contains expected data
    file_path = mock_config["state_file"]
    assert os.path.exists(file_path)
    
    with open(file_path, "r") as f:
        saved_state = json.load(f)
    
    assert "emergency_mode" in saved_state
    assert saved_state["emergency_mode"] is False
    assert saved_state["config"] == mock_config
    
    # Cleanup
    os.remove(file_path)

@pytest.mark.asyncio
async def test_calculate_position_size(emergency_manager):
    """Test position size calculation."""
    available_funds = 100000.0
    risk_factor = 0.02
    
    position_size = await emergency_manager.calculate_position_size(
        available_funds=available_funds,
        risk_factor=risk_factor
    )
    
    expected_size = available_funds * risk_factor
    assert position_size == expected_size

@pytest.mark.asyncio
async def test_system_health_error_handling(emergency_manager):
    """Test error handling in system health check."""
    # Force an error by setting market_data to an invalid value
    emergency_manager.market_data = "invalid"
    
    health_status = await emergency_manager.check_system_health()
    assert health_status["healthy"] is False
    assert "error" in health_status

@pytest.mark.asyncio
async def test_save_state_error_handling(emergency_manager):
    """Test error handling in state persistence."""
    # Force an error by setting an invalid file path
    emergency_manager.config["state_file"] = "/invalid/path/state.json"
    
    result = await emergency_manager.save_emergency_state()
    assert result is False

@pytest.mark.asyncio
async def test_position_size_error_handling(emergency_manager):
    """Test error handling in position size calculation."""
    result = await emergency_manager.calculate_position_size(
        available_funds="invalid",
        risk_factor=0.02
    )
    assert result == 0.0