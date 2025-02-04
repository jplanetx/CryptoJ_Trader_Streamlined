"""
Minimal viable trading bot main entry point.
Focuses on basic trading functionality with essential safety features.
"""

import os
import logging
import json
from typing import Dict
from coinbase.rest import RESTClient
from trading.trading_core import TradingCore
from trading.risk_management import RiskManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('main')

class TradingBot:
    def __init__(self, config_path: str = './config/config.json'):
        """Initialize minimal trading bot"""
        self.config = self._load_config(config_path)
        self.client = self._setup_client()
        self.trading_core = TradingCore(self.client, self.config['trading_pair'])
        self.risk_manager = RiskManager(self.config['risk'])

        logger.info(f"Trading bot initialized for {self.config['trading_pair']}")

    def _load_config(self, config_path: str) -> Dict:
        """Load and validate configuration"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)

            required_fields = ['trading_pair', 'risk']
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing required config field: {field}")

            return config
        except Exception as e:
            logger.error(f"Configuration error: {e}")
            raise

    def _setup_client(self) -> RESTClient:
        """Initialize exchange client"""
        try:
            api_key = os.environ.get("COINBASE_API_KEY")
            api_secret = os.environ.get("COINBASE_API_SECRET")

            if not api_key or not api_secret:
                raise ValueError("Missing API key or secret in environment variables")

            client = RESTClient(
                api_key=api_key,
                api_secret=api_secret
            )

            # Test API connection
            response = client.get_accounts()
            if not hasattr(response, 'accounts'):
                raise ValueError("Invalid API response")

            logger.info("Exchange client initialized successfully")
            return client
        except Exception as e:
            logger.error(f"Client setup error: {e}")
            raise

    def run(self):
        """Main trading loop with basic functionality"""
        try:
            logger.info("Starting trading bot")

            # Basic health check
            if not self.trading_core.check_health():
                raise SystemError("Health check failed")

            # Get current position
            position = self.trading_core.get_position()
            logger.info(f"Current position: {position}")

            logger.info("Trading bot ready for operation")

        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            raise

if __name__ == "__main__":
    try:
        bot = TradingBot()
        bot.run()
    except Exception as e:
        logger.critical(f"Bot startup failed: {e}")
