"""Test helpers for mocking dependencies"""

class MockWebSocketHandler:
    def __init__(self):
        self.connected = True
        self.subscriptions = set()

    async def subscribe(self, channel):
        self.subscriptions.add(channel)
        return True

    async def unsubscribe(self, channel):
        self.subscriptions.remove(channel)
        return True

class MockMarketDataHandler:
    def __init__(self):
        self.is_running = True
        self._websocket = MockWebSocketHandler()
        self.data = {}

    def is_data_fresh(self, max_age):
        return True

    def get_market_snapshot(self, trading_pair):
        return {
            'last_price': 50000.0,
            'order_book_depth': 20,
            'subscribed': True,
            'is_fresh': True
        }

    def get_recent_trades(self, trading_pair):
        return [
            {'price': 50000.0},
            {'price': 50100.0},
            {'price': 49900.0}
        ]

    def get_order_book(self, trading_pair):
        return {
            'bids': {'49000.0': '1.0', '48000.0': '1.0'},
            'asks': {'51000.0': '1.0', '52000.0': '1.0'}
        }