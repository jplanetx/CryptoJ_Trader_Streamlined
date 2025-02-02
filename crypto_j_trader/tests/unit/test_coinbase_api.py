"""Unit tests for Coinbase Advanced Trade API client"""
import pytest
import json
from unittest.mock import patch, mock_open, MagicMock, create_autospec
import requests

from crypto_j_trader.src.trading.coinbase_api import (
    CoinbaseAdvancedClient,
    CoinbaseApiError,
    OrderRequest,
    ApiCredentials
)

@pytest.fixture
def api_credentials() -> ApiCredentials:
    """Test API credentials"""
    return {
        "api_key": "test_key",
        "api_secret": "test_secret"
    }

@pytest.fixture
def mock_session():
    """Create a mock session with proper request method"""
    session = create_autospec(requests.Session, instance=True)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "order_id": "test_order_123",
        "product_id": "BTC-USD",
        "status": "pending"
    }
    session.request.return_value = mock_response
    return session

@pytest.fixture
def client(api_credentials, mock_session):
    """Test API client instance with mocked session"""
    with patch('requests.Session', return_value=mock_session):
        client = CoinbaseAdvancedClient(api_credentials)
        return client

def test_init(api_credentials):
    """Test client initialization"""
    client = CoinbaseAdvancedClient(api_credentials)
    assert client.api_key == "test_key"
    assert client.api_secret == "test_secret"
    assert client.BASE_URL == "https://api.coinbase.com/api/v3/brokerage"

def test_generate_headers(client):
    """Test API request header generation"""
    method = "POST"
    path = "/orders"
    body = json.dumps({"test": "data"})
    
    headers = client._generate_headers(method, path, body)
    
    assert "CB-ACCESS-KEY" in headers
    assert "CB-ACCESS-SIGN" in headers
    assert "CB-ACCESS-TIMESTAMP" in headers
    assert headers["Content-Type"] == "application/json"

def test_sign_message(client):
    """Test request signing"""
    timestamp = "1612345678"
    method = "POST"
    path = "/orders"
    body = json.dumps({"test": "data"})
    
    signature = client._sign_message(timestamp, method, path, body)
    
    assert isinstance(signature, str)
    assert len(signature) == 64  # SHA256 hex digest length

def test_create_order_success(client, mock_session):
    """Test successful order creation"""
    order = OrderRequest(
        product_id="BTC-USD",
        side="buy",
        order_type="market",
        size="0.01"
    )
    
    response = client.create_order(order)
    
    mock_session.request.assert_called_once()
    args = mock_session.request.call_args
    assert args[0][0] == "POST"  # Method
    assert "orders" in args[0][1]  # URL
    assert isinstance(args[1]["json"], dict)  # Order payload
    assert response == mock_session.request.return_value.json()

def test_create_limit_order(client, mock_session):
    """Test limit order creation"""
    order = OrderRequest(
        product_id="BTC-USD",
        side="buy",
        order_type="limit",
        size="0.01",
        price="50000.00"
    )
    
    response = client.create_order(order)
    
    mock_session.request.assert_called_once()
    args = mock_session.request.call_args
    assert args[0][0] == "POST"
    assert isinstance(args[1]["json"], dict)
    assert "limit" in str(args[1]["json"])
    assert response == mock_session.request.return_value.json()

def test_create_order_error(client, mock_session):
    """Test error handling in order creation"""
    mock_session.request.side_effect = requests.exceptions.RequestException("API Error")
    
    order = OrderRequest(
        product_id="BTC-USD",
        side="buy",
        order_type="market",
        size="0.01"
    )
    
    with pytest.raises(CoinbaseApiError) as exc_info:
        client.create_order(order)
    assert "API request failed" in str(exc_info.value)

def test_get_order_success(client, mock_session):
    """Test getting order details"""
    response = client.get_order("test_order_123")
    
    mock_session.request.assert_called_once()
    args = mock_session.request.call_args
    assert args[0][0] == "GET"
    assert "orders/test_order_123" in args[0][1]
    assert response == mock_session.request.return_value.json()

def test_list_orders_success(client, mock_session):
    """Test listing orders"""
    mock_session.request.return_value.json.return_value = [
        {"order_id": "123", "status": "open"},
        {"order_id": "456", "status": "filled"}
    ]
    
    response = client.list_orders()
    
    mock_session.request.assert_called_once()
    args = mock_session.request.call_args
    assert args[0][0] == "GET"
    assert "orders" in args[0][1]
    assert response == mock_session.request.return_value.json()

def test_cancel_order_success(client, mock_session):
    """Test order cancellation"""
    mock_session.request.return_value.json.return_value = {"cancelled": True}
    
    response = client.cancel_order("test_order_123")
    
    mock_session.request.assert_called_once()
    args = mock_session.request.call_args
    assert args[0][0] == "DELETE"
    assert "orders/test_order_123" in args[0][1]
    assert response == {"cancelled": True}

def test_get_product_success(client, mock_session):
    """Test getting product details"""
    mock_session.request.return_value.json.return_value = {
        "id": "BTC-USD",
        "base_currency": "BTC",
        "quote_currency": "USD"
    }
    
    response = client.get_product("BTC-USD")
    
    mock_session.request.assert_called_once()
    args = mock_session.request.call_args
    assert args[0][0] == "GET"
    assert "products/BTC-USD" in args[0][1]
    assert response == mock_session.request.return_value.json()

def test_get_product_book_success(client, mock_session):
    """Test getting order book"""
    mock_session.request.return_value.json.return_value = {
        "bids": [["50000.00", "0.5"]],
        "asks": [["50100.00", "0.3"]]
    }
    
    response = client.get_product_book("BTC-USD", level=1)
    
    mock_session.request.assert_called_once()
    args = mock_session.request.call_args
    assert args[0][0] == "GET"
    assert "products/BTC-USD/book" in args[0][1]
    assert response == mock_session.request.return_value.json()