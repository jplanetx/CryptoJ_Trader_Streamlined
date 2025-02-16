"""Integration tests for emergency management functionality"""
import pytest
import asyncio
from decimal import Decimal
from typing import Dict, Any
from datetime import datetime
from crypto_j_trader.src.trading.emergency_manager import EmergencyManager

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

class TestEmergencyManager:
    @pytest.fixture
    def emergency_manager(self, config_emergency: Dict[str, Any]) -> EmergencyManager:
        """Create EmergencyManager instance for testing"""
        em = EmergencyManager(config=config_emergency)
        asyncio.run(em.reset_emergency_state())
        return em

    async def setup_method(self):
        """Setup method to reset state before each test"""
        if hasattr(self, 'emergency_manager'):
            await self.emergency_manager.reset_emergency_state()

    @pytest.mark.asyncio
    async def test_validate_new_position(self, emergency_manager: EmergencyManager) -> None:
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
    async def test_emergency_shutdown(self, emergency_manager: EmergencyManager) -> None:
        """Test emergency shutdown functionality"""
        # Trigger shutdown
        await emergency_manager.emergency_shutdown()
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
        assert loaded_state.get('emergency_mode') is True

    @pytest.mark.asyncio
    async def test_system_health(self, emergency_manager: EmergencyManager) -> None:
        """Test system health monitoring"""
        health_status = await emergency_manager.get_system_health()
        assert isinstance(health_status, dict)
        assert 'status' in health_status
        assert 'last_check' in health_status
        assert 'metrics' in health_status

    @pytest.mark.asyncio
    async def test_risk_controls(self, emergency_manager: EmergencyManager) -> None:
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