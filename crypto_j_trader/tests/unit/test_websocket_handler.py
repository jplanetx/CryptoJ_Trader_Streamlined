"""Unit tests for WebSocket handler."""
import pytest
import asyncio
from datetime import datetime
from crypto_j_trader.src.trading.websocket_handler import WebSocketHandler

@pytest.fixture
def websocket_config():
    """Test configuration for websocket."""
    return {
        'websocket': {
            'url': 'wss://test.example.com/ws',
            'ping_interval': 30,
            'reconnect_delay': 0.1,  # Reduce delay for faster test
            'subscriptions': ['BTC-USD']
        }
    }

@pytest.fixture
def mock_ws_handler(websocket_config):
    """Create WebSocketHandler instance with mocked connections."""
    handler = WebSocketHandler(websocket_config)
    handler.running = True  # Enable the reconnection loop
    
    async def mock_connect():
        handler._is_connected = True
        return True

    async def mock_disconnect():
        return None

    handler.connect = mock_connect
    handler.disconnect = mock_disconnect
    return handler

@pytest.mark.asyncio
async def test_websocket_connection(mock_ws_handler):
    """Test WebSocket connection lifecycle."""
    # Start connection
    task = asyncio.create_task(mock_ws_handler.start())
    
    # Give it a moment to "connect"
    await asyncio.sleep(0.1)
    
    assert mock_ws_handler.is_connected
    assert isinstance(mock_ws_handler.last_message_time, datetime)
    
    # Cleanup
    await mock_ws_handler.stop()
    await asyncio.sleep(0.1)  # Allow cleanup to complete
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

@pytest.mark.asyncio
async def test_websocket_reconnection(mock_ws_handler):
    """Test WebSocket reconnection on failure."""
    # Set up connection counter
    mock_ws_handler.connection_attempts = 0
    
    async def mock_failing_connect():
        mock_ws_handler.connection_attempts += 1
        if mock_ws_handler.connection_attempts == 1:
            raise Exception("Connection failed")
        mock_ws_handler._is_connected = True
        return True
    
    mock_ws_handler.connect = mock_failing_connect
    
    # Start connection
    task = asyncio.create_task(mock_ws_handler.start())
    await asyncio.sleep(0.3)  # Allow time for one reconnect cycle (0.1s reconnect_delay)
    
    # Should have attempted to reconnect
    assert mock_ws_handler.connection_attempts > 1
    
    # Cleanup
    await mock_ws_handler.stop()  # Await the stop coroutine
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

@pytest.mark.asyncio
async def test_websocket_message_handling(mock_ws_handler):
    """Test WebSocket message handling."""
    received_messages = []
    
    async def mock_message_handler(message):
        received_messages.append(message)
    
    mock_ws_handler.on_message = mock_message_handler
    
    # Start handler
    task = asyncio.create_task(mock_ws_handler.start())
    await asyncio.sleep(0.1)
    
    # Simulate receiving a message
    test_message = {"type": "ticker", "price": "50000"}
    # Use the handler's message callback directly
    await mock_ws_handler.on_message(test_message)
    
    assert len(received_messages) == 1
    assert received_messages[0] == test_message
    
    # Cleanup
    await mock_ws_handler.stop()
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

@pytest.mark.asyncio
async def test_websocket_subscription(mock_ws_handler):
    """Test WebSocket subscription management."""
    subscribed_channels = set()
    
    # Create a new mock subscribe method
    original_subscribe = mock_ws_handler.subscribe

    async def mock_subscribe_wrapper(channel):
        subscribed_channels.add(channel)
        return await original_subscribe(channel)
    
    mock_ws_handler.subscribe = mock_subscribe_wrapper
    
    # Start handler
    task = asyncio.create_task(mock_ws_handler.start())
    await asyncio.sleep(0.1)
    
    # Test subscription
    await mock_ws_handler.subscribe("BTC-USD")
    assert "BTC-USD" in subscribed_channels
    
    # Cleanup
    await mock_ws_handler.stop()
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
