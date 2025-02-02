"""Unit tests for WebSocket handler."""
import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock
from crypto_j_trader.src.trading.websocket_handler import WebSocketHandler
import websockets
from websockets.exceptions import ConnectionClosed

@pytest.fixture
def websocket_config():
    return {
        'websocket': {
            'url': 'wss://test.example.com/ws',
            'ping_interval': 5,
            'reconnect_delay': 1,
            'subscription_retry_delay': 1,
            'heartbeat_timeout': 10,
            'max_missed_heartbeats': 3,
            'subscriptions': ['BTC/USD', 'ETH/USD']
        }
    }

@pytest.fixture
def mock_websocket():
    mock = AsyncMock()
    mock.recv = AsyncMock()
    mock.send = AsyncMock()
    mock.close = AsyncMock()
    return mock

@pytest.fixture
async def websocket_handler(websocket_config):
    handler = WebSocketHandler(websocket_config)
    yield handler
    await handler.stop()

@pytest.mark.asyncio
async def test_websocket_connection_success(websocket_handler, mock_websocket):
    with patch('websockets.connect', return_value=mock_websocket):
        success = await websocket_handler.connect()
        assert success
        assert websocket_handler.is_connected
        assert websocket_handler._ws is not None

@pytest.mark.asyncio
async def test_websocket_subscription(websocket_handler, mock_websocket):
    with patch('websockets.connect', return_value=mock_websocket):
        # Setup mock responses
        mock_websocket.recv.side_effect = [
            json.dumps({
                'type': 'subscribed',
                'channel': 'BTC/USD'
            })
        ]
        
        # Connect and subscribe
        await websocket_handler.connect()
        await websocket_handler.subscribe('BTC/USD')
        
        # Verify subscription message was sent
        mock_websocket.send.assert_called_with(
            json.dumps({
                'type': 'subscribe',
                'channel': 'BTC/USD'
            })
        )
        
        # Process messages to handle subscription confirmation
        await asyncio.sleep(0.1)
        assert 'BTC/USD' in websocket_handler.subscriptions

@pytest.mark.asyncio
async def test_websocket_message_handling(websocket_handler, mock_websocket):
    test_message = {'type': 'trade', 'price': 50000}
    message_received = asyncio.Event()
    
    async def message_handler(msg):
        assert msg == test_message
        message_received.set()
    
    with patch('websockets.connect', return_value=mock_websocket):
        # Setup mock response
        mock_websocket.recv.side_effect = [json.dumps(test_message)]
        
        # Connect and add message handler
        await websocket_handler.connect()
        websocket_handler.add_message_handler(message_handler)
        
        # Start message loop
        loop_task = asyncio.create_task(websocket_handler._message_loop())
        
        # Wait for message processing
        try:
            await asyncio.wait_for(message_received.wait(), timeout=1)
        finally:
            loop_task.cancel()
            try:
                await loop_task
            except asyncio.CancelledError:
                pass
        
        assert message_received.is_set()

@pytest.mark.asyncio
async def test_connection_recovery(websocket_handler, mock_websocket):
    connection_attempts = 0
    
    async def mock_connect(*args, **kwargs):
        nonlocal connection_attempts
        connection_attempts += 1
        if connection_attempts == 1:
            raise websockets.ConnectionClosed(1006, "Connection lost")
        return mock_websocket
    
    with patch('websockets.connect', side_effect=mock_connect):
        # Start handler
        handler_task = asyncio.create_task(websocket_handler.start())
        
        # Wait for reconnection
        await asyncio.sleep(2)
        
        # Stop handler
        await websocket_handler.stop()
        handler_task.cancel()
        try:
            await handler_task
        except asyncio.CancelledError:
            pass
        
        assert connection_attempts > 1

@pytest.mark.asyncio
async def test_heartbeat_monitoring(websocket_handler, mock_websocket):
    with patch('websockets.connect', return_value=mock_websocket):
        await websocket_handler.connect()
        
        # Start heartbeat monitoring
        heartbeat_task = asyncio.create_task(websocket_handler._heartbeat_loop())
        
        # Simulate missed heartbeats
        websocket_handler.last_message_time = datetime.now(timezone.utc) - timedelta(
            seconds=websocket_handler.heartbeat_timeout * 4
        )
        
        # Wait for heartbeat check
        await asyncio.sleep(websocket_handler.ping_interval * 2)
        
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        
        assert websocket_handler.missed_heartbeats >= websocket_handler.max_missed_heartbeats
        assert not websocket_handler.is_connected

@pytest.mark.asyncio
async def test_subscription_retry(websocket_handler, mock_websocket):
    subscription_succeeded = False
    
    async def mock_send(message):
        nonlocal subscription_succeeded
        msg = json.loads(message)
        if msg['type'] == 'subscribe':
            if not subscription_succeeded:
                subscription_succeeded = True
                raise websockets.ConnectionClosed(1006, "Connection lost")
    
    mock_websocket.send.side_effect = mock_send
    
    with patch('websockets.connect', return_value=mock_websocket):
        await websocket_handler.connect()
        await websocket_handler.subscribe('BTC/USD')
        
        # Wait for retry
        await asyncio.sleep(websocket_handler.subscription_retry_delay * 2)
        
        # The second attempt should succeed
        assert subscription_succeeded

@pytest.mark.asyncio
async def test_unsubscribe(websocket_handler, mock_websocket):
    with patch('websockets.connect', return_value=mock_websocket):
        await websocket_handler.connect()
        
        # Add subscription
        websocket_handler.subscriptions.add('BTC/USD')
        
        # Unsubscribe
        await websocket_handler.unsubscribe('BTC/USD')
        
        # Verify unsubscribe message was sent
        mock_websocket.send.assert_called_with(
            json.dumps({
                'type': 'unsubscribe',
                'channel': 'BTC/USD'
            })
        )
        
        assert 'BTC/USD' not in websocket_handler.subscriptions

@pytest.mark.asyncio
async def test_connection_info(websocket_handler, mock_websocket):
    with patch('websockets.connect', return_value=mock_websocket):
        await websocket_handler.connect()
        websocket_handler.subscriptions.add('BTC/USD')
        websocket_handler.pending_subscriptions.add('ETH/USD')
        
        info = websocket_handler.get_connection_info()
        
        assert info['connected'] is True
        assert info['running'] is True
        assert 'BTC/USD' in info['active_subscriptions']
        assert 'ETH/USD' in info['pending_subscriptions']
        assert isinstance(info['last_message'], str)
        assert isinstance(info['connection_attempts'], int)
        assert isinstance(info['missed_heartbeats'], int)