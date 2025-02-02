"""
Example test file demonstrating the usage of CryptoJ Trader test infrastructure.
"""
import pytest
import asyncio
import time
from decimal import Decimal

from crypto_j_trader.tests.utils import (
    test_config,
    mock_market_data,
    mock_account_balance,
    MockCoinbaseResponses,
    MockWebsocketMessages,
    handle_timeout
)

# Unit Test Examples
@pytest.mark.unit
def test_basic_configuration(test_config):
    """Example of a simple unit test using test configuration fixture."""
    assert test_config['trading']['symbols'] == ['BTC-USD', 'ETH-USD']
    assert test_config['paper_trading'] is True
    assert isinstance(test_config['risk_management']['max_position_size'], float)

@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_operation():
    """Example of an async test using pytest.mark.asyncio."""
    async with handle_timeout():
        # Simulate async operation
        await asyncio.sleep(0.1)
        assert True

@pytest.mark.unit
def test_mock_market_data(mock_market_data):
    """Example of using mock market data fixture."""
    btc_data = mock_market_data['BTC-USD']
    assert isinstance(btc_data['price'], float)
    assert btc_data['volume'] > 0
    assert all(key in btc_data for key in ['bid', 'ask', 'timestamp'])

# Integration Test Examples
@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_integration():
    """Example of an integration test with mock API responses."""
    async with handle_timeout():
        # Setup mock responses
        mock_product = MockCoinbaseResponses.get_product('BTC-USD')
        mock_order = MockCoinbaseResponses.create_order()
        
        # Test API interaction
        assert mock_product['product_id'] == 'BTC-USD'
        assert mock_order['success'] is True
        assert 'order_id' in mock_order

@pytest.mark.integration
@pytest.mark.asyncio
async def test_websocket_integration():
    """Example of testing websocket functionality."""
    async with handle_timeout():
        # Setup mock websocket message
        mock_trades = MockWebsocketMessages.market_trades('BTC-USD')
        
        # Verify message structure
        assert mock_trades['channel'] == 'market_trades'
        assert len(mock_trades['events']) > 0
        assert mock_trades['events'][0]['product_id'] == 'BTC-USD'

# Performance Test Examples
@pytest.mark.performance
def test_operation_timing(performance_thresholds):
    """Example of a performance test using thresholds."""
    start_time = time.time()
    
    # Simulate operation
    time.sleep(0.1)
    
    duration = time.time() - start_time
    assert duration <= performance_thresholds['api_response_time']

@pytest.mark.performance
def test_response_processing(performance_thresholds):
    """Example of testing response processing performance."""
    mock_response = MockCoinbaseResponses.get_fills()
    
    start_time = time.time()
    # Process mock response
    processed_fills = [
        {
            'id': fill['trade_id'],
            'price': Decimal(fill['price']),
            'size': Decimal(fill['size'])
        }
        for fill in mock_response['fills']
    ]
    duration = time.time() - start_time
    
    assert duration <= performance_thresholds['websocket_message_processing']
    assert len(processed_fills) == len(mock_response['fills'])

# Error Handling Examples
@pytest.mark.unit
def test_error_handling(mock_response_factory):
    """Example of testing error scenarios."""
    # Test with success response
    success_response = mock_response_factory(
        success=True,
        data={'result': 'success'}
    )
    assert success_response['success'] is True
    assert success_response['data']['result'] == 'success'
    
    # Test with error response
    error_response = mock_response_factory(
        success=False,
        error='Test error message'
    )
    assert error_response['success'] is False
    assert error_response['error'] == 'Test error message'

# End-to-End Test Example
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_order_flow():
    """Example of an end-to-end test covering a complete workflow."""
    async with handle_timeout():
        # Setup mock responses
        product = MockCoinbaseResponses.get_product('BTC-USD')
        create_order = MockCoinbaseResponses.create_order()
        get_order = MockCoinbaseResponses.get_order(create_order['order_id'])
        fills = MockCoinbaseResponses.get_fills()
        
        # Verify complete order flow
        assert product['status'] == 'online'
        assert create_order['success'] is True
        assert get_order['order']['status'] == 'FILLED'
        assert len(fills['fills']) > 0
        
        # Verify order details match across responses
        order_id = create_order['order_id']
        assert get_order['order']['order_id'] == order_id
        assert fills['fills'][0]['order_id'] == order_id

if __name__ == '__main__':
    pytest.main([__file__, '-v'])