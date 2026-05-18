import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import PropertyMock

import pytest
from asyncssh import PermissionDenied
from enum_here import ScreenName, ServerState
from main import PythonHereApp
from ui_here.server_screen_here import ServerScreenManager
from version_here import __version__


def test_dev_version_is_set():
    assert __version__ == "0.0.0"


def test_server_screen_update_states(mocker):
    screen = SimpleNamespace(current=None)
    app = SimpleNamespace(
        ssh_server_config_ready=asyncio.Event(),
        ssh_server_started=asyncio.Event(),
    )
    mocker.patch("ui_here.server_screen_here.App.get_running_app", return_value=app)
    unschedule = mocker.patch("ui_here.server_screen_here.Clock.unschedule")

    ServerScreenManager.update.__wrapped__(screen)
    assert screen.current == ServerState.not_configured

    app.ssh_server_config_ready.set()
    ServerScreenManager.update.__wrapped__(screen)
    assert screen.current == ServerState.starting_server

    app.ssh_server_started.set()
    screen.update_event = mocker.Mock()
    ServerScreenManager.update.__wrapped__(screen)
    assert screen.current == ServerState.ready
    unschedule.assert_called_once_with(screen.update_event)


@pytest.mark.asyncio
async def test_code_line_executed(capfd, app_instance, there):
    await there.runcode("print('hello there')")
    app_instance.on_ssh_connection_made.assert_called_once()
    assert capfd.readouterr().out == "hello there\n"


@pytest.mark.asyncio
async def test_connect_with_wrong_password(
    capfd, app_instance, there_with_wrong_password
):
    with pytest.raises(PermissionDenied):
        await there_with_wrong_password.runcode("print('hello there')")
    app_instance.on_ssh_connection_made.assert_not_called()
    assert not capfd.readouterr().out


@pytest.mark.asyncio
async def test_button_created(capfd, app_instance, there):
    await there.runcode(
        "\n".join(
            (
                "from kivy.app import App",
                "from kivy.uix.button import Button",
                "app = App.get_running_app()",
                "root = app.root",
                "root.add_widget(Button(text='button there'))",
                "print(root.children[0].text)",
            )
        )
    )
    assert capfd.readouterr().out == "button there\n"


@pytest.mark.asyncio
async def test_root_object_is_in_context(capfd, app_instance, there):
    await there.runcode("print(root)")
    captured = capfd.readouterr()
    assert captured.out.startswith("<ui_here.layout_here.RootLayout object ")


@pytest.mark.asyncio
async def test_settings_opened_from_action_bar(capfd, app_instance, there):
    assert app_instance.root.ids.screen_manager.current != "settings"
    await there.runcode("root.ids.open_settings_action.dispatch('on_release')")
    assert app_instance.root.ids.screen_manager.current == "settings"


@pytest.mark.asyncio
async def test_reset_window_environment_called(mocker, app_instance):
    app_instance.chdir = mocker.Mock()
    reset_window_environment = mocker.patch("main.reset_window_environment")
    app_instance._on_ssh_connection_made()
    reset_window_environment.assert_called_once()


def test_app_upload_dir_created(tmpdir):
    app = PythonHereApp()
    app.root_dir = tmpdir

    path = app.upload_dir

    assert path and Path(path).exists()
    assert app.upload_dir == path


def test_app_chdir_directory_changed(tmpdir, preserve_cwd):
    assert Path.cwd() != tmpdir
    app = PythonHereApp()
    app.chdir(tmpdir)
    assert Path.cwd() == tmpdir


@pytest.mark.asyncio
async def test_init_asyncio_state_creates_loop_owned_events():
    app = PythonHereApp()

    app.init_asyncio_state()
    first_config_ready = app.ssh_server_config_ready
    first_started = app.ssh_server_started
    first_connected = app.ssh_server_connected

    assert app.asyncio_loop is asyncio.get_running_loop()
    assert isinstance(first_config_ready, asyncio.Event)
    assert isinstance(first_started, asyncio.Event)
    assert isinstance(first_connected, asyncio.Event)

    app.init_asyncio_state()

    assert app.ssh_server_config_ready is not first_config_ready
    assert app.ssh_server_started is not first_started
    assert app.ssh_server_connected is not first_connected


