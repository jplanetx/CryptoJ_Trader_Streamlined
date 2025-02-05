"""
This module handles market data for the trading bot using mock data for paper trading.
"""

import logging
from typing import List
from decimal import Decimal

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.FileHandler('trading.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class MarketDataHandler:
    """
    Market data handler using mock data for paper trading.
    """
    def __init__(self):
        """
        Initialize mock market data handler.
        """
        self.last_prices = {
            "BTC-USD": Decimal("50000"),
            "ETH-USD": Decimal("2000")
        }
        self.price_history = {
            "BTC-USD": [
                Decimal("49800"),
                Decimal("49900"),
                Decimal("50000"),
                Decimal("50100"),
                Decimal("50200")
            ],
            "ETH-USD": [
                Decimal("1980"),
                Decimal("1990"),
                Decimal("2000"),
                Decimal("2010"),
                Decimal("2020")
            ]
        }
        self.is_running = True

    def get_current_price(self, trading_pair):
        """Gets the current price for a given trading pair from mock data."""
        return self.last_prices.get(trading_pair)

    def get_price_history(self, symbol, period='5m'):
        """Gets historical prices for volatility calculation from mock data."""
        return self.price_history.get(symbol, [])

    async def start(self):
        """Starts the market data handler."""
        self.is_running = True

    async def stop(self):
        """Stops the market data handler."""
        self.is_running = False

    def generate_trading_signal(self, symbol: str) -> str:
        """Generates a dummy trading signal for testing."""
        return "hold"  # Default to hold for mock data
