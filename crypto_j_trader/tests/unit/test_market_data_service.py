"""Market data service mock for testing"""
from decimal import Decimal
from typing import Dict, List, Optional, Any

class MockMarketDataService:
    """Mock market data service for testing"""
    def __init__(self):
        self.price_feed = {
            "BTC-USD": Decimal("50000"),
            "ETH-USD": Decimal("2000"),
            "LOW_LIQUIDITY": Decimal("100"),
            "ZERO_LIQUIDITY": Decimal("100"),
            "HIGH_VOLATILITY": Decimal("1000")
        }
        self.order_books = {
            "BTC-USD": {
                "bids": [[Decimal("49900"), Decimal("1.0")], [Decimal("49800"), Decimal("2.0")]],
                "asks": [[Decimal("50100"), Decimal("1.0")], [Decimal("50200"), Decimal("2.0")]]
            },
            "LOW_LIQUIDITY": {
                "bids": [[Decimal("99"), Decimal("0.1")]], 
                "asks": [[Decimal("101"), Decimal("0.1")]]
            },
            "ZERO_LIQUIDITY": {
                "bids": [], 
                "asks": []
            }
        }
        self._recent_trades = {
            "BTC-USD": [
                {"price": "50000"}, {"price": "50100"},
                {"price": "49900"}, {"price": "50200"}
            ],
            "HIGH_VOLATILITY": [
                {"price": "900"}, {"price": "1100"},
                {"price": "800"}, {"price": "1200"}
            ]
        }

    async def get_price(self, symbol: str) -> Optional[Decimal]:
        return self.price_feed.get(symbol)

    async def get_order_book(self, symbol: str) -> Optional[Dict[str, List[List[Decimal]]]]:
        return self.order_books.get(symbol)

    async def get_recent_trades(self, symbol: str) -> List[Dict[str, str]]:
        return self._recent_trades.get(symbol, [])

    async def is_running(self) -> bool:
        return True