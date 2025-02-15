"""Integration tests for paper trading system"""
from crypto_j_trader.src.trading.paper_trading import Position


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
        self._ws_handler = None  # Don't initialize WebSocket in tests
    
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
        return self.last_prices.get(trading_pair)
    
    def get_price_history(self, symbol, period='5m'):
        """Get historical prices for volatility calculation"""
        return self.price_history.get(symbol, [])
    
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
def trading_system(test_config):
    """Create OrderExecutor instance for trading system."""
    return OrderExecutor(
        trading_pair="BTC-USD",
        api_key=test_config['api_key'],
        base_url="https://example.com",  # Replace with the correct base URL
        timeout=test_config['timeout']
    )

@pytest.fixture
def multi_asset_trading_system():
    """Set up trading system for multi-asset trading"""
    exchange = MockExchangeService()
    market_data = MockMarketData()
    
    # Create a PaperTrader with an executor that can handle multiple pairs
    executor = OrderExecutor(exchange, "BTC-USD", paper_trading=True, trading_pair="BTC-USD")  # No default pair
    trader = PaperTrader(executor)
    
    return {
        "exchange": exchange,
        "market_data": market_data,
        "executor": executor,
        "trader": trader
    }

@pytest.mark.asyncio
async def test_full_trading_cycle(trading_system):
    """Test full trading cycle including position tracking and error handling."""
    # Create initial position
    trading_system.create_order(
        symbol="BTC-USD",
        side="buy",
        quantity=1.0,
        price=50000.0
    )
    
    # Verify position
    position = trading_system.get_position("BTC-USD")
    assert position["quantity"] == 1.0
    assert position["entry_price"] == 50000.0
    assert position["stop_loss"] == 47500.0
    
    # Reduce position
    trading_system.create_order(
        symbol="BTC-USD",
        side="sell",
        quantity=0.5,
        price=51000.0
    )
    
    # Verify reduced position
    position = trading_system.get_position("BTC-USD")
    assert position["quantity"] == 0.5
    assert position["entry_price"] == 50000.0
    assert position["stop_loss"] == 47500.0
    
    # Close position
    trading_system.create_order(
        symbol="BTC-USD",
        side="sell",
        quantity=0.5,
        price=52000.0
    )
    
    # Verify position is closed
    position = trading_system.get_position("BTC-USD")
    assert position["quantity"] == 0.0
    assert position["entry_price"] == 0.0
    assert position["stop_loss"] == 0.0

@pytest.mark.asyncio
async def test_risk_management_integration(trading_system):
    """Test risk management integration with trading system."""
    # Create initial position
    trading_system.create_order(
        symbol="BTC-USD",
        side="buy",
        quantity=1.0,
        price=50000.0
    )
    
    # Verify position
    position = trading_system.get_position("BTC-USD")
    assert position["quantity"] == 1.0
    assert position["entry_price"] == 50000.0
    assert position["stop_loss"] == 47500.0
    
    # Test risk management
    # ...additional risk management tests...

