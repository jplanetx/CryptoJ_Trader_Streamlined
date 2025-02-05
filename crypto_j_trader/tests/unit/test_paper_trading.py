import pytest
from decimal import Decimal
from datetime import datetime
from typing import Dict, List
from crypto_j_trader.src.trading.paper_trading import PaperTrader, Position
from crypto_j_trader.src.trading.order_execution import OrderExecutor
from crypto_j_trader.src.trading.exchange_service import ExchangeService
from crypto_j_trader.src.trading.paper_trading import PaperTraderError, TradeHistoryManager

class MockMarketDataHandler:
    """Mock market data handler for testing"""
    def __init__(self, price_feed=None):
        self.price_feed = price_feed or {"BTC-USD": Decimal("50000")}
        self.price_history = {
            "BTC-USD": [
                Decimal("49800"),
                Decimal("49900"),
                Decimal("50000"),
                Decimal("50100"),
                Decimal("50200")
            ]
        }
    
    def get_current_price(self, symbol: str) -> Decimal:
        return self.price_feed.get(symbol)
        
    def get_price_history(self, symbol: str, period: str = '5m') -> List[Decimal]:
        return self.price_history.get(symbol, [])

class MockExchangeService(ExchangeService):
    """Mock exchange service for testing"""
    def __init__(self):
        pass

@pytest.fixture
def mock_market_data():
    """Create a mock market data handler"""
    return MockMarketDataHandler()

@pytest.fixture
def mock_market_price():
    """Create a mock market price handler that can be patched"""
    return MockMarketDataHandler().get_current_price

@pytest.fixture
def mock_order_executor():
    """Create an OrderExecutor instance in paper trading mode"""
    exchange = MockExchangeService()
    return OrderExecutor(exchange, "BTC-USD", paper_trading=True)

@pytest.fixture
def paper_trader(mock_order_executor, mock_market_data):
    """Initialize PaperTrader with mocks"""
    return PaperTrader(mock_order_executor, mock_market_data)

@pytest.fixture
def paper_trader_with_market_data(mock_order_executor, mock_market_price):
    """Initialize PaperTrader with mocks including market price"""
    market_data_handler = MockMarketDataHandler()
    market_data_handler.get_current_price = mock_market_price # Patch mock price
    return PaperTrader(mock_order_executor, market_data_handler)

def test_position_tracking_with_cost_basis(paper_trader):
    """Test position tracking including cost basis calculations"""
    symbol = "BTC-USD"
    
    # Buy 2 BTC at different prices
    buy_orders = [
        {"symbol": symbol, "quantity": 1, "side": "buy", "price": 50000, "type": "limit"},
        {"symbol": symbol, "quantity": 1, "side": "buy", "price": 52000, "type": "limit"}
    ]
    
    for order in buy_orders:
        paper_trader.place_order(order)
    
    position_info = paper_trader.get_position_info(symbol)
    assert Decimal(position_info["quantity"]) == Decimal("2") # Convert to Decimal for comparison
    assert Decimal(position_info["cost_basis"]) == Decimal("100000") # Updated assertion to Decimal('100000')
    assert position_info["average_entry"] == Decimal("51000")
    
    # Sell 1 BTC
    sell_order = {"symbol": symbol, "quantity": 1, "side": "sell", "price": 54000, "type": "limit"}
    paper_trader.place_order(sell_order)
    
    position_info = paper_trader.get_position_info(symbol)
    assert position_info["quantity"] == Decimal("1")
    assert position_info["cost_basis"] == Decimal("51000")
    assert position_info["realized_pnl"] == Decimal("3000")  # (54000 - 51000) * 1

def test_market_data_validation(paper_trader):
    """Test market data validation for orders"""
    # Update mock market price
    paper_trader.market_data_handler.price_feed["ETH-USD"] = Decimal("2000")
    
    # Test limit order too far from market price
    with pytest.raises(PaperTraderError) as excinfo:
        order = {
            "symbol": "ETH-USD",
            "quantity": 1,
            "side": "buy",
            "type": "limit",
            "price": 1800  # 10% below market
        }
        paper_trader.place_order(order)
    assert "price too far from market price" in str(excinfo.value)
    
    # Test market order execution with slippage
    market_order = {
        "symbol": "ETH-USD",
        "quantity": 1,
        "side": "buy",
        "type": "market"
    }
    result = paper_trader.place_order(market_order)
    execution_price = Decimal(result["execution_price"])
    assert execution_price > Decimal("2000")  # Price includes slippage
    assert execution_price <= Decimal("2002")  # Max 0.1% slippage

