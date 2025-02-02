import asyncio
import logging
import json
from typing import Any, Dict

class EmergencyManager:
    """
    EmergencyManager handles emergency procedures such as system health monitoring,
    emergency state persistence, and position calculations.
    """
    def __init__(self, config: Dict[str, Any], market_data: Any = None) -> None:
        """
        Initialize EmergencyManager with configuration and optional market data.

        Args:
            config (Dict[str, Any]): Configuration dictionary.
            market_data (Any, optional): Market data for emergency procedures.
        """
        self.emergency_mode = False
        self.market_data = market_data
        self.logger = logging.getLogger(__name__)
        self.config = {}
        self._load_config(config)

    def _load_config(self, config: Dict[str, Any]) -> None:
        """
        Load configuration for emergency procedures.

        Args:
            config (Dict[str, Any]): Configuration dictionary.
        """
        self.config = config
        # Parse other configuration parameters if needed

    async def check_system_health(self) -> Dict[str, Any]:
        """
        Monitor system health metrics such as latency, data freshness, and position limits.

        Returns:
            Dict[str, Any]: A dictionary containing system health status.
        """
        try:
            # Check if market_data is valid type
            if self.market_data is not None and not hasattr(self.market_data, 'get_recent_prices'):
                raise ValueError("Invalid market data instance")

            # Simulate checking latency and market data freshness.
            await asyncio.sleep(0.1)
            latency = 100  # placeholder for latency in ms
            market_data_fresh = True if self.market_data else False
            # Check position limits from config or default values.
            position_limit = self.config.get("position_limit", 100000)

            status = {
                "healthy": True,
                "latency": latency,
                "market_data_fresh": market_data_fresh,
                "position_limit": position_limit
            }
            return status
        except Exception as e:
            self.logger.error(f"Health check error: {str(e)}")
            return {
                "healthy": False,
                "error": str(e),
                "latency": -1,
                "market_data_fresh": False,
                "position_limit": self.config.get("position_limit", 100000)
            }

    async def save_emergency_state(self) -> bool:
        """
        Save the current emergency state to a JSON file.

        Returns:
            bool: True if state saved successfully, else False.
        """
        try:
            state = {
                "emergency_mode": self.emergency_mode,
                "config": self.config
            }
            # Assuming file path from config or default file, use emergency_state.json
            file_path = self.config.get("state_file", "emergency_state.json")
            # Simulate file write with async sleep
            await asyncio.sleep(0.1)
            with open(file_path, "w") as f:
                json.dump(state, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Save emergency state error: {str(e)}")
            return False

    async def calculate_position_size(self, available_funds: float, risk_factor: float) -> float:
        """
        Calculate position size based on available funds and risk factor.

        Args:
            available_funds (float): Funds available for trading.
            risk_factor (float): Risk factor percentage (e.g., 0.02 for 2%).

        Returns:
            float: The calculated position size.
        """
        try:
            await asyncio.sleep(0.1)
            position_size = float(available_funds) * float(risk_factor)
            return position_size
        except Exception as e:
            self.logger.error(f"Position size calculation error: {str(e)}")
            return 0.0