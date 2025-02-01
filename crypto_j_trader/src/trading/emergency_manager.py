"""Emergency management system for cryptocurrency trading"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import asyncio
import pandas as pd
import numpy as np
import json
import os

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
        self.max_position_close_attempts = config.get('max_position_close_attempts', 3)
        self.position_close_retry_delay = config.get('position_close_retry_delay', 5)
        self.state_file = config.get('emergency_state_file', 'emergency_state.json')
        self.default_btc_price = config.get('default_btc_price', 50000.0)  # Default price for basic checks
        self.system_health_checks = {
            'data_freshness': True,
            'websocket_health': True,
            'position_manager': True,
            'order_executor': True
        }
        self.load_state()
        
    async def validate_new_position(self,
                              pair: str,
                              size: float,
                              portfolio_value: float,
                              market_data: Optional[Dict] = None) -> bool:
        """
        Validate if a new position can be opened given current system state
        
        Args:
            pair: Trading pair
            size: Position size in base currency
            portfolio_value: Current portfolio value
            market_data: Optional market data for additional checks
            
        Returns:
            bool: True if position can be opened, False otherwise
        """
        try:
            logger.debug(f"Validating new position - Pair: {pair}, Size: {size}, Portfolio Value: {portfolio_value}")
            logger.debug(f"Current emergency state - Shutdown: {self.emergency_shutdown}, Requested: {self.shutdown_requested}")
            
            # Block new positions during emergency shutdown
            if self.emergency_shutdown or self.shutdown_requested:
                logger.warning(f"New position blocked for {pair}: System in emergency mode")
                return False
                
            # Check system health
            if not all(self.system_health_checks.values()):
                logger.warning(f"New position blocked for {pair}: System health check failed")
                return False

            # Get current price for position size calculation
            current_price = self.default_btc_price  # Default price for basic validation
                
            # Validate against market conditions if data available
            if market_data and pair in market_data:
                data = market_data[pair]
                
                # Check data freshness
                if not self._check_data_freshness(data):
                    logger.warning(f"New position blocked for {pair}: Stale market data")
                    return False
                    
                # Update current price from market data
                current_price = float(data['price'].iloc[-1])
                
                # Check for extreme market conditions
                if self._check_price_movement(data, current_price):
                    logger.warning(f"New position blocked for {pair}: Extreme price movement")
                    return False
                    
                if self._check_volume_spike(data):
                    logger.warning(f"New position blocked for {pair}: Volume spike detected")
                    return False
            
            # Calculate position size as percentage of portfolio
            position_size_pct = (size * current_price) / portfolio_value if portfolio_value > 0 else float('inf')
            
            # Check against position size limit from config
            max_position_size = self.config.get('risk_management', {}).get('position_size_limit', 0.1)
            if position_size_pct > max_position_size:
                logger.warning(f"New position blocked for {pair}: Position size {position_size_pct:.2%} exceeds limit {max_position_size:.2%}")
                return False
            
            logger.info(f"New position validated for {pair}: size={size}, portfolio_value={portfolio_value}")
            return True
            
        except Exception as e:
            logger.error(f"Error validating new position for {pair}: {e}")
            return False
        
    def load_state(self) -> None:
        """Load persisted emergency state"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.emergency_shutdown = state.get('emergency_shutdown', False)
                    self.shutdown_requested = state.get('shutdown_requested', False)
                    if 'system_health_checks' in state:
                        self.system_health_checks.update(state['system_health_checks'])
                    logger.info("Loaded emergency state")
            else:
                logger.info("No existing state file found, using default values")
        except Exception as e:
            logger.error(f"Failed to load emergency state: {e}")
            
    def save_state(self) -> None:
        """Persist emergency state with proper error handling and atomic writes"""
        try:
            # Prepare state data
            state = {
                'emergency_shutdown': self.emergency_shutdown,
                'shutdown_requested': self.shutdown_requested,
                'system_health_checks': self.system_health_checks,
                'timestamp': datetime.now().isoformat()
            }
            
            # Create temp file for atomic write
            temp_file = f"{self.state_file}.tmp"
            try:
                # Write to temp file first
                with open(temp_file, 'w') as f:
                    json.dump(state, f, indent=2)
                    f.flush()  # Ensure all data is written
                    os.fsync(f.fileno())  # Force flush to disk
                
                # Atomic rename to target file
                os.replace(temp_file, self.state_file)
                logger.info("Emergency state saved successfully")
                
            except Exception as write_error:
                logger.error(f"Failed to write emergency state: {write_error}")
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception as cleanup_error:
                        logger.error(f"Failed to clean up temp file: {cleanup_error}")
                raise
                
        except Exception as e:
            logger.error(f"Failed to save emergency state: {e}")
            
    def _check_data_freshness(self, data: pd.DataFrame) -> bool:
        """Check if market data is fresh enough"""
        if data.empty:
            logger.warning("Empty market data")
            self.system_health_checks['data_freshness'] = False
            return False
            
        try:
            latest_time = data.index[-1]
            if isinstance(latest_time, str):
                latest_time = pd.to_datetime(latest_time)
            age = (datetime.now() - latest_time).total_seconds()
            is_fresh = age <= self.max_data_age_seconds
            if not is_fresh:
                logger.warning(f"Stale data detected: {age} seconds old")
                self.system_health_checks['data_freshness'] = False
            return is_fresh
        except Exception as e:
            logger.error(f"Error checking data freshness: {e}")
            self.system_health_checks['data_freshness'] = False
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
                    self.system_health_checks['websocket_health'] = False
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
            
    async def close_position_with_retry(self,
                                     pair: str,
                                     position: Dict,
                                     execute_trade: Any) -> bool:
        """Attempt to close a position with retries"""
        for attempt in range(self.max_position_close_attempts):
            try:
                logger.info(f"Attempting to close position {pair} (attempt {attempt + 1})")
                await execute_trade(
                    pair=pair,
                    side='sell',
                    quantity=position['quantity']
                )
                logger.info(f"Successfully closed position {pair}")
                return True
            except Exception as e:
                logger.error(f"Failed to close position {pair} (attempt {attempt + 1}): {e}")
                if attempt < self.max_position_close_attempts - 1:
                    await asyncio.sleep(self.position_close_retry_delay)
        return False

    async def initiate_emergency_shutdown(self, 
                                      positions: Dict,
                                      execute_trade: Any,
                                      websocket: Any) -> None:
        """Initiate emergency shutdown procedure"""
        try:
            self.emergency_shutdown = True
            self.shutdown_requested = True
            self.save_state()
            
            # Record emergency trigger time
            shutdown_time = datetime.now()
            logger.warning(f"Emergency shutdown initiated at {shutdown_time}")
            
            # Close all positions with retry mechanism
            position_statuses = {}
            for pair, position in positions.items():
                success = await self.close_position_with_retry(pair, position, execute_trade)
                position_statuses[pair] = "Closed" if success else "Failed to close"
                
            # Stop WebSocket connection
            try:
                await websocket.stop()
                self.system_health_checks['websocket_health'] = False
            except Exception as e:
                logger.error(f"Failed to stop WebSocket: {e}")
                
            # Log final shutdown status
            logger.warning("Emergency shutdown status:")
            logger.warning(f"Positions: {json.dumps(position_statuses, indent=2)}")
            logger.warning(f"System health: {json.dumps(self.system_health_checks, indent=2)}")
            
        except Exception as e:
            logger.error(f"Emergency shutdown error: {e}")
            self.emergency_shutdown = True
            self.save_state()

    def get_system_health(self) -> Dict:
        """Get current system health status"""
        return {
            'emergency_mode': self.emergency_shutdown,
            'system_checks': self.system_health_checks,
            'last_updated': datetime.now().isoformat()
        }

    def reset_emergency_state(self) -> None:
        """Reset emergency state after manual verification"""
        self.emergency_shutdown = False
        self.shutdown_requested = False
        self.system_health_checks = {k: True for k in self.system_health_checks}
        self.save_state()
        logger.info("Emergency state reset")