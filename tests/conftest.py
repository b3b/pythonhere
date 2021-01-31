import asyncio
import os
import sys
from pathlib import Path

from asyncssh import PermissionDenied
import nest_asyncio
import pytest
from kivy.config import Config
from kivy.core.window import Window

from herethere.everywhere import ConnectionConfig
from herethere.there.client import Client
from herethere.there.commands import ContextObject, there_group

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
def app_config():
    Config.read("../tests/config.ini")


@pytest.fixture
async def app_instance(mocker, capfd, app_config):

    async def nop():
        pass

    app = PythonHereApp()
    app._on_ssh_connection_made = app.on_ssh_connection_made
    app.on_ssh_connection_made = mocker.Mock()
    app.cancel_asyncio_tasks = nop

    app_task = asyncio.ensure_future(app.async_run_app())
    server_task = asyncio.ensure_future(run_ssh_server(app))
    await asyncio.wait_for(app.ssh_server_started.wait(), 5)
    yield app

    server_task.cancel()
    app_task.cancel()
    await asyncio.gather(app_task, server_task)
    app.root.clear_widgets()
    Window.children.clear()


@pytest.fixture
async def there(app_instance, connection_config):
    client = Client()
    await asyncio.wait_for(app_instance.ssh_server_started.wait(), 5)
    await client.connect(connection_config)
    yield client


@pytest.fixture
async def there_with_wrong_password(app_instance, connection_config):
    client = Client()
    connection_config.password = "nowhere"
    await asyncio.wait_for(app_instance.ssh_server_started.wait(), 5)
    with pytest.raises(PermissionDenied):
        await client.connect(connection_config)
    yield client


@pytest.fixture
def nested_event_loop(event_loop):
    nest_asyncio.apply()


@pytest.fixture
async def call_there_group(nested_event_loop, app_instance, there):
    def _callable(args, code):
        there_group(
            args,
            "test",
            standalone_mode=False,
            obj=ContextObject(client=there, code=code),
        )

    return _callable


@pytest.fixture
def preserve_cwd():
    original_cwd = Path.cwd()
    original_path = sys.path[:]

    yield original_cwd

    sys.path = original_path[:]
    os.chdir(original_cwd)