@pytest.mark.asyncio
async def test_cancel_app_tasks_cancels_owned_tasks_only():
    never_run = asyncio.Event()

    async def coro():
        await never_run.wait()

    app_task = asyncio.create_task(coro())
    server_task = asyncio.create_task(coro())
    unrelated_task = asyncio.create_task(coro())
    app = PythonHereApp()
    app.app_task = app_task
    app.server_task = server_task

    assert not app_task.cancelled()
    assert not server_task.cancelled()
    assert not unrelated_task.cancelled()

    await app.cancel_app_tasks()

    assert app_task.cancelled()
    assert server_task.cancelled()
    assert not unrelated_task.cancelled()

    unrelated_task.cancel()
    await asyncio.gather(unrelated_task, return_exceptions=True)


@pytest.mark.asyncio
async def test_on_ssh_connection_made_initializes_window_once(mocker):
    app = PythonHereApp()
    app.init_asyncio_state()
    app.chdir = mocker.Mock()
    mocker.patch.object(
        PythonHereApp,
        "upload_dir",
        new_callable=PropertyMock,
        return_value="/tmp/pythonhere-upload",
    )
    reset_window_environment = mocker.patch(
        "main.reset_window_environment", return_value="new-root"
    )

    app.on_ssh_connection_made()
    app.on_ssh_connection_made()

    assert app.ssh_server_connected.is_set()
    reset_window_environment.assert_called_once()
    app.chdir.assert_called_once_with("/tmp/pythonhere-upload")
    assert app.ssh_server_namespace["root"] == "new-root"


def test_update_server_config_status_schedules_threadsafe_updates(mocker):
    class ImmediateThread:
        def __init__(self, name, target):
            self.name = name
            self.target = target

        def start(self):
            self.target()

    app = PythonHereApp()
    app.asyncio_loop = mocker.Mock()
    app.ssh_server_config_ready = mocker.Mock()
    app.settings = mocker.Mock()
    app.settings.get_pythonhere_config.return_value = {
        "username": "here",
        "password": "there",
        "port": 8022,
    }
    screen = mocker.Mock()
    root = mocker.Mock()
    root.ids = SimpleNamespace(here_screen_manager=screen)
    app.root = root

    schedule_once = mocker.patch("main.Clock.schedule_once")
    mocker.patch("main.threading.Thread", ImmediateThread)

    app.update_server_config_status()

    assert screen.current == ServerState.starting_server
    root.switch_screen.assert_called_once_with(ScreenName.here)
    app.asyncio_loop.call_soon_threadsafe.assert_called_once_with(
        app.ssh_server_config_ready.set
    )
    schedule_once.assert_called_once()

    scheduled_callback = schedule_once.call_args[0][0]
    scheduled_callback(None)
    screen.update.assert_called_once()


@pytest.mark.asyncio
async def test_run_app_cancels_server_when_app_finishes(mocker):
    server_cancelled = asyncio.Event()

    async def fake_run_ssh_server(_app):
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            server_cancelled.set()
            raise

    async def fake_async_run_app():
        return None

    app = PythonHereApp()
    app.async_run_app = fake_async_run_app
    mocker.patch("main.run_ssh_server", fake_run_ssh_server)

    await app.run_app()

    assert server_cancelled.is_set()


@pytest.mark.asyncio
async def test_run_app_cancels_app_and_propagates_server_error(mocker):
    app_cancelled = asyncio.Event()

    async def fake_run_ssh_server(_app):
        raise RuntimeError("server failed")

    async def fake_async_run_app():
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            app_cancelled.set()
            raise

    app = PythonHereApp()
    app.async_run_app = fake_async_run_app
    mocker.patch("main.run_ssh_server", fake_run_ssh_server)

    with pytest.raises(RuntimeError, match="server failed"):
        await app.run_app()

    assert app_cancelled.is_set()
