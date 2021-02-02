"""PythonHere app."""
import asyncio
import os
from pathlib import Path
import sys
import threading
from typing import Any, Dict

from kivy.app import App
from kivy.config import Config, ConfigParser
from kivy.logger import Logger

from enum_here import ScreenName, ServerState
from exception_manager_here import install_exception_handler
from patches_here import monkeypatch_kivy
from server_here import run_ssh_server
from window_here import reset_window_environment

monkeypatch_kivy()


class PythonHereApp(App):
    """PythonHere main app."""

    def __init__(self):
        super().__init__()
        self.server_task = None
        self.settings = None
        self.ssh_server_config_ready = asyncio.Event()
        self.ssh_server_started = asyncio.Event()
        self.ssh_server_connected = asyncio.Event()
        self.ssh_server_namespace = {}
        self.icon = "data/logo/logo-32.png"

    @property
    def upload_dir(self) -> str:
        """Path to the directory to use for uploaded data."""
        root_dir = Path(self.user_data_dir or ".").resolve()
        upload_dir = Path(root_dir) / "upload"
        upload_dir.mkdir(exist_ok=True)
        return str(upload_dir)

    @property
    def config_path(self) -> str:
        """Path to the application config file."""
        root_dir = Path(self.user_data_dir or ".").resolve()
        return str(root_dir / "config.ini")

    def load_config(self) -> ConfigParser:
        """Returning the application configuration."""
        Config.read(self.config_path)  # Override the configuration file location
        return super().load_config()

    def build(self):
        """Initialize application UI."""
        super().build()
        install_exception_handler()

        self.settings = self.root.ids.settings

        self.ssh_server_namespace.update(
            {
                "app": self,
                "root": self.root,
            }
        )
        self.update_server_config_status()

    def run_app(self):
        """Run application and SSH server tasks."""
        self.ssh_server_started = asyncio.Event()
        self.server_task = asyncio.ensure_future(run_ssh_server(self))
        return asyncio.gather(self.async_run_app(), self.server_task)

    async def async_run_app(self):
        """Run app asynchronously."""
        try:
            await self.async_run(async_lib="asyncio")
            Logger.info("PythonHere: async run completed")
        except asyncio.CancelledError:
            Logger.info("PythonHere: app main task canceled")
        except Exception as exc:
            Logger.exception(exc)

        if self.server_task:
            self.server_task.cancel()

        if self.get_running_app():
            self.stop()

        await self.cancel_asyncio_tasks()

    async def cancel_asyncio_tasks(self):
        """Cancel all asyncio tasks."""
        tasks = [
            task for task in asyncio.all_tasks() if task is not asyncio.current_task()
        ]
        if tasks:
            for task in tasks:
                task.cancel()
            await asyncio.wait(tasks, timeout=1)

    def update_server_config_status(self):
        """Check and update value of the `ssh_server_config_ready`, update screen."""

        def update():
            if all(self.get_pythonhere_config().values()):
                self.ssh_server_config_ready.set()
            screen.update()

        screen = self.root.ids.here_screen_manager
        screen.current = ServerState.starting_server
        self.root.switch_screen(ScreenName.here)
        threading.Thread(name="update_server_config_status", target=update).start()

    def get_pythonhere_config(self):
        """Return user settings for SSH server."""
        return self.settings.get_pythonhere_config()

    def update_ssh_server_namespace(self, namespace: Dict[str, Any]):
        """Update SSH server namespace."""
        self.ssh_server_namespace.update(namespace)

    def on_start(self):
        """App start handler."""
        Logger.info("PythonHere: app started")

    def on_stop(self):
        """App stop handler."""
        Logger.info("PythonHere: app stopped")

    def on_pause(self):
        """Pause mode request handler."""
        return True

    def on_ssh_connection_made(self):
        """New authenticated SSH client connected handler."""
        Logger.info("PythonHere: new SSH client connected")
        if not self.ssh_server_connected.is_set():
            self.ssh_server_connected.set()
            Logger.info("PythonHere: reset window environment")
            self.ssh_server_namespace["root"] = reset_window_environment()
            self.chdir(self.upload_dir)

    def chdir(self, path: str):
        """Changes the working directory."""
        Logger.info("PythonHere: change working directory to %s", path)
        os.chdir(path)
        sys.path.insert(0, path)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(PythonHereApp().run_app())
    loop.close()
