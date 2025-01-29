import asyncio
import json
import logging
import websockets
from typing import Dict, Optional, Callable, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class WebSocketHandler:
    """Handles real-time market data via WebSocket connection"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize WebSocket handler with configuration"""
        self.config = config
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.callbacks: Dict[str, Callable] = {}
        self.subscribed_pairs: set = set()
        self.last_message_time: Optional[datetime] = None
        self.reconnect_delay = 1  # Initial reconnect delay in seconds
        self.max_reconnect_delay = 60  # Maximum reconnect delay in seconds
        self.is_running = False
        
        # Configure logging
        self._setup_logging()
        
    def _setup_logging(self) -> None:
        """Configure handler-specific logging"""
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
    async def connect(self) -> None:
        """Establish WebSocket connection with error handling and reconnection"""
        while self.is_running:
            try:
                async with websockets.connect(
                    'wss://advanced-trade-ws.coinbase.com',
                    ping_interval=30,  # Keep connection alive
                    ping_timeout=10
                ) as websocket:
                    self.ws = websocket
                    self.reconnect_delay = 1  # Reset reconnect delay on successful connection
                    logger.info("WebSocket connection established")
                    
                    # Subscribe to channels
                    await self._subscribe()
                    
                    # Start message handling loop
                    await self._message_loop()
                    
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"WebSocket connection closed: {e}, attempting to reconnect...")
                await self._handle_reconnect()
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await self._handle_reconnect()
                
    async def _handle_reconnect(self) -> None:
        """Handle reconnection with exponential backoff"""
        logger.info(f"Waiting {self.reconnect_delay}s before reconnecting...")
        await asyncio.sleep(self.reconnect_delay)
        self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
        
    async def _subscribe(self) -> None:
        """Subscribe to market data channels"""
        if not self.ws:
            logger.error("Cannot subscribe: WebSocket connection not established")
            return
            
        for pair in self.config['trading_pairs']:
            pair_id = pair['pair']
            message = {
                "type": "subscribe",
                "product_ids": [pair_id],
                "channel": "market_trades",
            }
            try:
                await self.ws.send(json.dumps(message))
                self.subscribed_pairs.add(pair_id)
                logger.info(f"Subscribed to {pair_id}")
            except Exception as e:
                logger.error(f"Failed to subscribe to {pair_id}: {e}")
            
    async def _message_loop(self) -> None:
        """Handle incoming WebSocket messages"""
        if not self.ws:
            logger.error("Cannot start message loop: WebSocket connection not established")
            return
            
        while self.is_running:
            try:
                message = await self.ws.recv()
                self.last_message_time = datetime.now()
                
                data = json.loads(message)
                await self._process_message(data)
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Connection closed during message loop")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode WebSocket message: {e}")
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                continue
                
    async def _process_message(self, data: Dict[str, Any]) -> None:
        """Process received market data and trigger callbacks"""
        if data.get('type') == 'market_trades':
            pair_id = data.get('product_id')
            if pair_id and pair_id in self.callbacks:
                try:
                    await self.callbacks[pair_id](data)
                except Exception as e:
                    logger.error(f"Error in callback for {pair_id}: {e}")
                    logger.debug(f"Callback error details: {e}", exc_info=True)
                    
    def register_callback(self, pair_id: str, callback: Callable) -> None:
        """Register callback for market data updates"""
        self.callbacks[pair_id] = callback
        logger.debug(f"Registered callback for {pair_id}")
        
    def unregister_callback(self, pair_id: str) -> None:
        """Remove callback for market data updates"""
        if pair_id in self.callbacks:
            del self.callbacks[pair_id]
            logger.debug(f"Unregistered callback for {pair_id}")
            
    async def start(self) -> None:
        """Start the WebSocket handler"""
        self.is_running = True
        logger.info("Starting WebSocket handler")
        await self.connect()
        
    async def stop(self) -> None:
        """Stop the WebSocket handler"""
        self.is_running = False
        if self.ws:
            logger.info("Closing WebSocket connection")
            await self.ws.close()
            self.ws = None
        logger.info("WebSocket handler stopped")
