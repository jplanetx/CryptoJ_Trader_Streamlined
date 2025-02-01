import pytest
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
    """Test risk assessment with high position value"""
    mock_market_data.get_market_snapshot.return_value = {
        'last_price': 50000.0,
        'order_book_depth': 20,
        'subscribed': True,
        'is_fresh': True
    }
    
    # Create moderately volatile price movements
    mock_market_data.get_recent_trades.return_value = [
        {'price': 50000.0},
        {'price': 51000.0},
        {'price': 49000.0}
    ]
    
    # High position value should exceed threshold due to position scaling
    assert risk_manager.assess_risk(100000.0, "BTC-USD") is False

def test_assess_risk_edge_case(risk_manager, mock_market_data):
    """Test risk assessment at threshold boundary"""
    mock_market_data.get_market_snapshot.return_value = {
        'last_price': 50000.0,
        'order_book_depth': 20,
        'subscribed': True,
        'is_fresh': True
    }
    
    # Create minimal volatility
    mock_market_data.get_recent_trades.return_value = [
        {'price': 50000.0},
        {'price': 50010.0},
        {'price': 49990.0}
    ]
    
    # Position value right at threshold boundary
    assert risk_manager.assess_risk(9950.0, "BTC-USD") is True
    assert risk_manager.assess_risk(10050.0, "BTC-USD") is False

def test_validate_order_success(risk_manager, mock_market_data):
    """Test successful order validation"""
    mock_market_data.get_order_book.return_value = {
        'bids': {'49000.0': '1.0', '48000.0': '1.0'},
        'asks': {'51000.0': '1.0', '52000.0': '1.0'}
    }
    
    is_valid, reason = risk_manager.validate_order("BTC-USD", 0.1, 50000.0)
    assert is_valid is True
    assert reason == "Order validated"

def test_validate_order_exceeds_max_value(risk_manager, mock_market_data):
    """Test order validation with value exceeding maximum"""
    mock_market_data.get_order_book.return_value = {
        'bids': {'49000.0': '1.0', '48000.0': '1.0'},
        'asks': {'51000.0': '1.0', '52000.0': '1.0'}
    }
    
    # Order value: 2.0 * 50000.0 = 100000.0 > max_order_value
    is_valid, reason = risk_manager.validate_order("BTC-USD", 2.0, 50000.0)
    assert is_valid is False
    assert "exceeds maximum" in reason

def test_validate_order_insufficient_liquidity(risk_manager, mock_market_data):
    """Test order validation with insufficient liquidity"""
    mock_market_data.get_order_book.return_value = {
        'bids': {'49000.0': '0.1', '48000.0': '0.1'},
        'asks': {'51000.0': '0.1', '52000.0': '0.1'}
    }
    
    # Order size larger than available liquidity (total liquidity = 0.2)
    is_valid, reason = risk_manager.validate_order("BTC-USD", 0.3, 50000.0)
    assert is_valid is False
    assert reason == "Order size exceeds safe liquidity threshold"

def test_validate_order_missing_order_book(risk_manager, mock_market_data):
    """Test order validation when order book is not available"""
    mock_market_data.get_order_book.return_value = None
    
    is_valid, reason = risk_manager.validate_order("BTC-USD", 0.1, 50000.0)
    assert is_valid is False
    assert reason == "Order book not available"

def test_update_threshold(risk_manager):
    """Test updating risk threshold"""
    new_threshold = 20000.0
    risk_manager.update_threshold(new_threshold)
    assert risk_manager.risk_threshold == new_threshold

def test_set_position_limit(risk_manager):
    """Test setting position limits"""
    trading_pair = "BTC-USD"
    max_size = 2.0
    risk_manager.set_position_limit(trading_pair, max_size)
    assert risk_manager.max_position_size[trading_pair] == max_size

def test_set_emergency_mode(risk_manager):
    """Test setting emergency mode"""
    risk_manager.set_emergency_mode(True)
    assert risk_manager.emergency_mode is True
    risk_manager.set_emergency_mode(False)
    assert risk_manager.emergency_mode is False