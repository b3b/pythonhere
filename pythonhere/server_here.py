"""SSH server."""
import asyncio
from pathlib import Path

from kivy.app import App
from kivy.logger import Logger
from herethere.here.server import SSHServerHere, ServerConfig, start_server

from exception_manager_here import show_exception_popup


class PythonHereServer(SSHServerHere):
    """SSH server protocol handler."""

    def auth_completed(self):
        """Authentication was completed successfully."""
        super().auth_completed()
        App.get_running_app().on_ssh_connection_made()


async def run_ssh_server(app):
    """Start and run SSH server."""
    Logger.debug("PythonHere: wait for %here settings")
    try:
        await app.ssh_server_config_ready.wait()
    except asyncio.CancelledError:
        return

    config = ServerConfig(
        host="",
        chroot=app.upload_dir,
        key_path=Path("./key.rsa").resolve(),
        **app.get_pythonhere_config(),
    )

    try:
        server = await start_server(
            config, namespace=app.ssh_server_namespace, server_factory=PythonHereServer
        )
        app.ssh_server_started.set()
    except Exception as exc:
        Logger.error("PythonHere: SSH server start error")
        Logger.exception(exc)
        show_exception_popup(exc)
        return

    try:
        await server.wait_closed()
    except asyncio.CancelledError:
        Logger.info("PythonHere: SSH server task canceled")
        await server.stop()
    except Exception as exc:
        Logger.errror("PythonHere: SSH server stop by exception")
        Logger.exception(exc)
        show_exception_popup(exc)
    Logger.info("PythonHere: SSH server closed")
