"""Emergency management system for cryptocurrency trading"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import asyncio
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class EmergencyManager:
    """Manages emergency conditions and shutdown procedures"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.emergency_shutdown = False
        self.shutdown_requested = False
        self.max_data_age_seconds = config.get('max_data_age_seconds', 300)
        self.emergency_price_change_threshold = config.get('emergency_price_change_threshold', 0.1)
        self.volume_spike_threshold = config.get('volume_spike_threshold', 5.0)
        
    def _check_data_freshness(self, data: pd.DataFrame) -> bool:
        """Check if market data is fresh enough"""
        if data.empty:
            logger.warning("Empty market data")
            return False
            
        try:
            latest_time = data.index[-1]
            if isinstance(latest_time, str):
                latest_time = pd.to_datetime(latest_time)
            age = (datetime.now() - latest_time).total_seconds()
            is_fresh = age <= self.max_data_age_seconds
            if not is_fresh:
                logger.warning(f"Stale data detected: {age} seconds old")
            return is_fresh
        except Exception as e:
            logger.error(f"Error checking data freshness: {e}")
            return False
        
    def _check_price_movement(self, data: pd.DataFrame, current_price: float) -> bool:
        """Check for excessive price movement"""
        try:
            if 'price' in data.columns and len(data) > 1:
                last_price = float(data['price'].iloc[-2])
                price_change = abs(current_price - last_price) / last_price
                if price_change > self.emergency_price_change_threshold:
                    logger.warning(f"Emergency: Large price movement: {price_change:.2%}")
                    return True
                return False
            else:
                logger.warning("No price data available for comparison")
                return False
        except Exception as e:
            logger.error(f"Error checking price movement: {e}")
            return False

    def _check_volume_spike(self, data: pd.DataFrame) -> bool:
        """Check for volume spike"""
        try:
            if 'size' in data.columns and len(data) > 1:
                recent_volume = float(data['size'].iloc[-1])
                avg_volume = float(data['size'].iloc[:-1].mean())
                if avg_volume > 0:
                    volume_ratio = recent_volume / avg_volume
                    if volume_ratio > self.volume_spike_threshold:
                        logger.warning(f"Emergency: Volume spike: {volume_ratio:.2f}x average")
                        return True
            return False
        except Exception as e:
            logger.error(f"Error checking volume spike: {e}")
            return False

    async def check_emergency_conditions(self, 
                                      pair: str, 
                                      current_price: float,
                                      market_data: Dict,
                                      websocket: Any = None) -> bool:
        """Check for emergency conditions that would trigger shutdown"""
        try:
            # WebSocket health check
            if websocket and hasattr(websocket, 'last_message_time'):
                time_since_last = (datetime.now() - websocket.last_message_time).total_seconds()
                if time_since_last > self.max_data_age_seconds:
                    logger.warning(f"WebSocket connection stale for {pair}")
                    return True
                    
            # Market data checks
            if pair not in market_data:
                logger.warning(f"No market data for {pair}")
                return False
                
            data = market_data[pair]
            if not isinstance(data, pd.DataFrame):
                logger.error(f"Invalid market data type for {pair}")
                return True
                
            if data.empty:
                logger.error(f"Empty market data for {pair}")
                return True
                
            # Data freshness check
            if not self._check_data_freshness(data):
                logger.warning(f"Market data not fresh for {pair}")
                return True
                
            # Check for emergency conditions
            if self._check_price_movement(data, current_price):
                return True
                
            if self._check_volume_spike(data):
                return True
                
            logger.debug(f"No emergency conditions detected for {pair}")
            return False
            
        except Exception as e:
            logger.error(f"Error checking emergency conditions: {e}")
            return True
            
    async def initiate_emergency_shutdown(self, 
                                        positions: Dict,
                                        execute_trade: Any,
                                        websocket: Any) -> None:
        """Initiate emergency shutdown procedure"""
        try:
            self.emergency_shutdown = True
            self.shutdown_requested = True
            
            # Close all positions
            for pair, position in positions.items():
                try:
                    await execute_trade(
                        pair=pair,
                        side='sell',
                        quantity=position['quantity']
                    )
                except Exception as e:
                    logger.error(f"Failed to close position {pair}: {e}")
                    
            # Stop WebSocket connection
            try:
                await websocket.stop()
            except Exception as e:
                logger.error(f"Failed to stop WebSocket: {e}")
                
        except Exception as e:
            logger.error(f"Emergency shutdown error: {e}")
            self.emergency_shutdown = True
