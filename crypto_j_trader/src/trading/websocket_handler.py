"""WebSocket handler for real-time market data."""
import asyncio
import logging
import json
import websockets
from typing import Dict, Any, Optional, Callable, List, Set
from datetime import datetime, timezone
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)

class WebSocketHandler:
    def __init__(self, config: Dict[str, Any]):
        """Initialize WebSocket handler with configuration."""
        self.config = config['websocket']
        self.url = self.config['url']
        self.ping_interval = self.config.get('ping_interval', 30)
        self.reconnect_delay = self.config.get('reconnect_delay', 5)
        self.max_reconnect_delay = self.config.get('max_reconnect_delay', 300)  # 5 minutes
        self.subscription_retry_delay = self.config.get('subscription_retry_delay', 5)
        self.heartbeat_timeout = self.config.get('heartbeat_timeout', 60)  # seconds
        self.max_missed_heartbeats = self.config.get('max_missed_heartbeats', 3)
        
        self._ws = None
        self._is_connected = False
        self.running = False
        self.subscriptions: Set[str] = set()
        self.pending_subscriptions: Set[str] = set()
        self.last_message_time = datetime.now(timezone.utc)
        self.connection_attempts = 0
        self.missed_heartbeats = 0
        self.message_handlers: List[Callable[[Dict[str, Any]], Any]] = []
        self._message_task = None
        self._heartbeat_task = None
        self._subscription_task = None

    @property
    def is_connected(self) -> bool:
        """Return current connection status."""
        return self._is_connected and self._ws is not None

    async def _heartbeat_loop(self) -> None:
        """Monitor connection health using heartbeats."""
        while self.running and self._is_connected:
            try:
                await asyncio.sleep(self.ping_interval)
                time_since_last = (datetime.now(timezone.utc) - self.last_message_time).total_seconds()
                
                if time_since_last > self.heartbeat_timeout:
                    self.missed_heartbeats += 1
                    logger.warning(f"Missed heartbeat {self.missed_heartbeats}/{self.max_missed_heartbeats}")
                    
                    if self.missed_heartbeats >= self.max_missed_heartbeats:
                        logger.error("Maximum missed heartbeats reached, forcing reconnection")
                        self._is_connected = False
                        if self._ws:
                            await self._ws.close()
                        break
                else:
                    self.missed_heartbeats = 0
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")

    async def _subscription_manager(self) -> None:
        """Manage subscriptions and retry failed ones."""
        while self.running:
            try:
                # Process pending subscriptions
                if self._is_connected and self.pending_subscriptions:
                    for channel in list(self.pending_subscriptions):
                        await self._subscribe_with_retry(channel)
                        await asyncio.sleep(0.5)  # Prevent flooding
                
                # Verify existing subscriptions
                if self._is_connected and self.subscriptions:
                    subscription_status = await self._verify_subscriptions()
                    if not subscription_status:
                        logger.warning("Some subscriptions are invalid, retrying...")
                        for channel in self.subscriptions:
                            self.pending_subscriptions.add(channel)
                
                await asyncio.sleep(self.subscription_retry_delay)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in subscription manager: {e}")
                await asyncio.sleep(self.subscription_retry_delay)

    async def start(self) -> None:
        """Start the WebSocket handler and maintain connection recovery."""
        self.running = True
        while self.running:
            try:
                if not await self.connect():
                    delay = min(self.reconnect_delay * (2 ** self.connection_attempts), 
                              self.max_reconnect_delay)
                    logger.info(f"Reconnecting in {delay} seconds...")
                    await asyncio.sleep(delay)
                    continue

                # Start background tasks
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                self._subscription_task = asyncio.create_task(self._subscription_manager())
                self._message_task = asyncio.create_task(self._message_loop())

                # Wait for any task to complete (which indicates an issue)
                done, pending = await asyncio.wait(
                    [self._heartbeat_task, self._subscription_task, self._message_task],
                    return_when=asyncio.FIRST_COMPLETED
                )

                # Cancel remaining tasks
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

                # Reset connection state
                self._is_connected = False
                self.connection_attempts += 1

            except Exception as e:
                logger.error(f"Critical WebSocket error: {e}")
            finally:
                if self.running:
                    await asyncio.sleep(self.reconnect_delay)

    async def stop(self) -> None:
        """Stop the WebSocket handler and cleanup resources."""
        self.running = False
        
        # Cancel all background tasks
        tasks = [self._message_task, self._heartbeat_task, self._subscription_task]
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Close connection
        await self.disconnect()
        
        # Reset state
        self.subscriptions.clear()
        self.pending_subscriptions.clear()
        self.connection_attempts = 0
        self.missed_heartbeats = 0

    async def connect(self) -> bool:
        """Establish WebSocket connection with retry logic."""
        try:
            if self._ws:
                await self.disconnect()
            
            # Initialize connection with ping_interval
            self._ws = await websockets.connect(
                self.url,
                ping_interval=self.ping_interval,
                close_timeout=5,
                extra_headers=self.config.get('headers', {})
            )
            
            # Send authentication if required
            if 'auth' in self.config:
                auth_message = {
                    "type": "auth",
                    **self.config['auth']
                }
                await self._ws.send(json.dumps(auth_message))
            
            self._is_connected = True
            self.last_message_time = datetime.now(timezone.utc)
            self.missed_heartbeats = 0
            logger.info("WebSocket connected successfully")
            
            # Add existing subscriptions to pending for resubscription
            self.pending_subscriptions.update(self.subscriptions)
            self.subscriptions.clear()
            
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
                # Move all subscriptions to pending for next connection
                self.pending_subscriptions.update(self.subscriptions)
                self.subscriptions.clear()

    async def subscribe(self, channel: str) -> None:
        """Subscribe to a channel."""
        self.pending_subscriptions.add(channel)
        if self._is_connected:
            await self._subscribe_with_retry(channel)

    async def _subscribe_with_retry(self, channel: str, max_attempts: int = 3) -> bool:
        """Subscribe to a channel with retry logic."""
        if not self._is_connected or not self._ws:
            return False

        for attempt in range(max_attempts):
            try:
                subscription_message = {
                    "type": "subscribe",
                    "channel": channel
                }
                await self._ws.send(json.dumps(subscription_message))
                
                # Wait for subscription confirmation
                confirmation = await self._wait_for_subscription_confirmation(channel)
                if confirmation:
                    self.subscriptions.add(channel)
                    self.pending_subscriptions.discard(channel)
                    logger.info(f"Successfully subscribed to {channel}")
                    return True
                    
            except Exception as e:
                logger.error(f"Subscription attempt {attempt + 1} failed for {channel}: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(self.subscription_retry_delay)
                    
        return False

    async def _wait_for_subscription_confirmation(self, channel: str, timeout: float = 5.0) -> bool:
        """Wait for subscription confirmation message."""
        try:
            start_time = datetime.now(timezone.utc)
            while (datetime.now(timezone.utc) - start_time).total_seconds() < timeout:
                if channel in self.subscriptions:
                    return True
                await asyncio.sleep(0.1)
            return False
        except Exception as e:
            logger.error(f"Error waiting for subscription confirmation: {e}")
            return False

    async def _verify_subscriptions(self) -> bool:
        """Verify all subscriptions are active."""
        try:
            if not self._is_connected or not self._ws:
                return False
                
            status_message = {
                "type": "status",
                "command": "subscriptions"
            }
            await self._ws.send(json.dumps(status_message))
            return True
            
        except Exception as e:
            logger.error(f"Error verifying subscriptions: {e}")
            return False

    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a channel."""
        self.pending_subscriptions.discard(channel)
        
        if not self._is_connected or not self._ws:
            self.subscriptions.discard(channel)
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
        """Main loop to receive and process messages."""
        while self._is_connected and self.running and self._ws:
            try:
                message = await self._ws.recv()
                self.last_message_time = datetime.now(timezone.utc)
                self.missed_heartbeats = 0
                
                # Parse message if needed
                if isinstance(message, str):
                    message = json.loads(message)
                
                # Handle subscription confirmations
                if message.get('type') == 'subscribed':
                    channel = message.get('channel')
                    if channel:
                        self.subscriptions.add(channel)
                        self.pending_subscriptions.discard(channel)
                
                await self.on_message(message)

            except ConnectionClosed:
                logger.warning("WebSocket connection closed")
                self._is_connected = False
                break
            except asyncio.CancelledError:
                logger.info("Message loop cancelled")
                raise
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON message received: {e}")
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                if not (self.running and self._is_connected):
                    break
                await asyncio.sleep(1)  # Prevent tight loop on persistent errors

    async def on_message(self, message: Dict[str, Any]) -> None:
        """Process a received message by dispatching it to all handlers."""
        if not self.running:
            return

        for handler in self.message_handlers:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")

    def add_message_handler(self, handler: Callable[[Dict[str, Any]], Any]) -> None:
        """Register a new message handler."""
        if handler not in self.message_handlers:
            self.message_handlers.append(handler)

    def remove_message_handler(self, handler: Callable[[Dict[str, Any]], Any]) -> None:
        """Remove a message handler."""
        if handler in self.message_handlers:
            self.message_handlers.remove(handler)

    def get_connection_info(self) -> Dict[str, Any]:
        """Get current connection status and statistics."""
        return {
            'connected': self.is_connected,
            'running': self.running,
            'last_message': self.last_message_time.isoformat(),
            'connection_attempts': self.connection_attempts,
            'missed_heartbeats': self.missed_heartbeats,
            'active_subscriptions': list(self.subscriptions),
            'pending_subscriptions': list(self.pending_subscriptions)
        }