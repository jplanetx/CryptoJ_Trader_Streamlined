"""
This module implements a basic paper trading module for CryptoJ Trader.
It provides a PaperTrader class to simulate trading without using real money,
while maintaining accurate position tracking and risk management.
"""
import json
import logging
import os
import time
from decimal import Decimal
from typing import Dict, Optional, List
from datetime import datetime
# import pandas as pd # Removed pandas import

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.FileHandler('paper_trading.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class PaperTraderError(Exception):
    """Custom exception for paper trading errors"""
    pass

class TradeHistoryManager:
    """Manages trade history persistence and recovery"""
    
    def __init__(self, data_dir: str = "data/trades"):
        """
        Initialize trade history manager
        
        Args:
            data_dir: Directory for storing trade data files
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.current_file = None
        self._init_trade_file()
        logger.info(f"TradeHistoryManager initialized with data directory: {data_dir}")
        
    def _init_trade_file(self) -> None:
        """Initialize new trade history file with date-based naming"""
        date_str = datetime.utcnow().strftime("%Y%m%d")
        self.current_file = os.path.join(self.data_dir, f"trades_{date_str}.json")
        if not os.path.exists(self.current_file):
            self._write_trades([])
            logger.info(f"Created new trade history file: {self.current_file}")
            
    def _write_trades(self, trades: List[Dict]) -> None:
        """Write trades to current file with error handling"""
        try:
            with open(self.current_file, 'w') as f:
                json.dump(trades, f, indent=2, default=str)
            logger.debug(f"Successfully wrote {len(trades)} trades to {self.current_file}")
        except Exception as e:
            logger.error(f"Failed to write trades: {str(e)}")
            raise PaperTraderError(f"Trade persistence failed: {str(e)}")
            
    def save_trade(self, trade: Dict) -> None:
        """
        Save new trade to history file
        
        Args:
            trade: Trade details including timestamp, symbol, side, quantity, price
        """
        try:
            trades = self.load_trades()
            trades.append(trade)
            self._write_trades(trades)
            logger.info(f"Trade saved successfully: {trade}")
        except Exception as e:
            logger.error(f"Failed to save trade: {str(e)}")
            raise PaperTraderError(f"Failed to save trade: {str(e)}")
            
    def load_trades(self, start_date: Optional[datetime] = None) -> List[Dict]:
        """
        Load trades from storage, optionally filtered by date
        
        Args:
            start_date: Optional start date to filter trades
        
        Returns:
            List of trade records
        """
        try:
            if not os.path.exists(self.current_file):
                logger.info(f"No trade history file found at {self.current_file}")
                return []
                
            with open(self.current_file) as f:
                trades = json.load(f)
            if start_date:
                trades = [
                    t for t in trades
                    if datetime.fromisoformat(t['timestamp']) >= start_date
                ]
            logger.debug(f"Loaded {len(trades)} trades from {self.current_file}")
            return trades
        except Exception as e:
            logger.error(f"Failed to load trades: {str(e)}")
            return []
            
    
    

























class Position:
    """Represents a trading position with detailed tracking information"""
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.quantity = Decimal("0")
        self.cost_basis = Decimal("0")
        self.realized_pnl = Decimal("0")
        self.unrealized_pnl = Decimal("0")
        self.average_entry_price = Decimal("0")
        self.last_update_time = None
        self.trades = []  # List to track individual trades
        logger.info(f"New position created for {symbol}")

class PaperTrader:
    def __init__(self, order_executor, market_data_handler=None, risk_controls=None): # Added risk_controls here
        """
        Initialize the PaperTrader with basic attributes and an order executor.

        Parameters:
            order_executor: An instance of OrderExecution to handle order execution
            market_data_handler: Optional MarketDataHandler for price validation
        """
        self.order_executor = order_executor
        self.market_data_handler = market_data_handler
        self.positions = {}  # Maps symbol to Position objects
        self.orders = []
        self.risk_controls = risk_controls # Use risk_controls from constructor
        self.initial_capital = Decimal("10000")  # Default initial capital
        self.current_capital = Decimal("10000")  # Start with initial capital
        self.daily_pnl = Decimal("0")  # Track daily P&L
        self.max_drawdown_level = self._calculate_max_drawdown_level()
        
        # Initialize trade history manager
        self.trade_history = TradeHistoryManager()
        logger.info("PaperTrader initialized with trade history management")

    def _calculate_max_drawdown_level(self) -> Decimal:
        """Calculate the maximum drawdown level."""
        max_drawdown_percent = self.risk_controls.get("max_drawdown", Decimal("0.1")) if self.risk_controls else Decimal("0.1") # Default 10% max drawdown if not set
        level = self.initial_capital - (self.initial_capital * max_drawdown_percent)
        logger.debug(f"Max drawdown level calculated: {level}")
        return level

    def integrate_risk_controls(self, risk_data: Dict) -> None: # Added integrate_risk_controls method
        """Integrate risk controls from a dictionary."""
        if not risk_data:
            logger.warning("Risk data is empty, no risk controls integrated.")
            return
        self.risk_controls = risk_data
        self._update_risk_control_decimals(risk_data)
        self.max_drawdown_level = self._calculate_max_drawdown_level()
        logger.info(f"Risk controls integrated: {self.risk_controls}")

    def _update_risk_control_decimals(self, risk_data: Dict) -> None:
        """Convert risk control values to Decimal type for accurate calculations."""
        if not risk_data:
            return
        
        decimal_fields = ['max_position_size', 'max_drawdown', 'daily_loss_limit']
        for field in decimal_fields:
            if field in risk_data:
                risk_data[field] = Decimal(str(risk_data[field]))
        logger.debug(f"Risk controls converted to Decimal: {risk_data}")

    def place_order(self, order: Dict) -> Dict:
        """
        Place a new order with validation and position tracking.
        
        Args:
            order (Dict): Order details including symbol, type, side, quantity, and optional price
            
        Returns:
            Dict: Order execution result
        """
        try:
            # Validate order first
            self._validate_order(order)
            
            # Convert quantity to Decimal
            order['quantity'] = Decimal(str(order['quantity']))
            
            # Apply risk controls if configured
            if self.risk_controls:
                max_position = self.risk_controls.get('max_position_size')
                if max_position:
                    current_pos = self.positions.get(order['symbol'], Position(order['symbol'])).quantity
                    if current_pos + order['quantity'] > Decimal(str(max_position)):
                        raise PaperTraderError(f"Order exceeds maximum position size of {max_position}")
            
            # Execute order through executor
            result = self.order_executor.execute_order(order)
            
            if result['status'] == 'filled':
                # Update position
                is_buy = order['side'].lower() == 'buy'
                price = Decimal(str(result.get('price', order.get('price', '0'))))
                self.update_position(order['symbol'], order['quantity'], price, is_buy)
                
                # Record trade
                trade_record = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'symbol': order['symbol'],
                    'side': order['side'],
                    'quantity': str(order['quantity']),
                    'price': str(price),
                    'type': order.get('type', 'market')
                }
                self.trade_history.save_trade(trade_record)
                
                # Update daily P&L
                self._update_daily_pnl(order)
                
                logger.info(f"Order executed successfully: {result}")
            else:
                logger.warning(f"Order not filled: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"Order placement failed: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def _validate_order(self, order: Dict) -> None:
        """
        Validate the order to ensure it has the required keys and valid values.
        
        Args:
            order (dict): The order to validate.
        
        Raises:
            PaperTraderError: If the order is invalid.
        """
        required_keys = ["symbol", "quantity", "side"]
        for key in required_keys:
            if key not in order:
                error_msg = f"Order validation failed: Missing required key '{key}' in order: {order}"
                logger.error(error_msg)
                raise PaperTraderError(error_msg)
        
        if not isinstance(order["quantity"], (int, float, Decimal)):
            error_msg = f"Order validation failed: 'quantity' must be a number, got: {type(order['quantity'])}"
            logger.error(error_msg)
            raise PaperTraderError(error_msg)

        if order["side"].lower() not in ["buy", "sell"]:
            error_msg = f"Order validation failed: 'side' must be 'buy' or 'sell', got: '{order['side']}'"
            logger.error(error_msg)
            raise PaperTraderError(error_msg)



    def _update_daily_pnl(self, order: Dict) -> None:
        """Updates daily P&L based on filled order."""
        quantity = Decimal(str(order["quantity"]))
        price = Decimal(str(order.get("price", "0")))
        if order["side"].lower() == "buy":
            self.daily_pnl -= quantity * price
        elif order["side"].lower() == "sell":
            self.daily_pnl += quantity * price
        logger.debug(f"Updated daily P&L: {self.daily_pnl}")

    def update_position(self, symbol: str, quantity: Decimal, price: Decimal, is_buy: bool) -> Position:
        """Update the trading position for a given symbol."""
        start_time = time.time()
        logger.info(f"Updating position for {symbol}: quantity={quantity}, price={price}, is_buy={is_buy}")
        
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol)
        
        position = self.positions[symbol]
        trade_quantity = quantity if is_buy else -quantity
        
        new_quantity = position.quantity + trade_quantity
        if new_quantity < 0:
            error_msg = f"Invalid position size {new_quantity} for symbol {symbol}. Paper trading does not support short selling."
            logger.error(error_msg)
            raise PaperTraderError(error_msg)
