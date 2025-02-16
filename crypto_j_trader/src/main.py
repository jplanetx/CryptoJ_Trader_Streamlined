"""
Minimal viable trading bot main entry point.
Focuses on basic trading functionality with essential safety features.
"""

import os
import logging
import json
from typing import Dict, Any
from coinbase.wallet.client import Client as RESTClient
from crypto_j_trader.src.trading.risk_management import RiskManager
from crypto_j_trader.src.trading.paper_trading import PaperTrader
from crypto_j_trader.src.trading.order_executor import OrderExecutor
from crypto_j_trader.src.trading.market_data_handler import MarketDataHandler

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

def validate_trading_pair(trading_pair: str) -> bool:
    """Validate trading pair format (e.g., 'BTC-USD')."""
    if not isinstance(trading_pair, str):
        return False
    parts = trading_pair.split('-')
    return len(parts) == 2 and all(parts)

class TradingBot:
    def __init__(self, config_path: str = './config/config.json'):
        """Initialize minimal trading bot"""
        self.config = self._load_config(config_path)
        self.client = None
        self.risk_manager = None
        self.market_data_handler = None
        self.order_executor = None
        self.paper_trader = None
        
        # Initialize core client first
        self.client = self._setup_client()
        
        # Initialize other handlers
        self._init_handlers()
        
        logger.info(f"Trading bot initialized for {self.config['trading_pair']}")

    def _init_handlers(self):
        """Initialize various handlers"""
        # Initialize market data handler
        self.market_data_handler = MarketDataHandler()
        
        # Initialize other components if needed
        if not self.risk_manager:
            self.risk_manager = RiskManager(self.config.get('risk', {}))
            
        if not self.order_executor:
            self.order_executor = OrderExecutor(trading_pair=self.config['trading_pair'])
            
        if not self.paper_trader:
            self.paper_trader = PaperTrader(
                order_executor=self.order_executor,
                market_data_handler=self.market_data_handler,
                config=self.config
            )

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

    def _setup_client(self) -> Any:
        """Initialize exchange client"""
        try:
            # For tests, check TESTING environment variable
            if os.getenv('TESTING') == 'true':
                api_key = 'test_api_key'
                api_secret = 'test_api_secret'
            else:
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
            # if not self.trading_core.check_health(): # Removed TradingCore
            #    raise SystemError("Health check failed")

            # Get current position
            # position = self.trading_core.get_position() # Removed TradingCore
            # logger.info(f"Current position: {position}")

            # Example order (replace with strategy logic)
            order = {
                "symbol": self.config['trading_pair'],
                "side": "buy",
                "quantity": 0.001,  # Changed from string to number
                "type": "market"
            }
            self.paper_trader.place_order(order)

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
