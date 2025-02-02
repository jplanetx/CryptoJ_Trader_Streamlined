import json
import asyncio
import logging
from typing import Dict, Optional, List
from decimal import Decimal
from pathlib import Path
from datetime import datetime

class EmergencyManager:
    def __init__(self, config_path: str, state_file: str = "emergency_state.json"):
        self.config_path = Path(config_path)
        self.state_file = Path(state_file)
        self.logger = logging.getLogger(__name__)
        self.emergency_mode = False
        self.position_limits = {}
        self._load_config()
        self._load_state()

    def _load_config(self) -> None:
        """Load emergency configuration settings."""
        try:
            with open(self.config_path) as f:
                config = json.load(f)
            self.max_positions = config.get('max_positions', {})
            self.risk_limits = config.get('risk_limits', {})
            self.emergency_thresholds = config.get('emergency_thresholds', {})
        except Exception as e:
            self.logger.error(f"Failed to load emergency config: {str(e)}")
            raise

    def _load_state(self) -> None:
        """Load emergency state from persistence file."""
        try:
            if self.state_file.exists():
                with open(self.state_file) as f:
                    state = json.load(f)
                self.emergency_mode = state.get('emergency_mode', False)
                self.position_limits = state.get('position_limits', {})
                # Convert position limits to Decimal
                self.position_limits = {k: Decimal(str(v)) for k, v in self.position_limits.items()}
        except Exception as e:
            self.logger.error(f"Failed to load emergency state: {str(e)}")
            self._save_state()  # Create new state file if loading fails

    def _save_state(self) -> None:
        """Save current emergency state to persistence file."""
        try:
            state = {
                'emergency_mode': self.emergency_mode,
                'position_limits': {k: str(v) for k, v in self.position_limits.items()},
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Ensure directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write state with atomic operation
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(state, f, indent=2)
            temp_file.replace(self.state_file)
            
        except Exception as e:
            self.logger.error(f"Failed to save emergency state: {str(e)}")
            raise

    async def validate_new_position(self, trading_pair: str, size: float, price: float) -> bool:
        """
        Validate if a new position can be taken based on current system state and limits.

        Args:
            trading_pair (str): The trading pair for the position
            size (float): Position size
            price (float): Current price

        Returns:
            bool: True if position is valid, False otherwise
        """
        try:
            if self.emergency_mode:
                self.logger.warning("Position validation failed: System in emergency mode")
                return False

            position_value = Decimal(str(size)) * Decimal(str(price))
            current_exposure = self.position_limits.get(trading_pair, Decimal('0'))
            max_allowed = Decimal(str(self.max_positions.get(trading_pair, 0)))

            # Check against position limits
            if current_exposure + position_value > max_allowed:
                self.logger.warning(
                    f"Position validation failed: Would exceed position limit for {trading_pair}"
                )
                return False

            # Check risk limits
            risk_limit = Decimal(str(self.risk_limits.get(trading_pair, 0)))
            if position_value > risk_limit:
                self.logger.warning(
                    f"Position validation failed: Exceeds risk limit for {trading_pair}"
                )
                return False

            # Check emergency thresholds
            threshold = Decimal(str(self.emergency_thresholds.get(trading_pair, float('inf'))))
            if position_value > threshold:
                self.logger.warning(
                    f"Position validation failed: Would trigger emergency threshold for {trading_pair}"
                )
                return False

            return True

        except Exception as e:
            self.logger.error(f"Position validation error: {str(e)}")
            return False

    async def emergency_shutdown(self) -> None:
        """Initiate emergency shutdown procedure."""
        try:
            # Set emergency mode first to prevent new positions
            self.emergency_mode = True
            self._save_state()
            
            # Cancel all active orders
            await self._cancel_all_orders()
            
            # Close all positions
            await self._close_all_positions()
            
            # Save final state
            self._save_state()
            
            self.logger.critical("Emergency shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Emergency shutdown error: {str(e)}")
            raise

    async def _cancel_all_orders(self) -> None:
        """Cancel all active orders during emergency shutdown."""
        try:
            # Implementation would connect to exchange service
            self.logger.info("Cancelling all active orders")
            await asyncio.sleep(0.1)  # Placeholder for actual API calls
            
            # Additional cleanup logic would go here
            # For each trading pair:
            # 1. Get all active orders
            # 2. Cancel each order
            # 3. Verify cancellation
            
        except Exception as e:
            self.logger.error(f"Order cancellation error: {str(e)}")
            raise

    async def _close_all_positions(self) -> None:
        """Close all open positions during emergency shutdown."""
        try:
            self.logger.info("Closing all open positions")
            
            # Implementation would:
            # 1. Get all open positions
            # 2. Create market orders to close each position
            # 3. Verify position closure
            
            await asyncio.sleep(0.1)  # Placeholder for actual API calls
            
            # Reset position limits after successful closure
            self.position_limits = {}
            self._save_state()
            
        except Exception as e:
            self.logger.error(f"Position closure error: {str(e)}")
            raise

    def update_position_limits(self, new_limits: Dict[str, float]) -> None:
        """
        Update position limits for trading pairs.

        Args:
            new_limits (Dict[str, float]): New position limits by trading pair
        """
        try:
            # Validate new limits
            for pair, limit in new_limits.items():
                if limit < 0:
                    raise ValueError(f"Invalid negative limit for {pair}")
                self.position_limits[pair] = Decimal(str(limit))
            
            self._save_state()
            self.logger.info(f"Position limits updated: {new_limits}")
            
        except Exception as e:
            self.logger.error(f"Position limits update error: {str(e)}")
            raise

    def get_system_health(self) -> Dict[str, any]:
        """
        Get current system health status.

        Returns:
            Dict[str, any]: System health information
        """
        try:
            # Calculate current exposure percentages
            exposure_percentages = {}
            for pair, current in self.position_limits.items():
                max_allowed = Decimal(str(self.max_positions.get(pair, 0)))
                if max_allowed > 0:
                    exposure_percentages[pair] = (current / max_allowed) * 100
            
            return {
                'emergency_mode': self.emergency_mode,
                'position_limits': {k: float(v) for k, v in self.position_limits.items()},
                'exposure_percentages': {k: float(v) for k, v in exposure_percentages.items()},
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Health status error: {str(e)}")
            return {'error': str(e)}

    async def restore_normal_operation(self) -> bool:
        """
        Attempt to restore system to normal operation mode.

        Returns:
            bool: True if restoration successful, False otherwise
        """
        try:
            if not self.emergency_mode:
                return True

            # Verify system health before restoration
            if not await self._verify_system_health():
                self.logger.warning("System health check failed during restoration attempt")
                return False

            # Verify all positions are within limits
            for pair, current in self.position_limits.items():
                max_allowed = Decimal(str(self.max_positions.get(pair, 0)))
                if current > max_allowed:
                    self.logger.warning(f"Position {pair} exceeds limits during restoration attempt")
                    return False

            self.emergency_mode = False
            self._save_state()
            self.logger.info("Normal operation restored")
            return True

        except Exception as e:
            self.logger.error(f"Restoration error: {str(e)}")
            return False

    async def _verify_system_health(self) -> bool:
        """
        Verify system health status before restoration.

        Returns:
            bool: True if system health checks pass
        """
        try:
            # Implement comprehensive health checks:
            # 1. Verify exchange connectivity
            await asyncio.sleep(0.1)  # Placeholder for connectivity check
            
            # 2. Verify position data consistency
            for pair in self.position_limits:
                if pair not in self.max_positions:
                    self.logger.error(f"Missing max position data for {pair}")
                    return False
            
            # 3. Verify risk limits are properly set
            for pair in self.position_limits:
                if pair not in self.risk_limits:
                    self.logger.error(f"Missing risk limit data for {pair}")
                    return False
            
            # 4. Check for any ongoing critical operations
            # (Implementation specific)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Health verification error: {str(e)}")
            return False

    def reset_emergency_state(self) -> None:
        """Reset emergency state and all associated data."""
        try:
            self.emergency_mode = False
            self.position_limits = {}
            self._save_state()
            self.logger.info("Emergency state reset completed")
        except Exception as e:
            self.logger.error(f"Emergency state reset error: {str(e)}")
            raise