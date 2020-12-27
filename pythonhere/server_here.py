"""SSH server."""
import asyncio
from pathlib import Path

from kivy.app import App
from kivy.logger import Logger
from herethere.here.server import SSHServerHere, ServerConfig, start_server


class PythonHereServer(SSHServerHere):
    """SSH server protocol handler."""

    def connection_made(self, *args, **kwargs):
        """Called when a channel is opened successfully."""
        super().connection_made(*args, **kwargs)
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
        raise

    try:
        await server.wait_closed()
    except asyncio.CancelledError:
        Logger.info("PythonHere: SSH server task canceled")
        await server.stop()
    except Exception as exc:
        Logger.errror("PythonHere: SSH server stop by exception")
        Logger.exception(exc)
        raise
    Logger.info("PythonHere: SSH server closed")
