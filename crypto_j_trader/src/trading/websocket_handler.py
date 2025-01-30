"""WebSocket handler for market data streaming"""
import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Coroutine, Union
import websockets

logger = logging.getLogger(__name__)

class WebSocketHandler:
    """Handles WebSocket connections for market data"""
    
    def __init__(self, trading_pairs: list[str] = None):
        self.trading_pairs = trading_pairs if trading_pairs is not None else []
        self.callbacks = []
        self.running = False
        self.ws = None
        self.last_message_time = datetime.now()
        self.reconnect_delay = 1  # Start with 1 second delay
        
    def register_callback(self, pairs: Union[str, list[str]], callback: Callable) -> None:
        """Register a callback for specific trading pairs"""
        if not isinstance(pairs, list):
            pairs = [pairs]
        self.callbacks.append(callback)
        for pair in pairs:
            if pair not in self.trading_pairs:
                self.trading_pairs.append(pair)
    
    def unregister_callback(self, pairs: Union[str, list[str]], callback: Callable) -> None:
        """Unregister a callback for specific trading pairs"""
        if not isinstance(pairs, list):
            pairs = [pairs]
        for pair in pairs:
            if pair in self.trading_pairs:
                self.trading_pairs.remove(pair)
        self.callbacks = [cb for cb in self.callbacks if cb != callback]
            
    async def _connect(self) -> bool:
        """Establish WebSocket connection"""
        try:
            self.ws = await websockets.connect('wss://ws-feed.pro.coinbase.com')
            self.last_message_time = datetime.now()
            
            # Subscribe to market data if we have trading pairs
            if self.trading_pairs:
                subscription = {
                    'type': 'subscribe',
                    'product_ids': self.trading_pairs,
                    'channel': 'market_trades'
                }
                try:
                    await self.ws.send(json.dumps(subscription))
                    logger.info(f"Subscribed to {len(self.trading_pairs)} trading pairs")
                    return True
                except Exception as e:
                    logger.error(f"Failed to send subscription: {e}")
                    return False
            else:
                logger.warning("No trading pairs registered for subscription")
                return True
                
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            return False
            
    async def _process_message(self, message: Union[str, dict]) -> None:
        """Process received message and invoke callbacks"""
        try:
            data = json.loads(message) if isinstance(message, str) else message
            errors = []
            
            for callback in self.callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    error_msg = f"Callback error: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            if errors:
                raise Exception("; ".join(errors))
                
        except Exception as e:
            logger.error(f"Message processing error: {e}")
            raise  # Re-raise the exception for proper error handling in tests
            
    async def start(self) -> None:
        """Start WebSocket handler"""
        logger.info("Starting WebSocket handler")
        self.running = True
        
        while self.running:
            try:
                connected = await self._connect()
                if connected:
                    self.reconnect_delay = 1  # Reset delay on successful connection
                    
                    while self.running:
                        try:
                            message = await self.ws.recv()
                            self.last_message_time = datetime.now()
                            await self._process_message(message)
                        except Exception as e:
                            if isinstance(e, websockets.exceptions.ConnectionClosed):
                                logger.error("WebSocket connection closed")
                                break
                            logger.error(f"WebSocket error: {e}")
                            break
                            
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                
            if self.running:
                logger.info(f"Waiting {self.reconnect_delay}s before reconnecting...")
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, 60)  # Exponential backoff
                
    async def stop(self) -> None:
        """Stop WebSocket handler"""
        self.running = False
        if self.ws:
            await self.ws.close()
        logger.info("WebSocket handler stopped")
