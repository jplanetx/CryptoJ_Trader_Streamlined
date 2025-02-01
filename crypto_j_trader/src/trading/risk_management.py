"""
risk_management.py

This module handles risk evaluations and enforces risk control measures
for order execution during live or paper trading.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from .market_data import MarketDataHandler

# Configure module logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

class RiskManager:
    def __init__(self, risk_threshold: float, market_data: MarketDataHandler):
        """
        Initialize the RiskManager with specified risk threshold and market data handler.
        
        Args:
            risk_threshold: Maximum allowable risk exposure
            market_data: Instance of MarketDataHandler for market data access
        """
        self.risk_threshold = risk_threshold
        self.market_data = market_data
        self.max_position_size: Dict[str, float] = {}
        self.max_order_value: float = 1000.0  # Default max order value for paper trading
        self.market_data_max_age = 5.0  # Maximum age of market data in seconds
        self.min_order_book_depth = 10  # Minimum required order book depth
        self.emergency_mode = False  # Emergency mode flag
        
    def validate_paper_trading(self, trading_pair: str) -> tuple[bool, str]:
        """
        Validate if system is ready for paper trading.
        
        Args:
            trading_pair: Trading pair to validate
            
        Returns:
            tuple[bool, str]: (is_ready, reason)
        """
        # Check if market data is running and fresh
        if not self.market_data.is_running:
            return False, "Market data handler not running"
            
        if not self.market_data.is_data_fresh(self.market_data_max_age):
            return False, "Market data not fresh"
            
        # Verify market data completeness
        snapshot = self.market_data.get_market_snapshot(trading_pair)
        if not snapshot['last_price']:
            return False, "No recent price data available"
            
        if snapshot['order_book_depth'] < self.min_order_book_depth:
            return False, "Insufficient order book depth"
            
        if not snapshot['subscribed']:
            return False, "Not subscribed to trading pair"
            
        return True, "Ready for paper trading"

    def assess_risk(self, position_value: float, trading_pair: str) -> bool:
        """
        Assess the current risk and determine if trading can proceed.
        
        Args:
            position_value: Current position value
            trading_pair: Trading pair being traded
            
        Returns:
            bool: True if risk is acceptable, False otherwise
        """
        try:
            # Check market data consistency
            is_ready, reason = self.validate_paper_trading(trading_pair)
            if not is_ready:
                logger.error("Market data validation failed: %s", reason)
                return False
                
            # Calculate market volatility from recent trades
            recent_trades = self.market_data.get_recent_trades(trading_pair)
            if not recent_trades:
                logger.error("No recent trades available for volatility calculation")
                return False
                
            # Enhanced volatility calculation using standard deviation
            prices = [trade['price'] for trade in recent_trades]
            avg_price = sum(prices) / len(prices)
            squared_diffs = [(p - avg_price) ** 2 for p in prices]
            std_dev = (sum(squared_diffs) / len(prices)) ** 0.5
            volatility = std_dev / avg_price
            
            # Calculate risk exposure with position scaling factor
            position_scale = 1.0 + (position_value / 10000.0)  # Scale factor increases with position size
            risk_exposure = position_value * volatility * position_scale
            
            if risk_exposure >= self.risk_threshold:  # Changed from > to >= for strict comparison
                logger.warning("Risk exposure (%.2f) exceeds threshold (%.2f)", 
                           risk_exposure, self.risk_threshold)
                return False
                
            logger.info("Risk assessment passed: exposure %.2f within threshold %.2f",
                       risk_exposure, self.risk_threshold)
            return True
            
        except Exception as e:
            logger.exception("Error during risk assessment: %s", str(e))
            return False
            
    def validate_order(self, trading_pair: str, order_size: float, 
                      order_price: float) -> tuple[bool, str]:
        """
        Validate if an order meets risk control requirements.
        
        Args:
            trading_pair: Trading pair for the order
            order_size: Size of the order
            order_price: Price of the order
            
        Returns:
            tuple[bool, str]: (is_valid, reason)
        """
        try:
            # Check if order value exceeds maximum
            order_value = order_size * order_price
            if order_value > self.max_order_value:
                return False, f"Order value {order_value} exceeds maximum {self.max_order_value}"
                
            # Verify order book depth can support the order
            order_book = self.market_data.get_order_book(trading_pair)
            if not order_book:
                return False, "Order book not available"
                
            # Check if there's enough liquidity
            total_liquidity = sum(float(size) for size in order_book['bids'].values())
            if order_size > total_liquidity * 0.1:  # Don't use more than 10% of available liquidity
                return False, "Order size exceeds safe liquidity threshold"
                
            return True, "Order validated"
            
        except Exception as e:
            logger.exception("Error validating order: %s", str(e))
            return False, f"Order validation error: {str(e)}"
            
    def update_threshold(self, new_threshold: float) -> None:
        """
        Update the risk threshold.
        
        Args:
            new_threshold: New risk threshold value
        """
        logger.info("Updating risk threshold from %.2f to %.2f", 
                   self.risk_threshold, new_threshold)
        self.risk_threshold = new_threshold
        
    def set_position_limit(self, trading_pair: str, max_size: float) -> None:
        """
        Set maximum position size for a trading pair.
        
        Args:
            trading_pair: Trading pair to set limit for
            max_size: Maximum position size allowed
        """
        self.max_position_size[trading_pair] = max_size
        logger.info("Set position limit for %s: %.2f", trading_pair, max_size)
        
    def set_emergency_mode(self, mode: bool) -> None:
        """
        Set the emergency mode.
        
        Args:
            mode: True to enable emergency mode, False to disable
        """
        self.emergency_mode = mode
        logger.info("Emergency mode set to %s", mode)