"""WebSocket handler for real-time market data."""
import asyncio
import logging
import json
import websockets
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class WebSocketHandler:
    def __init__(self, config: Dict[str, Any]):
        """Initialize WebSocket handler with configuration."""
        self.config = config['websocket']
        self.url = self.config['url']
        self.ping_interval = self.config.get('ping_interval', 30)
        self.reconnect_delay = self.config.get('reconnect_delay', 5)
        self.subscription_retry_delay = self.config.get('subscription_retry_delay', 5)
        self.heartbeat_timeout = self.config.get('heartbeat_timeout', 60)  # seconds
        
        self._ws = None
        self._is_connected = False
        self.running = False
        self.subscriptions = set()
        self.last_message_time = datetime.now(timezone.utc)
        self.connection_attempts = 0
        self.message_handlers: List[Callable[[Dict[str, Any]], Any]] = []
        self._message_task = None

    @property
    def is_connected(self) -> bool:
        """Return current connection status."""
        return self._is_connected

    async def start(self) -> None:
        """Start the WebSocket handler and maintain connection recovery."""
        self.running = True
        while self.running:
            try:
                if not await self.connect():
                    await asyncio.sleep(self.reconnect_delay)
                    continue

                # Auto-subscribe to channels configured in the settings
                for channel in self.config.get('subscriptions', []):
                    await self._subscribe_with_retry(channel)

                # Start the message loop as a background task
                self._message_task = asyncio.create_task(self._message_loop())
                await self._message_task

            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            finally:
                self._is_connected = False
                if self.running:
                    logger.info("Attempting to reconnect in %s seconds...", self.reconnect_delay)
                    await asyncio.sleep(self.reconnect_delay)

    async def stop(self) -> None:
        """Stop the WebSocket handler."""
        self.running = False
        if self._message_task and not self._message_task.done():
            self._message_task.cancel()
            try:
                await self._message_task
            except (asyncio.CancelledError, Exception):
                pass
        await self.disconnect()

    async def connect(self) -> bool:
        """Establish WebSocket connection with a ping interval for heartbeat."""
        try:
            if self._ws:
                await self.disconnect()
            # Initialize connection with ping_interval
            self._ws = await websockets.connect(self.url, ping_interval=self.ping_interval)
            self._is_connected = True
            self.last_message_time = datetime.now(timezone.utc)
            logger.info("WebSocket connected successfully")
            return True
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self._is_connected = False
            return False

    async def disconnect(self) -> None:
        """Close the WebSocket connection."""
        if self._ws:
            try:
                await self._ws.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
            finally:
                self._ws = None
                self._is_connected = False

    async def subscribe(self, channel: str) -> None:
        """Subscribe to a channel."""
        if not self._is_connected or not self._ws:
            logger.warning(f"Cannot subscribe to {channel}: not connected")
            return

        try:
            subscription_message = {
                "type": "subscribe",
                "channel": channel
            }
            await self._ws.send(json.dumps(subscription_message))
            self.subscriptions.add(channel)
            logger.info(f"Subscribed to channel: {channel}")
        except Exception as e:
            logger.error(f"Subscription error for {channel}: {e}")

    async def _subscribe_with_retry(self, channel: str) -> None:
        """Subscribe to a channel with retry logic."""
        max_attempts = 3
        attempt = 0
        while attempt < max_attempts and self.running and self._is_connected:
            attempt += 1
            try:
                await self.subscribe(channel)
                if channel in self.subscriptions:
                    return
                else:
                    raise Exception(f"Failed to subscribe to {channel}")
            except Exception as e:
                logger.error(f"Subscription attempt {attempt} failed for {channel}: {e}")
                if attempt < max_attempts:
                    await asyncio.sleep(self.subscription_retry_delay)

    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a channel."""
        if not self._is_connected or not self._ws:
            return

        try:
            unsubscribe_message = {
                "type": "unsubscribe",
                "channel": channel
            }
            await self._ws.send(json.dumps(unsubscribe_message))
            self.subscriptions.discard(channel)
            logger.info(f"Unsubscribed from channel: {channel}")
        except Exception as e:
            logger.error(f"Unsubscription error for {channel}: {e}")

    async def _message_loop(self) -> None:
        """Main loop to receive and process messages; triggers recovery if heartbeat is lost."""
        while self._is_connected and self.running and self._ws:
            try:
                message = await self._ws.recv()
                self.last_message_time = datetime.now(timezone.utc)
                
                # Parse message if needed
                if isinstance(message, str):
                    message = json.loads(message)
                
                await self.on_message(message)

                # Check heartbeat timeout
                if (datetime.now(timezone.utc) - self.last_message_time).total_seconds() > self.heartbeat_timeout:
                    logger.warning("No heartbeat received within timeout, closing connection")
                    self._is_connected = False
                    break

            except websockets.ConnectionClosed:
                logger.warning("WebSocket connection closed")
                self._is_connected = False
                break
            except asyncio.CancelledError:
                logger.info("Message loop cancelled")
                raise
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                # Continue processing if still connected
                if not (self.running and self._is_connected):
                    break
                continue

    async def on_message(self, message: Dict[str, Any]) -> None:
        """Process a received message by dispatching it to all handlers."""
        if not self.running:
            return

        try:
            for handler in self.message_handlers:
                await handler(message)
        except Exception as e:
            logger.error(f"Error in message handler: {e}")

    def add_message_handler(self, handler: Callable[[Dict[str, Any]], Any]) -> None:
        """Register a new message handler."""
        if handler not in self.message_handlers:
            self.message_handlers.append(handler)
