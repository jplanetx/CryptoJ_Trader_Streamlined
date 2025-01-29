import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, patch
import numpy as np

from crypto_j_trader.src.trading.trading_core import TradingCore
from crypto_j_trader.src.trading.risk_management import RiskManager

@pytest.fixture
def mock_exchange():
    mock = Mock()
    # Setup basic mock responses
    mock.get_product_ticker.return_value = Mock(price='50000.00')
    mock.get_product_candles.return_value = [
        Mock(close='50000.00'),
        Mock(close='50100.00'),
        Mock(close='49900.00')
    ]
    mock.get_product.return_value = Mock(product=True)
    mock.get_accounts.return_value = Mock(accounts=True)
    return mock

@pytest.fixture
def risk_config():
    return {
        'risk_management': {
            'daily_loss_limit': 0.02,
            'position_size_limit': 0.1,
            'stop_loss_pct': 0.05,
            'correlation_weight': 0.3,
            'volatility_weight': 0.4,
            'min_position_size': 0.02
        }
    }

@pytest.fixture
def trading_core(mock_exchange):
    return TradingCore(mock_exchange, 'BTC-USD')

@pytest.fixture
def trading_core_with_risk(mock_exchange, risk_config):
    risk_manager = RiskManager(risk_config)
    return TradingCore(mock_exchange, 'BTC-USD', risk_manager)

def test_basic_order_execution(trading_core, mock_exchange):
    # Setup mock order response
    mock_exchange.create_order.return_value = Mock(
        order={
            'order_id': '12345',
            'average_filled_price': '50000.00'
        }
    )
    
    # Execute buy order
    order = trading_core.execute_order('buy', Decimal('1.0'), Decimal('1000000'))
    
    assert order['order_id'] == '12345'
    assert trading_core.position['size'] == Decimal('1.0')
    assert trading_core.position['entry_price'] == Decimal('50000.00')

def test_position_tracking(trading_core, mock_exchange):
    # Setup mock responses
    mock_exchange.create_order.return_value = Mock(
        order={
            'order_id': '12345',
            'average_filled_price': '50000.00'
        }
    )
    
    # Execute multiple orders
    trading_core.execute_order('buy', Decimal('1.0'), Decimal('1000000'))
    trading_core.execute_order('buy', Decimal('0.5'), Decimal('1000000'))
    
    position = trading_core.get_position()
    assert position['size'] == 1.5
    assert position['entry_price'] == 50000.00
    
    # Sell partial position
    trading_core.execute_order('sell', Decimal('0.8'), Decimal('1000000'))
    position = trading_core.get_position()
    assert position['size'] == 0.7

def test_risk_controls(trading_core_with_risk, mock_exchange):
    # Test position size limit
    portfolio_value = Decimal('1000000')  # $1M portfolio
    max_position = portfolio_value * Decimal('0.1')  # 10% limit
    
    # Attempt to exceed position limit
    with pytest.raises(ValueError, match="Order rejected by risk controls"):
        trading_core_with_risk.execute_order('buy', max_position * Decimal('1.1'), portfolio_value)

def test_health_check(trading_core):
    assert trading_core.check_health() is True
    assert trading_core.is_healthy is True
    
    # Test failed health check
    trading_core.exchange.get_product.side_effect = Exception("API Error")
    assert trading_core.check_health() is False
    assert trading_core.is_healthy is False

def test_position_metrics_update(trading_core_with_risk, mock_exchange):
    # Setup initial position
    mock_exchange.create_order.return_value = Mock(
        order={
            'order_id': '12345',
            'average_filled_price': '50000.00'
        }
    )
    
    # Buy position
    trading_core_with_risk.execute_order('buy', Decimal('1.0'), Decimal('1000000'))
    
    # Mock current price higher than entry
    mock_exchange.get_product_ticker.return_value = Mock(price='51000.00')
    
    # Get updated position metrics
    position = trading_core_with_risk.get_position()
    
    # Verify unrealized P&L calculation
    assert position['unrealized_pnl'] == 1000.00  # (51000 - 50000) * 1.0
    assert position['stop_loss'] > 0

def test_volatility_calculation(trading_core_with_risk):
    # Test with mock candle data
    vol = trading_core_with_risk._calculate_volatility()
    assert isinstance(vol, float)
    assert vol > 0
    
    # Test fallback on error
    trading_core_with_risk.exchange.get_product_candles.side_effect = Exception("API Error")
    vol = trading_core_with_risk._calculate_volatility()
    assert vol == 0.2  # Default value
