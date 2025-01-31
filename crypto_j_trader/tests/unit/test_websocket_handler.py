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
            'reconnect_delay': 5,
            'subscriptions': ['BTC-USD']
        }
    }

@pytest.fixture
def mock_ws_handler(websocket_config):
    """Create WebSocketHandler instance with mocked connections."""
    handler = WebSocketHandler(websocket_config)
    handler.connect = asyncio.coroutine(lambda: True)  # Mock connection
    handler.disconnect = asyncio.coroutine(lambda: None)  # Mock disconnection
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
    mock_ws_handler.stop()
    await asyncio.sleep(0.1)  # Allow cleanup to complete
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

@pytest.mark.asyncio
async def test_websocket_reconnection(mock_ws_handler):
    """Test WebSocket reconnection on failure."""
    # Mock a connection failure
    connection_attempts = 0
    
    async def mock_connect():
        nonlocal connection_attempts
        connection_attempts += 1
        if connection_attempts == 1:
            raise Exception("Connection failed")
        return True
    
    mock_ws_handler.connect = mock_connect
    
    # Start connection
    task = asyncio.create_task(mock_ws_handler.start())
    await asyncio.sleep(0.1)
    
    # Should have attempted to reconnect
    assert connection_attempts > 1
    
    # Cleanup
    mock_ws_handler.stop()
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
    
    # Simulate receiving messages
    test_message = {"type": "ticker", "price": "50000"}
    await mock_ws_handler.process_message(test_message)
    
    assert len(received_messages) == 1
    assert received_messages[0] == test_message
    
    # Cleanup
    mock_ws_handler.stop()
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
    
    async def mock_subscribe(channel):
        subscribed_channels.add(channel)
        return True
    
    mock_ws_handler.subscribe = mock_subscribe
    
    # Start handler
    task = asyncio.create_task(mock_ws_handler.start())
    await asyncio.sleep(0.1)
    
    # Test subscription
    await mock_ws_handler.subscribe("BTC-USD")
    assert "BTC-USD" in subscribed_channels
    
    # Cleanup
    mock_ws_handler.stop()
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass