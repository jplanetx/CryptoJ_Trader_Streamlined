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
import pandas as pd

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
            
    def get_position_history(self, symbol: str) -> pd.DataFrame:
        """
        Get historical position data for analysis
        
        Args:
            symbol: Trading symbol to get history for
        
        Returns:
            DataFrame with position history
        """
        trades = self.load_trades()
        if not trades:
            logger.info(f"No trade history available for {symbol}")
            return pd.DataFrame()
            
        # Filter trades for symbol
        symbol_trades = [t for t in trades if t['symbol'] == symbol]
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(symbol_trades)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            logger.debug(f"Retrieved position history for {symbol}: {len(df)} records")
        return df

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
    def __init__(self, order_executor, market_data_handler=None):
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
        self.risk_controls = None
        self.initial_capital = Decimal("10000")  # Default initial capital
        self.current_capital = Decimal("10000")  # Start with initial capital
        self.daily_pnl = Decimal("0")  # Track daily P&L
        self.max_drawdown_level = self._calculate_max_drawdown_level()
        
        # Initialize trade history manager
        self.trade_history = TradeHistoryManager()
        logger.info("PaperTrader initialized with trade history management")

    def place_order(self, order: Dict) -> Dict:
        """
        Place a trading order using the order executor.
        
        Parameters:
            order (dict): The order details including symbol, quantity, price, and side
        
        Returns:
            dict: The order execution result from the executor
        """
        start_time = time.time()
        try:
            logger.info(f"Attempting to place order: {order}")
            
            # Validate order
            self._validate_order(order)
            
            # Check risk controls
            self._check_risk_controls(order)
            
            # Update symbol format if needed
            symbol = order["symbol"]
            if not "-" in symbol:
                symbol = f"{symbol[:3]}-{symbol[3:]}"
                order["symbol"] = symbol

            # Get order type
            order_type = order.get("type", "market").lower()
            
            # Market order logic
            if order_type == "market":
                if self.market_data_handler:
                    try:
                        market_price = self.market_data_handler.get_current_price(symbol)
                        if market_price:
                            # Apply simulated slippage (0-0.1% for simulation)
                            # Calculate dynamic slippage based on market activity
                            price_history = self.market_data_handler.get_price_history(symbol)
                            volatility = self._calculate_volatility(price_history)
                            slippage = min(volatility, Decimal("0.001"))  # Cap at 0.1%
                            
                            # Apply slippage based on order side
                            if order["side"].lower() == "buy":
                                price = market_price * (1 + slippage)
                            else:
                                price = market_price * (1 - slippage)
                            
                            order["price"] = str(price)
                            order["execution_price"] = str(price)
                            logger.debug(f"Applied slippage of {slippage} to market price: {price}")
                    except Exception as e:
                        error_msg = f"Failed to get market price: {str(e)}"
                        logger.error(error_msg)
                        raise PaperTraderError(error_msg)
                if "price" not in order:
                    raise PaperTraderError("Market price not available for market order")
                
                # For market orders, assume immediate fill
                order["status"] = "filled"
                
            # Limit order logic
            elif order_type == "limit":
                if self.market_data_handler:
                    try:
                        market_price = self.market_data_handler.get_current_price(symbol)
                        if market_price:
                            limit_price = Decimal(str(order["price"]))
                            # Validate limit price
                            self._validate_market_price(symbol, limit_price)
                            
                            logger.debug(f"Limit order processing: market_price={market_price}, limit_price={limit_price}, side={order['side']}")
                            if order["side"].lower() == "buy":
                                if market_price <= limit_price:
                                    order["status"] = "filled"
                                    order["price"] = str(market_price)  # Use market price for fill
                                    logger.info(f"Limit buy order filled at market price: {market_price}, limit_price={limit_price}")
                            else:  # sell
                                if market_price >= limit_price:
                                    order["status"] = "filled"
                                    order["price"] = str(market_price)  # Use market price for fill
                                    logger.info(f"Limit sell order filled at market price: {market_price}, limit_price={limit_price}")
                            else:
                                order["status"] = "pending" # Not filled yet
                                logger.info(f"Limit order pending, market price not reached: {market_price} vs limit {limit_price}, side={order['side']}") # Added side to log
                        else:
                             order["status"] = "rejected" # Could not get market price
                             raise PaperTraderError("Market price not available for limit order validation")
                    except Exception as e:
                        order["status"] = "rejected"
                        error_msg = f"Failed to get market price for limit order: {str(e)}"
                        logger.error(error_msg)
                        raise PaperTraderError(error_msg)
                else:
                    order["status"] = "rejected" # No market data handler
                    raise PaperTraderError("Market data handler required for limit orders")
            # Enhanced stop-loss order logic
            elif order_type == "stop-loss":
                if not self.market_data_handler:
                    order["status"] = "rejected"
                    raise PaperTraderError("Market data handler required for stop-loss orders")

                try:
                    market_price = self.market_data_handler.get_current_price(symbol)
                    if not market_price:
                        order["status"] = "rejected"
                        raise PaperTraderError("Market price not available for stop-loss order validation")

                    # Get stop-loss parameters
                    stop_price = Decimal(str(order["stop_price"]))
                    is_trailing = order.get("trailing", False)
                    trail_offset = Decimal(str(order.get("trail_offset", "0"))) if is_trailing else Decimal("0")
