"""
Core trading functionality implementing technical analysis, portfolio management,
and trade execution.
"""

import sys
import os
import json
import time
import re
import logging
import numpy as np
import pandas as pd
import asyncio
import signal
from .risk_management import RiskManager
from .websocket_handler import WebSocketHandler
from ..utils.monitoring import TradingMonitor
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta, timezone
from coinbase.rest import RESTClient
from ratelimit import limits, sleep_and_retry
from functools import wraps
from time import sleep
from itertools import combinations
import random

logger = logging.getLogger(__name__)

class TechnicalAnalysis:
    """Technical analysis indicators and calculations"""
    # [Previous TA class code remains unchanged...]

class TradingStrategy:
    """Trading strategy with multiple indicators and risk management"""
    # [Previous TradingStrategy class code remains unchanged...]

class PortfolioManager:
    """Manages portfolio positions and rebalancing"""
    # [Previous PortfolioManager class code remains unchanged...]

class TradingBot:
    """Enhanced trading bot with real-time data and emergency controls"""
    
    def __init__(self, config_path: str = './config.json'):
        """Initialize trading bot with enhanced features"""
        logger.debug("Starting bot initialization")
        logger.debug("Current working directory: %s", os.getcwd())
        
        self.config = self.load_config(config_path)
        self.client = self.setup_api_client()
        self.risk_manager = RiskManager(self.config)
        self.monitor = TradingMonitor(self.config)
        self.portfolio = None
        self.strategies = {}
        self.market_data = {}
        self.websocket_handler = None
        self.shutdown_requested = False
        self.emergency_shutdown = False
        self.last_heartbeat = datetime.now()
        self.initialize_components()
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("Trading bot initialized in %s mode",
                   "PAPER TRADING" if self.config['paper_trading'] else "LIVE")
        logger.info(f"Target: Double ${self.config['initial_capital']:.2f} to "
                   f"${self.config['target_capital']:.2f} in {self.config['days_target']} days")

    @staticmethod
    def load_api_keys() -> Dict[str, str]:
        """Load API keys from configuration file"""
        try:
            with open('./cdp_api_key.json', 'r') as f:
                data = json.load(f)
            return {
                'api_key': data['name'],
                'api_secret': data['privateKey']
            }
        except Exception as e:
            logger.error(f"Error loading API keys: {e}")
            raise

    def load_config(self, config_path: str) -> Dict:
        """Load and validate configuration"""
        logger.debug(f"Loading config from: {config_path}")
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            required_fields = [
                'initial_capital', 'target_capital', 'days_target',
                'paper_trading', 'trading_pairs', 'strategy'
            ]
            
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing required config field: {field}")
                    
            logger.debug("Config loaded successfully")
            return config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            raise

    def setup_api_client(self) -> RESTClient:
        """Initialize API client with credentials"""
        logger.debug("Loading API keys")
        try:
            api_keys = self.load_api_keys()
            client = RESTClient(
                api_key=api_keys['api_key'],
                api_secret=api_keys['api_secret']
            )
            
            # Test API connection
            accounts_response = client.get_accounts()
            accounts = accounts_response.accounts if hasattr(accounts_response, 'accounts') else []
            logger.info(f"API connection successful. Found {len(accounts)} accounts")
            return client
        except Exception as e:
            logger.error(f"Error setting up API client: {e}")
            raise

    def initialize_components(self):
        """Initialize trading components and WebSocket handler"""
        try:
            self.portfolio = PortfolioManager(self.config)
            self.strategies = {
                pair['pair']: TradingStrategy(self.config)
                for pair in self.config['trading_pairs']
            }
            
            # Initialize WebSocket handler if enabled
            if self.config.get('websocket', {}).get('enabled', False):
                self.websocket_handler = WebSocketHandler(self.config)
                # Register callbacks for each trading pair
                for pair in self.config['trading_pairs']:
                    self.websocket_handler.register_callback(
                        pair['pair'],
                        self._process_websocket_update
                    )
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
            raise

    def _validate_websocket_state(self) -> bool:
        """Validate WebSocket connection state"""
        if not self.websocket_handler:
            return True  # WebSocket not enabled
            
        if not self.websocket_handler.ws:
            logger.error("WebSocket connection not established")
            return False
            
        if not self.websocket_handler.is_running:
            logger.error("WebSocket handler not running")
            return False
            
        connected_pairs = set(self.websocket_handler.subscribed_pairs)
        configured_pairs = {pair['pair'] for pair in self.config['trading_pairs']}
        if not configured_pairs.issubset(connected_pairs):
            missing_pairs = configured_pairs - connected_pairs
            logger.error(f"Missing WebSocket subscriptions: {missing_pairs}")
            return False
            
        return True

    def _should_emergency_shutdown(self, error: Exception) -> bool:
        """Classify errors that should trigger emergency shutdown"""
        if isinstance(error, websockets.exceptions.ConnectionClosed):
            return self.websocket_handler.reconnect_delay >= self.websocket_handler.max_reconnect_delay
            
        if isinstance(error, Exception):
            error_str = str(error).lower()
            critical_keywords = [
                'api rate limit',
                'insufficient funds',
                'unauthorized',
                'invalid api key',
                'market offline'
            ]
            return any(keyword in error_str for keyword in critical_keywords)
            
        return False

    def _check_system_health(self) -> bool:
        """Enhanced system health monitoring"""
        try:
            # Check WebSocket connection health
            if self.websocket_handler:
                if not self.websocket_handler.last_message_time:
                    logger.error("No WebSocket messages received")
                    return False
                    
                # Check for stale WebSocket connection (no messages in 2x heartbeat interval)
                websocket_staleness = (datetime.now() - self.websocket_handler.last_message_time).total_seconds()
                heartbeat_threshold = self.config['websocket']['heartbeat_interval_seconds'] * 2
                if websocket_staleness > heartbeat_threshold:
                    logger.error(f"Stale WebSocket connection: {websocket_staleness}s since last message")
                    return False

                # Validate WebSocket state
                if not self._validate_websocket_state():
                    return False

            # Check market data staleness
            for pair, data in self.market_data.items():
                if data.empty:
                    logger.error(f"No market data for {pair}")
                    return False
                    
                latest_timestamp = data.index[-1]
                data_staleness = (datetime.now() - latest_timestamp).total_seconds()
                if data_staleness > self.config['execution']['interval_seconds'] * 3:
                    logger.error(f"Stale market data for {pair}: {data_staleness}s old")
                    return False

            # Check system resource limits
            if self.emergency_shutdown or self.shutdown_requested:
                return False

            return True
        except Exception as e:
            logger.error(f"Error in system health check: {e}")
            return False

    async def _initiate_emergency_shutdown(self):
        """Initiate emergency shutdown procedures"""
        try:
            logger.critical("EMERGENCY SHUTDOWN INITIATED")
            self.emergency_shutdown = True
            self.shutdown_requested = True
            
            # Close all open positions
            current_prices = {
                pair: data['price'].iloc[-1]
                for pair, data in self.market_data.items()
                if not data.empty
            }
            
            for pair, position in self.portfolio.positions.items():
                if position['quantity'] > 0 and pair in current_prices:
                    logger.info(f"Emergency: Closing position for {pair}")
                    await self.execute_trade(
                        pair,
                        'sell',
                        current_prices[pair],
                        position['quantity']
                    )
                    
            # Stop WebSocket connection
            if self.websocket_handler:
                await self.websocket_handler.stop()
                
            logger.critical("Emergency shutdown completed")
        except Exception as e:
            logger.error(f"Error during emergency shutdown: {e}")

    async def run_trading_loop(self):
        """Main trading loop with WebSocket integration and health monitoring"""
        logger.info("Starting trading loop")
        try:
            # Start WebSocket handler if enabled
            if self.websocket_handler:
                websocket_task = asyncio.create_task(self.websocket_handler.start())
                logger.info("WebSocket handler started")
            
            while not self.shutdown_requested:
                try:
                    # Update market data from REST API if WebSocket is not enabled
                    if not self.websocket_handler:
                        self.market_data = self.get_market_data()
                        if not self.market_data:
                            logger.warning("No market data received")
                            await asyncio.sleep(60)
                            continue

                    # Check system health
                    if not self._check_system_health():
                        logger.error("System health check failed")
                        await asyncio.sleep(30)  # Wait before retrying
                        continue

                    # Process each trading pair
                    for pair_config in self.config['trading_pairs']:
                        if self.emergency_shutdown:
                            logger.warning("Emergency shutdown active - skipping trading")
                            break
                            
                        pair = pair_config['pair']
                        if pair not in self.market_data:
                            continue
                            
                        try:
                            candles = self.market_data[pair]
                            signals = self.strategies[pair].analyze_market(candles)
                            current_price = candles['close'].iloc[-1]
                            
                            if signals['buy'] and not self.emergency_shutdown:
                                logger.info(f"Buy signal for {pair}")
                                await self.execute_trade(pair, 'buy', current_price)
                            elif signals['sell'] or self.emergency_shutdown:
                                logger.info(f"Sell signal for {pair}")
                                await self.execute_trade(pair, 'sell', current_price)
                        except Exception as e:
                            logger.error(f"Error processing {pair}: {e}")
                            if self._should_emergency_shutdown(e):
                                await self._initiate_emergency_shutdown()
                            continue

                    # Check for rebalancing
                    if not self.emergency_shutdown and self.portfolio.needs_rebalance():
                        current_prices = {
                            pair: data['close'].iloc[-1]
                            for pair, data in self.market_data.items()
                        }
                        await self.execute_rebalance(current_prices)

                    # Update monitoring metrics
                    for pair, data in self.market_data.items():
                        if not data.empty and pair in self.portfolio.positions:
                            position = self.portfolio.positions[pair]
                            metrics = {
                                'pair': pair,
                                'position_size': position['quantity'],
                                'current_price': data['close'].iloc[-1],
                                'entry_price': position['entry_price'],
                                'timestamp': datetime.now()
                            }
                            self.monitor.update_technical_metrics({'type': 'position_update', 'data': metrics})

                    # Wait for next iteration
                    await asyncio.sleep(self.config['execution']['interval_seconds'])
                except Exception as e:
                    logger.error(f"Error in trading loop iteration: {e}")
                    if self._should_emergency_shutdown(e):
                        await self._initiate_emergency_shutdown()
                    await asyncio.sleep(5)  # Brief pause before retrying
                
            logger.info("Trading loop stopping gracefully...")
            
            # Clean up
            if self.websocket_handler:
                await self.websocket_handler.stop()
                await websocket_task
        except Exception as e:
            logger.error(f"Fatal error in trading loop: {e}")
            await self._initiate_emergency_shutdown()
            raise

if __name__ == "__main__":
    bot = TradingBot()
    asyncio.run(bot.run_trading_loop())
