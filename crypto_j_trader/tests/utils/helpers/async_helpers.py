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
    return pytest.mark.asyncio(f)

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