@pytest.mark.asyncio
async def test_multi_asset_trading(trading_system):
    """Test multi-asset trading with trading system."""
    # Create BTC position
    trading_system.create_order(
        symbol="BTC-USD",
        side="buy",
        quantity=1.0,
        price=50000.0
    )
    
    # Create ETH position
    trading_system.create_order(
        symbol="ETH-USD",
        side="buy",
        quantity=10.0,
        price=2000.0
    )
    
    # Verify BTC position
    btc_pos = trading_system.get_position("BTC-USD")
    assert btc_pos["quantity"] == 1.0
    assert btc_pos["entry_price"] == 50000.0
    assert btc_pos["stop_loss"] == 47500.0
    
    # Verify ETH position
    eth_pos = trading_system.get_position("ETH-USD")
    assert eth_pos["quantity"] == 10.0
    assert eth_pos["entry_price"] == 2000.0
    assert eth_pos["stop_loss"] == 1900.0

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
    assert trader.get_position_info("BTC-USD")["quantity"] == Decimal("1.0")
    assert trader.get_position_info("ETH-USD")["quantity"] == Decimal("5.0")

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
    trader_position = trader.get_position_info("BTC-USD")["quantity"]
    executor_position = executor.get_position("BTC-USD")
    assert trader_position == Decimal("1.0")
    if executor_position:  # May be None in paper trading mode
        assert Decimal(str(executor_position["quantity"])) == trader_position

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
    
    # Execute trades that approach risk limits
    trades = [
        {"symbol": "BTC-USD", "type": "market", "side": "buy", "quantity": Decimal("3.0")},
        {"symbol": "BTC-USD", "type": "limit", "side": "sell", "quantity": Decimal("1.0"), "price": Decimal("49000")},
        {"symbol": "BTC-USD", "type": "market", "side": "buy", "quantity": Decimal("2.0")}  # Should approach position limit
    ]
    
    executed_trades = []
    for trade in trades:
        try:
            result = trader.place_order(trade)
            executed_trades.append({
                "trade": trade,
                "result": result,
                "position_after": trader.get_position_info("BTC-USD")
            })
        except Exception as e:
            executed_trades.append({
                "trade": trade,
                "error": str(e),
                "position_after": trader.get_position_info("BTC-USD")
            })
    
    
    # Verify trade execution logs
    assert len(executed_trades) == 3
    assert "result" in executed_trades[0]  # First trade should succeed
    assert "result" in executed_trades[1]  # Second trade should succeed
    assert "error" in executed_trades[2]   # Third trade should fail due to position limit
    
    # Verify position tracking consistency
    position_info = trader.get_position_info("BTC-USD")
    assert position_info["quantity"] == Decimal("2.0")  # 3.0 - 1.0
    
    # Verify order history completeness
    assert len(trader.orders) == 2  # Only successful orders should be recorded
    
    # Verify trade history accuracy
    # position = trader.positions["BTC-USD"] # Removed direct access to positions
    # trade_history = position.trades
    trade_history = [] # Temporarily set to empty list
    assert len(trade_history) == 2
    
    # Verify chronological order and details
    assert trade_history[0]["side"] == "buy"
    assert trade_history[0]["quantity"] == Decimal("3.0")
    assert trade_history[1]["side"] == "sell"
    assert trade_history[1]["quantity"] == Decimal("1.0")
    assert trade_history[1]["price"] == Decimal("49000")
@pytest.mark.integration
def test_trade_history_persistence(trading_system):
    """Test comprehensive trade history tracking and persistence"""
    trader = trading_system["trader"]
    
    # Execute a complex series of trades with multiple symbols
    trades = [
        {"symbol": "BTC-USD", "type": "market", "side": "buy", "quantity": Decimal("1.0")},
        {"symbol": "ETH-USD", "type": "limit", "side": "buy", "quantity": Decimal("10.0"), "price": Decimal("2000")},
        {"symbol": "BTC-USD", "type": "market", "side": "sell", "quantity": Decimal("0.5")},
        {"symbol": "ETH-USD", "type": "limit", "side": "sell", "quantity": Decimal("5.0"), "price": Decimal("2100")}
    ]
    
    for trade in trades:
        result = trader.place_order(trade)
        assert result["status"] == "filled"
        
    # Verify trade history for BTC
    btc_position = trader.positions["BTC-USD"]
    btc_trades = btc_position.trades
    assert len(btc_trades) == 2
    
    # Verify chronological order and details of BTC trades
    assert btc_trades[0]["side"] == "buy"
    assert btc_trades[0]["quantity"] == Decimal("1.0")
    assert btc_trades[1]["side"] == "sell"
    assert btc_trades[1]["quantity"] == Decimal("0.5")
    
    # Verify trade history for ETH
    eth_position = trader.positions["ETH-USD"]
    eth_trades = eth_position.trades
    assert len(eth_trades) == 2
    
    # Verify chronological order and details of ETH trades
    assert eth_trades[0]["side"] == "buy"
    assert eth_trades[0]["quantity"] == Decimal("10.0")
    assert eth_trades[0]["price"] == Decimal("2000")
    assert eth_trades[1]["side"] == "sell"
    assert eth_trades[1]["quantity"] == Decimal("5.0")
    assert eth_trades[1]["price"] == Decimal("2100")
    
    # Verify realized PnL calculations
    eth_realized_pnl = eth_position.realized_pnl
    expected_eth_pnl = (Decimal("2100") - Decimal("2000")) * Decimal("5.0")
    assert eth_realized_pnl == expected_eth_pnl

