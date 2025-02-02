"""
Mock responses and utilities for Coinbase Advanced API testing.
"""
from typing import Dict, Any, List
import json
from datetime import datetime, timezone
import unittest.mock

class MockCoinbaseResponses:
    """Collection of mock Coinbase API responses for testing."""

    @staticmethod
    def get_accounts() -> Dict[str, Any]:
        """Mock response for get accounts endpoint."""
        return {
            "accounts": [
                {
                    "uuid": "8bfc20d7-f7c6-4422-bf07-8243ca4169fe",
                    "name": "BTC-USD",
                    "currency": "BTC",
                    "available_balance": {"value": "1.23", "currency": "BTC"},
                    "default": False,
                    "active": True,
                    "created_at": "2025-02-01T12:00:00Z",
                    "updated_at": "2025-02-01T12:00:00Z",
                    "deleted_at": None,
                    "type": "ACCOUNT_TYPE_CRYPTO"
                }
            ],
            "has_next": False,
            "cursor": "",
            "size": 1
        }

    @staticmethod
    def get_product(product_id: str) -> Dict[str, Any]:
        """Mock response for get product endpoint."""
        return {
            "product_id": product_id,
            "price": "45000.00",
            "price_percentage_change_24h": "5.2",
            "volume_24h": "1000.0",
            "volume_percentage_change_24h": "10.5",
            "base_increment": "0.00000001",
            "quote_increment": "0.01",
            "quote_min_size": "1.00",
            "quote_max_size": "1000000.00",
            "base_min_size": "0.00001",
            "base_max_size": "1000.00",
            "base_name": "Bitcoin",
            "quote_name": "US Dollar",
            "watched": False,
            "is_disabled": False,
            "new": False,
            "status": "online",
            "cancel_only": False,
            "limit_only": False,
            "post_only": False,
            "trading_disabled": False
        }

    @staticmethod
    def create_order() -> Dict[str, Any]:
        """Mock response for create order endpoint."""
        return {
            "success": True,
            "order_id": "11111111-1111-1111-1111-111111111111",
            "success_response": {
                "order_id": "11111111-1111-1111-1111-111111111111",
                "product_id": "BTC-USD",
                "side": "BUY",
                "client_order_id": "client_order_id"
            },
            "error_response": None,
            "order_configuration": {
                "market_market_ioc": {
                    "quote_size": "100.00",
                    "base_size": None
                }
            }
        }

    @staticmethod
    def get_order(order_id: str) -> Dict[str, Any]:
        """Mock response for get order endpoint."""
        return {
            "order": {
                "order_id": order_id,
                "product_id": "BTC-USD",
                "user_id": "user123",
                "status": "FILLED",
                "side": "BUY",
                "order_configuration": {
                    "market_market_ioc": {
                        "quote_size": "100.00",
                        "base_size": None
                    }
                },
                "creation_time": "2025-02-01T12:00:00Z",
                "completion_time": "2025-02-01T12:00:01Z",
                "fill_fees": "0.50",
                "filled_size": "0.002",
                "average_filled_price": "45000.00",
                "commission": "0.50",
                "status_message": None,
                "client_order_id": "client_order_id"
            }
        }

    @staticmethod
    def get_fills() -> Dict[str, Any]:
        """Mock response for get fills endpoint."""
        return {
            "fills": [
                {
                    "entry_id": "22222222-2222-2222-2222-222222222222",
                    "trade_id": "1",
                    "order_id": "11111111-1111-1111-1111-111111111111",
                    "trade_time": "2025-02-01T12:00:01Z",
                    "trade_type": "FILL",
                    "price": "45000.00",
                    "size": "0.002",
                    "commission": "0.50",
                    "product_id": "BTC-USD",
                    "sequence_timestamp": "2025-02-01T12:00:01Z",
                    "side": "BUY"
                }
            ],
            "cursor": ""
        }

class MockWebsocketMessages:
    """Collection of mock websocket messages for testing."""

    @staticmethod
    def market_trades(product_id: str) -> Dict[str, Any]:
        """Generate mock market trades message."""
        return {
            "channel": "market_trades",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sequence_num": 1,
            "events": [
                {
                    "type": "market_trade",
                    "trade_id": "1",
                    "product_id": product_id,
                    "price": "45000.00",
                    "size": "0.1",
                    "side": "BUY",
                    "time": datetime.now(timezone.utc).isoformat()
                }
            ]
        }

    @staticmethod
    def ticker(product_id: str) -> Dict[str, Any]:
        """Generate mock ticker message."""
        return {
            "channel": "ticker",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sequence_num": 1,
            "events": [
                {
                    "type": "ticker",
                    "product_id": product_id,
                    "price": "45000.00",
                    "volume_24h": "1000.0",
                    "low_24h": "44000.00",
                    "high_24h": "46000.00",
                    "low_52w": "30000.00",
                    "high_52w": "50000.00",
                    "price_percent_chg_24h": "5.2"
                }
            ]
        }

def generate_error_response(code: str, message: str) -> Dict[str, Any]:
    """Generate a mock error response."""
    return {
        "error": True,
        "error_response": {
            "error": message,
            "code": code,
            "message": message
        },
        "success": False
    }

def mock_rate_limit_error() -> Dict[str, Any]:
    """Generate a mock rate limit error response."""
    return generate_error_response(
        "RATE_LIMIT_EXCEEDED",
        "Rate limit exceeded. Please try again later."
    )

def mock_insufficient_funds_error() -> Dict[str, Any]:
    """Generate a mock insufficient funds error response."""
    return generate_error_response(
        "INSUFFICIENT_FUNDS",
        "Insufficient funds for requested transaction."
    )

class MockExchangeService(unittest.mock.Mock): # Creating MockExchangeService class
    """Mock implementation of ExchangeService for testing."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.get_historical_data = unittest.mock.AsyncMock(return_value={})
        self.get_current_price = unittest.mock.AsyncMock(return_value={})
        self.start_price_feed = unittest.mock.AsyncMock() # Mock for websocket