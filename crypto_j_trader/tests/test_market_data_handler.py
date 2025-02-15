import unittest
from decimal import Decimal
from crypto_j_trader.src.trading.market_data_handler import MarketDataHandler

class TestMarketDataHandler(unittest.TestCase):

    def setUp(self):
        self.handler = MarketDataHandler()

    def test_init(self):
        # Test initialization
        self.assertEqual(self.handler.last_prices["BTC-USD"], Decimal("50000"))
        self.assertEqual(self.handler.last_prices["ETH-USD"], Decimal("2000"))
        self.assertEqual(len(self.handler.price_history["BTC-USD"]), 5)
        self.assertTrue(self.handler.is_running)

    def test_get_current_price(self):
        # Test get_current_price method
        self.assertEqual(self.handler.get_current_price("BTC-USD"), Decimal("50000"))
        self.assertEqual(self.handler.get_current_price("ETH-USD"), Decimal("2000"))
        self.assertIsNone(self.handler.get_current_price("UNKNOWN"))

    def test_get_price_history(self):
        # Test get_price_history method
        self.assertEqual(len(self.handler.get_price_history("BTC-USD")), 5)
        self.assertEqual(self.handler.get_price_history("BTC-USD")[0], Decimal("49800"))
        self.assertEqual(self.handler.get_price_history("BTC-USD")[-1], Decimal("50200"))
        self.assertEqual(self.handler.get_price_history("ETH-USD")[0], Decimal("1980"))
        self.assertEqual(self.handler.get_price_history("ETH-USD")[-1], Decimal("2020"))
        self.assertEqual(self.handler.get_price_history('BTC-USD', period='10m'), self.handler.price_history.get('BTC-USD'))
        self.assertEqual(self.handler.get_price_history('ETH-USD', period='10m'), self.handler.price_history.get('ETH-USD'))
        self.assertEqual(self.handler.get_price_history('UNKNOWN'), None)

    import asyncio

    async def test_start(self):
        # Test start method
        await self.handler.start()
        self.assertTrue(self.handler.is_running)

    async def test_stop(self):
        # Test stop method
        await self.handler.stop()
        self.assertFalse(self.handler.is_running)

    def test_generate_trading_signal(self):
        # Test generate_trading_signal method
        self.assertEqual(self.handler.generate_trading_signal("BTC-USD"), "hold")
        self.assertEqual(self.handler.generate_trading_signal("ETH-USD"), "hold")
        self.assertEqual(self.handler.generate_trading_signal("UNKNOWN"), "hold")

    def test_placeholder(self):
        self.assertTrue(True)