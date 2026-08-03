import asyncio
import os
import sys
import types
from contextlib import suppress
from pathlib import Path

import pytest
from asyncssh import PermissionDenied
from herethere.everywhere import ConnectionConfig
from herethere.everywhere.loop import run_sync
from herethere.there.client import Client
from herethere.there.commands import ContextObject, there_group
from kivy.clock import Clock
from kivy.config import Config
from kivy.core.window import Window
from main import PythonHereApp, run_ssh_server


async def run_herethere_sync(awaitable):
    """Run sync magic work while the in-process SSH server keeps its test loop.

    Use this only for code paths that exercise herethere's synchronous magic
    bridge. Plain async client tests should await the client API directly.
    """
    return await asyncio.to_thread(run_sync, awaitable)


@pytest.fixture
def connection_config(app_config):
    return ConnectionConfig(
        host="localhost",
        port=app_config,
        username="here",
        password="there",
    )


@pytest.fixture
def app_config(unused_tcp_port):
    Config.read(str(Path(__file__).with_name("config.ini")))
    Config.set("pythonhere", "port", str(unused_tcp_port))
    return unused_tcp_port


@pytest.fixture
async def app_instance(mocker, capfd, app_config, tmpdir):
    original_cwd = Path.cwd()
    os.chdir(Path(__file__).parents[1] / "pythonhere")
    key_path = Path(tmpdir) / "ssh_host_key"
    server_path = mocker.patch("server_here.Path")
    server_path.return_value.resolve.return_value = key_path
    mocker.patch("main.App.user_data_dir", tmpdir)
    Window.size = (800, 600)
    if Clock.has_ended:
        # Kivy's global Clock lifecycle is intentionally one-shot in a real
        # process. Tests create multiple complete app lifecycles in one process,
        # so make this fixture represent a fresh process for lifecycle-aware
        # events as well.
        Clock.has_ended = False

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
    os.chdir(original_cwd)


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
async def sync_there_client(app_instance, connection_config):
    """Client connected on herethere's sync magic loop.

    Use with command/magic helpers that call herethere.there.commands, because
    those commands call run_sync() internally and expect the client connection
    to belong to herethere's background magic loop.
    """
    client = Client()
    await asyncio.wait_for(app_instance.ssh_server_started.wait(), 5)
    await run_herethere_sync(client.connect(connection_config))
    try:
        yield client
    finally:
        connection = client.connection.connection
        await run_herethere_sync(client.disconnect())

        async def wait_closed():
            if connection is not None:
                await connection.wait_closed()

        with suppress(Exception):
            await run_herethere_sync(wait_closed())


@pytest.fixture
async def there_with_wrong_password(app_instance, connection_config):
    client = Client()
    connection_config.password = "nowhere"
    await asyncio.wait_for(app_instance.ssh_server_started.wait(), 5)
    with pytest.raises(PermissionDenied):
        await client.connect(connection_config)
    yield client


@pytest.fixture
async def call_there_group(app_instance, sync_there_client):
    """Call the synchronous %there command group from async tests.

    The command itself is synchronous, so it is run in a worker thread. This
    leaves pytest's event loop free to service the in-process PythonHere SSH
    server which receives the command.
    """

    async def _callable(args, code):
        return await asyncio.to_thread(
            there_group,
            args,
            "test",
            standalone_mode=False,
            obj=ContextObject(client=sync_there_client, code=code),
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
    """Install a small fake Android/Jnius surface for Android-only code paths.

    Keep this fake narrow: add methods/constants here only when tests exercise
    the corresponding behavior in android_here or launcher_here.
    """
    activity = mocker.Mock()
    context = mocker.Mock()
    app_info = mocker.Mock(icon=1)
    manager = mocker.Mock()
    manager.isRequestPinShortcutSupported.return_value = True
    context.getApplicationInfo.return_value = app_info
    activity.getApplicationContext.return_value = context
    activity.getSystemService.return_value = manager

    class Context:
        SHORTCUT_SERVICE = "shortcut"

    class Icon:
        createWithResource = mocker.Mock(return_value=mocker.Mock())

    class Intent:
        FLAG_ACTIVITY_NEW_TASK = 1
        FLAG_ACTIVITY_CLEAR_TASK = 2
        ACTION_MAIN = "android.intent.action.MAIN"

        def __init__(self, *args):
            self.args = args
            self.data = None
            self.flags = None
            self.action = None

        def setAction(self, action):
            self.action = action
            return self

        def setData(self, data):
            self.data = data
            return self

        def setFlags(self, flags):
            self.flags = flags
            return self

        def getData(self):
            return self.data

    class PythonActivity:
        mActivity = activity

    class ShortcutInfoBuilder:
        def __init__(self, *args):
            self.args = args

        def setShortLabel(self, label):
            self.short_label = label
            return self

        def setLongLabel(self, label):
            self.long_label = label
            return self

        def setIntent(self, intent):
            self.intent = intent
            return self

        def setIcon(self, icon):
            self.icon = icon
            return self

        def build(self):
            return self

    class System:
        exit = mocker.Mock()

    class Uri:
        @staticmethod
        def parse(value):
            uri = mocker.Mock()
            uri.toString.return_value = value
            return uri

    classes = {
        "android.content.Context": Context,
        "android.graphics.drawable.Icon": Icon,
        "android.content.Intent": Intent,
        "org.kivy.android.PythonActivity": PythonActivity,
        "android.content.pm.ShortcutInfo$Builder": ShortcutInfoBuilder,
        "java.lang.System": System,
        "android.net.Uri": Uri,
    }

    def autoclass(name):
        return classes[name]

    sys.modules["jnius"] = types.SimpleNamespace(
        autoclass=autoclass,
        cast=mocker.Mock(side_effect=lambda _class_name, obj: obj),
    )
    sys.modules["android"] = types.SimpleNamespace(activity=mocker.Mock())


@pytest.fixture
def test_py_script(app_instance):
    path = Path(app_instance.upload_dir) / "test.py"
    path.touch()
    return str(path)