# Update stop price for trailing stops
if is_trailing:
    # Save current highest/lowest prices for trailing
    if order["side"].lower() == "sell":
        # For sell orders, stop trails below market price
        if "last_high" not in order:
            order["last_high"] = market_price
            stop_price = market_price * (1 - trail_offset)
        elif market_price > order["last_high"]:
            order["last_high"] = market_price
            stop_price = market_price * (1 - trail_offset)
    else:  # buy stop
        if "last_low" not in order:
            order["last_low"] = market_price
            stop_price = market_price * (1 + trail_offset)
        elif market_price < order["last_low"]:
            order["last_low"] = market_price
            stop_price = market_price * (1 + trail_offset)
                            stop_price = min(stop_price, new_stop)

                    logger.debug(f"Stop-loss processing: {symbol} {order['side']} "
                              f"Market={market_price} Stop={stop_price} "
                              f"Trailing={is_trailing} Offset={trail_offset}")

                    # Check trigger conditions
                    # For stop-loss orders, price must move against the position
                    if ((order["side"].lower() == "sell" and market_price <= stop_price) or
                        (order["side"].lower() == "buy" and market_price >= stop_price)):
                        order["status"] = "filled"
                        
                                
                        # Calculate dynamic slippage based on market volatility
                        price_history = self.market_data_handler.get_price_history(symbol)
                        volatility = self._calculate_volatility(price_history)
                        base_slippage = Decimal("0.001")  # 0.1% baseline
                        dynamic_slippage = min(base_slippage + (volatility * Decimal("0.005")), Decimal("0.01"))
                        
                        # Apply slippage to execution price
                        if order["side"].lower() == "sell":
                            price = market_price * (1 - dynamic_slippage)
                        else:
                            price = market_price * (1 + dynamic_slippage)
                        
                        # Update order with execution details
                        order.update({
                            "price": str(price),
                            "status": "filled",
                            "execution_type": "stop-loss",
                            "trigger_price": str(stop_price),
                            "slippage": str(dynamic_slippage),
                            "execution_price": str(price)
                        })
                        logger.info(f"Stop-loss {order['side']} triggered: {symbol} "
                                  f"Market: {market_price} Stop: {stop_price} "
                                  f"Executed at: {price} Slippage: {dynamic_slippage:.4f}")
                    else:
                        order["status"] = "pending"
                        logger.info(f"Stop-loss {order['side']} pending: {symbol} "
                                  f"Market: {market_price} Stop: {stop_price}")

                except Exception as e:
                    order["status"] = "rejected"
                    error_msg = f"Stop-loss order failed: {str(e)}"
                    logger.error(error_msg)
                    raise PaperTraderError(error_msg)
            else:
                order["status"] = "rejected"
                raise PaperTraderError(f"Invalid order type: {order_type}")

            if order["status"] == "filled":
                # Store order with timestamp
                order["timestamp"] = self._get_current_timestamp()
                self.orders.append(order)
                
                # Execute order (in paper trading context, this is just updating internal state)
                result = self.order_executor.execute_order(order) # Keep this for consistency, even if it's a mock
            else:
                result = {"status": order["status"], "message": f"Order status: {order['status']}"} # For pending/rejected orders
            
            # Update position based on execution result
            if result["status"] == "filled":
                quantity = Decimal(str(order["quantity"]))
                price = Decimal(str(order["price"]))
                is_buy = order["side"].lower() == "buy"
                
                # Update capital
                trade_value = quantity * price
                if is_buy:
                    self.current_capital -= trade_value
                else:
                    self.current_capital += trade_value
                
                # Update position with detailed tracking
                position = self.update_position(symbol, quantity, price, is_buy)
                
                # Update daily P&L
                self._update_daily_pnl(order)
                
                # Save trade to history
                trade_record = {
                    "timestamp": order["timestamp"],
                    "symbol": symbol,
                    "side": order["side"],
                    "quantity": str(quantity),
                    "price": str(price),
                    "value": str(trade_value),
                    "position_size": str(position.quantity),
                    "cost_basis": str(position.cost_basis),
                    "realized_pnl": str(position.realized_pnl)
                }
                self.trade_history.save_trade(trade_record)
                logger.info(f"Trade executed and recorded: {trade_record}")
                
                # Add detailed execution info to result
                result.update({
                    "execution_price": str(price),
                    "position_size": str(position.quantity),
                    "avg_entry_price": str(position.average_entry_price),
                    "realized_pnl": str(position.realized_pnl)
                })
            
            end_time = time.time()
            duration = end_time - start_time
            logger.debug(f"Order processing time: {duration:.4f} seconds, Order: {order}")
            return result
            
        except PaperTraderError as pe:
            logger.error(f"PaperTraderError in place_order: {pe}")
            raise pe # Re-raise PaperTraderError to propagate it
        except Exception as e:
            error_msg = f"Unexpected error in order execution: {str(e)}, Order details: {order}"
            logger.exception(error_msg) # Use logger.exception to capture stack trace
            raise PaperTraderError(f"Order execution failed due to unexpected error: {str(e)}")

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
            error_msg = f"Insufficient position for {symbol}"
            logger.error(error_msg)
            raise PaperTraderError(error_msg)
        
        # Update cost basis and average entry price
        if is_buy:
            # For buys, update cost basis and quantity
            old_value = position.quantity * position.average_entry_price if position.quantity > 0 else Decimal("0")
            new_value = quantity * price
            total_value = old_value + new_value
            position.quantity = new_quantity
            position.cost_basis = total_value
            position.average_entry_price = total_value / position.quantity
        else:
            # For sells, calculate realized P&L first
            avg_cost_per_unit = position.cost_basis / position.quantity if position.quantity > 0 else Decimal("0")
            realized_pnl = (price - avg_cost_per_unit) * quantity
            position.realized_pnl += realized_pnl
            
            # Update position size and cost basis proportionally
            position.quantity = new_quantity
            if new_quantity > 0:
                # Adjust cost basis based on proportion of position sold
                remaining_ratio = new_quantity / position.quantity
                position.cost_basis = position.cost_basis * remaining_ratio
                position.average_entry_price = position.cost_basis / position.quantity
            else:
                # Position closed, reset cost basis and average entry
                position.cost_basis = Decimal("0")
                position.average_entry_price = Decimal("0")
        
        position.last_update_time = self._get_current_timestamp()
        
        # Add trade to position history
        trade_record = {
            "timestamp": position.last_update_time,
            "side": "buy" if is_buy else "sell",
            "quantity": str(quantity),
            "price": str(price),
            "cost_basis": str(position.cost_basis),
            "realized_pnl": str(realized_pnl if not is_buy else Decimal("0")),
            "type": "market",  # Default type
            "average_entry_price": str(position.average_entry_price),
            "execution_details": {  # Add execution details
                "slippage": "0",
                "trigger_price": None,
                "execution_type": "standard"
            }
        }
        position.trades.append(trade_record)
        
        logger.info(f"Position updated: {self.get_position_info(symbol)}")
        end_time = time.time()
        duration = end_time - start_time
        logger.debug(f"Position update time: {duration:.4f} seconds, Symbol: {symbol}, Quantity: {quantity}")
        return position

    def _get_current_timestamp(self) -> str:
        """Get current UTC timestamp in ISO format"""
        return datetime.utcnow().isoformat()

    def _validate_market_price(self, symbol: str, price: Decimal) -> bool:
        """Validate order price against current market data if available."""
        start_time = time.time()
        if not self.market_data_handler:
            return True
            
        try:
            market_price = self.market_data_handler.get_current_price(symbol)
            if market_price is None:
                return True
                
            # For limit and stop orders, check price against market
            if market_price:
                deviation = abs(price - market_price) / market_price
                if deviation > Decimal("0.10"):  # 10% threshold
                    error_msg = "price too far from market price"
                    logger.warning(f"Price deviation of {deviation:.2%} exceeds threshold")
                    raise PaperTraderError(error_msg)
            return True
        finally:
            end_time = time.time()
            duration = end_time - start_time
            logger.debug(f"Market price validation time: {duration:.4f} seconds, Symbol: {symbol}, Price: {price}")

    def get_position_info(self, symbol: str) -> dict:
        """Get detailed position information for a symbol."""
        position = self.positions.get(symbol)
        if not position:
            return {
                "symbol": symbol,
                "quantity": "0",
                "cost_basis": "0",
                "average_entry": "0",
                "realized_pnl": "0",
                "unrealized_pnl": "0",
                "last_update": None
            }
            
        return {
            "symbol": symbol,
            "quantity": str(position.quantity),
            "cost_basis": str(position.cost_basis),
            "average_entry": str(position.average_entry_price),
            "realized_pnl": str(position.realized_pnl),
            "unrealized_pnl": str(position.unrealized_pnl),
            "last_update": position.last_update_time
        }

    def get_trade_history(self, symbol: Optional[str] = None, start_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Get trade history for analysis
        
        Args:
            symbol: Optional symbol to filter trades
            start_date: Optional start date to filter trades
        
        Returns:
            DataFrame with trade history
        """
        try:
            df = self.trade_history.get_position_history(symbol)
            if start_date and not df.empty:
                df = df[df.index >= start_date]
            logger.info(f"Retrieved trade history for symbol={symbol}, start_date={start_date}. DataFrame shape: {df.shape}")
            return df
        except Exception as e:
            logger.error(f"Failed to retrieve trade history: {str(e)}")
            return pd.DataFrame()

    def integrate_risk_controls(self, risk_data: Dict) -> None:
        """Set or update risk control measures for paper trading."""
        logger.info(f"Integrating risk controls: {risk_data}")
        self.risk_controls = risk_data
        self._update_risk_control_decimals(risk_data)
        self.max_drawdown_level = self._calculate_max_drawdown_level()
        logger.info(f"Risk controls integrated and max drawdown level updated.")

    def _update_risk_control_decimals(self, risk_data: Dict) -> None:
        """Convert risk control values to Decimal."""
        if "max_position_size" in risk_data:
            risk_data["max_position_size"] = Decimal(str(risk_data["max_position_size"]))
        if "max_drawdown" in risk_data:
            risk_data["max_drawdown"] = Decimal(str(risk_data["max_drawdown"]))
        if "daily_loss_limit" in risk_data:
            risk_data["daily_loss_limit"] = Decimal(str(risk_data["daily_loss_limit"]))
        logger.debug("Risk control values converted to Decimal.")

    def _calculate_max_drawdown_level(self) -> Decimal:
        """Calculate the maximum drawdown level based on initial capital and max_drawdown percentage."""
        max_drawdown_percent = self.risk_controls.get("max_drawdown", Decimal("0")) if self.risk_controls else Decimal("0")
        level = self.initial_capital - (self.initial_capital * max_drawdown_percent)
        logger.debug(f"Max drawdown level calculated: {level}")
        return level

    def _calculate_volatility(self, price_history: List[Decimal]) -> Decimal:
        """
        Calculate price volatility using standard deviation of returns.
        
        Args:
            price_history: List of historical prices
            
        Returns:
            Decimal: Volatility measure (0-1 scale)
        """
        if not price_history or len(price_history) < 2:
            return Decimal("0.001")  # Default low volatility if insufficient data
            
        try:
            # Calculate returns
            returns = []
            for i in range(1, len(price_history)):
                prev_price = price_history[i-1]
                curr_price = price_history[i]
                if prev_price > 0:  # Avoid division by zero
                    returns.append((curr_price - prev_price) / prev_price)
                    
            if not returns:
                return Decimal("0.001")
                
            # Calculate standard deviation
            mean_return = sum(returns) / len(returns)
            squared_diff_sum = sum((r - mean_return) ** 2 for r in returns)
            volatility = Decimal(str((squared_diff_sum / len(returns)) ** 0.5))
            
            # Cap volatility at reasonable levels (0.1% to 10%)
            return max(min(volatility, Decimal("0.1")), Decimal("0.001"))
            
        except Exception as e:
            logger.warning(f"Error calculating volatility: {e}. Using default.")
            return Decimal("0.001")

    def get_position(self, symbol: str) -> Optional[Decimal]:
        """Get the current position for a symbol."""
        position = self.positions.get(symbol)
        if position:
            logger.debug(f"Retrieved position for {symbol}: {position.quantity}")
            return position.quantity
        else:
            logger.debug(f"No position found for {symbol}")
            return Decimal("0")

    def _validate_order(self, order: Dict) -> None:
        """Validate order parameters."""
        required_fields = ["symbol", "side", "quantity"]
        for field in required_fields:
            if field not in order:
                error_msg = f"Missing required field: {field}"
                logger.error(error_msg)
                raise PaperTraderError(error_msg)
                
        if order["side"].lower() not in ["buy", "sell"]:
            error_msg = f"Invalid order side: {order['side']}"
            logger.error(error_msg)
            raise PaperTraderError(error_msg)
            
        try:
            quantity = Decimal(str(order["quantity"]))
            if quantity <= 0:
                error_msg = "Order quantity must be positive"
                logger.error(error_msg)
                raise PaperTraderError(error_msg)
        except (TypeError, ValueError):
            error_msg = "Invalid order quantity"
            logger.error(error_msg)
            raise PaperTraderError(error_msg)
        logger.debug(f"Order validated successfully: {order}")

    def _check_risk_controls(self, order: Dict) -> None:
        """Check if order complies with risk controls."""
        if not self.risk_controls:
            logger.debug("Risk controls not set, skipping checks.")
            return
            
        quantity = Decimal(str(order["quantity"]))
        symbol = order["symbol"]
        position = self.positions.get(symbol)
        current_position = position.quantity if position else Decimal("0")
        logger.debug(f"Checking risk controls for order: {order}, current_position: {current_position}")
        
        # Check maximum position size
        if "max_position_size" in self.risk_controls:
            max_size = self.risk_controls["max_position_size"]
            if order["side"].lower() == "buy":
                if current_position + quantity > max_size:
                    error_msg = f"Order would exceed maximum position size of {max_size}"
                    logger.warning(error_msg)
                    raise PaperTraderError(error_msg)

        # Check max drawdown
        if "max_drawdown" in self.risk_controls:
            max_drawdown_percent = self.risk_controls["max_drawdown"]
            drawdown_value = self.initial_capital - self.current_capital
            max_drawdown_value = self.initial_capital * (max_drawdown_percent / Decimal("100"))
            if drawdown_value > max_drawdown_value:
                error_msg = f"Order would exceed maximum drawdown of {max_drawdown_percent}%"
                logger.warning(error_msg)
                raise PaperTraderError(error_msg)
        
        # Check daily loss limit
        if "daily_loss_limit" in self.risk_controls:
            daily_loss_limit = self.risk_controls["daily_loss_limit"]
            if self.daily_pnl < -daily_loss_limit:
                error_msg = f"Order would exceed daily loss limit of {daily_loss_limit}"
                logger.warning(error_msg)
                raise PaperTraderError(error_msg)
        logger.debug("Risk controls passed for order.")
