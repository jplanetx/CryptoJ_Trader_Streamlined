import unittest
from decimal import Decimal
from unittest.mock import MagicMock

from crypto_j_trader.src.trading.trading_core import TradingCore

class TestTradingCore(unittest.TestCase):
    def setUp(self):
        self.exchange_client = MagicMock()
        self.trading_pair = 'BTC-USD'
        self.trading_core = TradingCore(exchange_client=self.exchange_client, trading_pair=self.trading_pair)

    def test_execute_order_buy_market(self):
        # Setup mock response
        mock_order = {'order_id': '123', 'average_filled_price': '50000'}
        self.exchange_client.create_order.return_value = mock_order

        # Execute buy order
        result = self.trading_core.execute_order(side='buy', size=Decimal('1.0'), portfolio_value=Decimal('10000'))

        # Assertions
        self.exchange_client.create_order.assert_called_once()
        self.assertEqual(result['order_id'], '123')
        self.assertEqual(self.trading_core.position['size'], Decimal('1.0'))

    def test_execute_order_sell_market(self):
        # Setup initial position
        self.trading_core.position['size'] = Decimal('1.0')
        self.trading_core.position['entry_price'] = Decimal('50000')

        # Setup mock response
        mock_order = {'order_id': '124', 'average_filled_price': '51000'}
        self.exchange_client.create_order.return_value = mock_order

        # Execute sell order
        result = self.trading_core.execute_order(side='sell', size=Decimal('0.5'), portfolio_value=Decimal('10000'))

        # Assertions
        self.exchange_client.create_order.assert_called_once()
        self.assertEqual(result['order_id'], '124')
        self.assertEqual(self.trading_core.position['size'], Decimal('0.5'))

    def test_execute_order_limit(self):
        # Setup mock response
        mock_order = {'order_id': '125', 'average_filled_price': '50500'}
        self.exchange_client.create_order.return_value = mock_order

        # Execute limit order
        result = self.trading_core.execute_order(
            side='buy',
            size=Decimal('0.2'),
            portfolio_value=Decimal('10000'),
            order_type='limit',
            limit_price=Decimal('50500')
        )

        # Assertions
        self.exchange_client.create_order.assert_called_once_with(
            product_id='BTC-USD',
            side='buy',
            order_configuration={
                'limit': {
                    'base_size': '0.2',
                    'limit_price': '50500'
                }
            }
        )
        self.assertEqual(result['order_id'], '125')
        self.assertEqual(self.trading_core.position['size'], Decimal('0.2'))

    def test_health_check_pass(self):
        # Setup mock responses
        self.exchange_client.get_product.return_value = MagicMock(product='BTC-USD')
        self.exchange_client.get_accounts.return_value = MagicMock(accounts=['account1'])

        # Perform health check
        is_healthy = self.trading_core.check_health()

        # Assertions
        self.assertTrue(is_healthy)
        self.assertTrue(self.trading_core.is_healthy)

    def test_health_check_fail(self):
        # Setup mock to fail
        self.exchange_client.get_product.side_effect = Exception('API Error')

        # Perform health check
        is_healthy = self.trading_core.check_health()

        # Assertions
        self.assertFalse(is_healthy)
        self.assertFalse(self.trading_core.is_healthy)

if __name__ == '__main__':
    unittest.main()
