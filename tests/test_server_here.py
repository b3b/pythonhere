import asyncio
from pathlib import Path
from types import SimpleNamespace

import asyncssh
import pytest
from herethere.everywhere import ConnectionConfig
from herethere.there.client import Client
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
    assert config.sftp_root == app.upload_dir
    assert config.key_path == Path("./ssh_host_key").resolve()
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


@pytest.mark.asyncio
async def test_new_host_key_is_ed25519_and_legacy_key_is_untouched(
    mocker, monkeypatch, tmp_path, unused_tcp_port
):
    legacy_key = tmp_path / "key.rsa"
    legacy_contents = b"legacy key sentinel\n"
    legacy_key.write_bytes(legacy_contents)
    monkeypatch.chdir(tmp_path)

    app = make_app(mocker)
    app.upload_dir = str(tmp_path)
    app.get_pythonhere_config.return_value = {
        "username": "here",
        "password": "there",
        "port": unused_tcp_port,
    }
    app.ssh_server_config_ready.set()
    running_app = SimpleNamespace(on_ssh_connection_made=mocker.Mock())
    mocker.patch("server_here.App.get_running_app", return_value=running_app)

    server_task = asyncio.create_task(run_ssh_server(app))
    client = Client()
    connection_config = ConnectionConfig(
        host="localhost",
        port=unused_tcp_port,
        username="here",
        password="there",
    )

    try:
        await asyncio.wait_for(app.ssh_server_started.wait(), 5)
        await client.connect(connection_config)

        host_key = tmp_path / "ssh_host_key"
        assert asyncssh.read_private_key(host_key).get_algorithm() == "ssh-ed25519"
        assert legacy_key.read_bytes() == legacy_contents
        running_app.on_ssh_connection_made.assert_called_once_with()
    finally:
        await client.disconnect()
        server_task.cancel()
        await server_task
