"""Unit tests for OrderExecutor"""
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch

from crypto_j_trader.src.trading.order_execution import OrderExecutor
from crypto_j_trader.src.trading.exchange_service import (
    ExchangeService,
    ExchangeServiceError,
    MarketOrder,
    LimitOrder
)

@pytest.fixture
def mock_exchange_service():
    """Create a mock exchange service"""
    mock_service = Mock(spec=ExchangeService)
    mock_service.get_product_ticker.return_value = {"price": "50000.00"}
    return mock_service

@pytest.fixture
def order_executor(mock_exchange_service):
    """Create an OrderExecutor instance with mock exchange service"""
    return OrderExecutor(mock_exchange_service, "BTC-USD", paper_trading=False)

@pytest.fixture
def paper_trading_executor():
    """Create an OrderExecutor instance in paper trading mode"""
    return OrderExecutor(None, "BTC-USD", paper_trading=True)

def test_initialization(mock_exchange_service):
    """Test OrderExecutor initialization"""
    executor = OrderExecutor(mock_exchange_service, "BTC-USD")
    assert executor.trading_pair == "BTC-USD"
    assert executor.paper_trading is False
    assert executor.exchange is mock_exchange_service

def test_initialization_paper_trading():
    """Test OrderExecutor initialization in paper trading mode"""
    executor = OrderExecutor(None, "BTC-USD", paper_trading=True)
    assert executor.trading_pair == "BTC-USD"
    assert executor.paper_trading is True
    assert executor.exchange is None

def test_initialization_error():
    """Test OrderExecutor initialization with invalid parameters"""
    with pytest.raises(ValueError) as exc_info:
        OrderExecutor(None, "BTC-USD", paper_trading=False)
    assert "Exchange service cannot be None in live trading mode" in str(exc_info.value)

def test_market_order_execution(order_executor, mock_exchange_service):
    """Test market order execution"""
    mock_response = {
        "order_id": "test123",
        "product_id": "BTC-USD",
        "status": "filled",
        "price": "50000.00"
    }
    mock_exchange_service.place_market_order.return_value = mock_response
    mock_exchange_service.get_order_status.return_value = mock_response

    order = {
        "symbol": "BTC-USD",
        "side": "buy",
        "quantity": "0.1",
        "type": "market"
    }

    result = order_executor.execute_order(order)
    
    assert result == mock_response
    mock_exchange_service.place_market_order.assert_called_once()
    assert isinstance(
        mock_exchange_service.place_market_order.call_args[0][0],
        MarketOrder
    )

def test_limit_order_execution(order_executor, mock_exchange_service):
    """Test limit order execution"""
    mock_response = {
        "order_id": "test123",
        "product_id": "BTC-USD",
        "status": "open",
        "price": "50000.00"
    }
    mock_exchange_service.place_limit_order.return_value = mock_response
    mock_exchange_service.get_order_status.return_value = mock_response

    order = {
        "symbol": "BTC-USD",
        "side": "buy",
        "quantity": "0.1",
        "type": "limit",
        "price": "50000.00"
    }

    result = order_executor.execute_order(order)
    
    assert result == mock_response
    mock_exchange_service.place_limit_order.assert_called_once()
    assert isinstance(
        mock_exchange_service.place_limit_order.call_args[0][0],
        LimitOrder
    )

def test_paper_trading_market_order(paper_trading_executor):
    """Test market order execution in paper trading mode"""
    order = {
        "symbol": "BTC-USD",
        "side": "buy",
        "quantity": "0.1",
        "type": "market"
    }

    result = paper_trading_executor.execute_order(order)
    
    assert result["order_id"] == "paper_trade"
    assert result["product_id"] == "BTC-USD"
    assert result["status"] == "filled"
    assert Decimal(result["size"]) == Decimal("0.1")
    assert Decimal(result["price"]) == paper_trading_executor.default_fill_price

def test_paper_trading_limit_order(paper_trading_executor):
    """Test limit order execution in paper trading mode"""
    order = {
        "symbol": "BTC-USD",
        "side": "buy",
        "quantity": "0.1",
        "type": "limit",
        "price": "50000.00"
    }

    result = paper_trading_executor.execute_order(order)
    
    assert result["order_id"] == "paper_trade"
    assert result["product_id"] == "BTC-USD"
    assert result["status"] == "filled"
    assert Decimal(result["size"]) == Decimal("0.1")
    assert Decimal(result["price"]) == Decimal("50000.00")

def test_invalid_order_side(order_executor):
    """Test order execution with invalid side"""
    order = {
        "symbol": "BTC-USD",
        "side": "invalid",
        "quantity": "0.1",
        "type": "market"
    }

    with pytest.raises(ValueError) as exc_info:
        order_executor.execute_order(order)
    assert "Invalid order side" in str(exc_info.value)

def test_invalid_order_type(order_executor):
    """Test order execution with invalid type"""
    order = {
        "symbol": "BTC-USD",
        "side": "buy",
        "quantity": "0.1",
        "type": "invalid"
    }

    with pytest.raises(ValueError) as exc_info:
        order_executor.execute_order(order)
    assert "Invalid order type" in str(exc_info.value)

def test_missing_limit_price(order_executor):
    """Test limit order execution without price"""
    order = {
        "symbol": "BTC-USD",
        "side": "buy",
        "quantity": "0.1",
        "type": "limit"
    }

    with pytest.raises(ValueError) as exc_info:
        order_executor.execute_order(order)
    assert "Limit price required for limit orders" in str(exc_info.value)

def test_exchange_service_error(order_executor, mock_exchange_service):
    """Test handling of exchange service errors"""
    mock_exchange_service.place_market_order.side_effect = ExchangeServiceError("API Error")

    order = {
        "symbol": "BTC-USD",
        "side": "buy",
        "quantity": "0.1",
        "type": "market"
    }

    with pytest.raises(ExchangeServiceError) as exc_info:
        order_executor.execute_order(order)
    assert "API Error" in str(exc_info.value)

def test_position_tracking_buy(order_executor, mock_exchange_service):
    """Test position tracking for buy orders"""
    mock_response = {
        "order_id": "test123",
        "product_id": "BTC-USD",
        "status": "filled",
        "price": "50000.00"
    }
    mock_exchange_service.place_market_order.return_value = mock_response
    mock_exchange_service.get_order_status.return_value = mock_response

    order = {
        "symbol": "BTC-USD",
        "side": "buy",
        "quantity": "0.1",
        "type": "market"
    }

    order_executor.execute_order(order)
    position = order_executor.get_position("BTC-USD")
    
    assert position["quantity"] == Decimal("0.1")
    assert position["entry_price"] == Decimal("50000.00")

def test_position_tracking_sell(order_executor, mock_exchange_service):
    """Test position tracking for sell orders"""
    # Initialize position first
    order_executor.initialize_position("BTC-USD", Decimal("0.2"), Decimal("50000.00"))

    mock_response = {
        "order_id": "test123",
        "product_id": "BTC-USD",
        "status": "filled",
        "price": "51000.00"
    }
    mock_exchange_service.place_market_order.return_value = mock_response
    mock_exchange_service.get_order_status.return_value = mock_response

    order = {
        "symbol": "BTC-USD",
        "side": "sell",
        "quantity": "0.1",
        "type": "market"
    }

    order_executor.execute_order(order)
    position = order_executor.get_position("BTC-USD")
    
    assert position["quantity"] == Decimal("0.1")
    assert position["entry_price"] == Decimal("50000.00")