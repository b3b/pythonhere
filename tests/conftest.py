import asyncio
import pytest

from herethere.everywhere import ConnectionConfig
from herethere.there.client import Client

from main import PythonHereApp, run_ssh_server


@pytest.fixture
def connection_config():
    return ConnectionConfig(
        host="localhost",
        port=8022,
        username="here",
        password="there",
    )


@pytest.fixture
async def app_instance():
    app = PythonHereApp()
    app_task = asyncio.ensure_future(app.async_run_app())
    server_task = asyncio.ensure_future(run_ssh_server(app))
    await asyncio.wait_for(app.ssh_server_started.wait(), 5)
    yield app
    server_task.cancel()
    app_task.cancel()
    await asyncio.gather(app_task, server_task)


@pytest.fixture
async def there(app_instance, connection_config):
    client = Client()
    await asyncio.wait_for(app_instance.ssh_server_started.wait(), 5)
    await client.connect(connection_config)
    yield client
