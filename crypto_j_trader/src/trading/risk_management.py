"""
risk_management.py

This module handles risk evaluations and enforces risk control measures
for order execution during live or paper trading.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import math

try:
    from .market_data import MarketDataHandler
except ImportError:
    # For testing purposes
    from ...tests.unit.test_helpers import MockMarketDataHandler as MarketDataHandler

# Configure module logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

class RiskManager:
    def __init__(self, risk_threshold: float, market_data: MarketDataHandler):
        """Initialize RiskManager with risk threshold and market data handler."""
        self.risk_threshold = risk_threshold
        self.market_data = market_data
        self.max_position_size: Dict[str, float] = {}
        self.max_order_value: float = 1000.0
        self.market_data_max_age = 5.0
        self.min_order_book_depth = 10
        self.emergency_mode = False
        self.position_size_limit = 0.1
        self.volatility_scaling = 15.0
        self.position_scaling_factor = 15000.0

    def calculate_volatility(self, prices: list) -> float:
        """Calculate price volatility using standard deviation."""
        if not prices or len(prices) < 2:
            return 0.0
        avg_price = sum(prices) / len(prices)
        squared_diffs = [(p - avg_price) ** 2 for p in prices]
        variance = sum(squared_diffs) / (len(prices) - 1)  # Using n-1 for sample std dev
        std_dev = math.sqrt(variance)
        return (std_dev / avg_price) * self.volatility_scaling

    def assess_risk(self, position_value: float, trading_pair: str) -> bool:
        """Assess if current risk level is acceptable."""
        try:
            is_ready, reason = self.validate_paper_trading(trading_pair)
            if not is_ready:
                logger.error("Market data validation failed: %s", reason)
                return False
                
            recent_trades = self.market_data.get_recent_trades(trading_pair)
            if not recent_trades:
                logger.error("No recent trades available for volatility calculation")
                return False
                
            prices = [trade['price'] for trade in recent_trades]
            volatility = self.calculate_volatility(prices)
            
            # Exponential scaling for large positions
            position_scale = math.exp(position_value / self.position_scaling_factor)
            risk_exposure = position_value * volatility * position_scale
            
            if risk_exposure > self.risk_threshold:
                logger.warning("Risk exposure (%.2f) exceeds threshold (%.2f)", 
                             risk_exposure, self.risk_threshold)
                return False
                
            logger.info("Risk assessment passed: exposure %.2f within threshold %.2f",
                       risk_exposure, self.risk_threshold)
            return True
            
        except Exception as e:
            logger.exception("Error during risk assessment: %s", str(e))
            return False

    def validate_order(self, trading_pair: str, order_size: float, order_price: float) -> Tuple[bool, str]:
        """Validate if an order meets risk requirements."""
        try:
            # Calculate order value first to fail fast on obvious issues
            order_value = order_size * order_price
            if order_value > self.max_order_value:
                return False, f"Order value {order_value} exceeds maximum {self.max_order_value}"

            # Then check order book availability
            order_book = self.market_data.get_order_book(trading_pair)
            if not order_book or not isinstance(order_book, dict):
                return False, "Order book not available"

            # Check liquidity last (most expensive check)
            try:
                total_liquidity = sum(float(size) for size in order_book.get('bids', {}).values())
                if total_liquidity == 0:
                    return False, "No liquidity available"
                    
                if order_size > total_liquidity * 0.1:
                    return False, "Order size exceeds safe liquidity threshold"
            except (ValueError, TypeError, KeyError) as e:
                return False, f"Order validation error: Invalid order book data - {str(e)}"

            return True, "Order validated"
            
        except Exception as e:
            return False, f"Order validation error: {str(e)}"

    def validate_paper_trading(self, trading_pair: str) -> Tuple[bool, str]:
        """Validate if system is ready for paper trading."""
        try:
            if not self.market_data.is_running:
                return False, "Market data handler not running"
                
            if not self.market_data.is_data_fresh(self.market_data_max_age):
                return False, "Market data not fresh"
                
            snapshot = self.market_data.get_market_snapshot(trading_pair)
            if not snapshot or not snapshot.get('last_price'):
                return False, "No recent price data available"
                
            depth = snapshot.get('order_book_depth')
            if isinstance(depth, (int, float)) and depth < self.min_order_book_depth:
                return False, "Insufficient order book depth"
                
            if not snapshot.get('subscribed', False):
                return False, "Not subscribed to trading pair"
                
            return True, "Ready for paper trading"
        except Exception as e:
            return False, str(e)

    async def validate_new_position(self, trading_pair: str, size: float, portfolio_value: float, 
                                  market_data: Optional[Dict] = None) -> Tuple[bool, str]:
        """Validate if a new position can be opened."""
        try:
            if self.emergency_mode:
                return False, "System is in emergency mode"

            if not market_data:
                return False, "Market data not provided"

            current_price = None
            if trading_pair in market_data:
                df = market_data[trading_pair]
                if not df.empty and 'price' in df.columns:
                    current_price = float(df['price'].iloc[-1])
            
            if not current_price:
                return False, "Unable to determine current price"

            position_value = size * current_price
            if portfolio_value <= 0:
                return False, "Invalid portfolio value"

            position_pct = position_value / portfolio_value
            if position_pct > self.position_size_limit:
                return False, f"Position size ({position_pct:.2%}) exceeds limit ({self.position_size_limit:.2%})"

            if not self.assess_risk(position_value, trading_pair):
                return False, "Position would exceed risk threshold"

            return True, "Position validated"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def update_threshold(self, new_threshold: float) -> None:
        """Update the risk threshold."""
        logger.info("Updating risk threshold from %.2f to %.2f", 
                    self.risk_threshold, new_threshold)
        self.risk_threshold = new_threshold

    def set_position_limit(self, trading_pair: str, max_size: float) -> None:
        """Set maximum position size for a trading pair."""
        self.max_position_size[trading_pair] = max_size
        logger.info("Set position limit for %s: %.2f", trading_pair, max_size)

    def set_emergency_mode(self, mode: bool) -> None:
        """Set the emergency mode."""
        self.emergency_mode = mode
        logger.info("Emergency mode set to %s", mode)