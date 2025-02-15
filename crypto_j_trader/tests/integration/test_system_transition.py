"""Integration tests for system transition validation"""
import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

@pytest.fixture
async def system_components(test_config):
    """Create core system components for testing"""
    from crypto_j_trader.src.trading.trading_core import TradingBot
    from crypto_j_trader.src.trading.health_monitor import HealthMonitor
    from crypto_j_trader.src.trading.emergency_manager import EmergencyManager
    from crypto_j_trader.src.trading.paper_trading import PaperTrader
    
    health_monitor = HealthMonitor()
    emergency_manager = EmergencyManager(test_config)
    paper_trader = PaperTrader(test_config)
    trading_bot = TradingBot(
        config=test_config,
        health_monitor=health_monitor,
        emergency_manager=emergency_manager
    )
    
    return trading_bot, health_monitor, emergency_manager, paper_trader

@pytest.mark.asyncio
async def test_system_transition(system_components):
    """Test seamless system state transition"""
    trading_bot, health_monitor, emergency_manager, paper_trader = system_components
    
    # Verify initial state
    assert trading_bot.is_healthy
    assert not emergency_manager.emergency_mode
    
    # Execute test trade
    result = await trading_bot.execute_order('buy', 1.0, 50000.0, 'BTC-USD')
    assert result['status'] == 'filled'
    
    position = await trading_bot.get_position('BTC-USD')
    assert position['size'] == Decimal('1.0')
    
    # Verify health metrics recorded
    health = await trading_bot.check_health()
    assert isinstance(health, dict)
    assert health['status'] == 'healthy'

@pytest.mark.asyncio
async def test_component_synchronization(system_components):
    """Test component state synchronization"""
    trading_bot, health_monitor, emergency_manager, paper_trader = system_components
    
    # Record test metrics
    await health_monitor.record_latency('test', 50)
    await health_monitor.record_error('test_error')
    
    # Verify metrics persistence
    metrics = health_monitor.get_current_metrics()
    assert 'latency' in metrics
    assert metrics['latency'] >= 0