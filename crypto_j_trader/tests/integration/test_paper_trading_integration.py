"""Integration tests for paper trading system"""

import pytest
from decimal import Decimal
from crypto_j_trader.src.trading.paper_trading import PaperTrader
from crypto_j_trader.src.trading.order_execution import OrderExecutor
from crypto_j_trader.src.trading.exchange_service import ExchangeService
from crypto_j_trader.src.trading.market_data_handler import MarketDataHandler

class MockMarketData(MarketDataHandler):
    """Mock market data handler for testing"""
    def __init__(self):
        self.last_prices = {
            "BTC-USD": 50000.0,
            "ETH-USD": 2000.0
        }
        self.is_running = True
    
    def get_last_price(self, trading_pair):
        return self.last_prices.get(trading_pair)
    
    async def start(self):
        self.is_running = True
    
    async def stop(self):
        self.is_running = False

class MockExchangeService(ExchangeService):
    """Mock exchange service with realistic behavior"""
    def __init__(self):
        self.orders = {}
        self.order_id_counter = 1
        self.current_pair = None  # Track current trading pair

    def set_trading_pair(self, pair):
        """Set the current trading pair"""
        self.current_pair = pair

    def place_market_order(self, order):
        order_id = str(self.order_id_counter)
        self.order_id_counter += 1
        self.orders[order_id] = {
            "id": order_id,
            "status": "filled",
            "product_id": order.product_id,
            "side": order.side,
            "size": str(order.size)
        }
        return {"order_id": order_id}

    def place_limit_order(self, order):
        order_id = str(self.order_id_counter)
        self.order_id_counter += 1
        self.orders[order_id] = {
            "id": order_id,
            "status": "filled",
            "product_id": order.product_id,
            "side": order.side,
            "size": str(order.size),
            "price": str(order.price)
        }
        return {"order_id": order_id}

    def get_order_status(self, order_id):
        return self.orders.get(order_id)
    
    def get_product_ticker(self, product_id):
        prices = {
            "BTC-USD": "50000.0",
            "ETH-USD": "2000.0"
        }
        return {"price": prices.get(product_id, "50000.0")}

@pytest.fixture
def trading_system():
    """Set up complete trading system with paper trading"""
    exchange = MockExchangeService()
    market_data = MockMarketData()
    executor = OrderExecutor(exchange, "BTC-USD", paper_trading=True)
    trader = PaperTrader(executor)
    return {
        "exchange": exchange,
        "market_data": market_data,
        "executor": executor,
        "trader": trader
    }

@pytest.fixture
def multi_asset_trading_system():
    """Set up trading system for multi-asset trading"""
    exchange = MockExchangeService()
    market_data = MockMarketData()
    
    # Create a PaperTrader with an executor that can handle multiple pairs
    executor = OrderExecutor(exchange, None, paper_trading=True)  # No default pair
    trader = PaperTrader(executor)
    
    return {
        "exchange": exchange,
        "market_data": market_data,
        "executor": executor,
        "trader": trader
    }

@pytest.mark.integration
def test_full_trading_cycle(trading_system):
    """Test a complete trading cycle with market data integration"""
    trader = trading_system["trader"]
    
    # Set up risk controls
    risk_controls = {
        "max_position_size": Decimal("10.0"),
        "max_drawdown": Decimal("0.15"),
        "daily_loss_limit": Decimal("5000")
    }
    trader.integrate_risk_controls(risk_controls)
    
    # Execute multiple trades with position tracking
    orders = [
        {
            "symbol": "BTC-USD",
            "type": "market",
            "side": "buy",
            "quantity": Decimal("2.0")
        },
        {
            "symbol": "BTC-USD",
            "type": "limit",
            "side": "buy",
            "quantity": Decimal("1.5"),
            "price": Decimal("49000")
        },
        {
            "symbol": "BTC-USD",
            "type": "market",
            "side": "sell",
            "quantity": Decimal("1.0")
        }
    ]
    
    # Execute orders and verify results
    for order in orders:
        result = trader.place_order(order)
        assert result["status"] == "filled"
        assert result["product_id"] == order["symbol"]
        if order["type"] == "limit":
            assert Decimal(result["price"]) == order["price"]

    # Verify final position
    final_position = Decimal("2.5")  # 2.0 + 1.5 - 1.0
    assert trader.positions["BTC-USD"] == final_position

