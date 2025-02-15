import pytest
import json
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from websockets.exceptions import ConnectionClosedError as ConnectionClosed
from datetime import datetime, timedelta
from ...src.trading.websocket_handler import WebSocketHandler

@pytest.fixture
def health_monitor():
    """Create mock health monitor."""
    monitor = AsyncMock()
    monitor.record_latency = AsyncMock()
    monitor.record_error = AsyncMock()
    return monitor

@pytest.fixture
def message_handler():
    """Create mock message handler."""
    return AsyncMock()

@pytest.fixture
def websocket_handler(health_monitor, message_handler):
    """Create WebSocketHandler instance with mocks."""
    return WebSocketHandler(
        uri="wss://test.example.com/ws",
        health_monitor=health_monitor,
        message_handler=message_handler,
        ping_interval=1
    )

@pytest.fixture
def mock_websocket():
    """Create mock websocket connection."""
    websocket = AsyncMock()
    websocket.send = AsyncMock()
    websocket.recv = AsyncMock()
    websocket.ping = AsyncMock()
    websocket.close = AsyncMock()
    return websocket

@pytest.mark.asyncio
async def test_connection_monitor(websocket_handler, mock_websocket):
    """Test connection monitoring."""
    websocket_handler.websocket = mock_websocket
    websocket_handler.is_connected = True
    websocket_handler.last_message_time = datetime.utcnow() - timedelta(seconds=60)
    
    # Start connection monitor and let it run briefly
    task = asyncio.create_task(websocket_handler._connection_monitor())
    await asyncio.sleep(1.1)
    task.cancel()
    
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    assert websocket_handler.is_connected is False  # Should detect stale connection

@pytest.mark.asyncio
async def test_resubscribe(websocket_handler, mock_websocket):
    """Test resubscription after reconnection."""
    websocket_handler.websocket = mock_websocket
    websocket_handler.is_connected = True
    websocket_handler.subscriptions.add("test_channel_1")
    websocket_handler.subscriptions.add("test_channel_2")
    
    # Clear subscriptions and resubscribe
    channels = list(websocket_handler.subscriptions)
    await websocket_handler._resubscribe()
    await asyncio.sleep(0.1)  # Allow time for resubscription to complete
    
    assert all(channel in websocket_handler.subscriptions for channel in channels)
    assert mock_websocket.send.call_count == len(channels)

@pytest.mark.asyncio
async def test_send_message(websocket_handler, mock_websocket):
    """Test message sending."""
    websocket_handler.websocket = mock_websocket
    websocket_handler.is_connected = True
    
    test_message = {'type': 'test', 'data': 'test_data'}
    result = await websocket_handler.send_message(test_message)
    
    assert result is True
    mock_websocket.send.assert_called_once_with(json.dumps(test_message))

@pytest.mark.asyncio
async def test_send_message_not_connected(websocket_handler, mock_websocket):
    """Test message sending when not connected."""
    websocket_handler.is_connected = False
    
    with patch('websockets.connect', AsyncMock(return_value=mock_websocket)):
        test_message = {'type': 'test', 'data': 'test_data'}
        result = await websocket_handler.send_message(test_message)
        
        assert result is True
        assert websocket_handler.is_connected is True
        mock_websocket.send.assert_called_once()

@pytest.mark.asyncio
async def test_connection_status(websocket_handler, mock_websocket):
    """Test connection status reporting."""
    websocket_handler.websocket = mock_websocket
    websocket_handler.is_connected = True
    websocket_handler.subscriptions.add("test_channel")
    
    status = websocket_handler.get_connection_status()
    
    assert status['connected'] is True
    assert status['uri'] == "wss://test.example.com/ws"
    assert "test_channel" in status['subscriptions']
    assert 'last_message' in status
    assert 'connection_attempts' in status

@pytest.mark.asyncio
async def test_reset_connection(websocket_handler, mock_websocket):
    """Test connection reset."""
    websocket_handler.websocket = mock_websocket
    websocket_handler.is_connected = True
    
    with patch('websockets.connect', AsyncMock(return_value=mock_websocket)):
        result = await websocket_handler.reset_connection()
        
        assert result is True
        assert websocket_handler.connection_attempts == 0
        mock_websocket.close.assert_called_once()

@pytest.mark.asyncio
async def test_cleanup_tasks(websocket_handler):
    """Test background task cleanup."""
    # Create some dummy tasks
    async def dummy_task():
        while True:
            await asyncio.sleep(0.1)
    
    task1 = asyncio.create_task(dummy_task())
    task2 = asyncio.create_task(dummy_task())
    websocket_handler.connection_tasks = {task1, task2}
    
    await websocket_handler._cleanup_tasks()
    
    assert len(websocket_handler.connection_tasks) == 0
    assert task1.cancelled()
    assert task2.cancelled()

@pytest.mark.asyncio
async def test_handle_connection_error(websocket_handler, mock_websocket):
    """Test connection error handling."""
    websocket_handler.websocket = mock_websocket
    websocket_handler.is_connected = True
    
    with patch('websockets.connect', AsyncMock(return_value=mock_websocket)):
        await websocket_handler._handle_connection_error()
        
        assert not websocket_handler.is_connected
        mock_websocket.close.assert_called_once()
        # Should attempt reconnection
        await asyncio.sleep(0.1)
        assert websocket_handler.is_connected

