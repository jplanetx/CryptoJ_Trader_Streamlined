import unittest
from unittest.mock import patch
from crypto_j_trader.src.trading.trading_core import TradingBot

class TestTradingFlow(unittest.TestCase):
    def setUp(self):
        config = {
            'trading_pairs': ['BTC/USD', 'ETH/USD'],
            'position_size': 1.0,
            'stop_loss_pct': 0.05
        }
        self.bot = TradingBot(config)

    @patch('crypto_j_trader.src.trading.trading_core.logger')
    def test_full_trading_cycle(self, mock_logger):
        # Execute buy order
        buy_result = self.bot.execute_order('buy', 2.0, 50000.0)
        self.assertEqual(buy_result['status'], 'success')
        self.assertIn('order_id', buy_result)

        # Verify position
        position = self.bot.get_position()
        self.assertEqual(position['size'], 2.0)
        self.assertEqual(position['entry_price'], 50000.0)
        self.assertEqual(position['stop_loss'], 47500.0)

        # Execute sell order
        sell_result = self.bot.execute_order('sell', 2.0, 55000.0)
        self.assertEqual(sell_result['status'], 'success')
        self.assertIn('order_id', sell_result)

        # Verify position after sell
        position = self.bot.get_position()
        self.assertEqual(position['size'], 0.0)
        self.assertEqual(position['entry_price'], 0.0)
        self.assertEqual(position['stop_loss'], 0.0)

    @patch('crypto_j_trader.src.trading.trading_core.logger')
    def test_emergency_shutdown_during_trade(self, mock_logger):
        # Execute buy order
        buy_result = self.bot.execute_order('buy', 1.0, 50000.0)
        self.assertEqual(buy_result['status'], 'success')

        # Initiate emergency shutdown
        self.bot._emergency_shutdown()

        # Verify bot state after shutdown
        position = self.bot.get_position()
        self.assertEqual(position['size'], 0.0)
        self.assertEqual(position['entry_price'], 0.0)
        self.assertEqual(position['stop_loss'], 0.0)
        self.assertFalse(self.bot.is_healthy)

    def test_trading_flow_without_orders(self):
        # Verify initial state
        position = self.bot.get_position()
        self.assertEqual(position['size'], 0.0)
        self.assertEqual(position['entry_price'], 0.0)
        self.assertEqual(position['stop_loss'], 0.0)

    def test_trading_flow_with_invalid_orders(self):
        # Execute invalid buy order
        buy_result = self.bot.execute_order('buy', -1.0, 50000.0)
        self.assertEqual(buy_result['status'], 'error')
        self.assertIn('Invalid order parameters', buy_result['error'])

        # Execute invalid sell order
        sell_result = self.bot.execute_order('sell', 0.0, 55000.0)
        self.assertEqual(sell_result['status'], 'error')
        self.assertIn('Invalid order parameters', sell_result['error'])

if __name__ == '__main__':
    unittest.main()
