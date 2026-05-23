import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from server_here import PythonHereServer, run_ssh_server


def make_app(mocker):
    app = SimpleNamespace()
    app.upload_dir = "/tmp/pythonhere-upload"
    app.ssh_server_config_ready = asyncio.Event()
    app.ssh_server_started = asyncio.Event()
    app.ssh_server_namespace = {}
    app.get_pythonhere_config = mocker.Mock(
        return_value={"username": "here", "password": "there", "port": 8022}
    )
    return app


def test_pythonhere_server_auth_completed_notifies_app(mocker):
    app = mocker.Mock()
    mocker.patch("server_here.App.get_running_app", return_value=app)
    auth_completed = mocker.patch(
        "server_here.SSHServerHere.auth_completed", autospec=True
    )
    server = PythonHereServer("here", "there", mocker.Mock())

    server.auth_completed()

    auth_completed.assert_called_once_with(server)
    app.on_ssh_connection_made.assert_called_once_with()


@pytest.mark.asyncio
async def test_run_ssh_server_returns_when_cancelled_waiting_for_config(mocker):
    app = make_app(mocker)

    task = asyncio.create_task(run_ssh_server(app))
    await asyncio.sleep(0)
    task.cancel()

    await task
    assert task.done()


@pytest.mark.asyncio
async def test_run_ssh_server_clears_config_ready_after_start_error(mocker):
    app = make_app(mocker)
    app.ssh_server_config_ready.set()
    start_error = RuntimeError("cannot start")
    start_server = mocker.patch("server_here.start_server", side_effect=start_error)
    show_exception_popup = mocker.patch("server_here.show_exception_popup")

    task = asyncio.create_task(run_ssh_server(app))
    await asyncio.sleep(0)
    task.cancel()

    await task
    start_server.assert_called_once()
    config = start_server.call_args.args[0]
    assert config.host == ""
    assert config.chroot == app.upload_dir
    assert config.key_path == Path("./key.rsa").resolve()
    assert not app.ssh_server_config_ready.is_set()
    show_exception_popup.assert_called_once_with(start_error)


@pytest.mark.asyncio
async def test_run_ssh_server_reports_wait_closed_error(mocker):
    class BrokenServer:
        async def wait_closed(self):
            raise RuntimeError("server failed")

    app = make_app(mocker)
    app.ssh_server_config_ready.set()
    start_server = mocker.patch("server_here.start_server", return_value=BrokenServer())
    show_exception_popup = mocker.patch("server_here.show_exception_popup")

    await run_ssh_server(app)

    start_server.assert_called_once()
    assert app.ssh_server_started.is_set()
    exception = show_exception_popup.call_args.args[0]
    assert isinstance(exception, RuntimeError)
    assert str(exception) == "server failed"