@pytest.mark.asyncio
async def test_websocket_message_handling_with_multiple_subscriptions(
    websocket_handler, mock_websocket, message_handler
):
    """Test message handling with multiple subscriptions."""
    websocket_handler.websocket = mock_websocket
    websocket_handler.is_connected = True
    
    # Subscribe to multiple channels
    channels = ["channel1", "channel2", "channel3"]
    for channel in channels:
        await websocket_handler.subscribe(channel)
    
    # Test messages from different channels
    messages = [
        {'channel': 'channel1', 'data': 'data1'},
        {'channel': 'channel2', 'data': 'data2'},
        {'channel': 'channel3', 'data': 'data3'}
    ]
    
    for msg in messages:
        mock_websocket.recv.return_value = json.dumps(msg)
        task = asyncio.create_task(websocket_handler._message_handler_loop())
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        message_handler.assert_awaited_with(msg)

@pytest.mark.asyncio
async def test_websocket_reconnection_with_exponential_backoff(
    websocket_handler, mock_websocket
):
    """Test reconnection with exponential backoff."""
    connect_times = []
    
    # Mock connect to track call times
    async def mock_connect(*args, **kwargs):
        connect_times.append(time.time())
        raise ConnectionClosed(None, None)
    
    with patch('websockets.connect', mock_connect):
        task = asyncio.create_task(websocket_handler.connect())
        await asyncio.sleep(3)  # Allow for multiple reconnection attempts
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
    # Verify increasing delays between attempts
    delays = [connect_times[i+1] - connect_times[i] for i in range(len(connect_times)-1)]
    assert all(delays[i+1] > delays[i] for i in range(len(delays)-1))

@pytest.mark.asyncio
async def test_websocket_subscription_recovery(websocket_handler, mock_websocket):
    """Test subscription recovery after reconnection."""
    websocket_handler.websocket = mock_websocket
    websocket_handler.is_connected = True
    
    # Add initial subscriptions
    initial_channels = ["channel1", "channel2"]
    for channel in initial_channels:
        await websocket_handler.subscribe(channel)
    
    # Simulate disconnect and reconnect
    await websocket_handler._handle_connection_error()
    assert not websocket_handler.is_connected
    
    with patch('websockets.connect', AsyncMock(return_value=mock_websocket)):
        await websocket_handler.connect()
        
        # Verify all subscriptions were restored
        for channel in initial_channels:
           mock_websocket.send.assert_any_call(json.dumps({'type': 'subscribe', 'channel': channel}))

        # Verify subscription messages were sent
        assert mock_websocket.send.call_count >= len(initial_channels)

@pytest.mark.asyncio
async def test_websocket_health_monitoring_integration(
    websocket_handler, mock_websocket, health_monitor
):
    """Test integration with health monitoring."""
    websocket_handler.websocket = mock_websocket
    websocket_handler.is_connected = True
    
    # Test latency recording on connect
    with patch('websockets.connect', AsyncMock(return_value=mock_websocket)):
        await websocket_handler.connect()
        health_monitor.record_latency.assert_awaited_with('websocket_connect', pytest.approx(0, abs=100))
    
    # Test error recording
    mock_websocket.recv.side_effect = Exception("Test error")
    task = asyncio.create_task(websocket_handler._message_handler_loop())
    await asyncio.sleep(0.1)
    task.cancel()
    
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    health_monitor.record_error.assert_awaited_with("message_handling_error")

if __name__ == '__main__':
    pytest.main([__file__, '-v'])

"""Test websocket handler integration"""
import pytest
import asyncio
import json
import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock

class TestWebSocketHandler:
    @pytest.fixture
    def mock_health_monitor(self):
        """Create mock health monitor"""
        mock = AsyncMock()
        mock.record_latency = AsyncMock()
        mock.record_error = AsyncMock()
        return mock
        
    @pytest.fixture
    def message_handler(self):
        """Create message handler fixture"""
        async def handler(message: Dict[str, Any]) -> None:
            pass
        return handler
        
    @pytest.fixture
    def websocket_uri(self):
        """Test websocket URI"""
        return "wss://test.example.com/ws"

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_health_monitor, message_handler, websocket_uri):
        """Test successful websocket connection"""
        from crypto_j_trader.src.trading.websocket_handler import WebSocketHandler
        handler = WebSocketHandler(websocket_uri, mock_health_monitor, message_handler)
        
        assert handler.uri == websocket_uri
        assert handler.health_monitor == mock_health_monitor
        assert handler.message_handler == message_handler
        assert not handler.is_connected

    @pytest.mark.asyncio
    async def test_message_send(self, mock_health_monitor, message_handler, websocket_uri):
        """Test message sending"""
        handler = WebSocketHandler(websocket_uri, mock_health_monitor, message_handler)
        message = {"type": "test", "data": "test_data"}
        
        # Test sending without connection
        success = await handler.send_message(message)
        assert not success

        # Test sending after connection
        handler.is_connected = True
        handler.websocket = AsyncMock()
        
        success = await handler.send_message(message)
        assert success
        handler.websocket.send.assert_called_once_with(json.dumps(message))

    @pytest.mark.asyncio
    async def test_subscribe(self, mock_health_monitor, message_handler, websocket_uri):
        """Test channel subscription"""
        handler = WebSocketHandler(websocket_uri, mock_health_monitor, message_handler)
        handler.websocket = AsyncMock()
        handler.is_connected = True
        
        success = await handler.subscribe("test_channel")
        assert success
        assert "test_channel" in handler.subscriptions