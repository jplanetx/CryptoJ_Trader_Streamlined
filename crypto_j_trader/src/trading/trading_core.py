"""
Core trading bot implementation
"""
import logging
from decimal import Decimal
from typing import Dict, Optional, Any
from datetime import datetime
import json

from .market_data_handler import MarketDataHandler
from .exchange_service import ExchangeService
from .risk_management import RiskManager
from .emergency_manager import EmergencyManager
from .health_monitor import HealthMonitor

class TradingBot:
    """
    Main trading bot class implementing core trading functionality
    """
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize trading bot with configuration

        Args:
            config (Dict[str, Any]): Trading bot configuration
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Initialize components
        self.exchange = ExchangeService(
            api_key=config.get('api_key'),
            api_secret=config.get('api_secret'),
            paper_trading=config.get('paper_trading', True)
        )
        
        self.market_data = MarketDataHandler()
        self.risk_manager = RiskManager(config.get('risk', {}))
        self.health_monitor = HealthMonitor(config.get('health', {}))
        
        # Emergency manager expects a file path for state persistence
        emergency_config_path = config.get('emergency_config_path', 'emergency_config.json')
        self.emergency_manager = EmergencyManager(emergency_config_path)
        
        self.positions: Dict[str, Decimal] = {}
        self.is_running = False

    async def start(self) -> None:
        """Start the trading bot"""
        self.is_running = True
        self.logger.info("Trading bot started")
        await self.market_data.start()

    async def stop(self) -> None:
        """Stop the trading bot"""
        self.is_running = False
        self.logger.info("Trading bot stopped")
        await self.market_data.stop()

    async def execute_order(self, symbol: str, side: str, quantity: Decimal, 
                          order_type: str = "market", price: Optional[Decimal] = None) -> Dict[str, Any]:
        """
        Execute a trade order

        Args:
            symbol (str): Trading pair symbol
            side (str): Order side ("buy" or "sell")
            quantity (Decimal): Order quantity
            order_type (str, optional): Order type. Defaults to "market".
            price (Optional[Decimal], optional): Price for limit orders. Defaults to None.

        Returns:
            Dict[str, Any]: Order execution result
        """
        # Validate order with risk manager
        if not self.risk_manager.validate_order({
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "type": order_type,
            "price": price
        }):
            raise ValueError("Order failed risk validation")

        # Check system health
        health_status = await self.health_monitor.check_health()
        if health_status["status"] == "critical":
            raise RuntimeError("System health critical, cannot execute order")

        # Execute order
        try:
            result = await self.exchange.execute_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=order_type,
                price=price
            )
            
            # Update position tracking
            current_position = self.positions.get(symbol, Decimal('0'))
            if side == "buy":
                self.positions[symbol] = current_position + quantity
            else:
                self.positions[symbol] = current_position - quantity

            return result
        except Exception as e:
            self.logger.error(f"Order execution failed: {str(e)}")
            raise

    def get_position(self, symbol: str) -> Decimal:
        """
        Get current position for a symbol

        Args:
            symbol (str): Trading pair symbol

        Returns:
            Decimal: Current position size
        """
        return self.positions.get(symbol, Decimal('0'))

    async def check_health(self) -> Dict[str, Any]:
        """
        Check system health status

        Returns:
            Dict[str, Any]: Health check results
        """
        return await self.health_monitor.check_health()

    async def emergency_shutdown(self) -> None:
        """Initiate emergency shutdown procedure"""
        self.logger.warning("Initiating emergency shutdown")
        await self.emergency_manager.initiate_emergency_shutdown(
            positions=self.positions,
            execute_trade=self.execute_order,
            ws_handler=self.market_data._ws_handler
        )
        await self.stop()