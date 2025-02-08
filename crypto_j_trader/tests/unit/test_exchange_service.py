"""Unit tests for Exchange Service"""
import pytest
from unittest.mock import patch, mock_open, MagicMock
from decimal import Decimal
import json

from crypto_j_trader.src.trading.exchange_service import (
    ExchangeService,
    ExchangeServiceError,
    MarketOrder,
    LimitOrder
)
from crypto_j_trader.src.trading.coinbase_api import CoinbaseApiError

# Mock API credentials
MOCK_CREDENTIALS = {
    "api_key": "test_key",
    "api_secret": "test_secret"
}

@pytest.fixture
def mock_credentials_file():
    """Mock credentials file content"""
    return json.dumps(MOCK_CREDENTIALS)

@pytest.fixture
def exchange_service(mock_credentials_file):
    """Create exchange service instance with mocked credentials"""
    with patch("builtins.open", mock_open(read_data=mock_credentials_file)):
        return ExchangeService("dummy_path.json")

@pytest.fixture
def mock_api_response():
    """Mock successful API response"""
    return {
        "order_id": "test_order_123",
        "product_id": "BTC-USD",
        "status": "pending"
    }

def test_initialization(mock_credentials_file):
    """Test exchange service initialization"""
    with patch("builtins.open", mock_open(read_data=mock_credentials_file)):
        service = ExchangeService("dummy_path.json")
        assert service.credentials["api_key"] == "test_key"
        assert service.credentials["api_secret"] == "test_secret"

def test_initialization_invalid_credentials():
    """Test initialization with invalid credentials file"""
    with patch("builtins.open", mock_open(read_data="{invalid_json")):
        with pytest.raises(ExchangeServiceError) as exc_info:
            ExchangeService("dummy_path.json")
        assert "Failed to load API credentials" in str(exc_info.value)

def test_place_market_order_success(exchange_service, mock_api_response):
    """Test successful market order placement"""
    with patch.object(exchange_service, "paper_trading", new=False):
        with patch.object(exchange_service.client, "create_order", return_value=mock_api_response):
            order = MarketOrder(
                product_id="BTC-USD",
                side="buy",
                size=Decimal("0.01")
            )

            response = exchange_service.place_market_order(order)

            assert response == mock_api_response
            exchange_service.client.create_order.assert_called_once()

def test_place_market_order_failure(exchange_service):
    """Test market order placement failure"""
    with patch.object(
        exchange_service,
        "place_market_order",
        side_effect=ExchangeServiceError("Market order failed")
    ):
        order = MarketOrder(
            product_id="BTC-USD",
            side="buy",
            size=Decimal("0.01")
        )

        with pytest.raises(ExchangeServiceError) as exc_info:
            exchange_service.place_market_order(order)
        assert "Market order failed" in str(exc_info.value)

def test_place_limit_order_success(exchange_service, mock_api_response):
    """Test successful limit order placement"""
    with patch.object(exchange_service, "paper_trading", new=False):
        with patch.object(exchange_service.client, "create_order", return_value=mock_api_response):
            order = LimitOrder(
                product_id="BTC-USD",
                side="buy",
                size=Decimal("0.01"),
                price=Decimal("50000.00")
            )

            response = exchange_service.place_limit_order(order)

            assert response == mock_api_response
            exchange_service.client.create_order.assert_called_once()

def test_place_limit_order_failure(exchange_service):
    """Test limit order placement failure"""
    with patch.object(
        exchange_service,
        "place_limit_order",
        side_effect=ExchangeServiceError("Limit order failed")
    ):
        order = LimitOrder(
            product_id="BTC-USD",
            side="buy",
            size=Decimal("0.01"),
            price=Decimal("50000.00")
        )

        with pytest.raises(ExchangeServiceError) as exc_info:
            exchange_service.place_limit_order(order)
        assert "Limit order failed" in str(exc_info.value)

def test_get_order_status_success(exchange_service, mock_api_response):
    """Test successful order status retrieval"""
    with patch.object(exchange_service.client, "get_order", return_value=mock_api_response):
        response = exchange_service.get_order_status("test_order_123")
        assert response == mock_api_response
        exchange_service.client.get_order.assert_called_once_with("test_order_123")

def test_get_order_status_failure(exchange_service):
    """Test order status retrieval failure"""
    with patch.object(
        exchange_service.client,
        "get_order",
        side_effect=CoinbaseApiError("API Error")
    ):
        with pytest.raises(ExchangeServiceError) as exc_info:
            exchange_service.get_order_status("test_order_123")
        assert "Failed to get order status" in str(exc_info.value)

def test_cancel_order_success(exchange_service):
    """Test successful order cancellation"""
    with patch.object(exchange_service.client, "cancel_order", return_value={"cancelled": True}):
        result = exchange_service.cancel_order("test_order_123")
        assert result is True
        exchange_service.client.cancel_order.assert_called_once_with("test_order_123")

def test_cancel_order_failure(exchange_service):
    """Test order cancellation failure"""
    with patch.object(
        exchange_service.client,
        "cancel_order",
        side_effect=CoinbaseApiError("API Error")
    ):
        with pytest.raises(ExchangeServiceError) as exc_info:
            exchange_service.cancel_order("test_order_123")
        assert "Failed to cancel order" in str(exc_info.value)

def test_get_product_ticker_success(exchange_service):
    """Test successful product ticker retrieval"""
    mock_ticker = {"price": "50000.00", "volume": "100.0"}
    with patch.object(exchange_service.client, "get_ticker", return_value=mock_ticker):
        response = exchange_service.get_product_ticker("BTC-USD")
        assert response == mock_ticker
        exchange_service.client.get_ticker.assert_called_once_with("BTC-USD")

def test_get_order_book_success(exchange_service):
    """Test successful order book retrieval"""
    mock_book = {
        "bids": [["50000.00", "0.5"]],
        "asks": [["50100.00", "0.3"]]
    }
    with patch.object(exchange_service.client, "get_product_book", return_value=mock_book):
        response = exchange_service.get_order_book("BTC-USD", level=1)
        assert response == mock_book
        exchange_service.client.get_product_book.assert_called_once_with("BTC-USD", 1)

def test_get_account_balance_success(exchange_service):
    """Test successful account balance retrieval"""
    with patch.object(exchange_service, "paper_trading", new=False):
        mock_balance = {"available": "1.5", "hold": "0.5"}
        with patch.object(exchange_service.client, "get_account", return_value=mock_balance):
            response = exchange_service.get_account_balance()
            assert response == mock_balance
            exchange_service.client.get_account.assert_called_once()

def test_get_recent_trades_success(exchange_service):
    """Test successful recent trades retrieval"""
    mock_trades = [
        {"price": "50000.00", "size": "0.1"},
        {"price": "50001.00", "size": "0.2"}
    ]
    with patch.object(exchange_service.client, "get_trades", return_value=mock_trades):
        response = exchange_service.get_recent_trades("BTC-USD")
        assert response == mock_trades
        exchange_service.client.get_trades.assert_called_once_with("BTC-USD")