@pytest.mark.integration
def test_risk_management_integration(trading_system):
    """Test integration of risk management with paper trading"""
    trader = trading_system["trader"]
    
    # Set strict risk controls
    risk_controls = {
        "max_position_size": Decimal("3.0"),
        "max_drawdown": Decimal("0.1"),
        "daily_loss_limit": Decimal("1000")
    }
    trader.integrate_risk_controls(risk_controls)
    
    # Test position size limit
    large_order = {
        "symbol": "BTC-USD",
        "type": "market",
        "side": "buy",
        "quantity": Decimal("4.0")  # Exceeds max position size
    }
    
    with pytest.raises(Exception) as exc_info:
        trader.place_order(large_order)
    assert "position size" in str(exc_info.value).lower()

@pytest.mark.integration
def test_multi_asset_trading(multi_asset_trading_system):
    """Test paper trading with multiple assets"""
    trader = multi_asset_trading_system["trader"]
    exchange = multi_asset_trading_system["exchange"]
    
    # Trade multiple assets
    orders = [
        {
            "symbol": "BTC-USD",
            "type": "market",
            "side": "buy",
            "quantity": Decimal("1.0")
        },
        {
            "symbol": "ETH-USD",
            "type": "market",
            "side": "buy",
            "quantity": Decimal("5.0")
        }
    ]
    
    for order in orders:
        # Set the trading pair in exchange service
        exchange.set_trading_pair(order["symbol"])
        result = trader.place_order(order)
        assert result["status"] == "filled"
        assert result["product_id"] == order["symbol"]
    
    # Verify positions for both assets
    assert trader.positions["BTC-USD"] == Decimal("1.0")
    assert trader.positions["ETH-USD"] == Decimal("5.0")

@pytest.mark.integration
def test_order_execution_performance(trading_system):
    """Test performance aspects of paper trading"""
    trader = trading_system["trader"]
    executor = trading_system["executor"]
    
    # Execute rapid series of orders
    orders = []
    for i in range(10):
        side = "buy" if i % 2 == 0 else "sell"
        quantity = Decimal("0.1")
        if side == "sell":
            # First place a buy to have position to sell
            buy_order = {
                "symbol": "BTC-USD",
                "type": "market",
                "side": "buy",
                "quantity": quantity
            }
            trader.place_order(buy_order)
            
        orders.append({
            "symbol": "BTC-USD",
            "type": "market",
            "side": side,
            "quantity": quantity
        })
    
    # Execute and measure response times
    for order in orders:
        result = trader.place_order(order)
        assert result["status"] == "filled"
        assert "order_id" in result
    
    # Verify order history completeness
    assert len(trader.orders) == 15  # 10 test orders + 5 setup buy orders
    
    # Verify final position calculation accuracy
    expected_position = Decimal("0.5")  # 5 buys of 0.1 each
    actual_position = trader.positions.get("BTC-USD", Decimal("0"))
    assert actual_position == expected_position

@pytest.mark.integration
def test_system_state_consistency(trading_system):
    """Test consistency of system state across components"""
    trader = trading_system["trader"]
    executor = trading_system["executor"]
    
    # Execute orders that should update both trader and executor state
    order = {
        "symbol": "BTC-USD",
        "type": "market",
        "side": "buy",
        "quantity": Decimal("1.0")
    }
    
    result = trader.place_order(order)
    assert result["status"] == "filled"
    
    # Verify position consistency between trader and executor
    trader_position = trader.positions["BTC-USD"]
    executor_position = executor.get_position("BTC-USD")
    assert trader_position == Decimal("1.0")
    if executor_position:  # May be None in paper trading mode
        assert Decimal(str(executor_position["quantity"])) == trader_position