@pytest.mark.integration
def test_complex_multi_symbol_scenario(multi_asset_trading_system):
    """Test complex scenarios with multiple symbols trading simultaneously"""
    trader = multi_asset_trading_system["trader"]
    exchange = multi_asset_trading_system["exchange"]
    
    # Initialize risk controls
    risk_controls = {
        "max_position_size": Decimal("20.0"),
        "max_drawdown": Decimal("0.15"),
        "daily_loss_limit": Decimal("5000")
    }
    trader.integrate_risk_controls(risk_controls)
    
    # Complex trading sequence with multiple assets
    trades = [
        # Establish initial positions
        {"symbol": "BTC-USD", "type": "market", "side": "buy", "quantity": Decimal("2.0")},
        {"symbol": "ETH-USD", "type": "market", "side": "buy", "quantity": Decimal("15.0")},
        
        # Partial profit taking
        {"symbol": "BTC-USD", "type": "limit", "side": "sell", "quantity": Decimal("1.0"), "price": Decimal("51000")},
        {"symbol": "ETH-USD", "type": "limit", "side": "sell", "quantity": Decimal("5.0"), "price": Decimal("2100")},
        
        # Add to positions on dips
        {"symbol": "BTC-USD", "type": "limit", "side": "buy", "quantity": Decimal("1.5"), "price": Decimal("49000")},
        {"symbol": "ETH-USD", "type": "limit", "side": "buy", "quantity": Decimal("8.0"), "price": Decimal("1950")}
    ]
    
    positions_after_each_trade = []
    
    for trade in trades:
        exchange.set_trading_pair(trade["symbol"])
        result = trader.place_order(trade)
        assert result["status"] == "filled"
        
        # Record positions after each trade
        positions_after_each_trade.append({
            "BTC": trader.get_position_info("BTC-USD")["quantity"],
            "ETH": trader.get_position_info("ETH-USD")["quantity"],
            "trade": trade
        })
    
    # Verify final positions
    expected_btc = Decimal("2.5")  # 2.0 - 1.0 + 1.5
    expected_eth = Decimal("18.0")  # 15.0 - 5.0 + 8.0
    
    assert trader.get_position_info("BTC-USD")["quantity"] == expected_btc
    assert trader.get_position_info("ETH-USD")["quantity"] == expected_eth
    
    # Verify position evolution
    assert positions_after_each_trade[0]["BTC"] == Decimal("2.0")
    assert positions_after_each_trade[1]["ETH"] == Decimal("15.0")
    assert positions_after_each_trade[2]["BTC"] == Decimal("1.0")
    assert positions_after_each_trade[3]["ETH"] == Decimal("10.0")
    assert positions_after_each_trade[4]["BTC"] == expected_btc
    assert positions_after_each_trade[5]["ETH"] == expected_eth

    # Verify cost basis updates
    btc_info = trader.get_position_info("BTC-USD")
    eth_info = trader.get_position_info("ETH-USD")
    
    # Calculate expected cost basis
    expected_btc_cost = (Decimal("49000") * Decimal("1.5")) + (Decimal("50000") * Decimal("1.0"))
    expected_eth_cost = (Decimal("1950") * Decimal("8.0")) + (Decimal("2000") * Decimal("10.0"))
    
    assert btc_info["cost_basis"] == expected_btc_cost
    assert eth_info["cost_basis"] == expected_eth_cost

@pytest.mark.integration
def test_stop_loss_integration(trading_system):
    """Test stop-loss order functionality with market data integration"""
    trader = trading_system["trader"]
    market_data = trading_system["market_data"]
    
    # Set up initial position and risk controls
    symbol = "BTC-USD"
    initial_position = Decimal("5.0")
    trader.positions[symbol] = Position(symbol)
    trader.positions[symbol].quantity = initial_position
    trader.positions[symbol].average_entry_price = Decimal("50000")
    
    risk_controls = {
        "max_position_size": Decimal("10.0"),
        "max_drawdown": Decimal("0.15"),
        "daily_loss_limit": Decimal("5000")
    }
    trader.integrate_risk_controls(risk_controls)
    
    # Test simple stop-loss order
    stop_loss = {
        "symbol": symbol,
        "type": "stop-loss",
        "side": "sell",
        "quantity": Decimal("2.0"),
        "stop_price": "49000"  # 2% below entry
    }
    
    # Initially price is at 50000, stop should not trigger
    result = trader.place_order(stop_loss.copy())
    assert result["status"] == "pending"
    assert trader.get_position(symbol) == initial_position
    
    # Price drops to 48500, stop should trigger
    market_data.last_prices[symbol] = Decimal("48500")
    result = trader.place_order(stop_loss.copy())
    assert result["status"] == "filled"
    assert result["execution_type"] == "stop-loss"
    assert Decimal(result["trigger_price"]) == Decimal("49000")
    assert trader.get_position(symbol) == initial_position - Decimal("2.0")
    
    # Test trailing stop-loss
    trailing_stop = {
        "symbol": symbol,
        "type": "stop-loss",
        "side": "sell",
        "quantity": Decimal("1.0"),
        "stop_price": "49000",
        "trailing": True,
        "trail_offset": "0.02"  # 2% trailing stop
    }
    
    # Price recovers to 51000
    market_data.last_prices[symbol] = Decimal("51000")
    result = trader.place_order(trailing_stop.copy())
    assert result["status"] == "pending"
    
    # Price moves up to 52000, trailing stop should adjust
    market_data.last_prices[symbol] = Decimal("52000")
    result = trader.place_order(trailing_stop.copy())
    assert result["status"] == "pending"
    
    # Sharp drop to 50000 should trigger trailing stop
    market_data.last_prices[symbol] = Decimal("50000")
    result = trader.place_order(trailing_stop.copy())
    assert result["status"] == "filled"
    assert result["execution_type"] == "stop-loss"
    assert "slippage" in result
    assert trader.get_position(symbol) == Decimal("2.0")  # 5 - 2 - 1
    
    # Verify trade history
    trades = trader.positions[symbol].trades
    stop_loss_trades = [t for t in trades if t.get("type") == "stop-loss"]
    assert len(stop_loss_trades) == 2
    
    # Verify realized PnL
    position_info = trader.get_position_info(symbol)
    assert Decimal(position_info["realized_pnl"]) < Decimal("0")  # Should have loss due to stop-outs

