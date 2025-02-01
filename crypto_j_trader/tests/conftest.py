import pytest
import asyncio

@pytest.fixture(scope="function")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

def pytest_configure(config):
    config.option.asyncio_mode = "strict"