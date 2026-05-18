import asyncio
import os
import sys
from contextlib import suppress
from pathlib import Path

import nest_asyncio2
import pytest
from asyncssh import PermissionDenied
from herethere.everywhere import ConnectionConfig
from herethere.there.client import Client
from herethere.there.commands import ContextObject, there_group
from kivy.config import Config
from kivy.core.window import Window
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
async def app_instance(mocker, capfd, app_config, tmpdir):
    mocker.patch("main.App.user_data_dir", tmpdir)

    app = PythonHereApp()
    app.init_asyncio_state()
    app._on_ssh_connection_made = app.on_ssh_connection_made
    app.on_ssh_connection_made = mocker.Mock()

    app_task = asyncio.ensure_future(app.async_run_app())
    server_task = asyncio.ensure_future(run_ssh_server(app))
    await asyncio.wait_for(app.ssh_server_started.wait(), 5)
    yield app

    server_task.cancel()
    app_task.cancel()
    results = await asyncio.gather(app_task, server_task, return_exceptions=True)
    for result in results:
        if isinstance(result, BaseException) and not isinstance(
            result, asyncio.CancelledError
        ):
            raise result
    app.root.clear_widgets()
    Window.children.clear()


@pytest.fixture
async def there(app_instance, connection_config):
    client = Client()
    await asyncio.wait_for(app_instance.ssh_server_started.wait(), 5)
    await client.connect(connection_config)
    try:
        yield client
    finally:
        connection = client.connection.connection
        await client.disconnect()
        if connection is not None:
            with suppress(Exception):
                await connection.wait_closed()


@pytest.fixture
async def there_with_wrong_password(app_instance, connection_config):
    client = Client()
    connection_config.password = "nowhere"
    await asyncio.wait_for(app_instance.ssh_server_started.wait(), 5)
    with pytest.raises(PermissionDenied):
        await client.connect(connection_config)
    yield client


@pytest.fixture
def nested_event_loop():
    nest_asyncio2.apply()


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


@pytest.fixture
def mocked_android_modules(mocker):
    sys.modules["jnius"] = mocker.Mock()
    sys.modules["android"] = mocker.Mock()


@pytest.fixture
def test_py_script(app_instance):
    path = Path(app_instance.upload_dir) / "test.py"
    path.touch()
    return str(path)
