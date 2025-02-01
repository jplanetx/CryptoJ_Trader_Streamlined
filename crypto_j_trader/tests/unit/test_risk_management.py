import pytest
import pandas as pd
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from crypto_j_trader.src.trading.risk_management import RiskManager
from crypto_j_trader.src.trading.market_data import MarketDataHandler

@pytest.fixture
def mock_market_data():
    market_data = MagicMock(spec=MarketDataHandler)
    market_data.is_running = True
    market_data.is_data_fresh.return_value = True
    return market_data

@pytest.fixture
def risk_manager(mock_market_data):
    return RiskManager(risk_threshold=10000.0, market_data=mock_market_data)

def test_validate_paper_trading_success(risk_manager, mock_market_data):
    """Test successful paper trading validation"""
    mock_market_data.get_market_snapshot.return_value = {
        'last_price': 50000.0,
        'order_book_depth': 20,
        'subscribed': True,
        'is_fresh': True
    }
    
    is_ready, reason = risk_manager.validate_paper_trading("BTC-USD")
    assert is_ready is True
    assert reason == "Ready for paper trading"

def test_validate_paper_trading_market_data_not_running(risk_manager, mock_market_data):
    """Test paper trading validation when market data is not running"""
    mock_market_data.is_running = False
    
    is_ready, reason = risk_manager.validate_paper_trading("BTC-USD")
    assert is_ready is False
    assert reason == "Market data handler not running"

def test_validate_paper_trading_stale_data(risk_manager, mock_market_data):
    """Test paper trading validation with stale market data"""
    mock_market_data.is_data_fresh.return_value = False
    
    is_ready, reason = risk_manager.validate_paper_trading("BTC-USD")
    assert is_ready is False
    assert reason == "Market data not fresh"

def test_validate_paper_trading_insufficient_depth(risk_manager, mock_market_data):
    """Test paper trading validation with insufficient order book depth"""
    mock_market_data.get_market_snapshot.return_value = {
        'last_price': 50000.0,
        'order_book_depth': 5,  # Below minimum required depth
        'subscribed': True,
        'is_fresh': True
    }
    
    is_ready, reason = risk_manager.validate_paper_trading("BTC-USD")
    assert is_ready is False
    assert reason == "Insufficient order book depth"

def test_assess_risk_success(risk_manager, mock_market_data):
    """Test successful risk assessment with stable market"""
    mock_market_data.get_market_snapshot.return_value = {
        'last_price': 50000.0,
        'order_book_depth': 20,
        'subscribed': True,
        'is_fresh': True
    }
    
    # Simulate stable market conditions
    mock_market_data.get_recent_trades.return_value = [
        {'price': 50000.0},
        {'price': 50100.0},
        {'price': 49900.0}
    ]
    
    assert risk_manager.assess_risk(5000.0, "BTC-USD") is True

def test_assess_risk_high_volatility(risk_manager, mock_market_data):
    """Test risk assessment with high market volatility"""
    mock_market_data.get_market_snapshot.return_value = {
        'last_price': 50000.0,
        'order_book_depth': 20,
        'subscribed': True,
        'is_fresh': True
    }
    
    # Simulate highly volatile market
    mock_market_data.get_recent_trades.return_value = [
        {'price': 50000.0},
        {'price': 52000.0},
        {'price': 48000.0}
    ]
    
    # Even with moderate position size, high volatility should trigger risk threshold
    assert risk_manager.assess_risk(8000.0, "BTC-USD") is False

def test_assess_risk_high_exposure(risk_manager, mock_market_data):
    """Test risk assessment with high position value - should fail when strictly exceeding threshold"""
    mock_market_data.get_market_snapshot.return_value = {
        'last_price': 50000.0,
        'order_book_depth': 20,
        'subscribed': True,
        'is_fresh': True
    }
    
    mock_market_data.get_recent_trades.return_value = [
        {'price': 50000.0},
        {'price': 51000.0},
        {'price': 49000.0}
    ]
    
    # Test exactly at threshold should pass
    assert risk_manager.assess_risk(9950.0, "BTC-USD") is True
    
    # Test exceeding threshold should fail
    assert risk_manager.assess_risk(10050.0, "BTC-USD") is False

