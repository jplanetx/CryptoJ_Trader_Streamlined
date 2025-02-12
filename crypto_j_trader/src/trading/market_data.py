from typing import List, Optional, Dict, Any
import logging
import json
import asyncio

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
        """
        try:
            historical_data = await exchange_service.get_historical_data(symbols, history_days)
            for symbol, prices in historical_data.items():
                self.price_history[symbol] = prices
                if prices:  # Update current price if history exists
                    self.current_prices[symbol] = prices[-1]
        except Exception as e:
            self.logger.error(f"Error initializing price history: {str(e)}")
            raise

    from .trading_core import validate_trading_pair

    async def get_recent_prices(self, trading_pair: str) -> List[float]:
        if not validate_trading_pair(trading_pair):
            raise ValueError(f"Invalid trading pair format: {trading_pair}")
        """
        Get recent price history for a trading pair.

        Args:
            trading_pair (str): Trading pair identifier (e.g., "BTC-USD")

        Returns:
            List[float]: List of recent prices
        """
        try:
            if not isinstance(trading_pair, str):
                self.logger.error(f"Invalid trading pair type: {type(trading_pair)}")
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
            ValueError: If price is not a valid number
            TypeError: If trading_pair is not a string or price is not a number
        """
        try:
            if not isinstance(trading_pair, str):
                raise TypeError(f"Trading pair must be a string, got {type(trading_pair)}")
            
            if not isinstance(price, (int, float)):
                raise TypeError(f"Price must be a number, got {type(price)}")
            
            # Convert to float to handle both int and float inputs
            price_float = float(price)
            if price_float < 0:
                raise ValueError("Price cannot be negative")

            # Update current price
            self.current_prices[trading_pair] = price_float

            # Update price history
            if trading_pair not in self.price_history:
                self.price_history[trading_pair] = []
            self.price_history[trading_pair].append(price_float)
            # Keep only recent history (e.g., last 100 prices)
            self.price_history[trading_pair] = self.price_history[trading_pair][-100:]
        except Exception as e:
            self.logger.error(f"Error updating price history: {str(e)}")
            raise  # Re-raise the exception for proper error handling

    async def subscribe_price_updates(self, symbols: List[str]) -> None:
        """
        Subscribe to real-time price updates for specified symbols.

        Args:
            symbols (List[str]): List of trading pair symbols to subscribe to
        """
        try:
            if not self.exchange_service:
                raise ValueError("Exchange service not initialized")

            # Initialize current prices if not already set
            current_prices = await self.exchange_service.get_current_price(symbols)
            for symbol, price in current_prices.items():
                self.current_prices[symbol] = price

            # Start websocket connection if not already running
            if not self._running:
                self._running = True
                self._websocket_task = asyncio.create_task(self._handle_websocket_updates(symbols))

        except Exception as e:
            self.logger.error(f"Error subscribing to price updates: {str(e)}")
            # Log error but don't raise to maintain service stability
            self._running = False

    async def _handle_websocket_updates(self, symbols: List[str]) -> None:
        """
        Handle WebSocket connection and price updates.

        Args:
            symbols (List[str]): List of trading pair symbols
        """
        try:
            async for message in self.exchange_service.start_price_feed(symbols):
                if not self._running:
                    break

                try:
                    data = json.loads(message)
                    if data.get("type") == "ticker" and "symbol" in data and "price" in data:
                        symbol = data["symbol"]
                        price = float(data["price"])
                        await self.update_price_history(symbol, price)
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
