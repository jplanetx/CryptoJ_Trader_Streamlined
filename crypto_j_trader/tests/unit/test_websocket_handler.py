"""Tests for WebSocket handler functionality."""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch, create_autospec
import websockets
from crypto_j_trader.src.trading.websocket_handler import WebSocketHandler

@pytest.fixture
def config():
    return {
        'trading_pairs': [
            {'pair': 'BTC-USD'},
            {'pair': 'ETH-USD'}
        ]
    }

@pytest.fixture
def websocket_handler():
    return WebSocketHandler(['BTC-USD'])  # Initialize with trading pair

@pytest.mark.asyncio
async def test_websocket_connection(websocket_handler):
    """Test WebSocket connection establishment"""
    # Create mock WebSocket
    mock_ws = create_autospec(websockets.WebSocketClientProtocol)
    mock_ws.send = AsyncMock()
    mock_ws.recv = AsyncMock(return_value=json.dumps({
        'type': 'market_trades',
        'product_id': 'BTC-USD',
        'price': '50000',
        'size': '0.1'
    }))
    mock_ws.close = AsyncMock()
    
    async def mock_connect(*args, **kwargs):
        return mock_ws
        
    with patch('websockets.connect', side_effect=mock_connect) as mock_connect:
        # Start handler in background task
        task = asyncio.create_task(websocket_handler.start())
        await asyncio.sleep(0.1)  # Allow connection to establish

        # Verify subscription message was sent
        subscription_message = {
            'type': 'subscribe',
            'product_ids': ['BTC-USD'],
            'channel': 'market_trades'
        }
        expected_message = json.dumps(subscription_message)
        mock_ws.send.assert_called_once_with(expected_message)

        # Stop handler
        await websocket_handler.stop()
        await task

@pytest.mark.asyncio
async def test_message_processing(websocket_handler):
    """Test processing of received messages"""
    # Create mock callback
    callback_called = False
    callback_data = None

    async def mock_callback(data):
        nonlocal callback_called, callback_data
        callback_called = True
        callback_data = data

    # Register callback
    websocket_handler.register_callback(['BTC-USD'], mock_callback)

    # Create mock message
    test_message = {
        'type': 'market_trades',
        'product_id': 'BTC-USD',
        'price': '50000',
        'size': '0.1'
    }

    # Process message
    await websocket_handler._process_message(test_message)

    # Verify callback was called with correct data
    assert callback_called
    assert callback_data == test_message

@pytest.mark.asyncio
async def test_reconnection(websocket_handler):
    """Test reconnection behavior"""
    connection_attempts = 0
    
    async def mock_connect(*args, **kwargs):
        nonlocal connection_attempts
        connection_attempts += 1
        raise Exception("Connection failed")
    
    with patch('websockets.connect', side_effect=mock_connect):
        # Start handler
        task = asyncio.create_task(websocket_handler.start())
        await asyncio.sleep(3)
        
        # Stop handler
        await websocket_handler.stop()
        await task
        
        # Verify multiple connection attempts were made
        assert connection_attempts > 1

@pytest.mark.asyncio
async def test_callback_registration(websocket_handler):
    """Test callback registration and unregistration"""
    async def test_callback(data):
        pass

    # Test registering with single string
    websocket_handler.register_callback('BTC-USD', test_callback)
    assert test_callback in websocket_handler.callbacks
    assert 'BTC-USD' in websocket_handler.trading_pairs

    # Test registering with list
    websocket_handler.register_callback(['ETH-USD'], test_callback)
    assert 'ETH-USD' in websocket_handler.trading_pairs

    # Test unregistering with single string
    websocket_handler.unregister_callback('BTC-USD', test_callback)
    assert 'BTC-USD' not in websocket_handler.trading_pairs

    # Test unregistering with list
    websocket_handler.unregister_callback(['ETH-USD'], test_callback)
    assert test_callback not in websocket_handler.callbacks
    assert 'ETH-USD' not in websocket_handler.trading_pairs

@pytest.mark.asyncio
async def test_error_handling(websocket_handler):
    """Test error handling in message processing"""
    # Create failing callback
    async def failing_callback(data):
        raise Exception("Callback error")
    
    # Register callback
    websocket_handler.register_callback(['BTC-USD'], failing_callback)
    
    # Process message that will trigger callback error
    test_message = {
        'type': 'market_trades',
        'product_id': 'BTC-USD',
        'price': '50000',
        'size': '0.1'
    }
    
    # Should raise callback error
    with pytest.raises(Exception) as exc_info:
        await websocket_handler._process_message(test_message)
    assert "Callback error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_no_trading_pairs():
    """Test behavior when no trading pairs are registered"""
    handler = WebSocketHandler()  # Initialize without trading pairs
    
    mock_ws = create_autospec(websockets.WebSocketClientProtocol)
    mock_ws.send = AsyncMock()
    mock_ws.close = AsyncMock()
    
    async def mock_connect(*args, **kwargs):
        return mock_ws
    
    with patch('websockets.connect', side_effect=mock_connect):
        task = asyncio.create_task(handler.start())
        await asyncio.sleep(0.1)
        
        # Verify no subscription message was sent
        mock_ws.send.assert_not_called()
        
        await handler.stop()
        await task
