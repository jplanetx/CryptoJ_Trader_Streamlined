from typing import List, Optional
import logging

class MarketData:
    """
    MarketData class for handling market data operations and price history.
    """
    def __init__(self):
        """Initialize MarketData instance."""
        self.logger = logging.getLogger(__name__)
        self.price_history = {}

    async def get_recent_prices(self, trading_pair: str) -> List[float]:
        """
        Get recent price history for a trading pair.

        Args:
            trading_pair (str): Trading pair identifier (e.g., "BTC-USD")

        Returns:
            List[float]: List of recent prices
        """
        try:
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
        """
        try:
            if trading_pair not in self.price_history:
                self.price_history[trading_pair] = []
            self.price_history[trading_pair].append(price)
            # Keep only recent history (e.g., last 100 prices)
            self.price_history[trading_pair] = self.price_history[trading_pair][-100:]
        except Exception as e:
            self.logger.error(f"Error updating price history: {str(e)}")
