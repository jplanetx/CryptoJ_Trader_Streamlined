from typing import List, Optional, Dict, Any
import logging
import json
import asyncio
from .trading_core import validate_trading_pair

class MarketDataService:
    """
    MarketDataService class for handling market data operations and price history.
    Manages both historical and real-time price data through REST and WebSocket connections.
    """
    def __init__(self):
        """Initialize MarketDataService instance."""
        self.logger = logging.getLogger(__name__)
        self.price_history: Dict[str, List[float]] = {}
        self.current_prices: Dict[str, float] = {}
        self.exchange_service = None
        self._websocket_task = None
        self._running = False

    async def initialize_price_history(self, symbols: List[str], history_days: int, exchange_service: Any) -> None:
        """
        Initialize price history for specified trading pairs.

        Args:
            symbols (List[str]): List of trading pair symbols
            history_days (int): Number of days of historical data to fetch
            exchange_service (Any): Exchange service instance for data fetching

        Raises:
            TypeError: If symbols is not a list of strings or history_days is not an int
            ValueError: If history_days is negative
        """
        if not isinstance(symbols, list) or not all(isinstance(s, str) for s in symbols):
            raise TypeError("symbols must be a list of strings")
            
        if not isinstance(history_days, int):
            raise TypeError(f"history_days must be an integer, got {type(history_days)}")
            
        if history_days < 0:
            raise ValueError("history_days cannot be negative")

        try:
            historical_data = await exchange_service.get_historical_data(symbols, history_days)
            if not isinstance(historical_data, dict):
                raise TypeError(f"Historical data must be a dictionary, got {type(historical_data)}")

            for symbol, prices in historical_data.items():
                if not isinstance(prices, (list, tuple)):
                    self.logger.warning(f"Invalid price data format for {symbol}: {type(prices)}")
                    continue
                    
                self.price_history[symbol] = [float(p) for p in prices]  # Ensure all prices are floats
                if self.price_history[symbol]:  # Update current price if history exists
                    self.current_prices[symbol] = self.price_history[symbol][-1]
        except Exception as e:
            self.logger.error(f"Error initializing price history: {str(e)}")
            raise

    async def get_recent_prices(self, trading_pair: str) -> List[float]:
        """
        Get recent price history for a trading pair.

        Args:
            trading_pair (str): Trading pair identifier (e.g., "BTC-USD")

        Returns:
            List[float]: List of recent prices

        Raises:
            TypeError: If trading_pair is not a string
        """
        try:
            if not isinstance(trading_pair, str):
                self.logger.error(f"Invalid trading pair type: {type(trading_pair)}")
                raise TypeError(f"Trading pair must be a string, got {type(trading_pair)}")

            if not validate_trading_pair(trading_pair):
                self.logger.error(f"Invalid trading pair format: {trading_pair}")
                return []

            return self.price_history.get(trading_pair, [])
        except Exception as e:
            self.logger.error(f"Error retrieving recent prices: {str(e)}")
            return []

    async def update_price_history(self, trading_pair: str, price: float) -> None:
        """
        Update price history for a trading pair.

        Args:
            trading_pair (str): Trading pair identifier
            price (float): Current price

        Raises:
            TypeError: If trading_pair is not a string or price is not a number
            ValueError: If price is negative
        """
        if not isinstance(trading_pair, str):
            self.logger.error(f"Trading pair must be a string, got {type(trading_pair)}")
            raise TypeError(f"Trading pair must be a string, got {type(trading_pair)}")
        
        if not isinstance(price, (int, float)):
            self.logger.error(f"Price must be a number, got {type(price)}")
            raise TypeError(f"Price must be a number, got {type(price)}")
        
        price_float = float(price)
        if price_float < 0:
            self.logger.error(f"Price cannot be negative: {price_float}")
            raise ValueError("Price cannot be negative")

        try:
            # Update current price
            self.current_prices[trading_pair] = price_float

            # Initialize price history if needed
            if trading_pair not in self.price_history:
                self.price_history[trading_pair] = []
            
            # Update price history with validation
            self.price_history[trading_pair].append(price_float)
            
            # Keep only recent history (last 100 prices)
            max_history = 100
            self.price_history[trading_pair] = self.price_history[trading_pair][-max_history:]
            
        except Exception as e:
            self.logger.error(f"Error updating price history: {str(e)}")
            raise

    async def subscribe_price_updates(self, symbols: List[str]) -> None:
        """
        Subscribe to real-time price updates for specified symbols.

        Args:
            symbols (List[str]): List of trading pair symbols to subscribe to

        Raises:
            TypeError: If symbols is not a list of strings
            ValueError: If exchange service is not initialized
        """
        if not isinstance(symbols, list) or not all(isinstance(s, str) for s in symbols):
            raise TypeError("symbols must be a list of strings")

        try:
            if not self.exchange_service:
                self.logger.error("Exchange service not initialized")
                raise ValueError("Exchange service not initialized")

            # Initialize current prices if not already set
            current_prices = await self.exchange_service.get_current_price(symbols)
            if not isinstance(current_prices, dict):
                raise TypeError(f"Current prices must be a dictionary, got {type(current_prices)}")

            for symbol, price in current_prices.items():
                try:
                    self.current_prices[symbol] = float(price)
                except (ValueError, TypeError) as e:
                    self.logger.error(f"Invalid price format for {symbol}: {str(e)}")

            # Start websocket connection if not already running
            if not self._running:
                self._running = True
                self._websocket_task = asyncio.create_task(self._handle_websocket_updates(symbols))

        except Exception as e:
            self.logger.error(f"Error subscribing to price updates: {str(e)}")
            self._running = False
            raise

    async def _handle_websocket_updates(self, symbols: List[str]) -> None:
        """
        Handle WebSocket connection and price updates.

        Args:
            symbols (List[str]): List of trading pair symbols
        """
        if not isinstance(symbols, list) or not all(isinstance(s, str) for s in symbols):
            raise TypeError("symbols must be a list of strings")

        try:
            async for message in self.exchange_service.start_price_feed(symbols):
                if not self._running:
                    break

                try:
                    if not isinstance(message, str):
                        raise TypeError(f"Websocket message must be a string, got {type(message)}")
                        
                    data = json.loads(message)
                    if not isinstance(data, dict):
                        raise TypeError(f"Parsed message must be a dictionary, got {type(data)}")
                        
                    if data.get("type") == "ticker" and "symbol" in data and "price" in data:
                        symbol = str(data["symbol"])
                        try:
                            price = float(data["price"])
                            await self.update_price_history(symbol, price)
                        except (ValueError, TypeError) as e:
                            self.logger.error(f"Invalid price in websocket message: {str(e)}")
                except json.JSONDecodeError:
                    self.logger.error("Failed to parse websocket message")
                except Exception as e:
                    self.logger.error(f"Error processing websocket message: {str(e)}")

        except Exception as e:
            self.logger.error(f"WebSocket connection error: {str(e)}")
        finally:
            self._running = False

    async def stop(self) -> None:
        """Stop the market data service and cleanup resources."""
        self._running = False
        if self._websocket_task:
            self._websocket_task.cancel()
            try:
                await self._websocket_task
            except asyncio.CancelledError:
                pass
            self._websocket_task = None
