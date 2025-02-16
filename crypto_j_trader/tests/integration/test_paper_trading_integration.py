"""Integration tests for paper trading system"""
from decimal import Decimal
import pytest
from crypto_j_trader.src.trading.paper_trading import PaperTrader, Position
from crypto_j_trader.src.trading.order_executor import OrderExecutor  # Add this import


class MockMarketData:
    """Mock market data handler for testing"""
    def __init__(self):
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
        self._ws_handler = None
        self.price_feed = self.last_prices.copy()  # Add price_feed for compatibility

    async def start(self):
        """Mock start without WebSocket connection"""
        self.is_running = True
        return True
    
    async def stop(self):
        """Mock stop without WebSocket connection"""
        self.is_running = False
        return True

    def get_current_price(self, trading_pair):
        """Get current price from mock data"""
        return self.price_feed.get(trading_pair)
    
    def get_price_history(self, symbol, period='5m'):
        """Get historical prices for volatility calculation"""
        return self.price_history.get(symbol, [])
    
    async def start(self):
        self.is_running = True
    
    async def stop(self):
        self.is_running = False

class MockExchangeService:
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
def trading_system(test_config):
    """Create OrderExecutor instance for trading system."""
    exchange = MockExchangeService()
    market_data = MockMarketData()
    
    # Create PaperTrader with market data handler
    trader = PaperTrader(market_data, trading_pair="BTC-USD")
    # Add executor after PaperTrader creation
    executor = OrderExecutor(exchange, trading_pair="BTC-USD", paper_trading=True)
    trader.executor = executor
    
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
    
    # Create PaperTrader with market data handler
    trader = PaperTrader(market_data, trading_pair="BTC-USD")
    # Add executor after PaperTrader creation  
    executor = OrderExecutor(exchange, trading_pair="BTC-USD", paper_trading=True)
    trader.executor = executor
    
    return {
        "exchange": exchange,
        "market_data": market_data,
        "executor": executor,
        "trader": trader
    }

@pytest.mark.asyncio
async def test_full_trading_cycle(trading_system):
    """Test full trading cycle including position tracking and error handling."""
    trader = trading_system["trader"]
    
    # Create initial position
    order = {
        "symbol": "BTC-USD",
        "type": "market",
        "side": "buy",
        "quantity": 1.0
    }
    
    result = trader.place_order(order)
    assert result["status"] == "filled"
    
    # Verify position
    position_info = trader.get_position_info("BTC-USD")
    assert position_info["quantity"] == Decimal("1.0")
    
    # Reduce position
    order = {
        "symbol": "BTC-USD",
        "type": "market",
        "side": "sell",
        "quantity": 0.5
    }
    result = trader.place_order(order)
    assert result["status"] == "filled"
    
    # Verify reduced position
    position_info = trader.get_position_info("BTC-USD")
    assert position_info["quantity"] == Decimal("0.5")
    
    # Close position
    order = {
        "symbol": "BTC-USD",
        "type": "market",
        "side": "sell",
        "quantity": 0.5
    }
    result = trader.place_order(order)
    assert result["status"] == "filled"
    
    # Verify position is closed
    position_info = trader.get_position_info("BTC-USD")
    assert position_info["quantity"] == Decimal("0")

@pytest.mark.asyncio
async def test_risk_management_integration(trading_system):
    """Test risk management integration with trading system."""
    trader = trading_system["trader"]
    
    # Set up risk controls
    risk_controls = {
        "max_position_size": Decimal("5.0"),
        "max_drawdown": Decimal("0.2"),
        "daily_loss_limit": Decimal("5000")
    }
    trader.integrate_risk_controls(risk_controls)
    
    # Try to exceed position limit
    order = {
        "symbol": "BTC-USD",
        "type": "market",
        "side": "buy",
        "quantity": 6.0
    }
    result = trader.place_order(order)
    assert result["status"] == "error"
    assert "Position size limit exceeded" in result["message"]
    
    # Place valid order
    order = {
        "symbol": "BTC-USD",
        "type": "market",
        "side": "buy",
        "quantity": 3.0
    }
    result = trader.place_order(order)
    assert result["status"] == "filled"
    
    # Verify position
    position_info = trader.get_position_info("BTC-USD")
    assert position_info["quantity"] == Decimal("3.0")

