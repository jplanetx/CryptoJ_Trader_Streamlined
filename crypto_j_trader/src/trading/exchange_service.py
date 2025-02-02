"""
Exchange Service Layer

This module provides a high-level interface for interacting with the Coinbase Advanced Trade API.
It handles order execution, market data retrieval, and account management while providing
proper error handling and system monitoring.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from decimal import Decimal
import logging
import json

from .coinbase_api import (
    CoinbaseAdvancedClient,
    CoinbaseApiError,
    OrderRequest,
    ApiCredentials
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MarketOrder:
    """Market order details"""
    product_id: str
    side: str
    size: Decimal
    client_order_id: Optional[str] = None

@dataclass
class LimitOrder:
    """Limit order details"""
    product_id: str
    side: str
    size: Decimal
    price: Decimal
    client_order_id: Optional[str] = None

class OrderStatus:
    """Order status constants"""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"

class ExchangeServiceError(Exception):
    """Custom exception for exchange service errors"""
    pass

class ExchangeService:
    """
    High-level service for interacting with Coinbase Advanced Trade API.
    Provides error handling, retry logic, and monitoring.
    """

    def __init__(self, credentials_path: str):
        """
        Initialize the exchange service
        
        Args:
            credentials_path: Path to API credentials JSON file
        """
        self.credentials = self._load_credentials(credentials_path)
        self.client = CoinbaseAdvancedClient(self.credentials)
        logger.info("Exchange service initialized")

    def _load_credentials(self, credentials_path: str) -> ApiCredentials:
        """Load API credentials from JSON file"""
        try:
            with open(credentials_path) as f:
                creds = json.load(f)
                return {
                    "api_key": creds["api_key"],
                    "api_secret": creds["api_secret"]
                }
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
            raise ExchangeServiceError(f"Failed to load API credentials: {str(e)}")

    def place_market_order(self, order: MarketOrder) -> Dict[str, Any]:
        """
        Place a market order
        
        Args:
            order: MarketOrder object with order details
        
        Returns:
            Order response from the exchange
        
        Raises:
            ExchangeServiceError: If order placement fails
        """
        try:
            request = OrderRequest(
                product_id=order.product_id,
                side=order.side,
                order_type="market",
                size=str(order.size)
            )
            
            response = self.client.create_order(request)
            logger.info(f"Market order placed: {response.get('order_id')}")
            return response
            
        except CoinbaseApiError as e:
            logger.error(f"Failed to place market order: {str(e)}")
            raise ExchangeServiceError(f"Market order failed: {str(e)}")

    def place_limit_order(self, order: LimitOrder) -> Dict[str, Any]:
        """
        Place a limit order
        
        Args:
            order: LimitOrder object with order details
        
        Returns:
            Order response from the exchange
        
        Raises:
            ExchangeServiceError: If order placement fails
        """
        try:
            request = OrderRequest(
                product_id=order.product_id,
                side=order.side,
                order_type="limit",
                size=str(order.size),
                price=str(order.price)
            )
            
            response = self.client.create_order(request)
            logger.info(f"Limit order placed: {response.get('order_id')}")
            return response
            
        except CoinbaseApiError as e:
            logger.error(f"Failed to place limit order: {str(e)}")
            raise ExchangeServiceError(f"Limit order failed: {str(e)}")

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get current status of an order"""
        try:
            response = self.client.get_order(order_id)
            logger.debug(f"Order status retrieved: {order_id}")
            return response
        except CoinbaseApiError as e:
            logger.error(f"Failed to get order status: {str(e)}")
            raise ExchangeServiceError(f"Failed to get order status: {str(e)}")

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an open order
        
        Returns:
            True if order was cancelled successfully
        """
        try:
            self.client.cancel_order(order_id)
            logger.info(f"Order cancelled: {order_id}")
            return True
        except CoinbaseApiError as e:
            logger.error(f"Failed to cancel order: {str(e)}")
            raise ExchangeServiceError(f"Failed to cancel order: {str(e)}")

    def get_product_ticker(self, product_id: str) -> Dict[str, Any]:
        """Get current ticker for a product"""
        try:
            return self.client.get_ticker(product_id)
        except CoinbaseApiError as e:
            logger.error(f"Failed to get ticker: {str(e)}")
            raise ExchangeServiceError(f"Failed to get ticker: {str(e)}")

    def get_order_book(self, product_id: str, level: int = 1) -> Dict[str, Any]:
        """Get order book for a product"""
        try:
            return self.client.get_product_book(product_id, level)
        except CoinbaseApiError as e:
            logger.error(f"Failed to get order book: {str(e)}")
            raise ExchangeServiceError(f"Failed to get order book: {str(e)}")

    def get_account_balance(self) -> Dict[str, Any]:
        """Get account balance information"""
        try:
            return self.client.get_account()
        except CoinbaseApiError as e:
            logger.error(f"Failed to get account balance: {str(e)}")
            raise ExchangeServiceError(f"Failed to get account balance: {str(e)}")

    def get_recent_trades(self, product_id: str) -> List[Dict[str, Any]]:
        """Get recent trades for a product"""
        try:
            return self.client.get_trades(product_id)
        except CoinbaseApiError as e:
            logger.error(f"Failed to get recent trades: {str(e)}")
            raise ExchangeServiceError(f"Failed to get recent trades: {str(e)}")