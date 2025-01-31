import pytest
import numpy as np
from crypto_j_trader.src.trading.risk_management import RiskManager

@pytest.fixture
def risk_config():
    return {
        'risk_management': {
            'daily_loss_limit': 0.02,
            'position_size_limit': 0.1,
            'stop_loss_pct': 0.05,
            'correlation_weight': 0.3,
            'volatility_weight': 0.4,
            'min_position_size': 0.02,
            'max_positions': 5,
            'max_exposure': 0.5
        }
    }

@pytest.fixture
def risk_manager(risk_config):
    return RiskManager(risk_config)

def test_calculate_atr():
    risk_manager = RiskManager({'risk_management': {}})
    
    # Test data
    high_prices = np.array([10.0, 11.0, 10.5, 11.5, 12.0])
    low_prices = np.array([9.0, 9.5, 9.0, 10.0, 10.5])
    close_prices = np.array([9.5, 10.0, 9.5, 11.0, 11.5])
    
    atr = risk_manager.calculate_atr(high_prices, low_prices, close_prices, period=3)
    assert atr > 0
    assert isinstance(atr, float)

def test_calculate_correlation_risk():
    risk_manager = RiskManager({'risk_management': {}})
    
    # Test data - 3 assets, 5 time periods
    returns = np.array([
        [0.01, 0.02, 0.01],
        [0.02, 0.02, 0.02],
        [-0.01, -0.01, -0.01],
        [0.01, 0.015, 0.01],
        [0.02, 0.025, 0.02]
    ])
    
    correlation = risk_manager.calculate_correlation_risk(returns)
    assert -1 <= correlation <= 1
    assert isinstance(correlation, float)

def test_dynamic_stop_loss():
    risk_manager = RiskManager({'risk_management': {'stop_loss_pct': 0.05}})
    
    entry_price = 100.0
    high_prices = np.array([102.0, 103.0, 101.0, 104.0, 105.0])
    low_prices = np.array([98.0, 99.0, 97.0, 100.0, 101.0])
    close_prices = np.array([100.0, 101.0, 98.0, 103.0, 104.0])
    
    # Test with market data
    dynamic_stop = risk_manager.calculate_stop_loss(
        entry_price, high_prices, low_prices, close_prices
    )
    assert dynamic_stop < entry_price
    assert isinstance(dynamic_stop, float)
    
    # Test fallback without market data
    fallback_stop = risk_manager.calculate_stop_loss(entry_price)
    assert fallback_stop == entry_price * (1 - 0.05)

def test_position_sizing_with_correlation():
    risk_manager = RiskManager({'risk_management': {
        'position_size_limit': 0.1,
        'correlation_weight': 0.3,
        'volatility_weight': 0.4,
        'min_position_size': 0.02,
        'max_exposure': 0.5
    }})
    
    portfolio_value = 10000
    volatility = 0.2
    
    # Test data - 2 assets, 5 time periods
    correlation_matrix = np.array([
        [0.01, 0.015],
        [0.02, 0.02],
        [-0.01, -0.01],
        [0.01, 0.012],
        [0.02, 0.022]
    ])
    
    # Test with correlation data
    position_size = risk_manager.calculate_position_size(
        portfolio_value, volatility, correlation_matrix
    )
    assert position_size > 0
    assert position_size <= portfolio_value * risk_manager.position_size_limit
    assert position_size >= portfolio_value * risk_manager.min_position_size
    
    # Test without correlation data
    basic_position_size = risk_manager.calculate_position_size(portfolio_value, volatility)
    assert basic_position_size > 0
    assert basic_position_size <= portfolio_value * risk_manager.position_size_limit

def test_daily_loss_tracking():
    risk_manager = RiskManager({'risk_management': {'daily_loss_limit': 0.02}})
    portfolio_value = 10000
    
    # Test within limit
    risk_manager.update_daily_loss(-100)  # -1%
    assert risk_manager.check_daily_loss_limit(portfolio_value) is True
    
    # Test exceeding limit
    risk_manager.update_daily_loss(-150)  # Additional -1.5%
    assert risk_manager.check_daily_loss_limit(portfolio_value) is False

def test_position_count_limits(risk_manager):
    portfolio_value = 10000
    position_size = 500  # 5% each
    
    # Add positions up to limit
    for i in range(risk_manager.max_positions):
        symbol = f"COIN{i}"
        assert risk_manager.validate_new_position(symbol, position_size, portfolio_value) is True
        risk_manager.update_position(symbol, position_size)
    
    # Try to add one more position
    assert risk_manager.validate_new_position("EXTRA", position_size, portfolio_value) is False
    
    # Update existing position should be allowed
    assert risk_manager.validate_new_position("COIN0", position_size * 1.5, portfolio_value) is True

def test_exposure_limits(risk_manager):
    portfolio_value = 10000
    position_size = 2000  # 20% each
    
    # Add positions up to exposure limit
    symbols = ["COIN1", "COIN2"]
    for symbol in symbols:
        assert risk_manager.validate_new_position(symbol, position_size, portfolio_value) is True
        risk_manager.update_position(symbol, position_size)
    
    # Try to add position that would exceed exposure limit
    assert risk_manager.validate_new_position("COIN3", position_size, portfolio_value) is False
    
    # Verify total exposure
    assert risk_manager.get_total_exposure() == position_size * len(symbols)

def test_emergency_mode(risk_manager):
    portfolio_value = 10000
    position_size = 500
    
    # Test normal operation
    assert risk_manager.validate_new_position("COIN1", position_size, portfolio_value) is True
    
    # Enable emergency mode
    risk_manager.set_emergency_mode(True)
    
    # Verify no new positions allowed
    assert risk_manager.validate_new_position("COIN2", position_size, portfolio_value) is False
    
    # Verify position sizing returns 0 in emergency mode
    assert risk_manager.calculate_position_size(portfolio_value, 0.2) == 0.0
    
    # Disable emergency mode
    risk_manager.set_emergency_mode(False)
    
    # Verify normal operation restored
    assert risk_manager.validate_new_position("COIN3", position_size, portfolio_value) is True

def test_position_size_validation(risk_manager):
    portfolio_value = 10000
    
    # Test position within limits
    valid_size = portfolio_value * risk_manager.position_size_limit * 0.5
    assert risk_manager.validate_new_position("COIN1", valid_size, portfolio_value) is True
    
    # Test position exceeding individual limit
    invalid_size = portfolio_value * risk_manager.position_size_limit * 1.5
    assert risk_manager.validate_new_position("COIN2", invalid_size, portfolio_value) is False
    
    # Test updating position
    risk_manager.update_position("COIN1", valid_size)
    assert "COIN1" in risk_manager.active_positions
    assert risk_manager.active_positions["COIN1"] == valid_size
    
    # Test closing position
    risk_manager.update_position("COIN1", 0)
    assert "COIN1" not in risk_manager.active_positions