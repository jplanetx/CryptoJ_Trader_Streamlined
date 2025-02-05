import pytest
from decimal import Decimal
from crypto_j_trader.src.trading.paper_trading import PaperTrader
from crypto_j_trader.src.trading.order_execution import OrderExecutor
from crypto_j_trader.src.trading.exchange_service import ExchangeService
from crypto_j_trader.src.trading.paper_trading import PaperTraderError

class MockExchangeService(ExchangeService):
    """Mock exchange service for testing"""
    def __init__(self):
        pass

@pytest.fixture
def mock_order_executor():
    """Create an OrderExecutor instance in paper trading mode"""
    exchange = MockExchangeService()
    return OrderExecutor(exchange, "BTC-USD", paper_trading=True)

@pytest.fixture
def paper_trader(mock_order_executor):
    """Initialize PaperTrader with a mock order executor"""
    return PaperTrader(mock_order_executor)

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

def test_update_position_new_symbol(paper_trader):
    """Test position update for a new symbol"""
    symbol = "ETH-USD"
    quantity = Decimal("2.5")
    updated_position = paper_trader.update_position(symbol, quantity)
    assert updated_position == quantity
    assert paper_trader.positions[symbol] == quantity

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
    assert paper_trader.positions[symbol] == 2
    
    # Partial sell
    sell_order = {
        "symbol": symbol,
        "quantity": 1,
        "side": "sell",
        "type": "market"
    }
    paper_trader.place_order(sell_order)
    assert paper_trader.positions[symbol] == 1

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
    
    assert paper_trader.positions.get(symbol, 0) == expected_position

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
    final_position = trader.positions.get("BTC-USD", 0)
    assert final_position == 1  # 2 + 3 - 4 = 1
    
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
    risk_controls = {"max_drawdown": max_drawdown}
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