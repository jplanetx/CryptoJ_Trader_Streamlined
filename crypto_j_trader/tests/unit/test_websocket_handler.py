"""Unit tests for WebSocket handler."""
import pytest
import pytest_asyncio
import asyncio
import json
import websockets
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from crypto_j_trader.src.trading.websocket_handler import WebSocketHandler

# Use function scope for test isolation
pytestmark = pytest.mark.asyncio(loop_scope="function")

@pytest.fixture
def websocket_config():
    """Test configuration for websocket."""
    return {
        'websocket': {
            'url': 'wss://test.example.com/ws',
            'ping_interval': 0.1,  # Short interval for tests
            'reconnect_delay': 0.01,  # Very short delay for faster tests
            'subscriptions': ['BTC-USD']
        }
    }

def create_mock_ws():
    """Helper to create a mock websocket with proper side effects."""
    mock = AsyncMock()
    mock.send = AsyncMock()
    mock.close = AsyncMock()
    mock.closed = False
    
    # Configure recv responses
    responses = [
        '{"type":"connected"}',
        asyncio.CancelledError()
    ]
    
    async def mock_recv():
        if not responses:
            raise asyncio.CancelledError()
        return responses.pop(0)
        
    mock.recv = AsyncMock(side_effect=mock_recv)
    return mock

@pytest_asyncio.fixture
async def mock_ws_handler(websocket_config):
    """Create WebSocketHandler instance."""
    handler = WebSocketHandler(websocket_config)
    
    # Create a fresh mock websocket for each test
    async def mock_connect():
        handler._ws = create_mock_ws()
        handler._is_connected = True
        handler.last_message_time = datetime.now()
        return True
        
    handler.connect = mock_connect
    
    # Ensure initial connection
    await handler.connect()
    return handler

async def cleanup_handler(handler, task=None):
    """Helper function to properly cleanup handler and task."""
    handler.running = False
    
    if task and not task.done():
        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=0.1)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass
    
    if handler._ws:
        await handler._ws.close()
        handler._ws = None
    handler._is_connected = False

@pytest.mark.timeout(1)  # Ensure test doesn't hang
async def test_websocket_connection(mock_ws_handler):
    """Test WebSocket connection lifecycle."""
    task = None
    try:
        task = asyncio.create_task(mock_ws_handler.start())
        await asyncio.sleep(0.1)  # Increased wait for connection establishment
        assert mock_ws_handler._is_connected, "WebSocket should be connected"
        assert mock_ws_handler._ws is not None, "WebSocket connection exists"
    finally:
        await cleanup_handler(mock_ws_handler, task)

@pytest.mark.timeout(1)  # Ensure test doesn't hang
async def test_websocket_reconnection(mock_ws_handler):
    """Test WebSocket reconnection on failure."""
    task = None
    try:
        connection_attempts = 0
        
        async def mock_failing_connect():
            nonlocal connection_attempts
            connection_attempts += 1
            if connection_attempts == 1:
                raise Exception("Connection failed")
            if not mock_ws_handler._ws:
                mock_ws_handler._ws = create_mock_ws()
            mock_ws_handler._is_connected = True
            return True
        
        mock_ws_handler.connect = mock_failing_connect
        task = asyncio.create_task(mock_ws_handler.start())
        await asyncio.sleep(0.05)  # Short wait
        assert connection_attempts > 1
    finally:
        await cleanup_handler(mock_ws_handler, task)

@pytest.mark.timeout(1)  # Ensure test doesn't hang
async def test_websocket_message_handling(mock_ws_handler):
    """Test WebSocket message handling."""
    task = None
    try:
        received_messages = []
        test_message = {"type": "ticker", "price": "50000"}
        
        # Set up message handling
        mock_ws_handler._ws.recv = AsyncMock(side_effect=[
            json.dumps(test_message),
            asyncio.CancelledError()
        ])
        
        async def message_handler(message):
            received_messages.append(message)
        
        mock_ws_handler.add_message_handler(message_handler)
        task = asyncio.create_task(mock_ws_handler.start())
        await asyncio.sleep(0.05)  # Short wait
        
        assert len(received_messages) == 1
        assert received_messages[0] == test_message
    finally:
        await cleanup_handler(mock_ws_handler, task)

@pytest.mark.timeout(1)  # Ensure test doesn't hang
async def test_websocket_subscription(mock_ws_handler):
    """Test WebSocket subscription management."""
    task = None
    try:
        subscribed_channels = set()
        
        async def mock_send(message):
            data = json.loads(message)
            if data['type'] == 'subscribe':
                subscribed_channels.add(data['channel'])
                
        mock_ws_handler._ws.send = AsyncMock(side_effect=mock_send)
        task = asyncio.create_task(mock_ws_handler.start())
        await asyncio.sleep(0.05)  # Short wait
        
        await mock_ws_handler.subscribe("BTC-USD")
        assert "BTC-USD" in subscribed_channels
        assert "BTC-USD" in mock_ws_handler.subscriptions
    finally:
        await cleanup_handler(mock_ws_handler, task)

@pytest.mark.timeout(1)  # Ensure test doesn't hang
async def test_connection_recovery(mock_ws_handler):
    """Test WebSocket connection recovery scenarios."""
    task = None
    try:
        connection_states = []
        
        async def mock_connect():
            mock_ws_handler._ws = create_mock_ws()
            mock_ws_handler._is_connected = True
            connection_states.append("connected")
            return True
            
        async def mock_disconnect():
            if mock_ws_handler._ws:
                await mock_ws_handler._ws.close()
            mock_ws_handler._ws = None
            mock_ws_handler._is_connected = False
            connection_states.append("disconnected")
            # Raise ConnectionClosed to trigger reconnection
            raise websockets.ConnectionClosed(1006, "Connection closed")
            
        mock_ws_handler.connect = mock_connect
        mock_ws_handler.disconnect = mock_disconnect
        
        task = asyncio.create_task(mock_ws_handler.start())
        await asyncio.sleep(0.05)  # Short wait for initial connection
        
        assert mock_ws_handler.is_connected
        await mock_ws_handler.disconnect()
        await asyncio.sleep(0.1)  # Wait for reconnection
        
        assert mock_ws_handler.is_connected
        assert "disconnected" in connection_states
        assert connection_states.count("connected") >= 2
    finally:
        await cleanup_handler(mock_ws_handler, task)
