"""Unit tests for position management system."""
import pytest
import numpy as np
from crypto_j_trader.src.trading.position_manager import PositionManager

@pytest.fixture
def test_config():
    return {
        'risk_per_trade': 0.02,
        'position_limits': {
            'max_position_value': 10000.0,
            'max_leverage': 3.0,
            'min_position_size': 0.001
        },
        'size_precision': {
            'BTC-USD': 8,
            'ETH-USD': 6
        }
    }

@pytest.fixture
def position_manager(test_config):
    return PositionManager(test_config)

class TestPositionManager:
    def test_initialization(self, position_manager, test_config):
        """Test position manager initialization."""
        assert position_manager.config == test_config
        assert isinstance(position_manager.positions, dict)
        assert isinstance(position_manager.volatility_windows, dict)

    def test_calculate_position_size(self, position_manager):
        """Test position size calculation."""
        # Test normal case
        size = position_manager.calculate_position_size(
            'BTC-USD',
            account_value=100000.0,
            current_price=50000.0,
            volatility=0.5
        )
        assert size > 0
        assert size <= (100000.0 / 50000.0)  # Cannot be larger than account value

        # Test with high volatility
        high_vol_size = position_manager.calculate_position_size(
            'BTC-USD',
            account_value=100000.0,
            current_price=50000.0,
            volatility=1.0
        )
        assert high_vol_size < size  # Should reduce size with higher volatility

        # Test with small account value
        small_size = position_manager.calculate_position_size(
            'BTC-USD',
            account_value=100.0,
            current_price=50000.0,
            volatility=0.5
        )
        assert small_size == 0.0  # Should be zero if too small

    def test_calculate_volatility(self, position_manager):
        """Test volatility calculation."""
        # Generate sample price history
        price_history = [100.0 * (1 + 0.01 * i) for i in range(30)]
        
        # Test with sufficient history
        vol = position_manager.calculate_volatility('BTC-USD', price_history)
        assert vol > 0
        assert vol < 1.0  # Should be reasonable for our test data

        # Test with insufficient history
        short_history = price_history[:10]
        vol = position_manager.calculate_volatility('BTC-USD', short_history)
        assert vol == 0.0

        # Test with volatile prices
        volatile_prices = [100.0 * (1 + 0.1 * np.sin(i)) for i in range(30)]
        high_vol = position_manager.calculate_volatility('BTC-USD', volatile_prices)
        assert high_vol > vol  # Should be higher for more volatile prices

    def test_update_volatility_window(self, position_manager):
        """Test volatility window updates."""
        pair = 'BTC-USD'
        
        # Test initial update
        position_manager.update_volatility_window(pair, 50000.0)
        assert pair in position_manager.volatility_windows
        assert len(position_manager.volatility_windows[pair]) == 1

        # Test window limit
        for i in range(200):  # More than max window
            position_manager.update_volatility_window(pair, 50000.0 + i)
        assert len(position_manager.volatility_windows[pair]) == 100  # Max window size

    def test_calculate_dynamic_take_profit(self, position_manager):
        """Test dynamic take-profit calculations."""
        result = position_manager.calculate_dynamic_take_profit(
            'BTC-USD',
            entry_price=50000.0,
            position_size=1.0,
            volatility=0.5
        )
        
        assert 'levels' in result
        assert 'volatility_multiplier' in result
        assert len(result['levels']) > 0
        
        # Check level structure
        for level in result['levels']:
            assert 'pct' in level
            assert 'size' in level
            assert 'price' in level
            assert 'quantity' in level
            assert level['price'] > 50000.0  # Take profit should be above entry

        # Test with higher volatility
        high_vol_result = position_manager.calculate_dynamic_take_profit(
            'BTC-USD',
            entry_price=50000.0,
            position_size=1.0,
            volatility=1.0
        )
        assert high_vol_result['volatility_multiplier'] > result['volatility_multiplier']

    def test_validate_position_risk(self, position_manager):
        """Test position risk validation."""
        # Test valid position
        result = position_manager.validate_position_risk(
            'BTC-USD',
            new_position_size=0.1,
            current_price=50000.0,
            account_value=100000.0
        )
        assert result['valid']
        assert not result['messages']

        # Test position value limit
        large_result = position_manager.validate_position_risk(
            'BTC-USD',
            new_position_size=10.0,  # Very large position
            current_price=50000.0,
            account_value=100000.0
        )
        assert not large_result['valid']
        assert any('value' in msg.lower() for msg in large_result['messages'])

        # Test leverage limit
        leverage_result = position_manager.validate_position_risk(
            'BTC-USD',
            new_position_size=7.0,
            current_price=50000.0,
            account_value=100000.0
        )
        assert not leverage_result['valid']
        assert any('leverage' in msg.lower() for msg in leverage_result['messages'])
