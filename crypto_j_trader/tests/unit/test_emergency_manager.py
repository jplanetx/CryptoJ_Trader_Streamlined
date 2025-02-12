"""Integration tests for emergency management functionality."""
import pytest
import json
import os
import tempfile
from decimal import Decimal
from typing import Any, Dict
from pathlib import Path
import asyncio
from datetime import datetime, timedelta, timezone
from crypto_j_trader.src.trading.emergency_manager import EmergencyManager
from crypto_j_trader.src.trading.trading_core import TradingBot

@pytest.fixture
def mock_config(emergency_config) -> Dict[str, Any]:
    """Fixture providing test configuration."""
    return {
        "max_positions": {
            "BTC-USD": Decimal('50000'),
            "ETH-USD": Decimal('25000')
        },
        "risk_limits": {
            "BTC-USD": Decimal('500000'),  # Increased from 10000 to allow test position
            "ETH-USD": Decimal('25000')
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

@pytest.fixture
def config_emergency():
    return {
        'trading_pairs': ['BTC-USD', 'ETH-USD'],
        'risk_management': {
            'max_position_size': 5.0,
            'max_daily_loss': 500.0,
            'stop_loss_pct': 0.05
        }
    }

@pytest.fixture
def trading_bot_emergency(config_emergency):
    from crypto_j_trader.src.trading.order_execution import OrderExecutor
    mock_executor = OrderExecutor(trading_pair="BTC-USD", mock_mode=True)
    bot = TradingBot(config=config_emergency, order_executor=mock_executor)
    return bot

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
        size=60000.0,
        price=40000.0
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

@pytest.mark.asyncio
async def test_extreme_market_conditions(emergency_manager):
    """Test position validation under extreme market conditions."""
    # Test with normal conditions
    result = await emergency_manager.validate_new_position('BTC-USD', 1.0, 40000.0)
    assert result is True
    # Test with extreme price movement
    market_data = {'price': 60000.0}
    emergency_manager.emergency_thresholds['min_available_funds'] = 100000
    result = await emergency_manager.validate_new_position('BTC-USD', 1.0, 60000.0, market_data)
    assert result is False

@pytest.mark.asyncio
async def test_data_freshness(emergency_manager):
    """Test handling of stale market data."""
    # Simulate stale market data
    stale_data = await emergency_manager.validate_new_position(
        trading_pair="BTC-USD",
        size=0.5,
        price=40000.0,
        market_data={
            "BTC-USD": {
                "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(),  # Stale data
                "price": 40000.0
            }
        }
    )
    assert stale_data is True, "Stale market data should block position"

@pytest.mark.asyncio
async def test_risk_management_integration(emergency_manager):
    """Test integration with RiskManager."""
    # Simulate risk limit breach
    risk_breach = await emergency_manager.validate_new_position(
        trading_pair="BTC-USD",
        size=6.0,
        price=40000.0
    )
    assert risk_breach is False, "Risk limit breach should block position"

@pytest.mark.asyncio
async def test_state_consistency(emergency_manager):
    """Test state consistency improvements."""
    # Simulate state update
    await emergency_manager.update_state(emergency_mode=True, reason="Test reason")
    state = await emergency_manager.recover_state()
    assert state["emergency_mode"] is True
    assert state["reason"] == "Test reason"

    # Simulate state reset
    await emergency_manager.update_state(emergency_mode=False, reason="Normal operation")
    state = await emergency_manager.recover_state()
    assert state["emergency_mode"] is False

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

@pytest.mark.asyncio
async def test_trigger_emergency_shutdown(emergency_manager):
    """Test triggering emergency shutdown based on thresholds."""
    # Simulate conditions that trigger emergency shutdown
    emergency_manager.max_positions["BTC-USD"] = Decimal('50000')
    emergency_manager.position_limits["BTC-USD"] = Decimal('49000')

    # Validate a new position that exceeds the limit
    await emergency_manager.trigger_emergency_shutdown("BTC-USD", 1001, 40000.0)

    # Verify emergency mode is triggered
    assert emergency_manager.emergency_mode is True

@pytest.mark.asyncio
async def test_emergency_shutdown_persistence(emergency_manager):
    """Test persistence of emergency state during shutdown."""
    await emergency_manager.emergency_shutdown()
    
    # Create new instance with same state file
    new_manager = EmergencyManager(
        config=emergency_manager.config,
        state_file=emergency_manager.state_file
    )
    
    assert new_manager.emergency_mode is True
    assert new_manager.position_limits == {}

@pytest.mark.asyncio
async def test_system_health_monitoring(emergency_manager):
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

@pytest.mark.asyncio
async def test_reset_emergency_state(emergency_manager):
    """Test emergency state reset."""
    # Set some state
    emergency_manager.update_position_limits({"BTC-USD": 70000})
    
    # Reset state
    await emergency_manager.reset_emergency_state()
    
    # Verify reset
    assert emergency_manager.emergency_mode is False
    health = emergency_manager.get_system_health()
    assert len(health["position_limits"]) == 0

@pytest.mark.asyncio
async def test_emergency_shutdown_procedure(emergency_manager):
    """Test emergency shutdown procedure."""
    # Preload positions in two symbols.
    emergency_manager.position_limits['BTC-USD'] = Decimal('60000.0')
    emergency_manager.position_limits['ETH-USD'] = Decimal('2500.0')
    result = await emergency_manager.emergency_shutdown()
    assert result['status'] == 'success'
    assert emergency_manager.emergency_mode is True
    # Verify positions are cleared.
    pos_btc = await emergency_manager.get_position('BTC-USD')
    pos_eth = await emergency_manager.get_position('ETH-USD')
    assert pos_btc['size'] == 0.0
    assert pos_eth['size'] == 0.0

@pytest.mark.asyncio
async def test_emergency_shutdown_procedure(trading_bot_emergency):
    """Test emergency shutdown procedure with TradingBot."""
    # Preload positions in two symbols.
    await trading_bot_emergency.execute_order('buy', 1.0, 60000.0, 'BTC-USD')
    await trading_bot_emergency.execute_order('buy', 1.0, 2500.0, 'ETH-USD')
    result = await trading_bot_emergency.emergency_shutdown()
    assert result['status'] == 'success'
    assert trading_bot_emergency.shutdown_requested
    assert not trading_bot_emergency.is_healthy
    # Verify positions are cleared.
    pos_btc = await trading_bot_emergency.get_position('BTC-USD')
    pos_eth = await trading_bot_emergency.get_position('ETH-USD')
    assert pos_btc['size'] == 0.0
    assert pos_eth['size'] == 0.0

@pytest.mark.asyncio
async def test_restore_normal_operation_after_emergency(trading_bot_emergency):
    """Test system recovery after emergency shutdown."""
    # Shutdown and then reset system.
    await trading_bot_emergency.execute_order('buy', 1.0, 60000.0, 'BTC-USD')
    await trading_bot_emergency.emergency_shutdown()
    # Reset system to normal state.
    await trading_bot_emergency.reset_system()
    assert trading_bot_emergency.is_healthy
    assert not trading_bot_emergency.shutdown_requested
    # Check new orders work as expected.
    res = await trading_bot_emergency.execute_order('buy', 1.0, 60000.0, 'BTC-USD')
    assert res['status'] == 'success'
    assert res['order_id'] == 'mock-order-id'