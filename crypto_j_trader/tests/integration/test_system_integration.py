import pytest
from decimal import Decimal
from unittest.mock import patch
from crypto_j_trader.src.trading.trading_core import TradingBot  # Correct import

@pytest.mark.asyncio
async def test_trading_flow():
    config = {
        'trading_pairs': ['BTC-USD'],
        'risk_management': {
            'stop_loss_pct': 0.05,
            'max_position_size': 1.0,
        },
        'paper_trading': True
    }
    trading_bot = TradingBot(config)

    with patch('crypto_j_trader.src.trading.trading_core.OrderExecutor.create_order') as mock_create_order:
        mock_create_order.return_value = {'status': 'success', 'order_id': 'mock-order-id'}

        # Execute buy order
        buy_result = await trading_bot.execute_order('buy', 0.1, 50000.0, 'BTC-USD')
        assert buy_result['status'] == 'success'

        # Verify position
        position = await trading_bot.get_position('BTC-USD')
        assert position == Decimal('0')

        # Execute sell order
        sell_result = await trading_bot.execute_order('sell', 0.1, 55000.0, 'BTC-USD')
        assert sell_result['status'] == 'success'

        # Verify position after sell
        position = await trading_bot.get_position('BTC-USD')
        assert position == Decimal('0')
