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
            
            # Use a strict threshold: if risk_exposure is equal to or exceeds threshold, block trading
            if risk_exposure >= self.risk_threshold:
                logger.warning("Risk exposure (%.2f) exceeds threshold (%.2f)", 
                               risk_exposure, self.risk_threshold)
                return False
                
            logger.info("Risk assessment passed: exposure %.2f within threshold %.2f",
                        risk_exposure, self.risk_threshold)
            return True
            
        except Exception as e:
            logger.exception("Error during risk assessment: %s", str(e))
            return False

    def validate_order(self, trading_pair: str, order_size: float, order_price: float) -> tuple[bool, str]:
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
            # Verify order book availability
            order_book = self.market_data.get_order_book(trading_pair)
            if not order_book:
                return False, "Order book not available"
                
            # Check if there's enough liquidity first
            total_liquidity = sum(float(size) for size in order_book['bids'].values())
            if order_size > total_liquidity * 0.1:  # Don't use more than 10% of available liquidity
                return False, "Order size exceeds safe liquidity threshold"
                
            # Then check if order value exceeds maximum
            order_value = order_size * order_price
            if order_value > self.max_order_value:
                return False, f"Order value {order_value} exceeds maximum {self.max_order_value}"
                
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

    async def validate_new_position(self, trading_pair: str, size: float, portfolio_value: float, 
                                      market_data: Optional[Dict] = None) -> bool:
        """
        Validate if a new position can be opened given the current system state.
        
        Args:
            trading_pair: Trading pair for the new position
            size: Position size (in base currency)
            portfolio_value: Current portfolio value
            market_data: Optional market data for additional checks
            
        Returns:
            bool: True if position can be opened, False otherwise.
        """
        try:
            # Block new positions if emergency mode is active
            if self.emergency_mode:
                logger.warning("New position blocked for %s: System in emergency mode", trading_pair)
                return False

            # Use market data if provided to get current price; else use a default
            current_price = 50000.0
            if market_data and trading_pair in market_data:
                df = market_data[trading_pair]
                if not df.empty and 'price' in df.columns:
                    current_price = float(df['price'].iloc[-1])
            
            # Calculate the position size as a percentage of the portfolio
            position_pct = (size * current_price) / portfolio_value if portfolio_value > 0 else float('inf')
            max_pct = 0.1  # For example, limit to 10% of portfolio value
            
            logger.info("Validating new position for %s: position_pct=%.2f, max_pct=%.2f", trading_pair, position_pct, max_pct)
            return position_pct <= max_pct
            
        except Exception as e:
            logger.error("Error validating new position for %s: %s", trading_pair, e)
            return False
