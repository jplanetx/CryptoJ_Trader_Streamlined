import pytest

def test_basic():
    """Basic test to verify pytest setup"""
    assert True

@pytest.mark.asyncio
async def test_async_basic():
    """Basic async test to verify pytest-asyncio setup"""
    assert True