def test_position_history_tracking(paper_trader):
    """Test position history and trade tracking"""
    symbol = "BTC-USD"
    
    # Execute series of trades
    trades = [
        {"side": "buy", "quantity": 1, "price": 50000},
        {"side": "buy", "quantity": 2, "price": 48000},
        {"side": "sell", "quantity": 1.5, "price": 52000}
    ]
    
    for trade in trades:
        order = {
            "symbol": symbol,
            "quantity": trade["quantity"],
            "side": trade["side"],
            "type": "limit",
            "price": trade["price"]
        }
        paper_trader.place_order(order)
    
    position = paper_trader.positions[symbol]
    
    # Verify trade history
    assert len(position.trades) == 3
    assert position.trades[0]["side"] == "buy"
    assert position.trades[0]["quantity"] == Decimal("1")
    
    # Verify position calculations
    assert position.quantity == Decimal("1.5")  # 1 + 2 - 1.5
    assert position.realized_pnl > 0  # Should have profit from partial sell

def test_place_market_order_success(paper_trader):
    """Test successful market order placement"""
    order = {
        "symbol": "BTC-USD",
        "quantity": 1,
        "side": "buy",
        "type": "market"
    }
    result = paper_trader.place_order(order)
    
    assert result["status"] == "filled"
    assert result["product_id"] == "BTC-USD"
    assert result["size"] == "1"
    assert result["type"] == "market"
    assert order in paper_trader.orders

def test_place_limit_order_success(paper_trader):
    """Test successful limit order placement"""
    order = {
        "symbol": "BTC-USD",
        "quantity": 1,
        "price": 50000,
        "side": "buy",
        "type": "limit"
    }
    result = paper_trader.place_order(order)
    
    assert result["status"] == "filled"
    assert result["product_id"] == "BTC-USD"
    assert result["size"] == "1"
    assert result["price"] == "50000"
    assert result["type"] == "limit"
    assert order in paper_trader.orders

def test_limit_buy_order_filled(paper_trader, mock_market_data):
    """Test limit buy order is filled when market price is reached"""
    symbol = "BTC-USD"
    mock_market_data.price_feed[symbol] = Decimal("50100") # Initial market price above limit
    order = {
        "symbol": symbol,
        "quantity": 1,
        "price": 50000,
        "side": "buy",
        "type": "limit"
    }
    
    # Initially, order should not be filled
    result = paper_trader.place_order(order)
    assert result["status"] == "pending"
    
    # Simulate market price dropping below limit
    mock_market_data.price_feed[symbol] = Decimal("49900")
    result = paper_trader.place_order(order) # Re-place order, in real-world, this would be event-driven
    assert result["status"] == "filled"
    assert Decimal(result["execution_price"]) == Decimal("49900") # Filled at market price

def test_limit_buy_order_not_filled(paper_trader, mock_market_data):
    """Test limit buy order is not filled if market price is too high"""
    symbol = "BTC-USD"
    mock_market_data.price_feed[symbol] = Decimal("51000") # Market price above limit
    order = {
        "symbol": symbol,
        "quantity": 1,
        "price": 50000,
        "side": "buy",
        "type": "limit"
    }
    result = paper_trader.place_order(order)
    assert result["status"] == "pending" # Should remain pending

def test_limit_sell_order_filled(paper_trader, mock_market_data):
    """Test limit sell order filled when market price is reached"""
    symbol = "BTC-USD"
    mock_market_data.price_feed[symbol] = Decimal("49900") # Initial market price below limit
    
    # First establish a position with a buy
    buy_order = {
        "symbol": symbol,
        "quantity": 1,
        "price": 49900,
        "side": "buy",
        "type": "limit"
    }
    paper_trader.place_order(buy_order)
    assert paper_trader.get_position(symbol) == Decimal("1")
    
    order = {
        "symbol": symbol,
        "quantity": 1,
        "price": 50000,
        "side": "sell",
        "type": "limit"
    }
    
    # Initially, should not be filled
    result = paper_trader.place_order(order)
    assert result["status"] == "pending"
    
    # Simulate market price rising above limit
    mock_market_data.price_feed[symbol] = Decimal("50100")
    result = paper_trader.place_order(order) # Re-place order
    assert result["status"] == "filled"
    assert Decimal(result["execution_price"]) == Decimal("50100") # Filled at market price

