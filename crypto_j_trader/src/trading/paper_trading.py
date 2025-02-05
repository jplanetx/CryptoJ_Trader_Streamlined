"""
This module implements a basic paper trading module for CryptoJ Trader.
It provides a PaperTrader class to simulate trading without using real money,
while maintaining accurate position tracking and risk management.
"""
import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Optional, List

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
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.current_file = None
        self._init_trade_file()
        logger.info(f"TradeHistoryManager initialized with data directory: {data_dir}")
        
    def _init_trade_file(self) -> None:
        # Use timezone-aware UTC now
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        self.current_file = os.path.join(self.data_dir, f"trades_{date_str}.json")
        if not os.path.exists(self.current_file):
            self._write_trades([])
            logger.info(f"Created new trade history file: {self.current_file}")
            
    def _write_trades(self, trades: List[Dict]) -> None:
        try:
            with open(self.current_file, 'w') as f:
                json.dump(trades, f, indent=2, default=str)
            logger.debug(f"Successfully wrote {len(trades)} trades to {self.current_file}")
        except Exception as e:
            logger.error(f"Failed to write trades: {str(e)}")
            raise PaperTraderError(f"Trade persistence failed: {str(e)}")
            
    def save_trade(self, trade: Dict) -> None:
        try:
            trades = self.load_trades()
            trades.append(trade)
            self._write_trades(trades)
            logger.info(f"Trade saved successfully: {trade}")
        except Exception as e:
            logger.error(f"Failed to save trade: {str(e)}")
            raise PaperTraderError(f"Failed to save trade: {str(e)}")
            
    def load_trades(self, start_date: Optional[datetime] = None) -> List[Dict]:
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
    def __init__(self, order_executor, market_data_handler=None, risk_controls=None):
        """
        Initialize the PaperTrader with basic attributes and an order executor.

        Parameters:
            order_executor: An instance of OrderExecution to handle order execution
            market_data_handler: Optional MarketDataHandler for price validation
            risk_controls: Optional risk controls dictionary.
        """
        self.order_executor = order_executor
        self.market_data_handler = market_data_handler
        self.positions = {}  # Maps symbol to Position objects
        self.orders = []  # Stores all order results
        self.risk_controls = risk_controls  # Use risk_controls from constructor
        self.initial_capital = Decimal("10000")  # Default initial capital
        self.current_capital = Decimal("10000")  # Start with initial capital
        self.daily_pnl = Decimal("0")  # Track daily P&L
        self.max_drawdown_level = self._calculate_max_drawdown_level()
        self.trade_history = TradeHistoryManager()
        logger.info("PaperTrader initialized with trade history management")
        self.pending_trailing_stops = {}

    def _calculate_max_drawdown_level(self) -> Decimal:
        max_drawdown_percent = (self.risk_controls.get("max_drawdown", Decimal("0.1"))
                                if self.risk_controls else Decimal("0.1"))
        level = self.initial_capital - (self.initial_capital * max_drawdown_percent)
        logger.debug(f"Max drawdown level calculated: {level}")
        return level

    def integrate_risk_controls(self, risk_data: Dict) -> None:
        if not risk_data:
            logger.warning("Risk data is empty, no risk controls integrated.")
            return
        self.risk_controls = risk_data
        self._update_risk_control_decimals(risk_data)
        self.max_drawdown_level = self._calculate_max_drawdown_level()
        logger.info(f"Risk controls integrated: {self.risk_controls}")

    def _update_risk_control_decimals(self, risk_data: Dict) -> None:
        if not risk_data:
            return
        decimal_fields = ['max_position_size', 'max_drawdown', 'daily_loss_limit']
        for field in decimal_fields:
            if field in risk_data:
                risk_data[field] = Decimal(str(risk_data[field]))
        logger.debug(f"Risk controls converted to Decimal: {risk_data}")

    def place_order(self, order: Dict) -> Dict:
        # Check overall risk limits (e.g., drawdown) before processing order
        if self.current_capital <= self.max_drawdown_level:
            error_msg = "Risk limit exceeded: drawdown limit reached"
            logger.error(error_msg)
            result = {'status': 'error', 'message': error_msg}
            self.orders.append(result)
            return result

        self._validate_order(order)
        order['quantity'] = Decimal(str(order['quantity']))

        # Enforce risk control based on max_position_size for buy orders
        if self.risk_controls:
            max_position = self.risk_controls.get('max_position_size')
            if max_position and order['side'].lower() == 'buy':
                current_pos = self.get_position(order['symbol'])
                if current_pos + order['quantity'] > max_position:
                    error_msg = f"Order exceeds maximum position size of {max_position}"
                    logger.error(error_msg)
                    result = {'status': 'error', 'message': error_msg}
                    self.orders.append(result)
                    return result
        
        # Enforce daily loss limit
        daily_loss_limit = self.risk_controls.get('daily_loss_limit')
        if daily_loss_limit is not None:
            potential_pnl = self._calculate_potential_pnl(order)
            if self.daily_pnl + potential_pnl < -daily_loss_limit:
                error_msg = f"Order would exceed daily loss limit of {daily_loss_limit}"
                logger.error(error_msg)
                result = {'status': 'error', 'message': error_msg}
                self.orders.append(result)
                return result

        trigger_stop = False  # flag indicating immediate stop-loss trigger
        # Handle stop-loss orders
        if order.get('type') == 'stop-loss':
            current_price = Decimal(str(self.market_data_handler.get_current_price(order['symbol'])))
            stop_price = Decimal(str(order['stop_price']))
            if order['side'].lower() == 'sell':
                if current_price <= stop_price:
                    logger.info(f"Stop-loss triggered for {order['symbol']} (sell) at current price {current_price}")
                    order['type'] = 'market'
                    trigger_stop = True
                else:
                    if order.get('trailing'):
                        self.pending_trailing_stops[order['symbol']] = order.copy()
                        logger.info(f"Trailing stop-loss order pending for {order['symbol']}")
                    return {'status': 'error', 'message': 'pending'}
            elif order['side'].lower() == 'buy':
                if current_price >= stop_price:
                    logger.info(f"Stop-loss triggered for {order['symbol']} (buy) at current price {current_price}")
                    order['type'] = 'market'
                    trigger_stop = True
                else:
                    if order.get('trailing'):
                        self.pending_trailing_stops[order['symbol']] = order.copy()
                        logger.info(f"Trailing stop-loss order pending for {order['symbol']}")
                    return {'status': 'error', 'message': 'pending'}

        # Execute the order through the executor
        result = self.order_executor.execute_order(order)
        if 'product_id' not in result:
            result['product_id'] = order['symbol']

        # Always record the order result returned
        # If order is filled, attempt to update position and log trade details.
        if result.get('status') == 'filled':
            is_buy = order['side'].lower() == 'buy'
            # Use price from executor if available; otherwise fallback to order price
            price = Decimal(str(result.get('price', order.get('price', '0'))))
            try:
                self.update_position(
                    order['symbol'],
                    order['quantity'],
                    price,
                    is_buy,
                    trade_type=('stop-loss' if trigger_stop else order.get('type'))
                )
            except PaperTraderError as e:
                error_result = {'status': 'error', 'message': str(e)}
                self.orders.append(error_result)
                return error_result

            trade_record = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'symbol': order['symbol'],
                'side': order['side'],
                'quantity': str(order['quantity']),
                'price': str(price),
                'type': order.get('type', 'market')
            }
            if trigger_stop:
                trade_record['execution_type'] = 'stop-loss'
                trade_record['trigger_price'] = str(order['stop_price'])
            try:
                self.trade_history.save_trade(trade_record)
            except PaperTraderError as e:
                logger.error(f"Trade history persistence error: {str(e)}")
            # Also record trade in the position's trade history if exists
            if order['symbol'] in self.positions:
                self.positions[order['symbol']].trades.append(trade_record)
            # Update daily PnL and current capital accordingly
            self._update_daily_pnl(order)
        # Append the execution result (filled, pending, or error)
        self.orders.append(result)
        return result

    def _validate_order(self, order: Dict) -> None:
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
            
    def _calculate_potential_pnl(self, order: Dict) -> Decimal:
        """
        Calculate potential P&L for an order based on current market conditions.
        """
        quantity = Decimal(str(order["quantity"]))
        price = Decimal(str(order.get("price", "0")))
        if order["side"].lower() == "buy":
            return -quantity * price
        elif order["side"].lower() == "sell":
            return quantity * price
        return Decimal("0")

    def _update_daily_pnl(self, order: Dict) -> None:
        quantity = Decimal(str(order["quantity"]))
        price = Decimal(str(order.get("price", "0")))
        if order["side"].lower() == "buy":
            self.daily_pnl -= quantity * price
        elif order["side"].lower() == "sell":
            self.daily_pnl += quantity * price
        logger.debug(f"Updated daily P&L (before capital update): {self.daily_pnl}")
        # Update current capital as initial capital plus daily PnL
        self.current_capital = self.initial_capital + self.daily_pnl
        logger.debug(f"Current capital updated to: {self.current_capital}")

    def update_position(self, symbol: str, quantity: Decimal, price: Decimal, is_buy: bool, trade_type: Optional[str] = None) -> Position:
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
        # For buy orders, add to cost_basis; for sell orders, reduce it proportionally.
        if is_buy:
            position.cost_basis += quantity * price
        else:
            # Subtract the cost_basis proportional to the quantity sold.
            position.realized_pnl += quantity * (price - position.average_entry_price)
            position.cost_basis -= position.average_entry_price * quantity
        position.quantity = new_quantity
        if new_quantity != 0:
            position.average_entry_price = position.cost_basis / new_quantity
        else:
            position.average_entry_price = Decimal("0")
        position.last_update_time = datetime.now(timezone.utc)
        logger.debug(f"Position updated: {position.__dict__}")
        return position

    def get_position_info(self, symbol: str) -> Dict:
        if symbol not in self.positions:
            return {
                "symbol": symbol,
                "quantity": Decimal("0"),
                "cost_basis": Decimal("0"),
                "realized_pnl": Decimal("0"),
                "unrealized_pnl": Decimal("0"),
                "average_entry_price": Decimal("0")
            }
        position = self.positions[symbol]
        return {
            "symbol": position.symbol,
            "quantity": position.quantity,
            "cost_basis": position.cost_basis,
            "realized_pnl": position.realized_pnl,
            "unrealized_pnl": position.unrealized_pnl,
            "average_entry_price": position.average_entry_price
        }

    def get_position(self, symbol: str) -> Decimal:
        if symbol not in self.positions:
            return Decimal("0")
        return self.positions[symbol].quantity
