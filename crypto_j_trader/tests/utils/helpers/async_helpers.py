"""
Async testing utilities for CryptoJ Trader tests.
"""
import asyncio
import pytest
import functools
from typing import Generator, AsyncGenerator
import contextlib

def async_test(f):
    """Decorator for async test functions to run in event loop."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(f(*args, **kwargs))
    return pytest.mark.asyncio(wrapper)

@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create and provide a new event loop for each test."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture
async def async_timeout() -> AsyncGenerator[None, None]:
    """Fixture to enforce timeout for async tests."""
    yield
    # Clean up pending tasks
    pending = asyncio.all_tasks() - {asyncio.current_task()}
    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)

@contextlib.asynccontextmanager
async def handle_timeout():
    """Context manager for handling async timeouts."""
    try:
        yield
    finally:
        pending = asyncio.all_tasks() - {asyncio.current_task()}
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)