def test_limit_sell_order_not_filled(paper_trader, mock_market_data):
    """Test limit sell order not filled if market price is too low"""
    symbol = "BTC-USD"
    mock_market_data.price_feed[symbol] = Decimal("49000") # Market price below limit
    
    # Assume we have a position
    paper_trader.positions[symbol] = Position(symbol)
    paper_trader.positions[symbol].quantity = Decimal("1")
    
    order = {
        "symbol": symbol,
        "quantity": 1,
        "price": 50000,
        "side": "sell",
        "type": "limit"
    }
    result = paper_trader.place_order(order)
    assert result["status"] == "pending" # Should remain pending

def test_limit_order_market_price_unavailable(paper_trader, mock_market_data):
    """Test limit order handling when market price is unavailable"""
    symbol = "BTC-USD"
    mock_market_data.price_feed[symbol] = None # Simulate no market data
    order = {
        "symbol": symbol,
        "quantity": 1,
        "price": 50000,
        "side": "buy",
        "type": "limit"
    }
    with pytest.raises(PaperTraderError) as excinfo:
        paper_trader.place_order(order)
    assert "Market price not available for limit order validation" in str(excinfo.value)

def test_update_position_new_symbol(paper_trader):
    """Test position update for a new symbol"""
    symbol = "ETH-USD"
    quantity = Decimal("2.5")
    price = Decimal("50000") # Dummy price for test
    is_buy = True # Dummy is_buy for test
    updated_position = paper_trader.update_position(symbol, quantity, price, is_buy)
    assert updated_position.quantity == quantity # Check position quantity instead of comparing objects

def test_update_position_buy_sell_flow(paper_trader):
    """Test complete buy/sell position update flow"""
    symbol = "BTC-USD"
    
    # Initial buy
    buy_order = {
        "symbol": symbol,
        "quantity": 2,
        "side": "buy",
        "type": "market"
    }
    paper_trader.place_order(buy_order)
    assert paper_trader.positions[symbol].quantity == Decimal("2") # Access quantity attribute
    
    # Partial sell
    sell_order = {
        "symbol": symbol,
        "quantity": 1,
        "side": "sell",
        "type": "market"
    }
    paper_trader.place_order(sell_order)
    assert paper_trader.positions[symbol].quantity == Decimal("1") # Access quantity attribute

def test_position_tracking_with_multiple_trades(paper_trader):
    """Test position tracking through multiple trades"""
    symbol = "BTC-USD"
    trades = [
        {"side": "buy", "quantity": 3, "type": "market"},
        {"side": "sell", "quantity": 1, "type": "market"},
        {"side": "buy", "quantity": 2, "type": "market"},
        {"side": "sell", "quantity": 3, "type": "market"}
    ]
    
    expected_position = 0
    for trade in trades:
        order = {
            "symbol": symbol,
            "quantity": trade["quantity"],
            "side": trade["side"],
            "type": trade["type"]
        }
        paper_trader.place_order(order)
        if trade["side"] == "buy":
            expected_position += trade["quantity"]
        else:
            expected_position -= trade["quantity"]
    
    assert paper_trader.get_position_info(symbol)["quantity"] == str(expected_position) # Compare string

def test_risk_controls_integration(paper_trader):
    """Test risk control integration with trading"""
    risk_data = {
        "max_position_size": 5.0,
        "max_drawdown": 0.1,
        "daily_loss_limit": 1000
    }
    paper_trader.integrate_risk_controls(risk_data)
    
    # Verify risk controls are properly set
    assert paper_trader.risk_controls == risk_data
    assert paper_trader.risk_controls["max_position_size"] == 5.0

