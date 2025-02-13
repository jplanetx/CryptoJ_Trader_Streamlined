class MarketDataService:
    async def get_recent_prices(self, trading_pair):
        # Ensure trading_pair is a string for regex or matching functions
        trading_pair = str(trading_pair)
        # ...existing logic to retrieve prices...
        return [10000.0, 10100.0, 10200.0]  # dummy list for testing
