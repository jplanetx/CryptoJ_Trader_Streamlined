#!/usr/bin/env python3
import logging
from trading.trading_core import TradingBot
import asyncio

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('trades.log'),
            logging.StreamHandler()
        ]
    )
    
    # Initialize and run trading bot
    try:
        bot = TradingBot()
        asyncio.run(bot.run_trading_loop())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)