@pytest.mark.integration
def test_multi_asset_trading(multi_asset_trading_system):
    """Test paper trading with multiple assets"""
    trader = multi_asset_trading_system["trader"]
    
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
        result = trader.place_order(order)
        assert result["status"] == "filled"
        assert result["product_id"] == order["symbol"]
    
    # Verify positions for both assets
    assert trader.get_position_info("BTC-USD")["quantity"] == Decimal("1.0")
    assert trader.get_position_info("ETH-USD")["quantity"] == Decimal("5.0")

@pytest.mark.integration
def test_order_execution_performance(trading_system):
    """Test performance aspects of paper trading"""
    trader = trading_system["trader"]
    
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
    
    # Execute orders
    for order in orders:
        result = trader.place_order(order)
        assert result["status"] == "filled"
        assert "order_id" in result
    
    # Verify final position calculation accuracy
    expected_position = Decimal("0.5")  # 5 buys of 0.1 each
    position_info = trader.get_position_info("BTC-USD")
    assert position_info["quantity"] == expected_position

@pytest.mark.integration
def test_system_state_consistency(trading_system):
    """Test consistency of system state across components"""
    trader = trading_system["trader"]
    
    # Execute order
    order = {
        "symbol": "BTC-USD",
        "type": "market",
        "side": "buy",
        "quantity": Decimal("1.0")
    }
    
    result = trader.place_order(order)
    assert result["status"] == "filled"
    
    # Verify position
    position_info = trader.get_position_info("BTC-USD")
    assert position_info["quantity"] == Decimal("1.0")
    assert "cost_basis" in position_info
    assert "average_entry" in position_info

@pytest.mark.integration
def test_trade_logging_and_monitoring(trading_system):
    """Test comprehensive logging and monitoring of trading activities"""
    trader = trading_system["trader"]
    
    # Set up risk controls with monitoring
    risk_controls = {
        "max_position_size": Decimal("5.0"),
        "max_drawdown": Decimal("0.1"),
        "daily_loss_limit": Decimal("2000")
    }
    trader.integrate_risk_controls(risk_controls)
    
    # Execute trades
    trades = [
        {"symbol": "BTC-USD", "type": "market", "side": "buy", "quantity": Decimal("3.0")},
        {"symbol": "BTC-USD", "type": "limit", "side": "sell", "quantity": Decimal("1.0"), "price": Decimal("49000")},
        {"symbol": "BTC-USD", "type": "market", "side": "buy", "quantity": Decimal("2.0")}
    ]
    
    executed_trades = []
    for trade in trades:
        result = trader.place_order(trade)
        executed_trades.append({
            "trade": trade,
            "result": result,
            "position_after": trader.get_position_info("BTC-USD")
        })
        
    # Verify last position
    position_info = trader.get_position_info("BTC-USD")
    expected_position = Decimal("4.0")  # 3.0 - 1.0 + 2.0
    assert position_info["quantity"] == expected_position

@pytest.mark.integration
def test_stop_loss_integration(trading_system):
    """Test stop-loss order functionality"""
    trader = trading_system["trader"]
    market_data = trading_system["market_data"]
    
    # Set up initial position
    order = {
        "symbol": "BTC-USD",
        "type": "market",
        "side": "buy",
        "quantity": Decimal("2.0")
    }
    result = trader.place_order(order)
    assert result["status"] == "filled"
    
    # Place stop loss order
    stop_loss = {
        "symbol": "BTC-USD",
        "type": "stop-loss",
        "side": "sell",
        "quantity": Decimal("1.0"),
        "stop_price": "49000"
    }
    
    # Test when price is above stop
    market_data.price_feed["BTC-USD"] = Decimal("50000")
    result = trader.place_order(stop_loss)
    assert result["status"] == "pending"
    
    # Test when price hits stop
    market_data.price_feed["BTC-USD"] = Decimal("48000")
    result = trader.place_order(stop_loss)
    assert result["status"] == "filled"
    assert result["execution_type"] == "stop-loss"
    
    # Verify final position
    position_info = trader.get_position_info("BTC-USD")
    assert position_info["quantity"] == Decimal("1.0")


