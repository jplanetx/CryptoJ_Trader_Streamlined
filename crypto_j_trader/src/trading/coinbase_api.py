"""
Coinbase Advanced Trade API Client

This module implements the Coinbase Advanced Trade API v3 client with service abstractions
for order execution, market data, and account management.
"""
import hmac
import hashlib
import time
import json
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
import requests
from typing_extensions import TypedDict

class ApiCredentials(TypedDict):
    api_key: str
    api_secret: str

@dataclass
class OrderRequest:
    product_id: str
    side: str  # buy or sell
    order_type: str  # limit, market, stop, stop_limit
    size: str  # base currency amount
    price: Optional[str] = None  # required for limit orders
    stop_price: Optional[str] = None  # required for stop orders

class CoinbaseApiError(Exception):
    """Custom exception for Coinbase API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)

class CoinbaseAdvancedClient:
    """
    Coinbase Advanced Trade API Client implementing v3 endpoints
    Documentation: https://docs.cdp.coinbase.com/advanced-trade/docs/welcome
    """
    BASE_URL = "https://api.coinbase.com/api/v3/brokerage"

    def __init__(self, credentials: ApiCredentials):
        self.api_key = credentials['api_key']
        self.api_secret = credentials['api_secret']
        self.session = requests.Session()

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO 8601 format"""
        return str(int(time.time()))

    def _sign_message(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        """
        Generate signature for API request using HMAC SHA256
        
        Args:
            timestamp: Current timestamp
            method: HTTP method (GET, POST, etc)
            request_path: API endpoint path
            body: Request body for POST requests
        """
        message = f"{timestamp}{method}{request_path}{body}"
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        )
        return signature.hexdigest()

    def _generate_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """Generate required headers for API request"""
        timestamp = self._get_timestamp()
        return {
            "CB-ACCESS-KEY": self.api_key,
            "CB-ACCESS-SIGN": self._sign_message(timestamp, method, path, body),
            "CB-ACCESS-TIMESTAMP": timestamp,
            "Content-Type": "application/json"
        }

    def _request(self, method: str, path: str, data: Optional[Dict] = None) -> Dict:
        """
        Make authenticated request to Coinbase API
        
        Args:
            method: HTTP method
            path: API endpoint path
            data: Request payload for POST requests
        
        Returns:
            API response as dictionary
        
        Raises:
            CoinbaseApiError: If API request fails
        """
        url = f"{self.BASE_URL}{path}"
        body = json.dumps(data) if data else ""
        headers = self._generate_headers(method, path, body)

        try:
            response = self.session.request(method, url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            status_code = getattr(e.response, 'status_code', None)
            error_response = None
            try:
                error_response = e.response.json() if e.response else None
            except:
                pass
            raise CoinbaseApiError(
                f"API request failed: {str(e)}", 
                status_code=status_code,
                response=error_response
            )

    def create_order(self, order: OrderRequest) -> Dict[str, Any]:
        """
        Create a new order
        
        Args:
            order: OrderRequest object containing order details
        
        Returns:
            Order creation response
        """
        endpoint = "/orders"
        payload = {
            "product_id": order.product_id,
            "side": order.side,
            "order_configuration": {
                order.order_type: {
                    "quote_size": order.size
                }
            }
        }

        # Add price for limit orders
        if order.order_type == "limit" and order.price:
            payload["order_configuration"]["limit"]["limit_price"] = order.price

        # Add stop price for stop orders
        if order.order_type in ["stop", "stop_limit"] and order.stop_price:
            payload["order_configuration"][order.order_type]["stop_price"] = order.stop_price

        return self._request("POST", endpoint, payload)

    def get_order(self, order_id: str) -> Dict[str, Any]:
        """Get order details by ID"""
        endpoint = f"/orders/{order_id}"
        return self._request("GET", endpoint)

    def list_orders(self, product_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List orders with optional product filter"""
        endpoint = "/orders"
        if product_id:
            endpoint += f"?product_id={product_id}"
        return self._request("GET", endpoint)

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order by ID"""
        endpoint = f"/orders/{order_id}"
        return self._request("DELETE", endpoint)

    def get_product(self, product_id: str) -> Dict[str, Any]:
        """Get product details"""
        endpoint = f"/products/{product_id}"
        return self._request("GET", endpoint)

    def get_product_book(self, product_id: str, level: int = 1) -> Dict[str, Any]:
        """
        Get product order book
        
        Args:
            product_id: Product identifier
            level: Order book level (1, 2, or 3)
        """
        endpoint = f"/products/{product_id}/book?level={level}"
        return self._request("GET", endpoint)

    def get_ticker(self, product_id: str) -> Dict[str, Any]:
        """Get current ticker for a product"""
        endpoint = f"/products/{product_id}/ticker"
        return self._request("GET", endpoint)

    def get_trades(self, product_id: str) -> List[Dict[str, Any]]:
        """Get recent trades for a product"""
        endpoint = f"/products/{product_id}/trades"
        return self._request("GET", endpoint)

    def get_account(self) -> Dict[str, Any]:
        """Get account information"""
        endpoint = "/accounts"
        return self._request("GET", endpoint)