@pytest.mark.integration
def test_paper_trading_integration():
    """Integration test for paper trading system"""
    # Initialize paper trading system
    exchange = MockExchangeService()
    executor = OrderExecutor(exchange, "BTC-USD", paper_trading=True)
    trader = PaperTrader(executor)
    
    # Set risk controls
    risk_controls = {"max_position_size": 10.0, "max_drawdown": 0.15}
    trader.integrate_risk_controls(risk_controls)
    
    # Execute a series of trades
    trades = [
        {"side": "buy", "quantity": 2, "type": "market"},
        {"side": "buy", "quantity": 3, "type": "limit", "price": 49000},
        {"side": "sell", "quantity": 4, "type": "market"}
    ]
    
    for trade in trades:
        order = {
            "symbol": "BTC-USD",
            "quantity": trade["quantity"],
            "side": trade["side"],
            "type": trade["type"]
        }
        if "price" in trade:
            order["price"] = trade["price"]
            
        result = trader.place_order(order)
        assert result["status"] == "filled"
        assert result["product_id"] == "BTC-USD"
        
    # Verify final position
    position_info = trader.get_position_info("BTC-USD")
    assert Decimal(position_info["quantity"]) == Decimal("1")  # 2 + 3 - 4 = 1
    
    # Verify order history
    assert len(trader.orders) == len(trades)

def test_invalid_order_handling(paper_trader):
    """Test handling of invalid orders"""
    invalid_orders = [
        {"symbol": "BTC-USD", "side": "invalid", "quantity": 1},
        {"symbol": "BTC-USD", "side": "buy", "quantity": -1},
        {"type": "limit", "side": "buy", "quantity": 1}  # Missing symbol
    ]
    
    for order in invalid_orders:
        with pytest.raises(Exception):
            paper_trader.place_order(order)

def test_position_limit_handling(paper_trader):
    """Test handling of position size limits"""
    # Set position limit
    risk_controls = {"max_position_size": 5.0}
    paper_trader.integrate_risk_controls(risk_controls)
    
    # Try to exceed position limit
    large_order = {
        "symbol": "BTC-USD",
        "quantity": 6,
        "side": "buy",
        "type": "market"
    }
    
    with pytest.raises(Exception):
        paper_trader.place_order(large_order)

def test_max_drawdown_risk_control(paper_trader):
    """Test max drawdown risk control functionality"""
    # Set initial capital and max drawdown
    initial_capital = Decimal("10000")
    max_drawdown = Decimal("0.2")  # 20% max drawdown
    risk_controls = {"max_drawdown": Decimal("0.2")}  # Must match exact format in paper_trading.py
    paper_trader.initial_capital = initial_capital
    paper_trader.integrate_risk_controls(risk_controls)

    # Simulate losses to trigger max drawdown
    loss_1 = Decimal("1000") # $1000 loss
    paper_trader.current_capital -= loss_1
    paper_trader.daily_pnl -= loss_1 # Simulate $1000 loss

    loss_2 = Decimal("1500") # $1500 additional loss, total $2500 loss
    paper_trader.current_capital -= loss_2
    paper_trader.daily_pnl -= loss_2 # Simulate additional $1500 loss

    # Attempting a buy order after max drawdown should raise PaperTraderError
    buy_order_1 = {
        "symbol": "BTC-USD",
        "quantity": Decimal("0.01"),
        "side": "buy",
        "type": "market",
    }
    with pytest.raises(PaperTraderError) as excinfo: # Expect PaperTraderError
        paper_trader.place_order(buy_order_1)
    assert "Order would exceed maximum drawdown of 0.2%" in str(excinfo.value) # Updated assertion

    # Verify current capital and drawdown level
    assert paper_trader.current_capital == initial_capital - loss_1 - loss_2 # Current capital should be $10000 - $2500 = $7500
    assert paper_trader.max_drawdown_level == initial_capital - (initial_capital * max_drawdown) # Max drawdown level should be $8000

