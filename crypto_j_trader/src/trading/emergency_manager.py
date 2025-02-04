"""
Emergency Manager for handling system emergencies and risk events
"""
import json
import asyncio
import logging
from typing import Dict, Optional, List, Union
from decimal import Decimal
from pathlib import Path
from datetime import datetime

class EmergencyManager:
    def __init__(self, config: Union[str, Path, Dict], state_file: str = "emergency_state.json"):
        """
        Initialize EmergencyManager with either a config path or direct configuration

        Args:
            config: Either a path to config file or configuration dictionary
            state_file: Path to state persistence file
        """
        self.logger = logging.getLogger(__name__)
        self.state_file = Path(state_file)
        
        # Initialize default values
        self.emergency_mode = False
        self.position_limits = {}
        self.max_positions = {}
        self.risk_limits = {}
        self.emergency_thresholds = {}
        
        # Load configuration
        if isinstance(config, (str, Path)):
            self.config_path = Path(config)
            self._load_config_from_file()
        else:
            self._load_config_from_dict(config)
        
        # Load state
        self._load_state()
        
        # Log initial configuration
        self.logger.info(f"Initialized with max_positions: {self.max_positions}")
        self.logger.info(f"Risk limits: {self.risk_limits}")

    def _load_config_from_file(self) -> None:
        """Load emergency configuration from file."""
        try:
            with open(self.config_path) as f:
                config = json.load(f)
            self._load_config_from_dict(config)
        except Exception as e:
            self.logger.error(f"Failed to load emergency config file: {str(e)}")
            raise

    def _load_config_from_dict(self, config: Dict) -> None:
        """
        Load emergency configuration from dictionary.

        Args:
            config: Configuration dictionary
        """
        try:
            # Convert string values to Decimal with explicit logging
            self.max_positions = {}
            for k, v in config.get('max_positions', {}).items():
                self.max_positions[k] = Decimal(str(v))
                self.logger.debug(f"Set max position for {k}: {self.max_positions[k]}")
            
            self.risk_limits = {
                k: Decimal(str(v)) for k, v in config.get('risk_limits', {}).items()
            }
            self.emergency_thresholds = {
                k: Decimal(str(v)) for k, v in config.get('emergency_thresholds', {}).items()
            }
            
            # Initialize position limits to zero if not loaded from state
            for pair in self.max_positions.keys():
                if pair not in self.position_limits:
                    self.position_limits[pair] = Decimal('0')
            
        except Exception as e:
            self.logger.error(f"Failed to load emergency config: {str(e)}")
            raise

    async def validate_new_position(self, trading_pair: str, size: float, price: float) -> bool:
        """
        Validate if a new position can be taken based on current system state and limits.

        Args:
            trading_pair: The trading pair for the position
            size: Position size
            price: Current price

        Returns:
            True if position is valid, False otherwise
        """
        try:
            if self.emergency_mode:
                self.logger.warning("Position validation failed: System in emergency mode")
                return False

            size_dec = Decimal(str(size))
            price_dec = Decimal(str(price))
            position_value = size_dec * price_dec
            
            current_exposure = self.position_limits.get(trading_pair, Decimal('0'))
            max_allowed = self.max_positions.get(trading_pair, Decimal('0'))
            
            # Log validation values
            self.logger.debug(f"""
            Validating position:
            Trading Pair: {trading_pair}
            Size: {size_dec}
            Price: {price_dec}
            Position Value: {position_value}
            Current Exposure: {current_exposure}
            Max Allowed: {max_allowed}
            """)

            # Check against position limits
            if current_exposure + size_dec > max_allowed:
                self.logger.warning(
                    f"Position validation failed: Would exceed position limit for {trading_pair}. "
                    f"Current: {current_exposure}, New: {size_dec}, Max: {max_allowed}"
                )
                return False

            # Check risk limits
            risk_limit = self.risk_limits.get(trading_pair, Decimal('0'))
            if position_value > risk_limit:
                self.logger.warning(
                    f"Position validation failed: Exceeds risk limit for {trading_pair}"
                )
                return False

            # Check emergency thresholds
            threshold = self.emergency_thresholds.get(trading_pair, Decimal('inf'))
            if position_value > threshold:
                self.logger.warning(
                    f"Position validation failed: Would trigger emergency threshold for {trading_pair}"
                )
                return False

            return True

        except Exception as e:
            self.logger.error(f"Position validation error: {str(e)}")
            return False

    def _load_state(self) -> None:
        """Load emergency state from persistence file."""
        try:
            # Always initialize position_limits to zero for clean state
            self.position_limits = {
                pair: Decimal('0') for pair in self.max_positions.keys()
            }
            self.emergency_mode = False # Reset emergency mode
            if self.state_file.exists():
                with open(self.state_file) as f:
                    state = json.load(f)
                self.emergency_mode = state.get('emergency_mode', False)
                self.position_limits = {
                    k: Decimal(str(v)) for k, v in state.get('position_limits', {}).items()
                }
            else:
                # Initialize with zero positions if no state exists
                self.position_limits = {
                    pair: Decimal('0') for pair in self.max_positions.keys()
                }
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

    async def emergency_shutdown(self) -> None:
        """Initiate emergency shutdown procedure."""
        try:
            self.emergency_mode = True
            self._save_state()
            self.logger.warning("Emergency shutdown completed")
        except Exception as e:
            self.logger.error(f"Emergency shutdown error: {str(e)}")
            raise

    async def restore_normal_operation(self) -> bool:
        """
        Attempt to restore system to normal operation mode.

        Returns:
            True if restoration successful, False otherwise
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
                max_allowed = self.max_positions.get(pair, Decimal('0'))
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
            True if system health checks pass
        """
        try:
            # For paper trading, always return True
            if not hasattr(self, 'config_path'):
                return True
                
            # Verify position data consistency
            for pair in self.position_limits:
                if pair not in self.max_positions:
                    self.logger.error(f"Missing max position data for {pair}")
                    return False
            
            # Verify risk limits are properly set
            for pair in self.position_limits:
                if pair not in self.risk_limits:
                    self.logger.error(f"Missing risk limit data for {pair}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Health verification error: {str(e)}")
            return False