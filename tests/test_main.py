import asyncio
from pathlib import Path

from asyncssh import PermissionDenied
import pytest

from main import PythonHereApp
from version_here import __version__


def test_dev_version_is_set():
    assert __version__ == "0.0.0"


@pytest.mark.asyncio
async def test_starting_server_screen_shown(app_instance):
    app_instance.root.ids.here_screen_manager.update()
    assert app_instance.root.ids.here_screen_manager.current == "starting_server"


@pytest.mark.asyncio
async def test_code_line_executed(capfd, app_instance, there):
    await there.runcode("print('hello there')")
    app_instance.on_ssh_connection_made.assert_called_once()
    assert capfd.readouterr().out == "hello there\n"


@pytest.mark.asyncio
async def test_connect_with_wrong_password(capfd, app_instance,
                                           there_with_wrong_password):
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
    await there.runcode('print(root)')
    captured = capfd.readouterr()
    assert captured.out.startswith('<ui_here.layout_here.RootLayout object ')


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
async def test_cancel_all_tasks():

    async def coro():
        pass

    task = asyncio.ensure_future(coro())
    app = PythonHereApp()
    assert not task.cancelled()

    await app.cancel_asyncio_tasks()

    assert task.cancelled()