@pytest.mark.integration
def test_high_volume_orders(trading_system):
    """Stress test with a high volume of market orders"""
    trader = trading_system["trader"]
    
    # Define a large number of orders
    num_orders = 100
    orders = []
    for i in range(num_orders):
        side = "buy" if i % 2 == 0 else "sell"
        orders.append({
            "symbol": "BTC-USD",
            "type": "market",
            "side": side,
            "quantity": Decimal("0.01") # Small quantity for each order
        })
        
    # Execute orders in rapid succession
    for order in orders:
        result = trader.place_order(order)
        assert result["status"] == "filled"
        
    # Verify order history size
    assert len(trader.orders) == num_orders
    
    # Basic position check - net position should be close to zero
    position = trader.get_position_info("BTC-USD")
    assert abs(position["quantity"]) < Decimal("1.0") # Allow some deviation

@pytest.mark.integration
async def test_rapid_market_data_updates(trading_system):
    """Stress test with rapid market data updates"""
    trader = trading_system["trader"]
    market_data = trading_system["market_data"]
    
    # Prepare a series of rapid market data updates
    num_updates = 50
    initial_price = Decimal("50000.0")
    price_updates = []
    for i in range(num_updates):
        price_updates.append({
            "trading_pair": "BTC-USD",
            "price": str(initial_price + Decimal(i * 10)) # Increment price
        })
        
    # Rapidly update market data
    for update in price_updates:
        market_data.last_prices[update["trading_pair"]] = Decimal(update["price"])
        
    # Execute a trade after rapid updates
    order = {
        "symbol": "BTC-USD",
        "type": "market",
        "side": "buy",
        "quantity": Decimal("0.1")
    }
    result = trader.place_order(order)
    assert result["status"] == "filled"
    
    # Verify position after trade
    position = trader.get_position_info("BTC-USD")
    assert position["quantity"] == Decimal("0.1")
    
    # No explicit error verification, just ensure it completes without exceptions
    # and logs can be reviewed for performance

@pytest.mark.integration
async def test_concurrent_multi_symbol_trading(multi_asset_trading_system):
    """Stress test concurrent trading of multiple symbols"""
    trader = multi_asset_trading_system["trader"]
    exchange = multi_asset_trading_system["exchange"]
    
    # Define symbols and orders for concurrent trading
    symbols = ["BTC-USD", "ETH-USD"]
    num_concurrent_orders = 10
    
    async def place_order_for_symbol(symbol, order_index):
        """Helper function to place order for a symbol"""
        side = "buy" if order_index % 2 == 0 else "sell"
        order = {
            "symbol": symbol,
            "type": "market",
            "side": side,
            "quantity": Decimal("0.01")
        }
        exchange.set_trading_pair(symbol)
        result = trader.place_order(order)
        assert result["status"] == "filled"
        
    # Create and run concurrent tasks
    tasks = []
    for symbol in symbols:
        for i in range(num_concurrent_orders):
            tasks.append(asyncio.create_task(place_order_for_symbol(symbol, i)))
            
    await asyncio.gather(*tasks)
    
    # Verify order history size - should be total number of orders placed
    assert len(trader.orders) == num_concurrent_orders * len(symbols)
    
    # Basic position check for both symbols
    for symbol in symbols:
        position = trader.get_position_info(symbol)
        assert abs(position["quantity"]) < Decimal("1.0") # Allow some deviation

import asyncio # Import asyncio at the end of the file


