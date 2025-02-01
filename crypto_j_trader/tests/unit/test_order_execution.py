import pytest
from decimal import Decimal
from crypto_j_trader.src.trading.order_execution import OrderExecutor
from unittest.mock import MagicMock


@pytest.fixture
def mock_exchange_client():
    mock_client = MagicMock()
    mock_client.place_order.return_value = {"id": "test_order_id"}
    return mock_client

@pytest.fixture
def order_executor(mock_exchange_client):
    return OrderExecutor(
        exchange_client=mock_exchange_client,
        trading_pair="BTC-USD",
    )

@pytest.fixture
def paper_order_executor():
    return OrderExecutor(
        exchange_client=None,
        trading_pair="BTC-USD",
        paper_trading=True
    )

def test_execute_market_order(order_executor, mock_exchange_client):
    """Test basic market order execution"""
    result = order_executor.execute_order("buy", Decimal("0.1"))
    assert result["id"] == "test_order_id"
    assert order_executor.get_position("BTC-USD")["quantity"] == Decimal("0.1")
    mock_exchange_client.place_order.assert_called_once()


def test_execute_limit_order(order_executor, mock_exchange_client):
    """Test basic limit order execution"""
    order_executor.initialize_position("BTC-USD", Decimal("0.1"), Decimal("49000.0"))
    result = order_executor.execute_order("sell", Decimal("0.1"), "limit", Decimal("50000.0"))
    assert result["id"] == "test_order_id"
    position = order_executor.get_position("BTC-USD")
    assert position is None
    mock_exchange_client.place_order.assert_called_once()

def test_initialize_position(order_executor):
    """Test the position initialization method"""
    order_executor.initialize_position("BTC-USD", Decimal("0.5"), Decimal("45000.0"))
    position = order_executor.get_position("BTC-USD")
    assert position is not None
    assert position["quantity"] == Decimal("0.5")
    assert position["entry_price"] == Decimal("45000.0")



def test_execute_order_invalid_parameters(order_executor):
    """Test order execution with invalid parameters"""
    with pytest.raises(ValueError, match="Invalid order side: invalid"):    
      order_executor.execute_order("invalid", Decimal("0.1"))

    with pytest.raises(ValueError, match="Invalid order type: invalid"):    
      order_executor.execute_order("buy", Decimal("0.1"), "invalid")

    with pytest.raises(ValueError, match="Limit price required for limit orders"):    
      order_executor.execute_order("buy", Decimal("0.1"), "limit")


def test_paper_trade_market_order(paper_order_executor):
  """Test paper trade market order execution"""
  result = paper_order_executor.execute_order("buy", Decimal("0.1"))
  assert result["id"] == "paper_trade"
  assert result["status"] == "filled"
  assert paper_order_executor.get_position("BTC-USD")["quantity"] == Decimal("0.1")

def test_paper_trade_limit_order(paper_order_executor):
  """Test paper trade limit order execution"""
  paper_order_executor.initialize_position("BTC-USD", Decimal("0.1"), Decimal("49000.0"))
  result = paper_order_executor.execute_order("sell", Decimal("0.1"), "limit", Decimal("50000.0"))
  assert result["id"] == "paper_trade"
  assert result["status"] == "filled"
  assert paper_order_executor.get_position("BTC-USD") is None


def test_position_tracking_buy(order_executor, mock_exchange_client):
    """Test position tracking for buy orders"""
    # Initial buy
    order_executor.execute_order("buy", Decimal("0.1"), "market", Decimal("50000.0"))
    position = order_executor.get_position("BTC-USD")
    assert position is not None
    assert position["quantity"] == Decimal("0.1")
    assert position["entry_price"] == Decimal("50000.0")
    mock_exchange_client.place_order.assert_called_with(product_id='BTC-USD', side='buy', type='market', size='0.1')
    
    # Additional buy - should update position
    order_executor.execute_order("buy", Decimal("0.2"), "market", Decimal("51000.0"))
    position = order_executor.get_position("BTC-USD")
    assert position["quantity"] == Decimal("0.3")
    # Check weighted average entry price
    expected_price = (Decimal("0.1") * Decimal("50000.0") + Decimal("0.2") * Decimal("51000.0")) / Decimal("0.3")
    assert abs(position["entry_price"] - expected_price) < 0.01
    mock_exchange_client.place_order.assert_called_with(product_id='BTC-USD', side='buy', type='market', size='0.2')

def test_position_tracking_sell(order_executor, mock_exchange_client):
    """Test position tracking for sell orders"""
    # Initial buy
    order_executor.execute_order("buy", Decimal("0.3"), "market", Decimal("50000.0"))
    mock_exchange_client.place_order.assert_called_with(product_id='BTC-USD', side='buy', type='market', size='0.3')
    
    # Partial sell
    order_executor.execute_order("sell", Decimal("0.1"), "market", Decimal("52000.0"))
    mock_exchange_client.place_order.assert_called_with(product_id='BTC-USD', side='sell', type='market', size='0.1')
    position = order_executor.get_position("BTC-USD")
    assert position["quantity"] == Decimal("0.2")
    assert position["entry_price"] == Decimal("50000.0")  # Entry price unchanged for sells
    
    # Sell remaining - position should be closed
    order_executor.execute_order("sell", Decimal("0.2"), "market", Decimal("53000.0"))
    mock_exchange_client.place_order.assert_called_with(product_id='BTC-USD', side='sell', type='market', size='0.2')
    position = order_executor.get_position("BTC-USD")
    assert position is None

def test_sell_without_position(order_executor):
    """Test selling without an existing position"""
    with pytest.raises(ValueError, match="No position exists"):    
      order_executor.execute_order("sell", Decimal("0.1"))


def test_sell_exceeding_position(order_executor):
    """Test selling more than position size"""
    # Buy 0.1
    order_executor.execute_order("buy", Decimal("0.1"), "market", Decimal("50000.0"))

    # Try to sell 0.2
    with pytest.raises(ValueError, match="Insufficient position size"):    
      order_executor.execute_order("sell", Decimal("0.2"), "market", Decimal("51000.0"))

def test_multiple_positions(order_executor):
    """Test tracking multiple positions"""
    # Create BTC position
    order_executor = OrderExecutor(exchange_client = order_executor.exchange, trading_pair = "BTC-USD")
    order_executor.execute_order("buy", Decimal("0.1"), "market", Decimal("50000.0"))
    
    # Create ETH position
    order_executor2 = OrderExecutor(exchange_client = order_executor.exchange, trading_pair = "ETH-USD")
    order_executor2.execute_order("buy", Decimal("1.0"), "market", Decimal("3000.0"))
    
    # Verify both positions
    btc_pos = order_executor.get_position("BTC-USD")
    eth_pos = order_executor2.get_position("ETH-USD")
    
    assert btc_pos["quantity"] == Decimal("0.1")
    assert btc_pos["entry_price"] == Decimal("50000.0")
    assert eth_pos["quantity"] == Decimal("1.0")
    assert eth_pos["entry_price"] == Decimal("3000.0")