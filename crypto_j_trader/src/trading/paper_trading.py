"""
This module implements a basic paper trading module for CryptoJ Trader.
It provides a PaperTrader class to simulate trading without using real money,
while maintaining accurate position tracking and risk management.
"""
from decimal import Decimal
from typing import Dict, Optional

class PaperTraderError(Exception):
    """Custom exception for paper trading errors"""
    pass

class PaperTrader:
    def __init__(self, order_executor):
        """
        Initialize the PaperTrader with basic attributes and an order executor.

        Parameters:
            order_executor: An instance of OrderExecution to handle order execution

        Attributes:
            positions: A dictionary to track positions for each symbol
            orders: A list to store processed orders
            risk_controls: Risk control parameters
        """
        self.order_executor = order_executor
        self.positions = {}
        self.orders = []
        self.risk_controls = None
        self.initial_capital = Decimal("10000")  # Default initial capital
        self.current_capital = Decimal("10000")  # Start with initial capital
        self.daily_pnl = Decimal("0")  # Track daily P&L
        self.max_drawdown_level = self._calculate_max_drawdown_level() # Initialize max_drawdown_level

    def place_order(self, order: Dict) -> Dict:
        """
        Place a trading order using the order executor.
        
        Parameters:
            order (dict): The order details including symbol, quantity, price, and side
        
        Returns:
            dict: The order execution result from the executor
        
        Raises:
            PaperTraderError: If order validation fails or risk limits are exceeded
            Exception: If order execution fails
        """
        # Validate order
        self._validate_order(order)
        
        # Check risk controls
        self._check_risk_controls(order)
        
        # Update symbol format if needed
        if "symbol" in order:
            symbol = order["symbol"]
            if not "-" in symbol:
                order["symbol"] = f"{symbol[:3]}-{symbol[3:]}"

        # Initialize position if it doesn't exist
        if order["symbol"] not in self.positions:
            self.positions[order["symbol"]] = Decimal("0")

        # Store order in history
        self.orders.append(order)
        
        # Execute order
        result = self.order_executor.execute_order(order)
        
        # Update position based on execution result
        if result["status"] == "filled":
            quantity = Decimal(str(order["quantity"]))
            price = Decimal(str(order.get("price", "0"))) # Default to 0 if price is missing
            if order["side"].lower() == "buy":
                self.current_capital -= quantity * price
            elif order["side"].lower() == "sell":
                self.current_capital += quantity * price
            self._update_daily_pnl(order)
            
            if order["side"].lower() == "sell":
                quantity = -quantity # Make quantity negative for sell orders
            self.update_position(order["symbol"], quantity)
        
        return result

    def _update_daily_pnl(self, order: Dict) -> None:
        """
        Updates daily P&L based on filled order.
        """
        quantity = Decimal(str(order["quantity"]))
        price = Decimal(str(order.get("price", "0"))) # Default to 0 if price is missing
        if order["side"].lower() == "buy":
            self.daily_pnl -= quantity * price  # Cost of purchase
        elif order["side"].lower() == "sell":
            self.daily_pnl += quantity * price  # Revenue from sale

    def update_position(self, symbol: str, quantity: Decimal) -> Decimal:
        """
        Update the trading position for a given symbol.
        
        Parameters:
            symbol (str): The trading symbol (e.g., 'BTC-USD')
            quantity (Decimal): The change in quantity (positive for buys, negative for sells)
        
        Returns:
            Decimal: The updated position for the symbol
        
        Raises:
            PaperTraderError: If the update would result in a negative position
        """
        if symbol not in self.positions:
            self.positions[symbol] = Decimal("0")
            
        new_position = self.positions[symbol] + quantity
        if new_position < 0:
            raise PaperTraderError(f"Insufficient position for {symbol}")
            
        self.positions[symbol] = new_position
        return new_position

    def integrate_risk_controls(self, risk_data: Dict) -> None:
        """
        Set or update risk control measures for paper trading.
        
        Also updates the max_drawdown_level based on the new risk_data.
        """
        self.risk_controls = risk_data
        self._update_risk_control_decimals(risk_data) # Convert risk control values to Decimal
        self.max_drawdown_level = self._calculate_max_drawdown_level() # Update max_drawdown_level

    def _update_risk_control_decimals(self, risk_data: Dict) -> None:
        """
        Convert risk control values to Decimal.
        """
        if "max_position_size" in risk_data:
            risk_data["max_position_size"] = Decimal(str(risk_data["max_position_size"]))
        if "max_drawdown" in risk_data:
            risk_data["max_drawdown"] = Decimal(str(risk_data["max_drawdown"]))
        if "daily_loss_limit" in risk_data:
            risk_data["daily_loss_limit"] = Decimal(str(risk_data["daily_loss_limit"]))
        

    def _calculate_max_drawdown_level(self) -> Decimal:
        """
        Calculate the maximum drawdown level based on initial capital and max_drawdown percentage.
        """
        max_drawdown_percent = self.risk_controls.get("max_drawdown", Decimal("0")) if self.risk_controls else Decimal("0")
        return self.initial_capital - (self.initial_capital * max_drawdown_percent)

    def get_position(self, symbol: str) -> Optional[Decimal]:
        """
        Get the current position for a symbol.
        
        Parameters:
            symbol (str): The trading symbol
            
        Returns:
            Optional[Decimal]: The current position or None if no position exists
        """
        return self.positions.get(symbol)

    def _validate_order(self, order: Dict) -> None:
        """
        Validate order parameters.
        
        Parameters:
            order (dict): The order to validate
            
        Raises:
            PaperTraderError: If the order is invalid
        """
        required_fields = ["symbol", "side", "quantity"]
        for field in required_fields:
            if field not in order:
                raise PaperTraderError(f"Missing required field: {field}")
                
        if order["side"].lower() not in ["buy", "sell"]:
            raise PaperTraderError(f"Invalid order side: {order['side']}")
            
        try:
            quantity = Decimal(str(order["quantity"]))
            if quantity <= 0:
                raise PaperTraderError("Order quantity must be positive")
        except (TypeError, ValueError):
            raise PaperTraderError("Invalid order quantity")

    def _check_risk_controls(self, order: Dict) -> None:
        """
        Check if order complies with risk controls.
        
        Parameters:
            order (dict): The order to check
            
        Raises:
            PaperTraderError: If the order would violate risk controls
        """
        if not self.risk_controls:
            return
            
        quantity = Decimal(str(order["quantity"]))
        symbol = order["symbol"]
        current_position = self.positions.get(symbol, Decimal("0"))
        
        # Check maximum position size
        if "max_position_size" in self.risk_controls:
            max_size = self.risk_controls["max_position_size"]
            if order["side"].lower() == "buy":
                if current_position + quantity > max_size:
                    raise PaperTraderError(f"Order would exceed maximum position size of {max_size}")

        # Check max drawdown
        if "max_drawdown" in self.risk_controls:
            max_drawdown_percent = self.risk_controls["max_drawdown"]
            drawdown_value = self.initial_capital - self.current_capital
            max_drawdown_value = self.initial_capital * (max_drawdown_percent / 100)
            if drawdown_value > max_drawdown_value: # Changed to only check drawdown_value, not potential order impact
                raise PaperTraderError(
                    f"Order would exceed maximum drawdown of {max_drawdown_percent}%"
                )
        
        # Check daily loss limit
        if "daily_loss_limit" in self.risk_controls:
            daily_loss_limit = self.risk_controls["daily_loss_limit"]
            if self.daily_pnl < -daily_loss_limit: # Changed to only check daily_pnl, not potential order impact
                raise PaperTraderError(
                    f"Order would exceed daily loss limit of {daily_loss_limit}"
                )