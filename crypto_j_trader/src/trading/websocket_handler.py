"""WebSocket handler for market data streaming"""
import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, Coroutine, Union, List
import websockets
from websockets.exceptions import WebSocketException

logger = logging.getLogger(__name__)

class WebSocketHandler:
    """Handles WebSocket connections for market data"""
    
    def __init__(self, config: Dict[str, Any]):
        ws_config = config.get('websocket', {})
        self.url = ws_config.get('url', 'wss://ws-feed.pro.coinbase.com')
        self.trading_pairs = ws_config.get('subscriptions', [])
        self.ping_interval = ws_config.get('ping_interval', 30)
        self.reconnect_delay = ws_config.get('reconnect_delay', 5)
        self.max_connection_attempts = ws_config.get('max_connection_attempts', 5)
        self.health_check_interval = ws_config.get('health_check_interval', 60)
        self.callbacks: List[Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]] = []
        self.running = False
        self.ws = None
        self.last_message_time = datetime.now()
        self._is_connected = False
        self.connection_attempts = 0
        self._subscribed_channels = set()
        self._health_check_task = None
        self._message_handler_task = None
        
    @property
    def is_connected(self) -> bool:
        """Property to access connection status."""
        return self._is_connected and self.ws is not None and not self.ws.closed

    @property
    def is_healthy(self) -> bool:
        """Check if the connection is healthy based on last message time."""
        return (datetime.now() - self.last_message_time) < timedelta(seconds=self.health_check_interval)

    async def _health_check(self) -> None:
        """Periodic health check to monitor connection status."""
        while self.running:
            try:
                if self.is_connected and not self.is_healthy:
                    logger.warning("Health check failed - reconnecting...")
                    await self._reconnect()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(1)

    async def connect(self) -> bool:
        """Establish WebSocket connection with explicit retry mechanism."""
        self.connection_attempts += 1
        logger.info(f"WebSocket connection attempt {self.connection_attempts}")
        
        try:
            if self.ws:
                await self.ws.close()
            
            self.ws = await websockets.connect(self.url)
            self._is_connected = True
            self.last_message_time = datetime.now()
            
            # Subscribe to channels
            if self._subscribed_channels:
                subscription_message = {
                    "type": "subscribe",
                    "channels": list(self._subscribed_channels)
                }
                await self.ws.send(json.dumps(subscription_message))
            
            logger.info(f"WebSocket connection successful on attempt {self.connection_attempts}")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket connection error on attempt {self.connection_attempts}: {e}")
            self._is_connected = False
            
            if self.connection_attempts < self.max_connection_attempts:
                await asyncio.sleep(self.reconnect_delay)
                return await self.connect()
            
            return False

    async def _reconnect(self) -> None:
        """Handle reconnection logic."""
        self._is_connected = False
        self.connection_attempts = 0
        
        while self.running and not self.is_connected:
            try:
                success = await self.connect()
                if success:
                    break
                logger.error("Failed to reconnect")
                await asyncio.sleep(self.reconnect_delay)
            except Exception as e:
                logger.error(f"Reconnection error: {e}")
                await asyncio.sleep(self.reconnect_delay)

    async def _handle_messages(self) -> None:
        """Handle incoming WebSocket messages."""
        while self.running:
            try:
                if not self.is_connected:
                    await asyncio.sleep(0.1)
                    continue
                    
                message = await self.ws.recv()
                self.last_message_time = datetime.now()
                
                try:
                    parsed_message = json.loads(message)
                    await self.on_message(parsed_message)
                    
                    # Process callbacks
                    for callback in self.callbacks:
                        try:
                            await callback(parsed_message)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")
                            
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message: {e}")
                    
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed")
                await self._reconnect()
                
            except Exception as e:
                logger.error(f"Message handling error: {e}")
                await asyncio.sleep(0.1)

    async def start(self) -> None:
        """Start WebSocket handler with connection management"""
        logger.info("Starting WebSocket handler")
        self.running = True
        self.connection_attempts = 0
        
        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check())
        
        # Start message handler task
        self._message_handler_task = asyncio.create_task(self._handle_messages())
        
        while self.running and self.connection_attempts < self.max_connection_attempts:
            try:
                success = await self.connect()
                if success:
                    break
                logger.error("Failed to establish WebSocket connection")
            except Exception as e:
                logger.error(f"Error starting WebSocket handler: {e}")
                self._is_connected = False
                if self.connection_attempts < self.max_connection_attempts:
                    await asyncio.sleep(self.reconnect_delay)

    async def on_message(self, message: Dict[str, Any]):
        """Default message handler."""
        logger.info(f"Received message: {message}")
        
    async def stop(self):
        """Stop WebSocket connection."""
        self.running = False
        self._is_connected = False
        
        if self._health_check_task:
            self._health_check_task.cancel()
        
        if self._message_handler_task:
            self._message_handler_task.cancel()
            
        if self.ws:
            await self.ws.close()
            
    def add_callback(self, callback: Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]) -> None:
        """Add a message callback."""
        self.callbacks.append(callback)
        
    async def subscribe(self, channel: str) -> bool:
        """Subscribe to a channel."""
        self._subscribed_channels.add(channel)
        
        if self.is_connected:
            try:
                subscription_message = {
                    "type": "subscribe",
                    "channels": [channel]
                }
                await self.ws.send(json.dumps(subscription_message))
            except Exception as e:
                logger.error(f"Subscription error: {e}")
                return False
                
        return True