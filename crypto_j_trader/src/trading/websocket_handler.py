import asyncio
import json
import logging
import websockets
import time
import random
from typing import Dict, Set, Optional, Callable, Any
from datetime import datetime, timedelta
from websockets.exceptions import ConnectionClosed, InvalidStatusCode

class WebSocketHandler:
    def __init__(self, 
                 uri: str,
                 health_monitor: Any,
                 message_handler: Optional[Callable] = None,
                 ping_interval: int = 30):
        """
        Initialize WebSocket handler with connection management and health monitoring.

        Args:
            uri (str): WebSocket endpoint URI
            health_monitor (Any): Health monitoring instance
            message_handler (Optional[Callable]): Custom message handler function
            ping_interval (int): Ping interval in seconds
        """
        self.uri = uri
        self.health_monitor = health_monitor
        self.message_handler = message_handler
        self.ping_interval = ping_interval
        self.logger = logging.getLogger(__name__)
        
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.subscriptions: Set[str] = set()
        self.is_connected = False
        self.should_reconnect = True
        self.last_message_time = datetime.utcnow()
        self.connection_attempts = 0
        self.max_reconnect_delay = 300  # Maximum reconnection delay in seconds
        self.connection_tasks = set()

    def _start_background_tasks(self) -> None:
        """Start background tasks for connection management."""
        self.connection_tasks = set()
        self.connection_tasks.add(asyncio.create_task(self._heartbeat()))
        self.connection_tasks.add(asyncio.create_task(self._message_handler_loop()))
        self.connection_tasks.add(asyncio.create_task(self._connection_monitor()))

    async def _cleanup_tasks(self) -> None:
        """Clean up background tasks."""
        for task in self.connection_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self.connection_tasks.clear()

    async def connect(self) -> bool:
        """
        Establish WebSocket connection with retry logic.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if self.is_connected:
                return True

            self.connection_attempts += 1
            delay = min(2 ** self.connection_attempts + random.uniform(0, 1), 
                       self.max_reconnect_delay)

            self.logger.info(f"Attempting connection to {self.uri}")
            start_time = time.time()
            
            self.websocket = await websockets.connect(
                self.uri,
                ping_interval=self.ping_interval,
                ping_timeout=self.ping_interval // 2
            )
            
            self.is_connected = True
            self.connection_attempts = 0
            
            # Record connection latency
            latency = (time.time() - start_time) * 1000
            await self.health_monitor.record_latency('websocket_connect', latency)

            # Start background tasks
            self._start_background_tasks()
            
            # Resubscribe to previous subscriptions
            await self._resubscribe()
            
            self.logger.info("WebSocket connection established")
            return True

        except Exception as e:
            await self.health_monitor.record_error(f"websocket_connect_error: {str(e)}")
            self.logger.error(f"Connection error: {str(e)}")
            
            if self.should_reconnect:
                self.logger.info(f"Reconnecting in {delay} seconds")
                await asyncio.sleep(delay)
                return await self.connect()
            
            return False

    async def disconnect(self) -> None:
        """Gracefully close WebSocket connection."""
        try:
            self.should_reconnect = False
            await self._cleanup_tasks()
            
            if self.websocket:
                await self.websocket.close()
            
            self.is_connected = False
            self.logger.info("WebSocket connection closed")
        except Exception as e:
            self.logger.error(f"Disconnect error: {str(e)}")

    async def subscribe(self, channel: str) -> bool:
        """
        Subscribe to a WebSocket channel.

        Args:
            channel (str): Channel to subscribe to

        Returns:
            bool: True if subscription successful, False otherwise
        """
        try:
            if not self.is_connected:
                await self.connect()

            if channel in self.subscriptions:
                return True

            message = {
                'type': 'subscribe',
                'channel': channel
            }
            
            start_time = time.time()
            await self.websocket.send(json.dumps(message))
            
            # Record subscription latency
            latency = (time.time() - start_time) * 1000
            await self.health_monitor.record_latency('websocket_subscribe', latency)

            self.subscriptions.add(channel)
            self.logger.info(f"Subscribed to channel: {channel}")
            return True

        except Exception as e:
            await self.health_monitor.record_error(f"websocket_subscribe_error: {str(e)}")
            self.logger.error(f"Subscription error for channel {channel}: {str(e)}")
            return False

    async def unsubscribe(self, channel: str) -> bool:
        """
        Unsubscribe from a WebSocket channel.

        Args:
            channel (str): Channel to unsubscribe from

        Returns:
            bool: True if unsubscription successful, False otherwise
        """
        try:
            if not self.is_connected or channel not in self.subscriptions:
                return True

            message = {
                'type': 'unsubscribe',
                'channel': channel
            }
            
            await self.websocket.send(json.dumps(message))
            self.subscriptions.remove(channel)
            self.logger.info(f"Unsubscribed from channel: {channel}")
            return True

        except Exception as e:
            self.logger.error(f"Unsubscription error for channel {channel}: {str(e)}")
            return False

    async def _heartbeat(self) -> None:
        """Maintain connection with periodic ping/pong."""
        while self.is_connected and self.should_reconnect:
            try:
                await asyncio.sleep(self.ping_interval)
                if self.websocket:
                    ping_start = time.time()
                    pong_waiter = await self.websocket.ping()
                    await pong_waiter
                    latency = (time.time() - ping_start) * 1000
                    await self.health_monitor.record_latency('websocket_ping', latency)
                    self.last_message_time = datetime.utcnow()
            except Exception as e:
                self.logger.error(f"Heartbeat error: {str(e)}")
                await self._handle_connection_error()

    async def _message_handler_loop(self) -> None:
        """Handle incoming WebSocket messages."""
        while self.is_connected and self.should_reconnect:
            try:
                if not self.websocket:
                    await asyncio.sleep(1)
                    continue

                message = await self.websocket.recv()
                self.last_message_time = datetime.utcnow()

                if self.message_handler:
                    start_time = time.time()
                    await self.message_handler(json.loads(message))
                    latency = (time.time() - start_time) * 1000
                    await self.health_monitor.record_latency('message_processing', latency)

            except ConnectionClosed:
                self.logger.warning("WebSocket connection closed unexpectedly")
                await self._handle_connection_error()
            except json.JSONDecodeError as e:
                self.logger.error(f"Message parsing error: {str(e)}")
                await self.health_monitor.record_error('message_parse_error')
            except Exception as e:
                self.logger.error(f"Message handling error: {str(e)}")
                await self.health_monitor.record_error('message_handling_error')

    async def _connection_monitor(self) -> None:
        """Monitor connection health and trigger reconnection if needed."""
        while self.should_reconnect:
            try:
                await asyncio.sleep(self.ping_interval)
                
                if self.is_connected:
                    # Check last message time
                    time_since_last = (datetime.utcnow() - self.last_message_time).total_seconds()
                    
                    if time_since_last > self.ping_interval * 2:
                        self.logger.warning(f"No messages received for {time_since_last} seconds")
                        await self._handle_connection_error()
                        
            except Exception as e:
                self.logger.error(f"Connection monitor error: {str(e)}")

    async def _handle_connection_error(self) -> None:
        """Handle connection errors and initiate reconnection."""
        try:
            self.is_connected = False
            await self._cleanup_tasks()
            
            if self.websocket:
                await self.websocket.close()
                self.websocket = None

            if self.should_reconnect:
                await self.connect()

        except Exception as e:
            self.logger.error(f"Error handling connection error: {str(e)}")

    async def _resubscribe(self) -> None:
        """Resubscribe to all previous channels after reconnection."""
        try:
            channels = list(self.subscriptions)
            self.subscriptions.clear()
            
            for channel in channels:
                await self.subscribe(channel)
                
        except Exception as e:
            self.logger.error(f"Resubscription error: {str(e)}")
            await self.health_monitor.record_error('resubscription_error')

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """
        Send a message through the WebSocket connection.

        Args:
            message (Dict[str, Any]): Message to send

        Returns:
            bool: True if message sent successfully, False otherwise
        """
        try:
            if not self.is_connected:
                await self.connect()

            if self.websocket:
                start_time = time.time()
                await self.websocket.send(json.dumps(message))
                
                # Record message sending latency
                latency = (time.time() - start_time) * 1000
                await self.health_monitor.record_latency('message_send', latency)
                return True

            return False

        except Exception as e:
            self.logger.error(f"Message sending error: {str(e)}")
            await self.health_monitor.record_error('message_send_error')
            return False

    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get current connection status and metrics.

        Returns:
            Dict[str, Any]: Connection status information
        """
        return {
            'connected': self.is_connected,
            'uri': self.uri,
            'subscriptions': list(self.subscriptions),
            'last_message': self.last_message_time.isoformat(),
            'connection_attempts': self.connection_attempts
        }

    async def reset_connection(self) -> bool:
        """
        Reset and reestablish WebSocket connection.

        Returns:
            bool: True if reset successful, False otherwise
        """
        try:
            await self.disconnect()
            self.should_reconnect = True
            self.connection_attempts = 0
            return await self.connect()

        except Exception as e:
            self.logger.error(f"Connection reset error: {str(e)}")
            return False