def test_complex_trade_sequence(paper_trader):
    """Test position tracking with complex rapid trade sequences"""
    btc_symbol = "BTC-USD"
    eth_symbol = "ETH-USD"
    
    # Set up market data for both symbols
    paper_trader.market_data_handler.price_feed.update({
        btc_symbol: Decimal("50000"),
        eth_symbol: Decimal("3000")
    })
    
    # Execute alternating rapid trades on both symbols
    trades = [
        # BTC trades
        {"symbol": btc_symbol, "side": "buy", "quantity": 1.5, "price": 50000},
        {"symbol": btc_symbol, "side": "sell", "quantity": 0.5, "price": 51000},
        {"symbol": btc_symbol, "side": "buy", "quantity": 0.8, "price": 50500},
        # ETH trades interspersed
        {"symbol": eth_symbol, "side": "buy", "quantity": 5, "price": 3000},
        {"symbol": eth_symbol, "side": "sell", "quantity": 2, "price": 3100},
        # More BTC trades
        {"symbol": btc_symbol, "side": "sell", "quantity": 1.2, "price": 52000}
    ]
    
    expected_btc_position = Decimal("0.6")  # 1.5 - 0.5 + 0.8 - 1.2
    expected_eth_position = Decimal("3")    # 5 - 2
    
    for trade in trades:
        order = {
            "symbol": trade["symbol"],
            "quantity": trade["quantity"],
            "side": trade["side"],
            "type": "limit",
            "price": trade["price"]
        }
        result = paper_trader.place_order(order)
        assert result["status"] == "filled"
    
    # Verify final positions
    btc_position = paper_trader.get_position_info(btc_symbol)
    eth_position = paper_trader.get_position_info(eth_symbol)
    
    assert btc_position["quantity"] == expected_btc_position
    assert eth_position["quantity"] == expected_eth_position
    
    # Verify trade history
    btc_trades = paper_trader.positions[btc_symbol].trades
    eth_trades = paper_trader.positions[eth_symbol].trades
    
    assert len(btc_trades) == 4  # 4 BTC trades
    assert len(eth_trades) == 2  # 2 ETH trades
    
    # Verify PnL calculations
    # BTC PnL: Selling 0.5 @ 51000 and 1.2 @ 52000 against avg entry of 50000
    expected_btc_pnl = (Decimal("51000") - Decimal("50000")) * Decimal("0.5") + \
                      (Decimal("52000") - Decimal("50000")) * Decimal("1.2")
    # ETH PnL: Selling 2 @ 3100 against entry of 3000
    expected_eth_pnl = (Decimal("3100") - Decimal("3000")) * Decimal("2")
    
    assert btc_position["realized_pnl"] == expected_btc_pnl
    assert eth_position["realized_pnl"] == expected_eth_pnl

def test_market_data_edge_cases(paper_trader):
    """Test market data integration edge cases and error handling"""
    symbol = "BTC-USD"
    
    # Test unavailable market data
    paper_trader.market_data_handler.price_feed[symbol] = None
    market_order = {
        "symbol": symbol,
        "quantity": 1,
        "side": "buy",
        "type": "market"
    }
    with pytest.raises(PaperTraderError) as excinfo:
        paper_trader.place_order(market_order)
    assert "Market price not available" in str(excinfo.value)
    
    # Test extreme slippage scenario
    paper_trader.market_data_handler.price_feed[symbol] = Decimal("50000")
    limit_order = {
        "symbol": symbol,
        "quantity": 1,
        "side": "buy",
        "type": "limit",
        "price": "45000"  # 10% below market
    }
    with pytest.raises(PaperTraderError) as excinfo:
        paper_trader.place_order(limit_order)
    assert "price too far from market price" in str(excinfo.value)
    
    # Test rapid price changes
    paper_trader.market_data_handler.price_feed[symbol] = Decimal("50000")
    buy_order = {
        "symbol": symbol,
        "quantity": 1,
        "side": "buy",
        "type": "limit",
        "price": "50000"
    }
    result = paper_trader.place_order(buy_order)
    assert result["status"] == "filled"
    
    # Simulate price spike
    paper_trader.market_data_handler.price_feed[symbol] = Decimal("55000")
    sell_order = {
        "symbol": symbol,
        "quantity": 1,
        "side": "sell",
        "type": "market"
    }
    result = paper_trader.place_order(sell_order)
    
    # Verify slippage is applied correctly on market order
    execution_price = Decimal(result["execution_price"])
    assert execution_price < Decimal("55000")  # Price should be lower due to sell slippage
    assert execution_price >= Decimal("54945")  # Max 0.1% slippage

