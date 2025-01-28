import pytest
import asyncio
import json
from unittest.mock import Mock, patch
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
def websocket_handler(config):
    return WebSocketHandler(config)

@pytest.mark.asyncio
async def test_websocket_connection(websocket_handler):
    """Test WebSocket connection establishment"""
    
    # Mock websockets.connect
    mock_ws = Mock()
    mock_ws.send = Mock()
    mock_ws.recv = Mock(return_value=json.dumps({
        'type': 'market_trades',
        'product_id': 'BTC-USD',
        'price': '50000',
        'size': '0.1'
    }))
    mock_ws.close = Mock()
    
    with patch('websockets.connect', return_value=mock_ws):
        # Start handler in background task
        task = asyncio.create_task(websocket_handler.start())
        
        # Wait for connection
        await asyncio.sleep(0.1)
        
        # Verify subscription messages were sent
        subscription_message = {
            'type': 'subscribe',
            'product_ids': ['BTC-USD'],
            'channel': 'market_trades'
        }
        mock_ws.send.assert_called_with(json.dumps(subscription_message))
        
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
    websocket_handler.register_callback('BTC-USD', mock_callback)
    
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
        
        # Wait for multiple reconnection attempts
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
    
    # Register callback
    websocket_handler.register_callback('BTC-USD', test_callback)
    assert 'BTC-USD' in websocket_handler.callbacks
    
    # Unregister callback
    websocket_handler.unregister_callback('BTC-USD')
    assert 'BTC-USD' not in websocket_handler.callbacks

@pytest.mark.asyncio
async def test_error_handling(websocket_handler):
    """Test error handling in message processing"""
    
    # Create failing callback
    async def failing_callback(data):
        raise Exception("Callback error")
    
    # Register callback
    websocket_handler.register_callback('BTC-USD', failing_callback)
    
    # Process message
    test_message = {
        'type': 'market_trades',
        'product_id': 'BTC-USD',
        'price': '50000',
        'size': '0.1'
    }
    
    # Should not raise exception
    await websocket_handler._process_message(test_message)