def test_validate_order_insufficient_liquidity(risk_manager, mock_market_data):
    """Test order validation with insufficient liquidity - verify correct error message"""
    mock_market_data.get_order_book.return_value = {
        'bids': {'49000.0': '0.1', '48000.0': '0.1'},
        'asks': {'51000.0': '0.1', '52000.0': '0.1'}
    }
    
    # Order size larger than available liquidity (total liquidity = 0.2)
    is_valid, reason = risk_manager.validate_order("BTC-USD", 0.3, 50000.0)
    assert is_valid is False
    assert reason == "Order size exceeds safe liquidity threshold"

def test_validate_order_success(risk_manager, mock_market_data):
    """Test successful order validation"""
    mock_market_data.get_order_book.return_value = {
        'bids': {'49000.0': '1.0', '48000.0': '1.0'},
        'asks': {'51000.0': '1.0', '52000.0': '1.0'}
    }
    
    is_valid, reason = risk_manager.validate_order("BTC-USD", 0.1, 50000.0)
    assert is_valid is True
    assert reason == "Order validated"

def test_validate_order_edge_cases(risk_manager, mock_market_data):
    """Test order validation edge cases"""
    mock_market_data.get_order_book.return_value = {
        'bids': {'49000.0': '1.0', '48000.0': '1.0'},
        'asks': {'51000.0': '1.0', '52000.0': '1.0'}
    }
    
    # Test order at exactly max value
    max_size = risk_manager.max_order_value / 50000.0
    is_valid, reason = risk_manager.validate_order("BTC-USD", max_size, 50000.0)
    assert is_valid is True
    assert reason == "Order validated"
    
    # Test order slightly above max value
    is_valid, reason = risk_manager.validate_order("BTC-USD", max_size + 0.0001, 50000.0)
    assert is_valid is False
    assert "exceeds maximum" in reason

@pytest.mark.asyncio
async def test_validate_new_position_success(risk_manager, mock_market_data):
    """Test successful validation of a new position"""
    market_data = {
        "BTC-USD": pd.DataFrame({
            'price': [50000.0],
            'volume': [1.0]
        })
    }
    
    mock_market_data.get_recent_trades.return_value = [
        {'price': 50000.0},
        {'price': 50100.0},
        {'price': 49900.0}
    ]
    
    # Test with position within limits
    is_valid, reason = await risk_manager.validate_new_position(
        "BTC-USD",
        size=0.1,  # Small position
        portfolio_value=100000.0,  # Large portfolio
        market_data=market_data
    )
    assert is_valid is True
    assert reason == "Position validated"

@pytest.mark.asyncio
async def test_validate_new_position_emergency_mode(risk_manager):
    """Test position validation during emergency mode"""
    risk_manager.set_emergency_mode(True)
    
    is_valid, reason = await risk_manager.validate_new_position(
        "BTC-USD",
        size=0.1,
        portfolio_value=100000.0,
        market_data={"BTC-USD": pd.DataFrame({'price': [50000.0]})}
    )
    assert is_valid is False
    assert reason == "System is in emergency mode"

@pytest.mark.asyncio
async def test_validate_new_position_exceeds_limit(risk_manager, mock_market_data):
    """Test position validation when size exceeds portfolio percentage limit"""
    market_data = {
        "BTC-USD": pd.DataFrame({
            'price': [50000.0],
            'volume': [1.0]
        })
    }
    
    # Position value: 1.0 * 50000.0 = 50000.0
    # Portfolio value: 100000.0
    # Position percentage: 50% > 10% limit
    is_valid, reason = await risk_manager.validate_new_position(
        "BTC-USD",
        size=1.0,
        portfolio_value=100000.0,
        market_data=market_data
    )
    assert is_valid is False
    assert "Position size (50.00%) exceeds limit (10.00%)" in reason

@pytest.mark.asyncio
async def test_validate_new_position_missing_market_data(risk_manager):
    """Test position validation with missing market data"""
    is_valid, reason = await risk_manager.validate_new_position(
        "BTC-USD",
        size=0.1,
        portfolio_value=100000.0,
        market_data=None
    )
    assert is_valid is False
    assert reason == "Market data not provided"

def test_risk_assessment_error_handling(risk_manager, mock_market_data):
    """Test risk assessment error handling"""
    mock_market_data.get_recent_trades.side_effect = Exception("API Error")
    
    # Should handle exception gracefully and return False
    assert risk_manager.assess_risk(1000.0, "BTC-USD") is False

def test_order_validation_error_handling(risk_manager, mock_market_data):
    """Test order validation error handling"""
    mock_market_data.get_order_book.side_effect = Exception("Network Error")
    
    is_valid, reason = risk_manager.validate_order("BTC-USD", 0.1, 50000.0)
    assert is_valid is False
    assert "Order validation error" in reason