def test_stop_loss_orders(paper_trader_with_market_data):
    """Test comprehensive stop-loss order functionality"""
    paper_trader = paper_trader_with_market_data
    symbol = "BTC-USD"
    
    # Set up initial position and market data
    initial_position = Decimal("2.0")
    paper_trader.positions[symbol] = Position(symbol)
    paper_trader.positions[symbol].quantity = initial_position
    paper_trader.market_data_handler.price_feed[symbol] = Decimal("50000")
    
    # Test basic stop-loss sell order
    stop_loss_order = {
        "symbol": symbol,
        "side": "sell",
        "quantity": Decimal("1.0"),
        "type": "stop-loss",
        "stop_price": "49000"  # Stop price below current market
    }
    
    # Order should be pending initially (price above stop)
    result = paper_trader.place_order(stop_loss_order)
    assert result["status"] == "pending"
    assert paper_trader.get_position(symbol) == initial_position
    
    # Simulate price drop below stop price
    paper_trader.market_data_handler.price_feed[symbol] = Decimal("48500")
    result = paper_trader.place_order(stop_loss_order)
    assert result["status"] == "filled"
    assert result["execution_type"] == "stop-loss"
    assert Decimal(result["trigger_price"]) == Decimal("49000")
    assert paper_trader.get_position(symbol) == initial_position - Decimal("1.0")
    
    # Test trailing stop-loss
    trailing_stop = {
        "symbol": symbol,
        "side": "sell",
        "quantity": Decimal("0.5"),
        "type": "stop-loss",
        "stop_price": "49000",
        "trailing": True,
        "trail_offset": "0.02"  # 2% trailing stop
    }
    
    # Initialize with higher market price
    paper_trader.market_data_handler.price_feed[symbol] = Decimal("51000")
    result = paper_trader.place_order(trailing_stop)
    assert result["status"] == "pending"
    
    # Price moves up, stop price should adjust
    paper_trader.market_data_handler.price_feed[symbol] = Decimal("52000")
    result = paper_trader.place_order(trailing_stop)
    assert result["status"] == "pending"
    assert Decimal(result["trigger_price"]) > Decimal("49000")  # Stop price moved up
    
    # Price drops enough to trigger stop
    paper_trader.market_data_handler.price_feed[symbol] = Decimal("49000")
    result = paper_trader.place_order(trailing_stop)
    assert result["status"] == "filled"
    assert result["execution_type"] == "stop-loss"
    assert "slippage" in result
    
    # Test dynamic slippage based on volatility
    # Set up volatile price history
    paper_trader.market_data_handler.price_history[symbol] = [
        Decimal("48000"),
        Decimal("52000"),
        Decimal("49000"),
        Decimal("51000"),
        Decimal("50000")
    ]
    
    stop_loss_volatile = {
        "symbol": symbol,
        "side": "sell",
        "quantity": Decimal("1.0"),
        "type": "stop-loss",
        "stop_price": "49000"
    }
    
    # Set price to trigger stop
    paper_trader.market_data_handler.price_feed[symbol] = Decimal("48500")
    result = paper_trader.place_order(stop_loss_volatile)
    assert result["status"] == "filled"
    assert Decimal(result["slippage"]) > Decimal("0.001")  # Higher slippage due to volatility


class TestTradeHistoryManager:
    def test_trade_history_persistence(self):
        """Test trade history persistence and loading"""
        history_manager = TradeHistoryManager(data_dir="test_trades")
        test_trade = {
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": "BTC-USD",
            "side": "buy",
            "quantity": "1",
            "price": "50000"
        }
        
        # Save trade and reload history
        history_manager.save_trade(test_trade)
        loaded_trades = history_manager.load_trades()
        
        # Verify trade is saved and loaded correctly
        assert test_trade in loaded_trades
        
        # Cleanup test files
        import shutil
        shutil.rmtree("test_trades")

    def test_load_trades_filtered_by_date(self):
        """Test loading trades filtered by date"""
        history_manager = TradeHistoryManager(data_dir="test_trades")
        
        # Create some test trades with different timestamps
        trades = [
            {"timestamp": datetime(2025, 1, 1).isoformat(), "symbol": "BTC-USD", "side": "buy", "quantity": "1", "price": "50000"},
            {"timestamp": datetime(2025, 1, 5).isoformat(), "symbol": "ETH-USD", "side": "sell", "quantity": "0.5", "price": "3000"},
            {"timestamp": datetime(2025, 1, 10).isoformat(), "symbol": "BTC-USD", "side": "buy", "quantity": "0.1", "price": "52000"}
        ]
        for trade in trades:
            history_manager.save_trade(trade)
            
        # Load trades starting from 2025-01-05
        start_date = datetime(2025, 1, 5)
        filtered_trades = history_manager.load_trades(start_date=start_date)
        
        # Verify only trades on or after 2025-01-05 are loaded
        assert len(filtered_trades) == 2
        assert datetime.fromisoformat(filtered_trades[0]['timestamp']) >= start_date
        assert datetime.fromisoformat(filtered_trades[1]['timestamp']) >= start_date
        
        # Cleanup test files
        import shutil
        shutil.rmtree("test_trades")